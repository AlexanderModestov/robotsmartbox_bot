"""Marketplace navigation and workflow callback handlers"""

import logging
import asyncio
import math
from aiogram import Router, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Create router for marketplace callbacks
marketplace_router = Router()

def get_messages_class(language='en'):
    """Get appropriate messages class based on language - defaults to English"""
    from bot.messages import Messages
    from bot.messages_en import Messages as MessagesEn
    return Messages if language == 'ru' else MessagesEn

def get_user_language(message):
    """Simple fallback for getting user language from callback queries"""
    if hasattr(message.from_user, 'language_code') and message.from_user.language_code:
        if message.from_user.language_code.startswith('ru'):
            return 'ru'
        elif message.from_user.language_code.startswith('en'):
            return 'en'
    return 'ru'  # Default to Russian

async def get_user_language_async(message, supabase_client):
    """Async version for getting user language from database"""
    try:
        user_data = await supabase_client.get_user_by_telegram_id(message.from_user.id)
        if user_data and hasattr(user_data, 'language') and user_data.language:
            return user_data.language
    except Exception:
        pass
    return get_user_language(message)

@marketplace_router.callback_query(lambda c: c.data.startswith('marketplace_cat_'))
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

@marketplace_router.callback_query(lambda c: c.data == 'back_to_marketplace')
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

@marketplace_router.callback_query(lambda c: c.data.startswith('marketplace_subcat_'))
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

        # Get user language for localization first
        user_language = await get_user_language_async(callback_query, supabase_client)

        # Get workflows from database for this category and subcategory
        # Include Russian fields and filter based on user language
        if user_language == 'ru':
            response = await asyncio.to_thread(
                lambda: supabase_client.client.table('documents')
                .select('id, name, name_ru, short_description, short_description_ru, description, description_ru, url')
                .eq('category', category_folder)
                .eq('subcategory', subcategory_folder)
                .not_.is_('short_description_ru', 'null')
                .neq('short_description_ru', '')
                .execute()
            )
        else:
            response = await asyncio.to_thread(
                lambda: supabase_client.client.table('documents')
                .select('id, name, name_ru, short_description, short_description_ru, description, description_ru, url')
                .eq('category', category_folder)
                .eq('subcategory', subcategory_folder)
                .not_.is_('short_description', 'null')
                .neq('short_description', '')
                .execute()
            )

        workflows = response.data if response.data else []
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
            # Use localized short_description as button text
            if user_language == 'ru':
                button_text = workflow.get('short_description_ru') or workflow.get('short_description', 'Automation')
            else:
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

@marketplace_router.callback_query(lambda c: c.data == 'page_info')
async def handle_page_info(callback_query: types.CallbackQuery):
    """Handle page info button click (just acknowledge)"""
    await callback_query.answer("Page information")

@marketplace_router.callback_query(lambda c: c.data.startswith('workflow_detail_'))
async def handle_workflow_detail(callback_query: types.CallbackQuery, supabase_client):
    """Handle individual workflow detail view from database - show description and request options"""
    try:
        # Parse callback data: workflow_detail_workflow_id
        workflow_id = callback_query.data.replace('workflow_detail_', '')

        # Get user language first to determine which fields to require
        user_language = await get_user_language_async(callback_query, supabase_client)

        # Get workflow details from database (including Russian fields)
        # Only show if it has content in the user's language
        if user_language == 'ru':
            response = await asyncio.to_thread(
                lambda: supabase_client.client.table('documents')
                .select('id, name, name_ru, short_description, short_description_ru, description, description_ru, url, category, subcategory')
                .eq('id', workflow_id)
                .not_.is_('description_ru', 'null')
                .neq('description_ru', '')
                .execute()
            )
        else:
            response = await asyncio.to_thread(
                lambda: supabase_client.client.table('documents')
                .select('id, name, name_ru, short_description, short_description_ru, description, description_ru, url, category, subcategory')
                .eq('id', workflow_id)
                .not_.is_('description', 'null')
                .neq('description', '')
                .execute()
            )

        if not response.data:
            await callback_query.answer("Workflow not found")
            return

        workflow_data = response.data[0]
        messages_class = get_messages_class(user_language)

        # Create workflow detail message with localized labels
        # Use Russian fields if user language is Russian and they exist
        if user_language == 'ru':
            name = workflow_data.get('name_ru') or workflow_data.get('name', 'Untitled Workflow')
            description = workflow_data.get('description_ru') or workflow_data.get('description', '')
        else:
            name = workflow_data.get('name', 'Untitled Workflow')
            description = workflow_data.get('description', '')

        if name.endswith('.json'):
            name = name[:-5]  # Remove .json extension
        workflow_title = name.replace('-', ' ').replace('_', ' ').title()

        category_name = workflow_data.get('category', '').replace('_', ' ').replace('-', ' ').title()
        subcategory_name = workflow_data.get('subcategory', '').replace('_', ' ').replace('-', ' ').title()

        # Note: Translation service removed - using description as-is

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

