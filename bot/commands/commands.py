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
from bot.config import Config
from bot.services.automation_handler import AutomationHandler

# States for FSM
class UserState(StatesGroup):
    help = State()
    waiting_for_question = State()
    automation_query = State()
    automation_category = State()

# Create routers for commands
start_router = Router()
content_router = Router()

@start_router.message(CommandStart())
async def cmd_start(message: types.Message, supabase_client):
    """Start command handler"""
    user_name = message.from_user.first_name
    await message.answer(Messages.START_CMD["welcome"](user_name))
    
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
    await message.answer(
        Messages.ABOUT_MESSAGE,
        parse_mode="Markdown"
    )

@content_router.message(Command('automatizations'))
async def list_automatizations(message: types.Message, supabase_client):
    """Show automatization examples with categories from Supabase"""
    try:
        # Fetch unique categories from documents table
        response = supabase_client.client.table('documents').select('category').not_('category', 'is', 'null').execute()
        
        categories = []
        if response.data:
            # Get unique categories
            unique_categories = set()
            for doc in response.data:
                if doc['category'] and doc['category'].strip():
                    unique_categories.add(doc['category'].strip())
            categories = sorted(list(unique_categories))
        
        # Create keyboard with categories
        keyboard_buttons = []
        
        # Add "All automatizations" button first
        keyboard_buttons.append([
            InlineKeyboardButton(text="🤖 Все автоматизации", callback_data="automations_all")
        ])
        
        # Add category buttons
        for category in categories[:8]:  # Limit to 8 categories to avoid keyboard size issues
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⚙️ {category}", callback_data=f"automation_cat_{category}")
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Log the command access
        print(f"🤖 Automatizations command: User {message.from_user.id} ({message.from_user.username}) accessing automatization examples")
        logging.info(f"Automatizations command: User {message.from_user.id} accessing automatization examples")
        
        await message.answer(
            "🤖 *Примеры автоматизации*\n\n"
            "Здесь вы найдете примеры различных автоматизаций для повышения эффективности.\n\n"
            "Выберите категорию:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in list_automatizations: {e}")
        await message.answer("Ошибка при загрузке автоматизаций.")

@content_router.message(Command('booking'))
async def schedule_command(message: types.Message):
    """Handle booking command with Calendly webapp"""
    try:
        # Create Calendly webapp button
        calendly_button = InlineKeyboardButton(
            text="📅 Забронировать сессию",
            web_app=WebAppInfo(url=Config.CALENDLY_LINK)
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[calendly_button]])
        
        # Log the booking access
        print(f"📅 Booking command: User {message.from_user.id} ({message.from_user.username}) accessing booking webapp")
        logging.info(f"Booking command: User {message.from_user.id} accessing booking webapp")
        
        await message.answer(
            "📅 *Бронирование сессии*\n\n"
            "Выберите удобное время для консультации через Calendly.\n"
            "Нажмите кнопку ниже для открытия календаря:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in schedule_command: {e}")
        await message.answer("Ошибка при загрузке календаря бронирования.")

@content_router.message(Command('pay'))
async def pay_command(message: types.Message):
    """Handle payment command with Stripe webapp"""
    try:
        # Create Stripe payment webapp button
        stripe_button = InlineKeyboardButton(
            text="💳 Оплатить услугу",
            web_app=WebAppInfo(url=Config.STRIPE_PAYMENT_LINK)
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[stripe_button]])
        
        # Log the payment access
        print(f"💳 Pay command: User {message.from_user.id} ({message.from_user.username}) accessing payment webapp")
        logging.info(f"Pay command: User {message.from_user.id} accessing payment webapp")
        
        await message.answer(
            "💳 *Оплата услуги*\n\n"
            "Нажмите кнопку ниже для безопасной оплаты через Stripe:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in pay_command: {e}")
        await message.answer("Ошибка при загрузке страницы оплаты.")

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
        # Fetch all automation documents
        response = supabase_client.client.table('documents').select('id, metadata, url, category').not_('category', 'is', 'null').limit(10).execute()
        
        message_text = "🤖 <b>Все автоматизации</b>\n\n"
        
        if response.data:
            for doc in response.data:
                metadata = doc.get('metadata', {})
                if isinstance(metadata, dict):
                    file_name = metadata.get('file_name', 'Unnamed')
                    url = doc.get('url') or metadata.get('url', '#')
                    category = doc.get('category', 'Uncategorized')
                    
                    message_text += f"⚙️ <b>{file_name}</b>\n"
                    message_text += f"📂 Категория: {category}\n"
                    if url and url != '#':
                        message_text += f"🔗 <a href='{url}'>Открыть</a>\n"
                    message_text += "\n"
        else:
            message_text += "Примеры автоматизаций пока не найдены."
        
        back_button = InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_automations")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button]])
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_automations_all: {e}")
        await callback_query.answer("Ошибка при загрузке автоматизаций")

