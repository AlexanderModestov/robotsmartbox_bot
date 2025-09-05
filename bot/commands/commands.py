import logging
import os
import json
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from bot.messages import Messages
from bot.messages_en import Messages as MessagesEn
from bot.config import Config

def get_user_language(message):
    """Detect user language from message or user settings"""
    # Check user's language code first
    if hasattr(message.from_user, 'language_code') and message.from_user.language_code:
        if message.from_user.language_code.startswith('en'):
            return 'en'
    
    # Check message text for English keywords
    if message.text:
        english_keywords = ['start', 'help', 'about', 'settings', 'hello', 'hi']
        text_lower = message.text.lower()
        for keyword in english_keywords:
            if keyword in text_lower:
                return 'en'
    
    # Default to English
    return 'en'

def get_messages_class(language='en'):
    """Get appropriate messages class based on language - defaults to English"""
    return Messages if language == 'ru' else MessagesEn

# States for FSM
class UserState(StatesGroup):
    help = State()
    waiting_for_question = State()

# Create routers for commands
start_router = Router()
content_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: types.Message, supabase_client):
    """Start command handler"""
    user_name = message.from_user.first_name
    
    # Detect user language and get appropriate messages
    user_language = get_user_language(message)
    messages_class = get_messages_class(user_language)
    
    await message.answer(messages_class.START_CMD["welcome"](user_name))
    
    try:
        # Register user in Supabase
        await supabase_client.create_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name
        )
    except Exception as e:
        logging.warning(f"User registration error: {e}")

@start_router.message(Command("about"))
async def about(message: types.Message):
    """About command handler"""
    # Detect user language and get appropriate messages
    user_language = get_user_language(message)
    messages_class = get_messages_class(user_language)
    
    await message.answer(
        messages_class.ABOUT_MESSAGE,
        parse_mode="Markdown"
    )

@content_router.message(Command('automatizations'))
async def list_automatizations(message: types.Message, supabase_client):
    """Show automatization examples with categories from Supabase"""
    try:
        # Fetch categories from categories table
        response = supabase_client.client.table('categories').select('id, name').order('name').execute()
        
        categories = []
        if response.data:
            categories = response.data[:8]  # Limit to 8 categories to avoid keyboard size issues
        
        # Create keyboard with categories
        keyboard_buttons = []
        
        # Add "All automatizations" button first
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        keyboard_buttons.append([
            InlineKeyboardButton(text=messages_class.AUTOMATIONS_CMD["all_automations_button"], callback_data="automations_all")
        ])
        
        # Add category buttons
        for category in categories:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⚙️ {category['name']}", callback_data=f"automation_cat_{category['id']}")
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Log the command access
        print(f"🤖 Automatizations command: User {message.from_user.id} ({message.from_user.username}) accessing automatization examples")
        logging.info(f"Automatizations command: User {message.from_user.id} accessing automatization examples")
        
        # Get appropriate welcome text from messages
        automation_text = messages_class.AUTOMATIONS_CMD["welcome"]
        
        await message.answer(
            automation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in list_automatizations: {e}")
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        await message.answer(messages_class.AUTOMATIONS_CMD["loading_error"])

@content_router.message(Command('booking'))
async def schedule_command(message: types.Message):
    """Handle booking command with Calendly webapp"""
    try:
        # Get messages based on user language (defaults to English)
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        
        # Create Calendly webapp button
        calendly_button = InlineKeyboardButton(
            text=messages_class.BOOKING_CMD["button_text"],
            web_app=WebAppInfo(url=Config.CALENDLY_LINK)
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[calendly_button]])
        
        # Log the booking access
        print(f"📅 Booking command: User {message.from_user.id} ({message.from_user.username}) accessing booking webapp")
        logging.info(f"Booking command: User {message.from_user.id} accessing booking webapp")
        
        message_text = messages_class.BOOKING_CMD["title"] + messages_class.BOOKING_CMD["description"]
        
        await message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in schedule_command: {e}")
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        await message.answer(messages_class.BOOKING_CMD["loading_error"])

