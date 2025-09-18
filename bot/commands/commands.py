import logging
import os
import json
import csv
import math
import asyncio
from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from bot.messages import Messages
from bot.messages_en import Messages as MessagesEn
from bot.config import Config
from bot.services.translation_service import TranslationService

async def get_user_language_async(message, supabase_client):
    """Async version: Detect user language from database settings, message or user settings"""
    try:
        # First, try to get user's language preference from database
        user_data = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        print(f"🔍 User {message.from_user.id} data from DB: {user_data}")
        if user_data and hasattr(user_data, 'language') and user_data.language:
            print(f"🔍 User {message.from_user.id} language from DB: {user_data.language}")
            logging.info(f"User {message.from_user.id} language from DB: {user_data.language}")
            return user_data.language
        else:
            print(f"🔍 User {message.from_user.id} no language in DB, using fallback")

    except Exception as e:
        # If database check fails, continue with fallback logic
        print(f"🔍 Database language check error for user {message.from_user.id}: {e}")
        logging.warning(f"Could not get user language from database: {e}")

    # Use fallback logic
    fallback_lang = get_user_language_fallback(message)
    print(f"🔍 User {message.from_user.id} fallback language: {fallback_lang}")
    return fallback_lang

def get_user_language(message):
    """Synchronous fallback version: Detect user language from message or Telegram settings"""
    return get_user_language_fallback(message)

def get_user_language_fallback(message):
    """Fallback logic for language detection"""
    # Check user's Telegram language code
    if hasattr(message.from_user, 'language_code') and message.from_user.language_code:
        if message.from_user.language_code.startswith('ru'):
            logging.info(f"User {message.from_user.id} language from Telegram: ru")
            return 'ru'
        elif message.from_user.language_code.startswith('en'):
            logging.info(f"User {message.from_user.id} language from Telegram: en")
            return 'en'

    # Check message text for language indicators
    if message.text:
        # Check for Cyrillic characters (indicates Russian)
        if any('\u0400' <= char <= '\u04FF' for char in message.text):
            logging.info(f"User {message.from_user.id} language from text: ru (Cyrillic)")
            return 'ru'

        # Check for English keywords
        english_keywords = ['start', 'help', 'about', 'settings', 'hello', 'hi']
        text_lower = message.text.lower()
        for keyword in english_keywords:
            if keyword in text_lower:
                logging.info(f"User {message.from_user.id} language from text: en (keywords)")
                return 'en'

    # Default to Russian (since most users seem to prefer Russian)
    logging.info(f"User {message.from_user.id} language: ru (default)")
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

