import logging
import tempfile
import os
import json
import time
from aiogram import Router, types, F
from aiogram.enums import ChatAction
from aiogram.fsm.context import FSMContext
from bot.services.elevenlabs import TextToSpeechService
from bot.config import Config
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, FSInputFile
from bot.messages_en import Messages as MessagesEn
from bot.messages import Messages as MessagesRu
import openai

# Create router for question handling
question_router = Router()

def get_proper_title(content_type, original_title):
    """Get proper title from config files based on content type and original title"""
    try:
        # Map content_type to config file
        config_files = {
            'text': 'text_descriptions.json',
            'video': 'video_descriptions.json', 
            'podcast': 'podcast_descriptions.json',
            'audio': 'podcast_descriptions.json',  # Use podcast config for audio
            'url': 'url_descriptions.json'
        }
        
        config_file = config_files.get(content_type)
        if not config_file:
            return original_title
            
        # Load config file
        config_path = os.path.join(os.path.dirname(__file__), '..', 'configs', config_file)
        if not os.path.exists(config_path):
            return original_title
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            
        # Find matching entry in config
        content_key = 'texts' if content_type == 'text' else 'videos'
        if content_key in config_data and original_title in config_data[content_key]:
            return config_data[content_key][original_title]['name']
            
        return original_title
        
    except Exception as e:
        logging.warning(f"Error getting proper title: {e}")
        return original_title

# In-memory storage for pagination (in production, use Redis or database)
user_pagination_data = {}

async def transcribe_voice_cloud(message: types.Message) -> str:
    """Transcribe voice message using OpenAI Whisper API"""
    # Get the file
    file_id = message.voice.file_id if message.voice else message.audio.file_id
    file = await message.bot.get_file(file_id)
    
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
            await message.bot.download_file(file.file_path, temp_file.name)
            
            # Use OpenAI Whisper API for transcription (v1.0+ syntax)
            client = openai.AsyncOpenAI()
            with open(temp_file.name, 'rb') as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ru"
                )
            
            return transcript.text.strip()
            
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@question_router.message(F.text | F.voice | F.audio)
async def handle_user_question(message: types.Message, state: FSMContext, supabase_client):
    """Handle user questions with RAG pipeline"""
    # Extract text from message (text or voice)
    user_text = None
    
    if message.text:
        user_text = message.text
    elif message.voice or message.audio:
        # Show processing message for voice
        processing_voice_message = await message.answer(Messages.QUESTION_CMD["voice_processing"])
        
        try:
            user_text = await transcribe_voice_cloud(message)
            await processing_voice_message.delete()
            
            if not user_text or user_text.strip() == "":
                await message.answer("Could not recognize speech. Please try again or send a text message.")
                return
                
        except Exception as e:
            logging.error(f"Error transcribing voice: {e}")
            await processing_voice_message.edit_text("Error transcribing voice message. Please try again.")
            return
    else:
        await message.answer("Please send a text or voice message with your request.")
        return
    
    processing_message = None

    try:
        # Get user from database to determine language
        user = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await message.answer("Ошибка: пользователь не найден. Попробуйте команду /start")
            return

        # Determine user language and get appropriate messages
        user_language = user.language if user and hasattr(user, 'language') and user.language else 'en'
        messages_class = MessagesRu if user_language == 'ru' else MessagesEn

        # Show processing message in user's language
        processing_message = await message.answer(messages_class.RAG_RESPONSES["processing"])

        # Send typing action
        await message.bot.send_chat_action(
            chat_id=message.from_user.id,
            action=ChatAction.TYPING
        )

        # STEP 1: ChatGPT Recommendations with localized prompt
        client = openai.AsyncOpenAI()

        # Use localized prompt based on user language
        chatgpt_prompt = messages_class.RAG_PROMPT

        chatgpt_response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": chatgpt_prompt},
                {"role": "user", "content": f"Automation task: {user_text}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        chatgpt_text = chatgpt_response.choices[0].message.content
        
        # STEP 2: Vector Similarity Search for Similar Automations
        similar_automations = []
        keyboard = None
        
        try:
            # Generate embedding for the user query
            embedding_response = await client.embeddings.create(
                input=user_text,
                model="text-embedding-3-large"
            )
            query_embedding = embedding_response.data[0].embedding
            
            # Search for similar automations in the database
            search_results = await supabase_client.search_automations_by_similarity(
                query_embedding=query_embedding,
                limit=3
            )
            
            if search_results:
                similar_automations = search_results
                
                # Create inline keyboard with similar automations (no header button)
                keyboard_buttons = []
                
                for i, automation in enumerate(similar_automations[:3]):
                    button_text = f"⚙️ {automation.get('title', 'Automation')[:40]}..."
                    keyboard_buttons.append([InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"automation_detail_{automation.get('id')}"
                    )])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
                
        except Exception as vector_error:
            logger.error(f"Vector search failed: {vector_error}")
            # Continue without similar automations if vector search fails
        
        # Combine responses
        response_text = final_response = chatgpt_text
        
        if similar_automations:
            final_response += f"\n\n🔍 **Found {len(similar_automations)} similar automations in our database**\n"
            final_response += "Click the buttons below to explore specific examples:"
            response_text = final_response
        
        # Check if user prefers audio responses
        if user.isAudio:
            try:
                # Generate audio using ElevenLabs
                logging.info(f"🎧 Generating audio response for user {message.from_user.id}")
                tts_service = TextToSpeechService()
                
                # Generate audio file (use only ChatGPT response for audio, not buttons)
                audio_path = tts_service.text_to_speech(
                    text=chatgpt_text,  # Only ChatGPT text for audio
                    quality_preset="conversational",  # Good for bot responses
                    output_filename=f"response_{message.from_user.id}_{int(time.time())}.mp3"
                )
                
                # Send audio file
                audio_file = FSInputFile(audio_path)
                await processing_message.delete()  # Delete processing message
                
                if keyboard:
                    # Send audio with sources buttons
                    await message.answer_audio(
                        audio=audio_file,
                        reply_markup=keyboard,
                        caption="🎧 Аудиоответ"
                    )
                else:
                    # Send audio without buttons
                    await message.answer_audio(
                        audio=audio_file,
                        caption="🎧 Аудиоответ"
                    )
                
                # Clean up audio file
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass  # File cleanup failed, but not critical
                
                logging.info(f"✅ Successfully sent audio response to user {message.from_user.id}")
                return
                
            except Exception as audio_error:
                logging.error(f"⚠️ Audio generation failed, falling back to text: {audio_error}")
                # Fall back to text response if audio generation fails
        
        # Send text response (either user prefers text or audio generation failed)
        logging.info(f"📤 RAG Step 5: Response Formatting - Sending final response (length: {len(response_text)} chars)")
        try:
            await processing_message.edit_text(response_text, reply_markup=keyboard, parse_mode="Markdown")
            logging.info(f"✅ RAG Step 5: Response Formatting - Successfully sent response with Markdown")
        except Exception as markdown_error:
            # Fallback: send without markdown if parsing fails
            logging.warning(f"⚠️ RAG Step 5: Response Formatting - Markdown parsing failed, sending as plain text: {markdown_error}")
            await processing_message.edit_text(response_text, reply_markup=keyboard)
            logging.info(f"✅ RAG Step 5: Response Formatting - Successfully sent response as plain text")
        
    except Exception as e:
        logging.error(f"❌ RAG Pipeline: Fatal error processing question for user {message.from_user.id}: {e}")
        await processing_message.edit_text(Messages.QUESTION_CMD["error"])



