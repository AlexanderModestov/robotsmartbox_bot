"""
Run the bot with payment webhook support
This script starts both the Telegram bot and the webhook server for payment processing
"""

import asyncio
import logging
import multiprocessing
import uvicorn
from bot.main import main as run_bot
from bot.payments.webhook_server import app
from bot.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_webhook_server():
    """Run the webhook server in a separate process"""
    try:
        port = int(getattr(Config, 'WEBHOOK_PORT', 8000))
        logger.info(f"Starting webhook server on port {port}")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Error running webhook server: {e}")

async def run_bot_async():
    """Run the bot asynchronously"""
    try:
        logger.info("Starting Telegram bot")
        await run_bot()
    except Exception as e:
        logger.error(f"Error running bot: {e}")

def main():
    """Main function to start both services"""
    logger.info("🚀 Starting RoboSmartBox Bot with Payment Support")

    # Validate configuration
    try:
        Config.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return

    # Check if Stripe webhook secret is configured
    if not Config.STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured - webhook verification will fail")

    # Start webhook server in a separate process
    webhook_process = multiprocessing.Process(target=run_webhook_server)
    webhook_process.start()

    try:
        # Run the bot in the main process
        asyncio.run(run_bot_async())
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Clean up webhook process
        logger.info("Shutting down webhook server")
        webhook_process.terminate()
        webhook_process.join(timeout=5)
        if webhook_process.is_alive():
            webhook_process.kill()

        logger.info("All services stopped")

if __name__ == "__main__":
    main()