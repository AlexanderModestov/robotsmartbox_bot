"""Language selection and management callback handlers"""

import logging
from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Create router for language callbacks
language_router = Router()

def get_messages_class(language='en'):
    """Get appropriate messages class based on language - defaults to English"""
    from bot.messages import Messages
    from bot.messages_en import Messages as MessagesEn
    return Messages if language == 'ru' else MessagesEn

@language_router.callback_query(lambda c: c.data.startswith('lang_'))
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

@language_router.callback_query(lambda c: c.data == 'change_language')
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

@language_router.callback_query(lambda c: c.data.startswith('set_lang_'))
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
        from bot.callbacks.settings_callbacks import back_to_settings
        await back_to_settings(callback_query, supabase_client)
    except Exception as e:
        logging.error(f"Error saving language preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")

# Note: change_language and set_lang_ handlers are also moved here since they're settings-related
@language_router.callback_query(lambda c: c.data == 'change_language')
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

@language_router.callback_query(lambda c: c.data.startswith('set_lang_'))
async def handle_set_language_from_settings(callback_query: types.CallbackQuery, supabase_client):
    """Handle language setting from settings menu"""
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
        from bot.callbacks.settings_callbacks import back_to_settings
        await back_to_settings(callback_query, supabase_client)
    except Exception as e:
        logging.error(f"Error saving language preference: {e}")
        await callback_query.answer("Произошла ошибка при сохранении настроек")