@content_router.message(Command('pay'))
async def pay_command(message: types.Message):
    """Handle payment command with Stripe webapp"""
    try:
        # Get messages based on user language (defaults to English)
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        
        # Create Stripe payment webapp button
        stripe_button = InlineKeyboardButton(
            text=messages_class.PAY_CMD["button_text"],
            web_app=WebAppInfo(url=Config.STRIPE_PAYMENT_LINK)
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[stripe_button]])
        
        # Log the payment access
        print(f"💳 Pay command: User {message.from_user.id} ({message.from_user.username}) accessing payment webapp")
        logging.info(f"Pay command: User {message.from_user.id} accessing payment webapp")
        
        message_text = messages_class.PAY_CMD["title"] + messages_class.PAY_CMD["description"]
        
        await message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in pay_command: {e}")
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        await message.answer(messages_class.PAY_CMD["loading_error"])

@content_router.message(Command('subscribe'))
async def subscribe_command(message: types.Message):
    """Handle subscription command"""
    await message.answer(
        "⚙️ Функционал подписки в разработке и скоро будет доступен!\n\n"
        "В будущем оформив подписку, Вы получите безлимитный доступ к материалам.", 
        parse_mode="HTML"
    )

@content_router.message(Command('settings'))
async def settings_command(message: types.Message, supabase_client):
    """Settings command handler"""
    try:
        # Get current user settings from database
        user = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        
        if user:
            audio_status = "🔊 Аудио" if user.isAudio else "📝 Текст"
            notif_status = "🔔 Включены" if user.notification else "🔕 Отключены"
            
            # Dynamic buttons based on current settings
            if user.isAudio:
                format_button_text = "📝 Выбрать текстовые ответы"
                format_callback = "format_text"
            else:
                format_button_text = "🎧 Выбрать аудиоответы"
                format_callback = "format_audio"
            
            if user.notification:
                notif_button_text = "🔕 Отключить уведомления"
                notif_callback = "notifications_off"
            else:
                notif_button_text = "🔔 Включить уведомления"
                notif_callback = "notifications_on"
        else:
            audio_status = "📝 Текст"
            notif_status = "🔕 Отключены"
            format_button_text = "🎧 Выбрать аудиоответы"
            format_callback = "format_audio"
            notif_button_text = "🔔 Включить уведомления"
            notif_callback = "notifications_on"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=format_button_text, callback_data=format_callback)],
            [InlineKeyboardButton(text=notif_button_text, callback_data=notif_callback)]
        ])
        
        settings_text = (
            "⚙️ <b>Настройки</b>\n\n"
            "<b>Текущие настройки:</b>\n"
            f"💬 Формат ответов: {audio_status}\n"
            f"🔔 Уведомления: {notif_status}\n\n"
            "Выберите действие:"
        )
        
        await message.answer(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in settings command: {e}")
        await message.answer("Произошла ошибка при загрузке настроек")



@content_router.callback_query(lambda c: c.data == 'setting_quiz')
async def setting_quiz(callback_query: types.CallbackQuery):
    """Handle quiz setting"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Начать квиз", callback_data="start_quiz")],
        [InlineKeyboardButton(text="📊 Мои результаты", callback_data="quiz_results")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_settings")]
    ])
    
    await callback_query.message.edit_text(
        "📝 <b>Прохождение квиза по темам эфира</b>\n\nПроверьте свои знания по темам эфира:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@content_router.callback_query(lambda c: c.data == 'back_to_settings')
async def back_to_settings(callback_query: types.CallbackQuery, supabase_client):
    """Go back to main settings menu"""
    try:
        # Get current user settings from database
        user = await supabase_client.get_user_by_telegram_id(callback_query.from_user.id)
        
        if user:
            audio_status = "🔊 Аудио" if user.isAudio else "📝 Текст"
            notif_status = "🔔 Включены" if user.notification else "🔕 Отключены"
            
            # Dynamic buttons based on current settings
            if user.isAudio:
                format_button_text = "📝 Выбрать текстовые ответы"
                format_callback = "format_text"
            else:
                format_button_text = "🎧 Выбрать аудиоответы"
                format_callback = "format_audio"
            
            if user.notification:
                notif_button_text = "🔕 Отключить уведомления"
                notif_callback = "notifications_off"
            else:
                notif_button_text = "🔔 Включить уведомления"
                notif_callback = "notifications_on"
        else:
            audio_status = "📝 Текст"
            notif_status = "🔕 Отключены"
            format_button_text = "🎧 Выбрать аудиоответы"
            format_callback = "format_audio"
            notif_button_text = "🔔 Включить уведомления"
            notif_callback = "notifications_on"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=format_button_text, callback_data=format_callback)],
            [InlineKeyboardButton(text=notif_button_text, callback_data=notif_callback)]
        ])
        
        settings_text = (
            "⚙️ <b>Настройки</b>\n\n"
            "<b>Текущие настройки:</b>\n"
            f"💬 Формат ответов: {audio_status}\n"
            f"🔔 Уведомления: {notif_status}\n\n"
            "Выберите действие:"
        )
        
        try:
            await callback_query.message.edit_text(
                settings_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        except Exception as edit_error:
            # Handle case when message content is the same (Telegram error)
            if "message is not modified" in str(edit_error):
                # Message content is identical, just acknowledge the callback
                pass
            else:
                # Re-raise other errors
                raise edit_error
    except Exception as e:
        logging.error(f"Error in back_to_settings: {e}")
        await callback_query.answer("Произошла ошибка при загрузке настроек")

@content_router.callback_query(lambda c: c.data in ['format_text', 'format_audio'])
async def handle_format_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle response format selection"""
    is_audio = callback_query.data == 'format_audio'
    format_type = "аудио" if is_audio else "текстовом"
    
    try:
        # Save user preference to database
        user_data = {
            'telegram_id': callback_query.from_user.id,
            'isAudio': is_audio
        }
        
        await supabase_client.create_or_update_user(user_data)
        
        # Show brief confirmation and redirect back to settings
        await callback_query.answer(f"✅ Формат изменен на {format_type}")
        
        # Redirect back to settings menu
        await back_to_settings(callback_query, supabase_client)
    except Exception as e:
        logging.error(f"Error saving format preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

@content_router.callback_query(lambda c: c.data in ['notifications_on', 'notifications_off'])
async def handle_notifications_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle notifications setting selection"""
    notifications_enabled = callback_query.data == 'notifications_on'
    status = "включены" if notifications_enabled else "отключены"
    
    try:
        # Save notification preference to database
        user_data = {
            'telegram_id': callback_query.from_user.id,
            'notification': notifications_enabled
        }
        
        await supabase_client.create_or_update_user(user_data)
        
        # Show brief confirmation and redirect back to settings
        await callback_query.answer(f"✅ Уведомления {status}")
        
        # Redirect back to settings menu
        await back_to_settings(callback_query, supabase_client)
    except Exception as e:
        logging.error(f"Error saving notification preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

@content_router.callback_query(lambda c: c.data.startswith('quiz_page_'))
async def handle_quiz_pagination(callback_query: types.CallbackQuery):
    """Handle quiz pagination"""
    try:
        # Extract page number from callback data
        page = int(callback_query.data.replace('quiz_page_', ''))
        
        # Show quiz topics for the requested page
        await show_quiz_topics(callback_query.message, page=page, edit_message=True)
        
        # Answer callback query
        await callback_query.answer()
        
    except Exception as e:
        logging.error(f"Error in handle_quiz_pagination: {e}")
        await callback_query.answer("Ошибка при навигации по страницам")

@content_router.callback_query(lambda c: c.data in ['start_quiz', 'quiz_results'])
async def handle_quiz_actions(callback_query: types.CallbackQuery):
    """Handle quiz actions"""
    if callback_query.data == 'start_quiz':
        await callback_query.message.edit_text(
            "🎯 <b>Квиз в разработке</b>\n\n"
            "Функционал квиза по темам эфира скоро будет доступен!\n"
            "Следите за обновлениями.",
            parse_mode="HTML"
        )
    else:  # quiz_results
        await callback_query.message.edit_text(
            "📊 <b>Результаты квиза</b>\n\n"
            "У вас пока нет результатов квизов.\n"
            "Пройдите квиз, чтобы увидеть свои достижения!",
            parse_mode="HTML"
        )

@content_router.callback_query(lambda c: c.data == 'materials_web_app')
async def handle_materials_web_app(callback_query: types.CallbackQuery):
    """Handle web app materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}"
        webapp_button = InlineKeyboardButton(
            text="🌐 Открыть Web App",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "🌐 <b>Web App</b>\n\n"
            "Интерактивные материалы и приложения для обучения.\n"
            "Нажмите кнопку ниже для доступа к веб-приложению:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_web_app: {e}")
        await callback_query.answer("Ошибка при загрузке веб-приложения")

@content_router.callback_query(lambda c: c.data == 'materials_videos')
async def handle_materials_videos(callback_query: types.CallbackQuery):
    """Handle videos materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}/videos"
        webapp_button = InlineKeyboardButton(
            text="🎥 Открыть видео",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "🎥 <b>Videos</b>\n\n"
            "Видеоуроки, записи лекций и обучающие материалы.\n"
            "Нажмите кнопку ниже для просмотра видеоматериалов:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_videos: {e}")
        await callback_query.answer("Ошибка при загрузке видео")

@content_router.callback_query(lambda c: c.data == 'materials_texts')
async def handle_materials_texts(callback_query: types.CallbackQuery):
    """Handle texts materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}/texts"
        webapp_button = InlineKeyboardButton(
            text="📝 Открыть тексты",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "📝 <b>Texts</b>\n\n"
            "Статьи, конспекты, учебные материалы и документация.\n"
            "Нажмите кнопку ниже для доступа к текстовым материалам:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_texts: {e}")
        await callback_query.answer("Ошибка при загрузке текстов")

