import logging
import os
import json
import csv
import math
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

@content_router.message(Command('marketplace'))
async def list_marketplace(message: types.Message, supabase_client):
    """Show marketplace with workflow categories from local folders"""
    try:
        # Get workflow categories from local folders
        workflows_path = os.path.join(os.getcwd(), 'workflows')
        categories = []
        
        if os.path.exists(workflows_path):
            # Get all directories in workflows folder
            for item in os.listdir(workflows_path):
                item_path = os.path.join(workflows_path, item)
                if os.path.isdir(item_path):
                    categories.append({
                        'name': item.replace('_', ' ').replace('-', ' ').title(),
                        'folder': item
                    })
        
        # Sort categories alphabetically
        categories.sort(key=lambda x: x['name'])
        
        # Create keyboard with categories
        keyboard_buttons = []
        
        # Add category buttons
        user_language = get_user_language(message)
        messages_class = get_messages_class(user_language)
        
        for category in categories:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"📁 {category['name']}", callback_data=f"marketplace_cat_{category['folder']}")
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

@content_router.callback_query(lambda c: c.data.startswith('marketplace_cat_'))
async def handle_marketplace_category(callback_query: types.CallbackQuery):
    """Handle marketplace category selection - show subcategories (subfolders)"""
    try:
        category_folder = callback_query.data.replace('marketplace_cat_', '')
        
        # Get subcategories from local folders
        category_path = os.path.join(os.getcwd(), 'workflows', category_folder)
        subcategories = []
        
        if os.path.exists(category_path):
            # Get all directories in the category folder
            for item in os.listdir(category_path):
                item_path = os.path.join(category_path, item)
                if os.path.isdir(item_path):
                    subcategories.append({
                        'name': item.replace('_', ' ').replace('-', ' ').title(),
                        'folder': item
                    })
        
        # Sort subcategories alphabetically
        subcategories.sort(key=lambda x: x['name'])
        
        # Create keyboard with subcategories
        keyboard_buttons = []
        
        # Add subcategory buttons
        messages_class = get_messages_class('en')  # Default to English for callbacks
        
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
        message_text = f"📁 <b>{category_display_name}</b>\n\nChoose a workflow:"
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_marketplace_category: {e}")
        await callback_query.answer("Error loading category. Please try again.")

@content_router.callback_query(lambda c: c.data == 'back_to_marketplace')
async def handle_back_to_marketplace(callback_query: types.CallbackQuery):
    """Handle back to marketplace menu"""
    try:
        # Get workflow categories from local folders
        workflows_path = os.path.join(os.getcwd(), 'workflows')
        categories = []
        
        if os.path.exists(workflows_path):
            # Get all directories in workflows folder
            for item in os.listdir(workflows_path):
                item_path = os.path.join(workflows_path, item)
                if os.path.isdir(item_path):
                    categories.append({
                        'name': item.replace('_', ' ').replace('-', ' ').title(),
                        'folder': item
                    })
        
        # Sort categories alphabetically
        categories.sort(key=lambda x: x['name'])
        
        # Create keyboard with categories
        keyboard_buttons = []
        
        # Add category buttons
        messages_class = get_messages_class('en')  # Default to English for callbacks
        
        for category in categories:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"📁 {category['name']}", callback_data=f"marketplace_cat_{category['folder']}")
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
async def handle_marketplace_subcategory(callback_query: types.CallbackQuery):
    """Handle marketplace subcategory selection - show workflows from CSV with pagination"""
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
        
        # Read workflows from CSV file
        csv_path = os.path.join(os.getcwd(), 'workflows', category_folder, subcategory_folder, 'workflows.csv')
        workflows = []
        
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as csvfile:
                    csv_reader = csv.DictReader(csvfile)
                    workflows = list(csv_reader)
            except Exception as csv_error:
                logging.error(f"Error reading CSV file {csv_path}: {csv_error}")
        
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
        
        # Create message
        workflow_name = subcategory_folder.replace('_', ' ').replace('-', ' ').title()
        category_name = category_folder.replace('_', ' ').replace('-', ' ').title()
        
        message_text = f"⚙️ <b>{workflow_name}</b>\n"
        message_text += f"📂 <b>Category:</b> {category_name}\n\n"
        
        if current_workflows:
            message_text += f"📋 <b>Available Workflows</b> (Page {page}/{total_pages}):\n\n"
        else:
            message_text += "📋 <b>No workflows available in this category yet.</b>\n\n"
        
        # Create keyboard with workflow buttons
        keyboard_buttons = []
        
        # Add workflow buttons (6 per page)
        for workflow in current_workflows:
            title = workflow.get('title', 'Untitled Workflow')
            workflow_id = workflow.get('id', '')
            
            # Truncate title if too long for button
            button_text = title[:65] + "..." if len(title) > 65 else title
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🔧 {button_text}", 
                    callback_data=f"workflow_detail_{category_folder}_{subcategory_folder}_{workflow_id}"
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
async def handle_workflow_detail(callback_query: types.CallbackQuery):
    """Handle individual workflow detail view from CSV - show description and request options"""
    try:
        # Parse callback data: workflow_detail_category_subcategory_workflow_id
        callback_data = callback_query.data.replace('workflow_detail_', '')
        parts = callback_data.split('_')
        
        if len(parts) < 3:
            await callback_query.answer("Invalid workflow selection")
            return
        
        # Extract category, subcategory, and workflow_id
        category_folder = parts[0]
        subcategory_folder = parts[1]
        workflow_id = '_'.join(parts[2:])  # In case ID contains underscores
        
        # Read workflow details from CSV
        csv_path = os.path.join(os.getcwd(), 'workflows', category_folder, subcategory_folder, 'workflows.csv')
        workflow_data = None
        
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as csvfile:
                    csv_reader = csv.DictReader(csvfile)
                    for row in csv_reader:
                        if row.get('id') == workflow_id:
                            workflow_data = row
                            break
            except Exception as csv_error:
                logging.error(f"Error reading CSV file {csv_path}: {csv_error}")
        
        if not workflow_data:
            await callback_query.answer("Workflow not found")
            return
        
        # Create workflow detail message
        workflow_title = workflow_data.get('title', 'Untitled Workflow')
        category_name = category_folder.replace('_', ' ').replace('-', ' ').title()
        subcategory_name = subcategory_folder.replace('_', ' ').replace('-', ' ').title()
        
        message_text = f"🔧 <b>Automation Details</b>\n\n"
        message_text += f"📋 <b>Name:</b> {workflow_title}\n\n"
        message_text += f"📂 <b>Category:</b> {category_name} → {subcategory_name}\n"
        message_text += f"🆔 <b>ID:</b> {workflow_id}\n\n"
        message_text += "💡 This automation can help streamline your workflow processes. "
        message_text += "Contact us to get access to this automation template."
        
        # Create keyboard with action options
        keyboard_buttons = []
        
        # Request this automation button
        keyboard_buttons.append([
            InlineKeyboardButton(
                text="✅ Request this automation", 
                callback_data=f"request_csv_workflow_{category_folder}_{subcategory_folder}_{workflow_id}"
            )
        ])
        
        # Back to workflow list button
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"⬅️ Back to {subcategory_name} List", 
                callback_data=f"marketplace_subcat_{category_folder}_{subcategory_folder}"
            )
        ])
        
        # Back to category button
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"📁 Back to {category_name}", 
                callback_data=f"marketplace_cat_{category_folder}"
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

