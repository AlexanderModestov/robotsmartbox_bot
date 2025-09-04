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
import openai

# Create routers for question handling
question_router = Router()
query_router = Router()

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
        processing_voice_message = await message.answer("🎤 Распознаю голосовое сообщение...")
        
        try:
            user_text = await transcribe_voice_cloud(message)
            await processing_voice_message.delete()
            
            if not user_text or user_text.strip() == "":
                await message.answer("Не удалось распознать речь. Попробуйте еще раз или отправьте текстовое сообщение.")
                return
                
        except Exception as e:
            logging.error(f"Error transcribing voice: {e}")
            await processing_voice_message.edit_text("Ошибка при распознавании голосового сообщения. Попробуйте еще раз.")
            return
    else:
        await message.answer("Пожалуйста, отправьте текстовое или голосовое сообщение с вашим запросом.")
        return
    
    # Show processing message
    processing_message = await message.answer("🤔 Обрабатываю ваш вопрос...")

        # Send typing action
    await message.bot.send_chat_action(
        chat_id=message.from_user.id, 
        action=ChatAction.TYPING
    )
    
    try:
        # Get user from database
        user = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        if not user:
            await processing_message.edit_text("Ошибка: пользователь не найден. Попробуйте команду /start")
            return
        
        # Create OpenAI client and call API with n8n automation expert prompt
        client = openai.AsyncOpenAI()
        
        n8n_prompt = """Ты эксперт по автоматизации n8n. Отвечай ТОЛЬКО на вопросы об автоматизации задач и процессов.

ВАЖНО: Если вопрос НЕ связан с автоматизацией задач, процессов или рабочих потоков, отвечай ТОЧНО: "Я не знаю ответ на Ваш вопрос. Я могу предложить только варианты по автоматизации."

Для вопросов об автоматизации предоставь краткий ответ с этими 3 разделами:

Формат ответа:
🤖 Решение для автоматизации n8n (2-3 предложения)
Опиши точно, как автоматизировать эту задачу, используя узлы и рабочие процессы n8n.

✅ Преимущества (3 пункта)
• Экономия времени: [конкретные часы/неделю сэкономлены]
• Снижение ошибок: [% улучшение]
• Масштабируемость: [потенциал роста]

💰 Экономия средств (1-2 предложения)
Рассчитай примерную месячную экономию в долларах на основе почасовых ставок и сэкономленного времени.

Правила:
- Не указывай конкретные названия узлов n8n, используй только описание
- Используй числа и проценты
- Общий ответ не более 150 слов
- Сосредоточься только на самой эффективной автоматизации
- Предполагай стоимость труда $25/час для расчетов"""

        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": n8n_prompt},
                {"role": "user", "content": f"Задача для автоматизации: {user_text}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        # No sources needed for this automation response
        keyboard = None
        
        # Check if user prefers audio responses
        if user.isAudio:
            try:
                # Generate audio using ElevenLabs
                logging.info(f"🎧 Generating audio response for user {message.from_user.id}")
                tts_service = TextToSpeechService()
                
                # Generate audio file
                audio_path = tts_service.text_to_speech(
                    text=response_text,
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
        await processing_message.edit_text(
            "Произошла ошибка при обработке вашего вопроса. Попробуйте еще раз или обратитесь к администратору."
        )


