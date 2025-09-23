class Messages:
    START_CMD = {
        "welcome": lambda user_name: (
            f"👋 Hello, {user_name}!\n\n"
            "I'm an automation assistant bot! My goal is to help you understand how to automate daily tasks and solve your problems using modern technologies.\n\n"
            "What I can do:\n"
            "• 🤖 Analyze your problems and suggest automation solutions\n"
            "• 💼 Optimize work and business processes\n"
            "• 📱 Recommend digital automation tools\n"
            "• 🎯 Improve your personal efficiency\n\n"
            "Available commands:\n"
            "/marketplace - Browse automation examples by category\n"
            "/booking - Schedule a consultation\n"
            "/pay - Make a payment for services\n"
            "/settings - Bot settings and preferences\n"
            "/help - Ask a question directly\n"
            "/about - Learn more about this bot\n\n"
            "💬 You can also just send me any message describing a task you want to automate, and I'll provide expert advice plus similar automation examples from our database!\n\n"
            "Where shall we start? 🚀"
        )
    }

    VIDEOS_CMD = {
        "list": "Select a video to watch 🎥",
        "not_found": "❌ Sorry, the video was not found.",
        "no_videos": "📭 No video files are currently available.",
        "button_text": lambda filename: f"🎥 Watch: {filename}",
        "error": lambda error: f"❌ An error occurred: {error}",
        "processing_error": "❌ Sorry, there was an error processing the video. Please try again later.",
        "large_file": "📢 This video is too large to send directly. Please use the web player:",
        "streaming_caption": lambda video_name: f"▶️ Streaming: {video_name}",
        "web_player_button": "🌐 Watch in Web Player"
    }

    WARNINGS_AND_ERRORS = {
        "general": lambda error: f"An error occurred: {error}",
        "video_not_found": "Video not found",
        "no_access": "You don't have access to this video",
        "BOT_STOPPED_MESSAGE": "Bot has been stopped. Goodbye! 👋",
        "MAIN_ERROR_MESSAGE": "An error occurred in the main loop: {}",
        "DB_CONNECTION_CLOSED_MESSAGE": "Database connection has been closed. 🔒",
        "MESSAGE_PROCESSING_ERROR": "Error processing message: {}"
    }

    ABOUT_MESSAGE = (
        "🤖 *Automation Assistant Bot*\n\n"
        "I am your personal AI assistant for automating daily tasks and improving efficiency.\n\n"
        "**💬 Ask me about your automation challenges!**\n"
        "Simply describe your current problem or need in a message, and I'll help you find the best automation solution.\n\n"
        "**I can help you:**\n"
        "• 🤖 Analyze problems and suggest automation solutions\n"
        "• 💼 Optimize work and business processes\n"
        "• 📱 Recommend digital automation tools\n"
        "• 🎯 Improve personal productivity\n"
        "• 📚 Provide automation knowledge base\n"
        "• 📅 Schedule automation consultations\n\n"
        "**💡 Examples of questions you can ask:**\n"
        "• \"How can I automate my email responses?\"\n"
        "• \"I need to sync data between Google Sheets and CRM\"\n"
        "• \"Help me automate social media posting\"\n\n"
        "*Just type your question as a regular message!*"
    )

    HELP_MESSAGE = (
        "🔍 *Available Commands*\n\n"
        "/start - Start the bot\n"
        "/about - Learn about this bot\n"
        "/help - Show this help message\n"
        "/videos - List available videos\n"
        "/search [term] - Search through video content\n"
        "/info - Get video summaries\n"
        "/history - View your search history\n\n"
        "You can also:\n"
        "• Send text messages to ask questions\n"
        "• Send voice messages for voice-to-text conversion"
    )

    SETTINGS_CMD = {
        "main_menu": "⚙️ <b>Settings</b>\n\nSelect a section to configure:",
        "response_format": "💬 Response format selection",
        "notifications": "🔔 Notification settings",
        "quiz_section": "📝 Quiz section",
        "response_format_menu": "💬 <b>Response format selection</b>\n\nChoose your preferred response format:",
        "notifications_menu": "🔔 <b>Notification settings</b>\n\nConfigure notifications for new materials:",
        "quiz_menu": "📝 <b>Quiz section</b>\n\nTest your knowledge:",
        "format_text": "📝 Text message",
        "format_audio": "🎵 Audio message",
        "notifications_on": "🔔 Enable notifications",
        "notifications_off": "🔕 Disable notifications",
        "start_quiz": "🎯 Start quiz",
        "quiz_results": "📊 My results",
        "back_button": "⬅️ Back",
        "format_saved": lambda format_type: f"✅ Response format changed to <b>{format_type}</b>\n\nAnswers will now come in the selected format.",
        "notifications_saved": lambda status: f"✅ Notifications <b>{status}</b>\n\nSetting saved successfully.",
        "quiz_in_development": "🎯 <b>Quiz in development</b>\n\nQuiz functionality will be available soon!\nStay tuned for updates.",
        "quiz_no_results": "📊 <b>Quiz results</b>\n\nYou don't have any quiz results yet.\nTake a quiz to see your achievements!",
        "setting_save_error": "Error saving settings",
        # Status display texts
        "status_audio": "🔊 Audio",
        "status_text": "📝 Text",
        "status_notifications_on": "🔔 Enabled",
        "status_notifications_off": "🔕 Disabled",
        "status_lang_english": "🇬🇧 English",
        "status_lang_russian": "🇷🇺 Русский",
        # Dynamic button texts
        "button_switch_to_text": "📝 Switch to text responses",
        "button_switch_to_audio": "🎧 Switch to audio responses",
        "button_enable_notifications": "🔔 Enable notifications",
        "button_disable_notifications": "🔕 Disable notifications",
        "language_section": "🌐 Change language"
    }

    SEARCH_CMD = {
        "no_query": "Please provide a search term after /search command.\nExample: /search climate change",
    }

    INFO_CMD = {
        "no_summaries": "📭 No summary files are currently available.",
        "select_summary": "📋 Select a video to view its summary:",
        "summary_header": lambda filename: f"📝 Summary for {filename}:\n\n",
        "file_error": "❌ Sorry, there was an error reading the summary file. Please try again later."
    }

    HISTORY_CMD = {
        "no_history": "📭 You haven't made any search requests yet.",
        "history_header": "📋 Your recent search history:\n\n",
        "error": "❌ Sorry, there was an error retrieving your history. Please try again later."
    }

    AUDIO_CMD = {
        "processing": "🎧 Processing your audio message...",
        "no_speech_detected": "❌ Sorry, I couldn't detect any speech in this audio.",
        "transcription_error": "❌ Sorry, I had trouble understanding the audio. Please try again.",
        "processing_error": "❌ An error occurred while processing your audio message. Please try again.",
    }

    QUESTION_CMD = {
        "processing": "🤔 Processing your question...",
        "voice_processing": "🎤 Transcribing voice message...",
        "error": "An error occurred while processing your question. Please try again or contact the administrator."
    }

    AUTOMATIONS_CMD = {
        "welcome": (
            "🛒 *Marketplace*\n\n"
            "You can find here real workflows for automate the routine that you can use immediately\n\n"
            "Choose a category:"
        ),
        "category_header": lambda category_name: f"⚙️ <b>Automations: {category_name}</b>\n\nChoose an automation:",
        "category_label": lambda category_name: f"📂 Category: {category_name}\n",
        "open_link": lambda url: f"🔗 <a href='{url}'>Open on n8n.io</a>\n",
        "no_examples_found": "No automation examples found yet.",
        "no_examples_in_category": lambda category_name: f"No automation examples found in '{category_name}' category yet.",
        "automation_detail_header": lambda filename: f"🤖 <b>{filename}</b>\n\n",
        "automation_description": lambda description: f"📝 <b>Description:</b>\n{description}\n\n",
        "get_automation_button": "✅ Get this automation",
        "back_button": "⬅️ Back",
        "back_to_category": "⬅️ Back to category",
        "loading_error": "Error loading automations.",
        "choose_workflow": "Choose an Automation:",
        # Workflow detail labels
        "workflow_detail_title": "🔧 Automation Details",
        "workflow_name_label": "📋 Name:",
        "workflow_category_label": "🗂️ Category:",
        "workflow_description_label": "📄 Description:",
        "request_automation_button": "✅ Request this automation",
        # Subcategory display
        "available_automations": lambda count: f"📋 <b>Available Automations</b> ({count}):",
        "no_automations_available": "📋 <b>No automations available in this category yet.</b>",
        # Navigation buttons
        "back_to_marketplace_button": "🏠 Back to Marketplace",
        "back_to_marketplace_short_button": "⬅️ Back to Marketplace",
        "previous_page_button": "⬅️ Previous",
        "next_page_button": "Next ➡️"
    }

    RAG_RESPONSES = {
        "processing": "🤔 Processing your question...",
        "voice_processing": "🎤 Processing voice message...",
        "sources_found": lambda count: f"Sources found: {count}",
        "no_sources": "No sources found for your query, but I'll try to help based on general knowledge.",
        "error": "An error occurred while processing your question. Please try again or contact the administrator.",
        "similar_automations_found": lambda count: f"🔍 **Found {count} similar automations in our database**",
        "explore_examples": "Click the buttons below to explore specific examples:"
    }

    BOOKING_CMD = {
        "title": "📅 *Session Booking*\n\n",
        "description": "Choose a convenient time for consultation through Calendly.\nClick the button below to open the calendar:",
        "button_text": "📅 Book a session",
        "loading_error": "Error loading booking calendar."
    }

    HELP_CMD = {
        "ask_question": "Please write your question in free form and in <b>one message</b>!",
        "message_received": "Your message has been received. Expect a response within 24 hours. Thank you for being with us."
    }

    SUBSCRIBE_CMD = {
        "title": "🔥 <b>Premium Subscription</b>\n\n",
        "description": (
            "Get full access to all automation capabilities:\n\n"
            "🔍 <b>Unlimited Search</b> - unlimited queries in automation database\n"
            "⚙️ <b>More Workflows & Agents</b> - access to exclusive solutions\n"
            "💡 <b>Most Current Insights</b> - be first to know about new trends\n"
            "🎯 <b>Priority Support</b> - fast responses to your questions\n\n"
            "Price: <b>€20/month</b>\n\n"
            "Click the button below to subscribe:"
        ),
        "button_text": "💳 Subscribe Now",
        "loading_error": "Error loading payment page.",
        "payment_success": "✅ <b>Subscription successful!</b>\n\nYou now have access to all premium features. Welcome to the automation club! 🚀",
        "payment_error": "❌ Payment processing error occurred. Please try again or contact support."
    }

    PAY_CMD = {
        "title": "💳 *Service Payment*\n\n",
        "description": "Click the button below for secure payment through Stripe:",
        "button_text": "💳 Pay for service",
        "loading_error": "Error loading payment page."
    }

    RAG_PROMPT = """You are an n8n automation expert. Answer ONLY automation-related questions.

IMPORTANT: If the question is NOT related to task automation, processes, or workflows, respond EXACTLY:
"I can only answer automation-related questions. Maybe you'd like to know how automation could support this?"

For automation questions, provide a brief response with these 3 sections:

Response format:
🤖 n8n Automation Solution (2–3 sentences)
Describe how to automate this task using n8n workflows. Mention node types or logic if helpful, but avoid deep technical detail.

✅ Benefits (3 points)
• Time saving: [estimated hours/week saved]
• Error reduction: [approx. % improvement]
• Scalability: [growth potential]

💰 Cost Savings (1–2 sentences)
Estimate monthly savings in dollars based on hours saved × $25/hour (adjustable if needed).

Rules:
Focus on the most effective automation only
Use realistic numbers and percentages (avoid random placeholders)
Maximum 150 words total

IMPORTANT: Respond in the same language as the user's question."""