@start_router.callback_query(lambda c: c.data.startswith('lang_'))
async def handle_language_selection(callback_query: types.CallbackQuery, supabase_client):
    """Handle language selection"""
    try:
        # Extract language from callback data
        language = callback_query.data.replace('lang_', '')
        user_name = callback_query.from_user.first_name

        # Create user with selected language
        user_data = {
            'telegram_id': callback_query.from_user.id,
            'username': callback_query.from_user.username,
            'language': language
        }

        # Save user to database
        await supabase_client.create_or_update_user(user_data)

        # Get appropriate messages class
        messages_class = get_messages_class(language)

        # Send welcome message in selected language
        await callback_query.message.edit_text(
            messages_class.START_CMD["welcome"](user_name),
            parse_mode="HTML"
        )

        # Acknowledge the callback
        language_name = "English" if language == "en" else "Русский"
        await callback_query.answer(f"Language set to {language_name}")

    except Exception as e:
        logging.error(f"Error handling language selection: {e}")
        await callback_query.answer("Error setting language. Please try again.")

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
            lang_status = "🇬🇧 English" if user.language == 'en' else "🇷🇺 Русский"

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
            lang_status = "🇬🇧 English"
            format_button_text = "🎧 Выбрать аудиоответы"
            format_callback = "format_audio"
            notif_button_text = "🔔 Включить уведомления"
            notif_callback = "notifications_on"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=format_button_text, callback_data=format_callback)],
            [InlineKeyboardButton(text=notif_button_text, callback_data=notif_callback)],
            [InlineKeyboardButton(text="🌐 Изменить язык", callback_data="change_language")]
        ])

        settings_text = (
            "⚙️ <b>Настройки</b>\n\n"
            "<b>Текущие настройки:</b>\n"
            f"💬 Формат ответов: {audio_status}\n"
            f"🔔 Уведомления: {notif_status}\n"
            f"🌐 Язык: {lang_status}\n\n"
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

@content_router.callback_query(lambda c: c.data == 'change_language')
async def handle_change_language(callback_query: types.CallbackQuery):
    """Handle language change request"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")
        ],
        [InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="back_to_settings")]
    ])

    await callback_query.message.edit_text(
        "🌐 <b>Выбор языка</b>\n\n"
        "Выберите язык интерфейса:\n\n"
        "🇬🇧 English\n"
        "🇷🇺 Русский",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@content_router.callback_query(lambda c: c.data.startswith('set_lang_'))
async def handle_set_language(callback_query: types.CallbackQuery, supabase_client):
    """Handle language setting"""
    try:
        language = callback_query.data.replace('set_lang_', '')

        # Save language preference to database
        user_data = {
            'telegram_id': callback_query.from_user.id,
            'language': language
        }

        await supabase_client.create_or_update_user(user_data)

        # Show brief confirmation and redirect back to settings
        language_name = "English" if language == "en" else "Русский"
        await callback_query.answer(f"✅ Язык изменен на {language_name}")

        # Redirect back to settings menu
        await back_to_settings(callback_query, supabase_client)
    except Exception as e:
        logging.error(f"Error saving language preference: {e}")
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





@content_router.callback_query(lambda c: c.data.startswith('marketplace_cat_'))
async def handle_marketplace_category(callback_query: types.CallbackQuery, supabase_client):
    """Handle marketplace category selection - show subcategories from database"""
    try:
        category_folder = callback_query.data.replace('marketplace_cat_', '')

        # Get distinct subcategories from documents table for this category
        response = await asyncio.to_thread(
            lambda: supabase_client.client.table('documents')
            .select('subcategory')
            .eq('category', category_folder)
            .not_.is_('subcategory', 'null')
            .neq('subcategory', '')
            .execute()
        )

        # Extract unique subcategories
        subcategories = []
        if response.data:
            unique_subcategories = list(set([doc['subcategory'] for doc in response.data if doc.get('subcategory')]))
            unique_subcategories.sort()
            subcategories = [
                {
                    'name': subcat.replace('_', ' ').replace('-', ' ').title(),
                    'folder': subcat  # Keep original for callback data
                }
                for subcat in unique_subcategories
            ]

        # Create keyboard with subcategories
        keyboard_buttons = []

        # Get user language for localization
        user_language = get_user_language(callback_query)
        messages_class = get_messages_class(user_language)

        for subcategory in subcategories:
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"⚙️ {subcategory['name']}",
                    callback_data=f"marketplace_subcat_{category_folder}_{subcategory['folder']}"
                )
            ])

        # Add back to main marketplace button
        keyboard_buttons.append([
            InlineKeyboardButton(text="⬅️ Back to Marketplace", callback_data="back_to_marketplace")
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        category_display_name = category_folder.replace('_', ' ').replace('-', ' ').title()
        message_text = f"🗂️ <b>{category_display_name}</b>\n\n{messages_class.AUTOMATIONS_CMD['choose_workflow']}"

        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Error in handle_marketplace_category: {e}")
        await callback_query.answer("Error loading category. Please try again.")

@content_router.callback_query(lambda c: c.data == 'back_to_marketplace')
async def handle_back_to_marketplace(callback_query: types.CallbackQuery, supabase_client):
    """Handle back to marketplace menu"""
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
        messages_class = get_messages_class('en')  # Default to English for callbacks

        for category in categories:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"🗂️ {category['name']}", callback_data=f"marketplace_cat_{category['folder']}")
            ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        # Get appropriate welcome text from messages
        automation_text = messages_class.AUTOMATIONS_CMD["welcome"]

        await callback_query.message.edit_text(
            automation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Error in handle_back_to_marketplace: {e}")
        await callback_query.answer("Error loading marketplace. Please try again.")

@content_router.callback_query(lambda c: c.data.startswith('marketplace_subcat_'))
async def handle_marketplace_subcategory(callback_query: types.CallbackQuery, supabase_client):
    """Handle marketplace subcategory selection - show workflows from database with pagination"""
    try:
        # Parse callback data: marketplace_subcat_category_subcategory or marketplace_subcat_category_subcategory_page_N
        callback_data = callback_query.data.replace('marketplace_subcat_', '')

        # Check if this includes page information
        page = 1
        if '_page_' in callback_data:
            parts = callback_data.split('_page_')
            callback_data = parts[0]
            page = int(parts[1])

        callback_parts = callback_data.split('_', 1)
        if len(callback_parts) != 2:
            await callback_query.answer("Invalid workflow selection")
            return

        category_folder, subcategory_folder = callback_parts

        # Get workflows from database for this category and subcategory
        # Only include automations that have short_description (not null)
        response = await asyncio.to_thread(
            lambda: supabase_client.client.table('documents')
            .select('id, name, short_description, description, url')
            .eq('category', category_folder)
            .eq('subcategory', subcategory_folder)
            .not_.is_('short_description', 'null')
            .neq('short_description', '')
            .execute()
        )

        workflows = response.data if response.data else []

        # Get user language for localization
        user_language = await get_user_language_async(callback_query, supabase_client)
        messages_class = get_messages_class(user_language)

        # Pagination settings
        items_per_page = 6
        total_items = len(workflows)
        total_pages = math.ceil(total_items / items_per_page) if total_items > 0 else 1

        # Ensure page is within valid range
        page = max(1, min(page, total_pages))

        # Get items for current page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        current_workflows = workflows[start_idx:end_idx]

        # Create localized message
        workflow_name = subcategory_folder.replace('_', ' ').replace('-', ' ').title()
        category_name = category_folder.replace('_', ' ').replace('-', ' ').title()

        message_text = f"⚙️ <b>{workflow_name}</b>\n"
        message_text += f"<b>{messages_class.AUTOMATIONS_CMD['workflow_category_label']}</b> {category_name}\n\n"

        if workflows:
            message_text += f"{messages_class.AUTOMATIONS_CMD['available_automations'](total_items)}\n\n"
        else:
            message_text += f"{messages_class.AUTOMATIONS_CMD['no_automations_available']}\n\n"
        
        # Create keyboard with workflow buttons
        keyboard_buttons = []
        
        # Add workflow buttons (6 per page)
        for workflow in current_workflows:
            # Use short_description as button text (since we filtered for non-null short_description)
            button_text = workflow.get('short_description', 'Automation')
            workflow_id = workflow.get('id', '')

            # Truncate button text if too long for Telegram button limit
            if len(button_text) > 60:
                button_text = button_text[:57] + "..."

            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🔧 {button_text}",
                    callback_data=f"workflow_detail_{workflow_id}"
                )
            ])
        
        # Add pagination buttons if needed
        if total_pages > 1:
            pagination_row = []
            
            # Previous page button
            if page > 1:
                pagination_row.append(
                    InlineKeyboardButton(
                        text="⬅️ Previous", 
                        callback_data=f"marketplace_subcat_{category_folder}_{subcategory_folder}_page_{page-1}"
                    )
                )
            
            # Page indicator
            pagination_row.append(
                InlineKeyboardButton(
                    text=f"📄 {page}/{total_pages}", 
                    callback_data="page_info"
                )
            )
            
            # Next page button
            if page < total_pages:
                pagination_row.append(
                    InlineKeyboardButton(
                        text="Next ➡️", 
                        callback_data=f"marketplace_subcat_{category_folder}_{subcategory_folder}_page_{page+1}"
                    )
                )
            
            keyboard_buttons.append(pagination_row)
        
        # Back navigation buttons
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"⬅️ Back to {category_name}", 
                callback_data=f"marketplace_cat_{category_folder}"
            )
        ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🏠 Back to Marketplace", callback_data="back_to_marketplace")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_marketplace_subcategory: {e}")
        await callback_query.answer("Error loading workflows. Please try again.")

@content_router.callback_query(lambda c: c.data == 'page_info')
async def handle_page_info(callback_query: types.CallbackQuery):
    """Handle page info button click (just acknowledge)"""
    await callback_query.answer("Page information")

@content_router.callback_query(lambda c: c.data.startswith('workflow_detail_'))
async def handle_workflow_detail(callback_query: types.CallbackQuery, supabase_client):
    """Handle individual workflow detail view from database - show description and request options"""
    try:
        # Parse callback data: workflow_detail_workflow_id
        workflow_id = callback_query.data.replace('workflow_detail_', '')

        # Get workflow details from database
        response = await asyncio.to_thread(
            lambda: supabase_client.client.table('documents')
            .select('id, name, short_description, description, url, category, subcategory')
            .eq('id', workflow_id)
            .execute()
        )

        if not response.data:
            await callback_query.answer("Workflow not found")
            return

        workflow_data = response.data[0]

        # Get user language for localization (async version to check database)
        user_language = await get_user_language_async(callback_query, supabase_client)
        messages_class = get_messages_class(user_language)

        # Create workflow detail message with localized labels
        name = workflow_data.get('name', 'Untitled Workflow')
        if name.endswith('.json'):
            name = name[:-5]  # Remove .json extension
        workflow_title = name.replace('-', ' ').replace('_', ' ').title()

        category_name = workflow_data.get('category', '').replace('_', ' ').replace('-', ' ').title()
        subcategory_name = workflow_data.get('subcategory', '').replace('_', ' ').replace('-', ' ').title()
        description = workflow_data.get('description', '')

        # Debug: Log user language and description details
        print(f"🔍 Workflow detail - User {callback_query.from_user.id} language: {user_language}")
        print(f"🔍 Description length: {len(description) if description else 0}")
        print(f"🔍 Should translate: {description and user_language == 'ru'}")

        # Translate description if user language is Russian
        if description and user_language == 'ru':
            try:
                print(f"🔄 Starting translation for user {callback_query.from_user.id}")
                translation_service = TranslationService()
                translated_description = translation_service.translate_text(description, 'ru', 'en')
                print(f"🔍 Translation result length: {len(translated_description) if translated_description else 0}")
                if translated_description:
                    description = translated_description
                    print(f"✅ Successfully translated description for user {callback_query.from_user.id}")
                else:
                    print(f"⚠️ Translation returned empty for user {callback_query.from_user.id}")
            except Exception as e:
                print(f"❌ Translation error for user {callback_query.from_user.id}: {e}")
                import traceback
                print(f"❌ Full traceback: {traceback.format_exc()}")
                # Keep original description if translation fails

        # Build clean message with only name, category, and description
        message_text = f"{messages_class.AUTOMATIONS_CMD['workflow_detail_title']}\n\n"
        message_text += f"<b>{messages_class.AUTOMATIONS_CMD['workflow_name_label']}</b> {workflow_title}\n\n"

        if category_name and subcategory_name:
            message_text += f"<b>{messages_class.AUTOMATIONS_CMD['workflow_category_label']}</b> {category_name} → {subcategory_name}\n\n"
        elif category_name:
            message_text += f"<b>{messages_class.AUTOMATIONS_CMD['workflow_category_label']}</b> {category_name}\n\n"

        if description:
            message_text += f"<b>{messages_class.AUTOMATIONS_CMD['workflow_description_label']}</b> {description}\n\n"
        
        # Create keyboard with action options
        keyboard_buttons = []
        
        # Request this automation button
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=messages_class.AUTOMATIONS_CMD["request_automation_button"],
                callback_data=f"request_workflow_{workflow_id}"
            )
        ])

        # Back to workflow list button (if we have category and subcategory)
        if workflow_data.get('category') and workflow_data.get('subcategory'):
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"⬅️ Back to {subcategory_name} List",
                    callback_data=f"marketplace_subcat_{workflow_data['category']}_{workflow_data['subcategory']}"
                )
            ])

            # Back to category button
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🗂️ Back to {category_name}",
                    callback_data=f"marketplace_cat_{workflow_data['category']}"
                )
            ])

        # Always include back to marketplace
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="🏠 Back to Marketplace",
                callback_data="back_to_marketplace"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_workflow_detail: {e}")
        await callback_query.answer("Error loading workflow details. Please try again.")


@content_router.callback_query(lambda c: c.data.startswith('request_workflow_'))
async def handle_request_workflow(callback_query: types.CallbackQuery):
    """Handle workflow request"""
    try:
        # Parse callback data: request_workflow_category_subcategory
        callback_parts = callback_query.data.replace('request_workflow_', '').split('_', 1)
        if len(callback_parts) != 2:
            await callback_query.answer("Invalid workflow request")
            return
            
        category_folder, subcategory_folder = callback_parts
        workflow_name = subcategory_folder.replace('_', ' ').replace('-', ' ').title()
        category_name = category_folder.replace('_', ' ').replace('-', ' ').title()
        
        # Log the workflow request
        user_id = callback_query.from_user.id
        username = callback_query.from_user.username or "Unknown"
        
        logging.info(f"User {user_id} ({username}) requested workflow: {category_name} / {workflow_name}")
        print(f"🎯 Workflow Request: User {user_id} ({username}) wants workflow: {category_name} / {workflow_name}")
        
        # Send notification to admin if configured
        try:
            from bot.config import Config
            if hasattr(Config, 'TELEGRAM_ADMIN_ID') and Config.TELEGRAM_ADMIN_ID:
                admin_message = f"""🎯 **New Workflow Request**
                
👤 **User:** @{username} ({user_id})
🗂️ **Category:** {category_name}
⚙️ **Workflow:** {workflow_name}
📅 **Time:** {callback_query.message.date}

Please contact this user to provide the workflow."""
                
                await callback_query.bot.send_message(
                    chat_id=Config.TELEGRAM_ADMIN_ID,
                    text=admin_message,
                    parse_mode="Markdown"
                )
                
        except Exception as admin_error:
            logging.error(f"Failed to notify admin: {admin_error}")
        
        # Acknowledge the request to the user
        await callback_query.answer(f"✅ Request received! We'll contact you soon with details for '{workflow_name}' workflow.", show_alert=True)
        
    except Exception as e:
        logging.error(f"Error in handle_request_workflow: {e}")
        await callback_query.answer("❌ Error processing your request. Please try again.")


@content_router.callback_query(lambda c: c.data.startswith('automation_cat_'))
async def handle_automation_category(callback_query: types.CallbackQuery, supabase_client):
    """Handle specific automation category selection"""
    try:
        category_id = callback_query.data.replace('automation_cat_', '')
        
        # Use category_id as category name (since we don't have a separate categories table)
        category_name = category_id.replace('_', ' ').title()
        
        # Fetch automation documents for this category using proper joins
        response = supabase_client.client.table('documents').select('''
            id, url, short_description, name, category, subcategory, tags
        ''').eq('category', category_id).not_.is_('short_description', 'null').neq('short_description', '').limit(10).execute()
        
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
        # Get distinct categories from documents table
        response = supabase_client.client.table('documents').select('category').not_.is_('category', 'null').neq('category', '').execute()

        # Extract unique categories
        categories = []
        if response.data:
            unique_categories = list(set([doc['category'] for doc in response.data if doc.get('category')]))
            unique_categories.sort()
            categories = [{'id': cat, 'name': cat.replace('_', ' ').title()} for cat in unique_categories[:8]]
        
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
            id, url, short_description, description, name, category, subcategory, tags
        ''').eq('id', automation_id).execute()
        
        # Default to English for callbacks
        messages_class = get_messages_class('en')
        
        if response.data and len(response.data) > 0:
            doc = response.data[0]
            
            # Get document details
            name = doc.get('name', 'Unnamed').replace('.json', '').replace('-', ' ').title()
            url = doc.get('url', '#')
            description = doc.get('description', doc.get('short_description', 'No description available'))

            # Get category info from the new schema
            category_name = doc.get('category', 'Uncategorized')
            category_id = doc.get('category')
            subcategory = doc.get('subcategory', '')
            tags = doc.get('tags', [])
            
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
        
        # Send notification to admin
        try:
            from bot.config import Config
            admin_id = Config.TELEGRAM_ADMIN_ID
            
            admin_message = f"""🎯 **New Automation Request**
            
👤 **User:** @{username} ({user_id})
⚙️ **Automation ID:** {automation_id}
📅 **Time:** {callback_query.message.date}

Please contact this user to provide the automation."""
            
            await callback_query.bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode="Markdown"
            )
            
        except Exception as admin_error:
            logging.error(f"Failed to notify admin: {admin_error}")
        
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


