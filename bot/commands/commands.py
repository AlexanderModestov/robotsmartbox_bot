import logging
import math
import asyncio
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.messages import Messages
from bot.messages_en import Messages as MessagesEn
from bot.config import Config
from bot.services.translation_service import TranslationService

async def get_user_language_async(message, supabase_client):
    """Async version: Detect user language from database settings, message or user settings"""
    try:
        # First, try to get user's language preference from database
        user_data = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        if user_data and hasattr(user_data, 'language') and user_data.language:
            logging.info(f"User {message.from_user.id} language from DB: {user_data.language}")
            return user_data.language

    except Exception as e:
        # If database check fails, continue with fallback logic
        logging.warning(f"Could not get user language from database: {e}")

    # Use fallback logic
    return get_user_language_fallback(message)

def get_user_language(message):
    """Synchronous fallback version: Detect user language from message or Telegram settings"""
    return get_user_language_fallback(message)

def get_user_language_fallback(message):
    """Fallback logic for language detection"""
    # Check user's Telegram language code
    if hasattr(message.from_user, 'language_code') and message.from_user.language_code:
        if message.from_user.language_code.startswith('ru'):
            return 'ru'
        elif message.from_user.language_code.startswith('en'):
            return 'en'

    # Check message text for language indicators
    if hasattr(message, 'text') and message.text:
        # Check for Cyrillic characters (indicates Russian)
        if any('\u0400' <= char <= '\u04FF' for char in message.text):
            return 'ru'

        # Check for English keywords
        english_keywords = ['start', 'help', 'about', 'settings', 'hello', 'hi']
        text_lower = message.text.lower()
        for keyword in english_keywords:
            if keyword in text_lower:
                return 'en'

    # Default to Russian (since most users seem to prefer Russian)
    return 'ru'

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

    try:
        # Check if user already exists
        existing_user = await supabase_client.get_user_by_telegram_id(message.from_user.id)

        if existing_user:
            # User exists, use their saved language
            user_language = existing_user.language or 'en'
            messages_class = get_messages_class(user_language)
            await message.answer(messages_class.START_CMD["welcome"](user_name))
        else:
            # New user, show language selection
            await show_language_selection(message)

    except Exception as e:
        logging.warning(f"User check error: {e}")
        # Fallback to showing language selection for new users
        await show_language_selection(message)

