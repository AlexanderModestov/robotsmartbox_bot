class Messages:
    START_CMD = {
        "welcome": lambda user_name: (
            f"👋 Hello, {user_name}!\n\n"
            "I'm Vlada's assistant bot. \n"
            "Feel free to ask me any questions! Just type your question, and I'll do my best to help you 💬\nI use the knowledge from Vlada's videos. \n\n"
            "As well I can suggest to you next options:\n"
            "• 🎥 Watching Vlada's educational videos\n"
            "• 🔍 Finding specific topics discussed in the videos\n"
            "• 📝 Getting video summaries\n"
            "• ❓ Answering your questions about any topic\n\n"
            "Extra available commands:\n"
            "/help - Show help message\n"
            "/videos - List available videos\n"
            "/info - Get video summaries\n"
            "Let's start! Write your questions or choose the option from the list."
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
        "🤖 *AI Video Assistant*\n\n"
        "I am your personal AI assistant for managing and interacting with video content. "
        "I can help you:\n\n"
        "• 🎥 List available videos\n"
        "• 🔍 Search through video content\n"
        "• 📝 Show video summaries\n"
        "• 📊 Track your requests\n\n"
        "Use /help to see all available commands."
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
