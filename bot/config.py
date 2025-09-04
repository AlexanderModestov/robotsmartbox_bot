import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_ADMIN_ID = int(os.getenv('TELEGRAM_ADMIN_ID', '0'))
    
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
    GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-4.1-mini')
    SEARCH_LIMIT = int(os.getenv('SEARCH_LIMIT', '5'))
    
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    RATE_LIMIT_REQUESTS_PER_DAY = int(os.getenv('RATE_LIMIT_REQUESTS_PER_DAY', '50'))
    WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-webapp-domain.com')
    CALENDLY_LINK = os.getenv('CALENDLY_LINK', 'https://calendly.com/your-calendar')
    STRIPE_PAYMENT_LINK = os.getenv('STRIPE_PAYMENT_LINK', 'https://buy.stripe.com/your-payment-link')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    
    @classmethod
    def validate(cls):
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True