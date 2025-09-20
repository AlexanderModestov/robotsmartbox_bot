import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import Config
from bot.supabase_client import SupabaseClient
from bot.commands.commands import start_router, content_router
from bot.handlers.handlers import question_router
from bot.callbacks.language_callbacks import language_router
from bot.callbacks.settings_callbacks import settings_router
from bot.callbacks.marketplace_callbacks import marketplace_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main bot function"""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated successfully")
        
        # Debug URL values
        logger.info(f"SUPABASE_URL: {Config.SUPABASE_URL}")
        logger.info(f"WEBAPP_URL: {Config.WEBAPP_URL}")
        logger.info(f"CALENDLY_LINK: {Config.CALENDLY_LINK}")
        logger.info(f"STRIPE_PAYMENT_LINK: {Config.STRIPE_PAYMENT_LINK}")
        
        # Initialize bot and dispatcher
        try:
            bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
            logger.info("Bot initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Bot: {e}")
            raise
        
        dp = Dispatcher(storage=MemoryStorage())
        
        # Initialize Supabase client
        try:
            supabase_client = SupabaseClient(
                supabase_url=Config.SUPABASE_URL,
                supabase_key=Config.SUPABASE_KEY
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Supabase client with URL '{Config.SUPABASE_URL}': {e}")
            raise
        
        # Add dependency injection for supabase client
        dp.workflow_data.update(supabase_client=supabase_client)
        
        # Include routers
        dp.include_router(start_router)
        dp.include_router(content_router)
        dp.include_router(question_router)
        dp.include_router(language_router)
        dp.include_router(settings_router)
        dp.include_router(marketplace_router)
        
        # Add middleware to inject supabase client
        @dp.message.outer_middleware()
        async def inject_supabase(handler, event, data):
            data['supabase_client'] = supabase_client
            return await handler(event, data)
        
        @dp.callback_query.outer_middleware()
        async def inject_supabase_callback(handler, event, data):
            data['supabase_client'] = supabase_client
            return await handler(event, data)
        
        logger.info("Bot initialized successfully")
        
        # Start polling
        await dp.start_polling(bot, allowed_updates=['message', 'callback_query'])
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")