async def show_language_selection(message: types.Message):
    """Show language selection keyboard for new users"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ]
    ])

    # Send in both languages for first interaction
    welcome_text = (
        "🤖 Welcome! Please select your language:\n"
        "🤖 Добро пожаловать! Пожалуйста, выберите ваш язык:"
    )

    await message.answer(welcome_text, reply_markup=keyboard)

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

@content_router.message(Command('marketplace'))
async def list_marketplace(message: types.Message, supabase_client):
    """Show marketplace with workflow categories from Supabase documents table"""
    try:
        # Get distinct categories from documents table
        response = await asyncio.to_thread(
            lambda: supabase_client.client.table('documents')
            .select('category')
            .not_.is_('category', 'null')
            .neq('category', '')
            .execute()
        )

        # Extract unique categories
        categories = []
        if response.data:
            unique_categories = list(set([doc['category'] for doc in response.data if doc.get('category')]))
            unique_categories.sort()
            categories = [
                {
                    'name': cat.replace('_', ' ').replace('-', ' ').title(),
                    'folder': cat  # Keep original for callback data
                }
                for cat in unique_categories
            ]
        
        # Create keyboard with categories
        keyboard_buttons = []
        
        # Add category buttons
        user_language = await get_user_language_async(message, supabase_client)
        print(f"🔍 Marketplace: User {message.from_user.id} detected language: {user_language}")
        messages_class = get_messages_class(user_language)
        
        for category in categories:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"🗂️ {category['name']}", callback_data=f"marketplace_cat_{category['folder']}")
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Log the command access
        print(f"🛒 Marketplace command: User {message.from_user.id} ({message.from_user.username}) accessing marketplace")
        logging.info(f"Marketplace command: User {message.from_user.id} accessing marketplace")
        
        # Get appropriate welcome text from messages
        automation_text = messages_class.AUTOMATIONS_CMD["welcome"]
        
        await message.answer(
            automation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in list_marketplace: {e}")
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        await message.answer("Error loading marketplace. Please try again later.")

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
async def pay_command(message: types.Message, supabase_client):
    """Handle payment command with Stripe webapp"""
    try:
        # Get messages based on user language (defaults to English)
        user_language = await get_user_language_async(message, supabase_client)
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
        # Get user language and messages
        user_language = await get_user_language_async(message, supabase_client)
        messages_class = get_messages_class(user_language)

        # Get current user settings from database
        user = await supabase_client.get_user_by_telegram_id(message.from_user.id)

        if user:
            # Use messages from message files
            audio_status = messages_class.SETTINGS_CMD["status_audio"] if user.isAudio else messages_class.SETTINGS_CMD["status_text"]
            notif_status = messages_class.SETTINGS_CMD["status_notifications_on"] if user.notification else messages_class.SETTINGS_CMD["status_notifications_off"]
            lang_status = messages_class.SETTINGS_CMD["status_lang_english"] if user.language == 'en' else messages_class.SETTINGS_CMD["status_lang_russian"]

            # Dynamic buttons based on current settings
            if user.isAudio:
                format_button_text = messages_class.SETTINGS_CMD["button_switch_to_text"]
                format_callback = "format_text"
            else:
                format_button_text = messages_class.SETTINGS_CMD["button_switch_to_audio"]
                format_callback = "format_audio"

            if user.notification:
                notif_button_text = messages_class.SETTINGS_CMD["button_disable_notifications"]
                notif_callback = "notifications_off"
            else:
                notif_button_text = messages_class.SETTINGS_CMD["button_enable_notifications"]
                notif_callback = "notifications_on"
        else:
            # Default values using messages
            audio_status = messages_class.SETTINGS_CMD["status_text"]
            notif_status = messages_class.SETTINGS_CMD["status_notifications_off"]
            lang_status = messages_class.SETTINGS_CMD["status_lang_english"]
            format_button_text = messages_class.SETTINGS_CMD["button_switch_to_audio"]
            format_callback = "format_audio"
            notif_button_text = messages_class.SETTINGS_CMD["button_enable_notifications"]
            notif_callback = "notifications_on"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=format_button_text, callback_data=format_callback)],
            [InlineKeyboardButton(text=notif_button_text, callback_data=notif_callback)],
            [InlineKeyboardButton(text=messages_class.SETTINGS_CMD["language_section"], callback_data="change_language")]
        ])

        # Use dynamic message text based on language
        if user_language == 'en':
            settings_text = (
                f"{messages_class.SETTINGS_CMD['main_menu']}\n\n"
                f"<b>Current settings:</b>\n"
                f"💬 Response format: {audio_status}\n"
                f"🔔 Notifications: {notif_status}\n"
                f"🌐 Language: {lang_status}\n\n"
                f"Select an action:"
            )
        else:
            settings_text = (
                f"{messages_class.SETTINGS_CMD['main_menu']}\n\n"
                f"<b>Текущие настройки:</b>\n"
                f"💬 Формат ответов: {audio_status}\n"
                f"🔔 Уведомления: {notif_status}\n"
                f"🌐 Язык: {lang_status}\n\n"
                f"Выберите действие:"
            )

        await message.answer(
            settings_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Error in settings command: {e}")
        await message.answer(messages_class.SETTINGS_CMD["setting_save_error"] if 'messages_class' in locals() else "Error loading settings")







@content_router.message(Command('help'))
async def command_request(message: types.Message, state: FSMContext, supabase_client) -> None:
    """Help command - initiate question asking"""
    # Get user language and appropriate messages
    user_language = await get_user_language_async(message, supabase_client)
    print(f"🔍 Help command - User {message.from_user.id} detected language: {user_language}")
    messages_class = get_messages_class(user_language)
    print(f"🔍 Help command - Using messages class: {messages_class.__name__ if hasattr(messages_class, '__name__') else type(messages_class)}")

    await message.answer(messages_class.HELP_CMD["ask_question"], parse_mode="HTML")
    await state.set_state(UserState.help)

# Request help - send to admin
@content_router.message(UserState.help)
async def help(message: types.Message, state: FSMContext, supabase_client):
    """Send message to admin"""
    # Get user language and appropriate messages
    user_language = await get_user_language_async(message, supabase_client)
    messages_class = get_messages_class(user_language)

    user_mention = f"[{message.from_user.full_name}](tg://user?id={message.from_user.id})"
    await message.answer(messages_class.HELP_CMD["message_received"])
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