@content_router.callback_query(lambda c: c.data.startswith('automation_cat_'))
async def handle_automation_category(callback_query: types.CallbackQuery, supabase_client):
    """Handle specific automation category selection"""
    try:
        category = callback_query.data.replace('automation_cat_', '')
        
        # Fetch automation documents for this category
        response = supabase_client.client.table('documents').select('id, metadata, url, category').eq('category', category).limit(10).execute()
        
        message_text = f"⚙️ <b>Автоматизации: {category}</b>\n\n"
        
        if response.data:
            for doc in response.data:
                metadata = doc.get('metadata', {})
                if isinstance(metadata, dict):
                    file_name = metadata.get('file_name', 'Unnamed')
                    url = doc.get('url') or metadata.get('url', '#')
                    
                    message_text += f"🤖 <b>{file_name}</b>\n"
                    if url and url != '#':
                        message_text += f"🔗 <a href='{url}'>Открыть</a>\n"
                    message_text += "\n"
        else:
            message_text += f"Примеры автоматизаций в категории '{category}' пока не найдены."
        
        back_button = InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_automations")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button]])
        
        await callback_query.message.edit_text(
            message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_automation_category: {e}")
        await callback_query.answer("Ошибка при загрузке категории автоматизаций")

@content_router.callback_query(lambda c: c.data == 'back_to_automations')
async def handle_back_to_automations(callback_query: types.CallbackQuery, supabase_client):
    """Handle back to automatizations menu"""
    try:
        # Fetch unique categories from documents table
        response = supabase_client.client.table('documents').select('category').not_('category', 'is', 'null').execute()
        
        categories = []
        if response.data:
            # Get unique categories
            unique_categories = set()
            for doc in response.data:
                if doc['category'] and doc['category'].strip():
                    unique_categories.add(doc['category'].strip())
            categories = sorted(list(unique_categories))
        
        # Create keyboard with categories
        keyboard_buttons = []
        
        # Add "All automatizations" button first
        keyboard_buttons.append([
            InlineKeyboardButton(text="🤖 Все автоматизации", callback_data="automations_all")
        ])
        
        # Add category buttons
        for category in categories[:8]:  # Limit to 8 categories to avoid keyboard size issues
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⚙️ {category}", callback_data=f"automation_cat_{category}")
            ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback_query.message.edit_text(
            "🤖 *Примеры автоматизации*\n\n"
            "Здесь вы найдете примеры различных автоматизаций для повышения эффективности.\n\n"
            "Выберите категорию:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logging.error(f"Error in handle_back_to_automations: {e}")
        await callback_query.answer("Ошибка при возврате к автоматизациям")


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

@content_router.message(Command('automate'))
async def automate_command(message: types.Message, state: FSMContext, supabase_client):
    """Handle /automate command"""
    try:
        automation_handler = AutomationHandler(supabase_client)
        
        # Check if user provided a query with the command
        command_parts = message.text.split(' ', 1)
        if len(command_parts) > 1:
            # User provided query directly
            query = command_parts[1].strip()
            
            await message.answer("🔍 Ищу подходящие автоматизации...")
            
            # Process the query
            result = await automation_handler.handle_automation_query(
                user_id=message.from_user.id,
                query=query
            )
            
            if result.get('success') and result.get('recommendations'):
                # Format and send results
                response = result.get('contextual_response', 'Найдены подходящие автоматизации:')
                await message.answer(response, parse_mode="Markdown")
                
                # Send each automation as a separate message
                for i, automation in enumerate(result['recommendations'][:3], 1):  # Limit to top 3
                    automation_text = automation_handler.format_automation_for_telegram(automation)
                    
                    # Create inline keyboard for this automation
                    keyboard_buttons = []
                    
                    # Add URL button if available
                    if automation.get('url'):
                        keyboard_buttons.append([
                            InlineKeyboardButton(text="🔗 Открыть на n8n.io", url=automation['url'])
                        ])
                    
                    # Add similar automations button
                    keyboard_buttons.append([
                        InlineKeyboardButton(text="🔍 Похожие автоматизации", callback_data=f"similar_{automation.get('title', '')[:20]}")
                    ])
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
                    
                    await message.answer(
                        automation_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                
                if len(result['recommendations']) > 3:
                    await message.answer(f"И еще {len(result['recommendations']) - 3} автоматизаций. Уточните запрос для более точных результатов.")
            
            else:
                # No results found
                error_message = result.get('contextual_response', 'К сожалению, не удалось найти подходящие автоматизации.')
                await message.answer(error_message)
                
                # Suggest categories
                categories = automation_handler.get_available_categories()[:5]
                suggestion_text = "\n📚 **Попробуйте поискать в категориях:**\n"
                for cat in categories:
                    suggestion_text += f"• {cat['name']}\n"
                suggestion_text += "\nИспользуйте /knowledge для просмотра всех категорий."
                
                await message.answer(suggestion_text, parse_mode="Markdown")
        
        else:
            # No query provided, ask for it
            await message.answer(
                "🤖 **Помощь в автоматизации**\n\n"
                "Опишите задачу, которую хотите автоматизировать:\n\n"
                "**Примеры:**\n"
                "• Автоматически отправлять email уведомления\n"
                "• Синхронизировать данные между Google Sheets и базой данных\n"
                "• Создавать посты в социальных сетях из RSS\n"
                "• Обрабатывать заказы в интернет-магазине\n\n"
                "Просто опишите вашу задачу в следующем сообщении:",
                parse_mode="Markdown"
            )
            await state.set_state(UserState.automation_query)
    
    except Exception as e:
        logging.error(f"Error in automate command: {e}")
        await message.answer("Произошла ошибка. Попробуйте еще раз позже.")

@content_router.message(UserState.automation_query)
async def handle_automation_query_state(message: types.Message, state: FSMContext, supabase_client):
    """Handle automation query in FSM state"""
    try:
        automation_handler = AutomationHandler(supabase_client)
        
        await message.answer("🔍 Ищу подходящие автоматизации...")
        
        # Process the query
        result = await automation_handler.handle_automation_query(
            user_id=message.from_user.id,
            query=message.text
        )
        
        await state.clear()  # Clear the state
        
        if result.get('success') and result.get('recommendations'):
            # Send contextual response
            response = result.get('contextual_response', 'Найдены подходящие автоматизации:')
            await message.answer(response, parse_mode="Markdown")
            
            # Send top 3 automations
            for automation in result['recommendations'][:3]:
                automation_text = automation_handler.format_automation_for_telegram(automation)
                
                # Create inline keyboard
                keyboard_buttons = []
                if automation.get('url'):
                    keyboard_buttons.append([
                        InlineKeyboardButton(text="🔗 Открыть на n8n.io", url=automation['url'])
                    ])
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
                
                await message.answer(
                    automation_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        
        else:
            await message.answer("К сожалению, не удалось найти подходящие автоматизации для вашего запроса. Попробуйте использовать другие ключевые слова.")
    
    except Exception as e:
        logging.error(f"Error handling automation query: {e}")
        await message.answer("Произошла ошибка при обработке запроса.")
        await state.clear()

@content_router.message(Command('knowledge'))
async def knowledge_command(message: types.Message, supabase_client):
    """Handle /knowledge command - show automation knowledge base"""
    try:
        automation_handler = AutomationHandler(supabase_client)
        
        # Get available categories
        categories = automation_handler.get_available_categories()
        
        # Create inline keyboard with categories
        keyboard_buttons = []
        
        # Add trending button first
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔥 Популярные автоматизации", callback_data="knowledge_trending")
        ])
        
        # Add beginner button
        keyboard_buttons.append([
            InlineKeyboardButton(text="🚀 Для начинающих", callback_data="knowledge_beginner")
        ])
        
        # Add categories (2 per row)
        for i in range(0, len(categories), 2):
            row = []
            for j in range(2):
                if i + j < len(categories):
                    cat = categories[i + j]
                    emoji_map = {
                        'social-media': '📱',
                        'ai-ml': '🧠', 
                        'business-automation': '💼',
                        'data-processing': '📊',
                        'communication': '💬',
                        'productivity': '⚡',
                        'web-scraping': '🕷️',
                        'marketing': '📈',
                        'api-integration': '🔗',
                        'e-commerce': '🛒'
                    }
                    emoji = emoji_map.get(cat['key'], '⚙️')
                    row.append(InlineKeyboardButton(
                        text=f"{emoji} {cat['name'][:15]}",
                        callback_data=f"knowledge_cat_{cat['key']}"
                    ))
            if row:
                keyboard_buttons.append(row)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        # Send knowledge base overview
        message_text = """📚 **База знаний по автоматизации**

Добро пожаловать в базу знаний! Здесь вы найдете:

🔥 **Популярные автоматизации** - самые востребованные решения
🚀 **Для начинающих** - простые автоматизации для старта
📂 **По категориям** - организованные по типам задач

**Всего доступно:** более 150 готовых автоматизаций

Выберите интересующую категорию:"""
        
        await message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    except Exception as e:
        logging.error(f"Error in knowledge command: {e}")
        await message.answer("Ошибка при загрузке базы знаний.")

# Knowledge base callback handlers
@content_router.callback_query(lambda c: c.data.startswith('knowledge_'))
async def handle_knowledge_callback(callback_query: types.CallbackQuery, supabase_client):
    """Handle knowledge base callback queries"""
    try:
        automation_handler = AutomationHandler(supabase_client)
        action = callback_query.data.replace('knowledge_', '')
        
        await callback_query.answer()
        
        if action == 'trending':
            await callback_query.message.edit_text("🔍 Загружаю популярные автоматизации...")
            
            result = await automation_handler.get_trending_automations(callback_query.from_user.id)
            
            if result.get('success') and result.get('recommendations'):
                response = "🔥 **Популярные автоматизации**\n\n"
                response += result.get('contextual_response', '')
                
                await callback_query.message.edit_text(response, parse_mode="Markdown")
                
                # Send each automation
                for automation in result['recommendations'][:4]:  # Top 4
                    automation_text = automation_handler.format_automation_for_telegram(automation, include_details=False)
                    
                    keyboard_buttons = []
                    if automation.get('url'):
                        keyboard_buttons.append([
                            InlineKeyboardButton(text="🔗 Открыть", url=automation['url'])
                        ])
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
                    
                    await callback_query.message.answer(
                        automation_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
        
        elif action == 'beginner':
            await callback_query.message.edit_text("🔍 Загружаю автоматизации для начинающих...")
            
            result = await automation_handler.get_beginner_automations(callback_query.from_user.id)
            
            if result.get('success') and result.get('recommendations'):
                response = result.get('contextual_response', '🚀 Автоматизации для начинающих')
                await callback_query.message.edit_text(response, parse_mode="Markdown")
                
                # Send automations
                for automation in result['recommendations'][:4]:
                    automation_text = automation_handler.format_automation_for_telegram(automation, include_details=False)
                    
                    keyboard_buttons = []
                    if automation.get('url'):
                        keyboard_buttons.append([
                            InlineKeyboardButton(text="🔗 Открыть", url=automation['url'])
                        ])
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
                    
                    await callback_query.message.answer(
                        automation_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
        
        elif action.startswith('cat_'):
            category = action.replace('cat_', '')
            await callback_query.message.edit_text(f"🔍 Загружаю автоматизации категории: {category}...")
            
            result = await automation_handler.handle_category_browse(callback_query.from_user.id, category)
            
            if result.get('success') and result.get('recommendations'):
                category_info = result.get('category_info', {})
                response = f"📂 **{category_info.get('name', category)}**\n\n"
                response += category_info.get('description', '') + "\n\n"
                response += f"Найдено {len(result['recommendations'])} автоматизаций:"
                
                await callback_query.message.edit_text(response, parse_mode="Markdown")
                
                # Send automations
                for automation in result['recommendations'][:4]:
                    automation_text = automation_handler.format_automation_for_telegram(automation, include_details=False)
                    
                    keyboard_buttons = []
                    if automation.get('url'):
                        keyboard_buttons.append([
                            InlineKeyboardButton(text="🔗 Открыть", url=automation['url'])
                        ])
                    
                    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
                    
                    await callback_query.message.answer(
                        automation_text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
            else:
                await callback_query.message.edit_text(f"В категории {category} пока нет доступных автоматизаций.")
    
    except Exception as e:
        logging.error(f"Error handling knowledge callback: {e}")
        await callback_query.answer("Произошла ошибка", show_alert=True)