@content_router.callback_query(lambda c: c.data == 'materials_podcasts')
async def handle_materials_podcasts(callback_query: types.CallbackQuery):
    """Handle podcasts materials selection"""
    try:
        webapp_url = f"{Config.WEBAPP_URL}/podcasts"
        webapp_button = InlineKeyboardButton(
            text="🎧 Открыть подкасты",
            web_app=WebAppInfo(url=webapp_url)
        )
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[webapp_button]])
        
        await callback_query.message.edit_text(
            "🎧 <b>Podcasts</b>\n\n"
            "Аудиоматериалы, подкасты и записи обсуждений.\n"
            "Нажмите кнопку ниже для прослушивания подкастов:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in materials_podcasts: {e}")
        await callback_query.answer("Ошибка при загрузке подкастов")

@content_router.callback_query(lambda c: c.data == 'automations_all')
async def handle_automations_all(callback_query: types.CallbackQuery, supabase_client):
    """Handle all automatizations selection"""
    try:
        # Fetch all automation documents with their categories via proper joins
        response = supabase_client.client.table('documents').select('''
            id, url, short_description, filename,
            automations!inner(
                categories!inner(name)
            )
        ''').limit(10).execute()
        
        # Default to English for callbacks
        messages_class = get_messages_class('en')
        message_text = messages_class.AUTOMATIONS_CMD["all_automations_header"]
        
        # Create buttons for each automation using short_description as button text
        keyboard_buttons = []
        if response.data:
            for doc in response.data:
                doc_id = doc.get('id')
                short_desc = doc.get('short_description', 'Automation')
                
                # Truncate button text if too long (Telegram limit)
                button_text = short_desc[:60] + "..." if len(short_desc) > 60 else short_desc
                
                keyboard_buttons.append([
                    InlineKeyboardButton(text=button_text, callback_data=f"automation_detail_{doc_id}")
                ])
        
        else:
            message_text += messages_class.AUTOMATIONS_CMD["no_examples_found"]
        
        # Add back button
        keyboard_buttons.append([
            InlineKeyboardButton(text=messages_class.AUTOMATIONS_CMD["back_button"], callback_data="back_to_automations")
        ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_automations_all: {e}")
        messages_class = get_messages_class('en')
        await callback_query.answer(messages_class.AUTOMATIONS_CMD["loading_error"])

@content_router.callback_query(lambda c: c.data.startswith('automation_cat_'))
async def handle_automation_category(callback_query: types.CallbackQuery, supabase_client):
    """Handle specific automation category selection"""
    try:
        category_id = callback_query.data.replace('automation_cat_', '')
        
        # First get the category name
        category_response = supabase_client.client.table('categories').select('name').eq('id', category_id).execute()
        category_name = 'Unknown'
        if category_response.data:
            category_name = category_response.data[0]['name']
        
        # Fetch automation documents for this category using proper joins
        response = supabase_client.client.table('documents').select('''
            id, url, short_description, filename,
            automations!inner(
                categories!inner(name)
            )
        ''').eq('automations.category', category_id).limit(10).execute()
        
        # Default to English for callbacks
        messages_class = get_messages_class('en')
        message_text = messages_class.AUTOMATIONS_CMD["category_header"](category_name)
        
        # Create buttons for each automation using short_description as button text
        keyboard_buttons = []
        if response.data:
            for doc in response.data:
                doc_id = doc.get('id')
                short_desc = doc.get('short_description', 'Automation')
                
                # Truncate button text if too long (Telegram limit)
                button_text = short_desc[:60] + "..." if len(short_desc) > 60 else short_desc
                
                keyboard_buttons.append([
                    InlineKeyboardButton(text=button_text, callback_data=f"automation_detail_{doc_id}")
                ])
        else:
            message_text += messages_class.AUTOMATIONS_CMD["no_examples_in_category"](category_name)
        
        # Add back button
        keyboard_buttons.append([
            InlineKeyboardButton(text=messages_class.AUTOMATIONS_CMD["back_button"], callback_data="back_to_automations")
        ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_automation_category: {e}")
        messages_class = get_messages_class('en')
        await callback_query.answer(messages_class.AUTOMATIONS_CMD["loading_error"])

@content_router.callback_query(lambda c: c.data == 'back_to_automations')
async def handle_back_to_automations(callback_query: types.CallbackQuery, supabase_client):
    """Handle back to automatizations menu"""
    try:
        # Fetch categories from categories table
        response = supabase_client.client.table('categories').select('id, name').order('name').execute()
        
        categories = []
        if response.data:
            categories = response.data[:8]  # Limit to 8 categories to avoid keyboard size issues
        
        # Create keyboard with categories
        keyboard_buttons = []
        
        # Add "All automatizations" button first
        messages_class = get_messages_class('en')  # Default to English for callbacks
        keyboard_buttons.append([
            InlineKeyboardButton(text=messages_class.AUTOMATIONS_CMD["all_automations_button"], callback_data="automations_all")
        ])
        
        # Add category buttons
        for category in categories:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⚙️ {category['name']}", callback_data=f"automation_cat_{category['id']}")
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Use English messages for callback queries by default
        automation_text = messages_class.AUTOMATIONS_CMD["welcome"]
        
        await callback_query.message.edit_text(
            automation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_back_to_automations: {e}")
        messages_class = get_messages_class('en')
        await callback_query.answer(messages_class.AUTOMATIONS_CMD["loading_error"])

@content_router.callback_query(lambda c: c.data.startswith('automation_detail_'))
async def handle_automation_detail(callback_query: types.CallbackQuery, supabase_client):
    """Handle automation detail view - Step 3 of the flow"""
    try:
        automation_id = callback_query.data.replace('automation_detail_', '')
        
        # Fetch specific automation document with full description
        response = supabase_client.client.table('documents').select('''
            id, url, short_description, description, filename,
            automations!inner(
                categories!inner(name)
            )
        ''').eq('id', automation_id).execute()
        
        # Default to English for callbacks
        messages_class = get_messages_class('en')
        
        if response.data and len(response.data) > 0:
            doc = response.data[0]
            
            # Get document details
            filename = doc.get('filename', 'Unnamed').replace('.json', '').replace('-', ' ').title()
            url = doc.get('url', '#')
            description = doc.get('description', doc.get('short_description', 'No description available'))
            
            # Get category name for back navigation
            category_name = 'Uncategorized'
            category_id = None
            if doc.get('automations') and len(doc['automations']) > 0:
                automation_info = doc['automations'][0]
                category_info = automation_info.get('categories')
                if category_info:
                    category_name = category_info.get('name', 'Uncategorized')
                category_id = automation_info.get('category')
            
            # Build message - just show the description
            message_text = messages_class.AUTOMATIONS_CMD["automation_description"](description)
            
            # Create keyboard with action button and navigation
            keyboard_buttons = []
            
            # Get automation button
            keyboard_buttons.append([
                InlineKeyboardButton(text=messages_class.AUTOMATIONS_CMD["get_automation_button"], 
                                   callback_data=f"get_automation_{automation_id}")
            ])
            
            # Back to category button (if we have category_id)
            if category_id:
                keyboard_buttons.append([
                    InlineKeyboardButton(text=messages_class.AUTOMATIONS_CMD["back_to_category"], 
                                       callback_data=f"automation_cat_{category_id}")
                ])
            else:
                # Back to main menu
                keyboard_buttons.append([
                    InlineKeyboardButton(text=messages_class.AUTOMATIONS_CMD["back_button"], 
                                       callback_data="back_to_automations")
                ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback_query.message.edit_text(
                message_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
        else:
            # Automation not found
            await callback_query.answer("Automation not found")
            
    except Exception as e:
        logging.error(f"Error in handle_automation_detail: {e}")
        messages_class = get_messages_class('en')
        await callback_query.answer(messages_class.AUTOMATIONS_CMD["loading_error"])

@content_router.callback_query(lambda c: c.data.startswith('get_automation_'))
async def handle_get_automation(callback_query: types.CallbackQuery, supabase_client):
    """Handle automation request - when user wants to get the automation"""
    try:
        automation_id = callback_query.data.replace('get_automation_', '')
        
        # Log the automation request
        user_id = callback_query.from_user.id
        username = callback_query.from_user.username or "Unknown"
        
        logging.info(f"User {user_id} ({username}) requested automation {automation_id}")
        print(f"🎯 Automation Request: User {user_id} ({username}) wants automation {automation_id}")
        
        # You can add logic here to:
        # 1. Save the request to database
        # 2. Send notification to admin
        # 3. Provide download link
        # 4. Schedule follow-up
        
        # For now, just acknowledge the request
        await callback_query.answer("✅ Request received! We'll contact you soon with automation details.", show_alert=True)
        
    except Exception as e:
        logging.error(f"Error in handle_get_automation: {e}")
        await callback_query.answer("❌ Error processing your request. Please try again.")


@content_router.message(Command('help'))
async def command_request(message: types.Message, state: FSMContext) -> None:
    """Help command - initiate question asking"""
    await message.answer("Пожалуйста, напиши Ваш вопрос в свободной форме и <b>одним сообщением</b>!", parse_mode="HTML")
    await state.set_state(UserState.help)

# Request help - send to admin
@content_router.message(UserState.help)
async def help(message: types.Message, state: FSMContext):
    """Send message to admin"""
    user_mention = f"[{message.from_user.full_name}](tg://user?id={message.from_user.id})"
    await message.answer("Ваше сообщение принято. Ожидайте ответа в течении суток. Спасибо, что вы с нами.")
    await state.clear()
    
    # Send to admin if admin ID is configured
    if Config.TELEGRAM_ADMIN_ID and Config.TELEGRAM_ADMIN_ID != 0:
        try:
            await message.bot.send_message(
                chat_id=Config.TELEGRAM_ADMIN_ID,
                text=f"Пользователь {user_mention} спрашивает:\n\n{message.text}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Error sending message to admin: {e}")

# ===============================
# AUTOMATION COMMANDS
# ===============================