@marketplace_router.callback_query(lambda c: c.data.startswith('request_workflow_'))
async def handle_request_workflow(callback_query: types.CallbackQuery, supabase_client):
    """Handle workflow request"""
    try:
        # Parse callback data: request_workflow_workflow_id
        workflow_id = callback_query.data.replace('request_workflow_', '')

        # Get workflow details from database
        response = await asyncio.to_thread(
            lambda: supabase_client.client.table('documents')
            .select('id, name, category, subcategory')
            .eq('id', workflow_id)
            .execute()
        )

        if not response.data:
            await callback_query.answer("Workflow not found")
            return

        workflow_data = response.data[0]
        workflow_name = workflow_data.get('name', 'Unknown Workflow')
        if workflow_name.endswith('.json'):
            workflow_name = workflow_name[:-5]  # Remove .json extension
        workflow_name = workflow_name.replace('-', ' ').replace('_', ' ').title()

        category_folder = workflow_data.get('category', 'unknown')
        subcategory_folder = workflow_data.get('subcategory', 'unknown')
        category_name = category_folder.replace('_', ' ').replace('-', ' ').title()
        subcategory_name = subcategory_folder.replace('_', ' ').replace('-', ' ').title()

        # Log the workflow request
        user_id = callback_query.from_user.id
        username = callback_query.from_user.username or "Unknown"

        logging.info(f"User {user_id} ({username}) requested workflow: {category_name} / {subcategory_name} / {workflow_name}")
        print(f"🎯 Workflow Request: User {user_id} ({username}) wants workflow: {category_name} / {subcategory_name} / {workflow_name}")

        # Send notification to admin if configured
        try:
            from bot.config import Config
            if hasattr(Config, 'TELEGRAM_ADMIN_ID') and Config.TELEGRAM_ADMIN_ID:
                admin_message = f"""🎯 **New Workflow Request**

👤 **User:** @{username} ({user_id})
🗂️ **Category:** {category_name}
📁 **Subcategory:** {subcategory_name}
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

# Legacy automation callback handlers (kept for backward compatibility)
@marketplace_router.callback_query(lambda c: c.data.startswith('automation_cat_'))
async def handle_automation_category(callback_query: types.CallbackQuery, supabase_client):
    """Handle specific automation category selection"""
    try:
        category_id = callback_query.data.replace('automation_cat_', '')

        # Use category_id as category name (since we don't have a separate categories table)
        category_name = category_id.replace('_', ' ').title()

        # Get user language
        user_language = await get_user_language_async(callback_query, supabase_client)
        messages_class = get_messages_class(user_language)

        # Fetch automation documents for this category (including Russian fields)
        # Filter based on user language to show only automations with descriptions in that language
        if user_language == 'ru':
            response = supabase_client.client.table('documents').select('''
                id, url, short_description, short_description_ru, name, name_ru, category, subcategory, tags
            ''').eq('category', category_id).not_.is_('short_description_ru', 'null').neq('short_description_ru', '').limit(10).execute()
        else:
            response = supabase_client.client.table('documents').select('''
                id, url, short_description, short_description_ru, name, name_ru, category, subcategory, tags
            ''').eq('category', category_id).not_.is_('short_description', 'null').neq('short_description', '').limit(10).execute()

        message_text = messages_class.AUTOMATIONS_CMD["category_header"](category_name)

        # Create buttons for each automation using localized short_description as button text
        keyboard_buttons = []
        if response.data:
            for doc in response.data:
                doc_id = doc.get('id')

                # Use Russian short description if user language is Russian and it exists
                if user_language == 'ru':
                    short_desc = doc.get('short_description_ru') or doc.get('short_description', 'Automation')
                else:
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

@marketplace_router.callback_query(lambda c: c.data == 'back_to_automations')
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

@marketplace_router.callback_query(lambda c: c.data.startswith('automation_detail_'))
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

@marketplace_router.callback_query(lambda c: c.data.startswith('get_automation_'))
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