@content_router.callback_query(lambda c: c.data.startswith('request_csv_workflow_'))
async def handle_request_csv_workflow(callback_query: types.CallbackQuery):
    """Handle workflow request from CSV listing"""
    try:
        # Parse callback data: request_csv_workflow_category_subcategory_workflow_id
        callback_data = callback_query.data.replace('request_csv_workflow_', '')
        parts = callback_data.split('_')
        
        if len(parts) < 3:
            await callback_query.answer("Invalid workflow request")
            return
        
        # Extract category, subcategory, and workflow_id
        category_folder = parts[0]
        subcategory_folder = parts[1]
        workflow_id = '_'.join(parts[2:])  # In case ID contains underscores
        
        # Read workflow details from CSV to get the title
        csv_path = os.path.join(os.getcwd(), 'workflows', category_folder, subcategory_folder, 'workflows.csv')
        workflow_title = "Unknown Workflow"
        
        if os.path.exists(csv_path):
            try:
                with open(csv_path, 'r', encoding='utf-8') as csvfile:
                    csv_reader = csv.DictReader(csvfile)
                    for row in csv_reader:
                        if row.get('id') == workflow_id:
                            workflow_title = row.get('title', 'Unknown Workflow')
                            break
            except Exception as csv_error:
                logging.error(f"Error reading CSV file {csv_path}: {csv_error}")
        
        category_name = category_folder.replace('_', ' ').replace('-', ' ').title()
        subcategory_name = subcategory_folder.replace('_', ' ').replace('-', ' ').title()
        
        # Log the workflow request
        user_id = callback_query.from_user.id
        username = callback_query.from_user.username or "Unknown"
        
        logging.info(f"User {user_id} ({username}) requested workflow: {category_name} / {subcategory_name} / {workflow_title} (ID: {workflow_id})")
        print(f"🎯 Workflow Request: User {user_id} ({username}) wants workflow: {category_name} / {subcategory_name} / {workflow_title} (ID: {workflow_id})")
        
        # Send notification to admin if configured
        try:
            from bot.config import Config
            if hasattr(Config, 'TELEGRAM_ADMIN_ID') and Config.TELEGRAM_ADMIN_ID:
                admin_message = f"""🎯 **New Workflow Request**
                
👤 **User:** @{username} ({user_id})
📁 **Category:** {category_name} → {subcategory_name}
⚙️ **Workflow:** {workflow_title}
🆔 **ID:** {workflow_id}
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
        short_title = workflow_title[:50] + "..." if len(workflow_title) > 50 else workflow_title
        await callback_query.answer(f"✅ Request received! We'll contact you soon with details for '{short_title}'.", show_alert=True)
        
    except Exception as e:
        logging.error(f"Error in handle_request_csv_workflow: {e}")
        await callback_query.answer("❌ Error processing your request. Please try again.")

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
📁 **Category:** {category_name}
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


