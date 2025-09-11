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
        "I am your personal AI assistant for automating daily tasks and improving efficiency. "
        "I can help you:\n\n"
        "• 🤖 Analyze problems and suggest automation solutions\n"
        "• 💼 Optimize work and business processes\n"
        "• 📱 Recommend digital automation tools\n"
        "• 🎯 Improve personal productivity\n"
        "• 📚 Provide automation knowledge base\n"
        "• 📅 Schedule automation consultations\n\n"
        "Use /help to ask questions directly."
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
        "all_automations_button": "🤖 All Automations",
        "all_automations_header": "🤖 <b>All Automations</b>\n\nChoose an automation:",
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
        "loading_error": "Error loading automations."
    }

    BOOKING_CMD = {
        "title": "📅 *Session Booking*\n\n",
        "description": "Choose a convenient time for consultation through Calendly.\nClick the button below to open the calendar:",
        "button_text": "📅 Book a session",
        "loading_error": "Error loading booking calendar."
    }

    PAY_CMD = {
        "title": "💳 *Service Payment*\n\n",
        "description": "Click the button below for secure payment through Stripe:",
        "button_text": "💳 Pay for service",
        "loading_error": "Error loading payment page."
    }
