"""Settings management callback handlers"""

import logging
from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Create router for settings callbacks
settings_router = Router()

@settings_router.callback_query(lambda c: c.data == 'back_to_settings')
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

@settings_router.callback_query(lambda c: c.data in ['format_text', 'format_audio'])
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

@settings_router.callback_query(lambda c: c.data in ['notifications_on', 'notifications_off'])
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