import asyncio
import os
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from .models import User

class SupabaseClient:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client: Client = create_client(supabase_url, supabase_key)
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        try:
            # Use asyncio.to_thread to run the synchronous operation in a thread
            response = await asyncio.to_thread(
                lambda: self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()
            )
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    async def create_or_update_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        try:
            existing_user = await self.get_user_by_telegram_id(user_data['telegram_id'])
            
            if existing_user:
                response = await asyncio.to_thread(
                    lambda: self.client.table('users').update(user_data).eq('telegram_id', user_data['telegram_id']).execute()
                )
            else:
                response = await asyncio.to_thread(
                    lambda: self.client.table('users').insert(user_data).execute()
                )
            
            if response.data:
                return User(**response.data[0])
            return None
        except Exception as e:
            print(f"Error creating/updating user: {e}")
            return None
    
    async def search_automations_by_similarity(self, query_embedding: List[float], limit: int = 3, threshold: float = None, user_language: str = 'en') -> List[Dict[str, Any]]:
        """
        Search for similar automation documents using Supabase pgvector similarity

        Args:
            query_embedding: Query vector embedding from OpenAI (3072 dimensions)
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0.0 to 1.0)
            user_language: User's language ('ru' or 'en') for localized results

        Returns:
            List of automation documents ranked by vector similarity
        """
        # Get threshold from environment variable if not provided
        if threshold is None:
            threshold = float(os.getenv('SIMILARITY_THRESHOLD', '0.3'))

        try:
            print(f"🔍 Searching for similar automations with threshold={threshold}, limit={limit}")

            # Use pgvector cosine similarity with proper SQL
            # Convert similarity threshold to cosine distance (1 - similarity)
            max_distance = 1.0 - threshold

            # Create a PostgreSQL function call or use direct SQL
            response = await asyncio.to_thread(
                lambda: self.client.rpc('search_similar_documents', {
                    'query_embedding': query_embedding,
                    'similarity_threshold': threshold,
                    'result_limit': limit
                }).execute()
            )

            if not response.data:
                print("🔍 No similar automations found above threshold")
                return []

            # Format results with localization
            results = []
            for doc in response.data:
                # Use localized fields based on user language
                if user_language == 'ru':
                    title = doc.get('name_ru') or doc.get('name', 'Unnamed')
                    short_description = doc.get('short_description_ru') or doc.get('short_description', '')
                    description = doc.get('description_ru') or doc.get('description', '')
                else:
                    title = doc.get('name', 'Unnamed')
                    short_description = doc.get('short_description', '')
                    description = doc.get('description', '')

                # Format title
                if title and title.endswith('.json'):
                    title = title[:-5]  # Remove .json extension
                if title:
                    title = title.replace('-', ' ').replace('_', ' ').title()
                else:
                    title = 'Unnamed Automation' if user_language == 'en' else 'Безымянная автоматизация'

                results.append({
                    'id': doc['id'],
                    'title': title,
                    'short_description': short_description,
                    'description': description,
                    'url': doc.get('url', ''),
                    'category': doc.get('category', 'Uncategorized'),
                    'subcategory': doc.get('subcategory', ''),
                    'tags': doc.get('tags', []),
                    'similarity': doc.get('similarity', 0.0)
                })

            print(f"🔍 Found {len(results)} similar automations above threshold {threshold}")
            for i, doc in enumerate(results):
                print(f"🔍 Rank {i+1}: {doc['title']} (similarity: {doc.get('similarity', 'N/A')})")

            return results

        except Exception as e:
            print(f"Error in pgvector similarity search: {e}")
            return []
    
    
    
    async def create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[User]:
        """Create user only if doesn't exist - for handlers compatibility"""
        # Check if user already exists
        existing_user = await self.get_user_by_telegram_id(telegram_id)
        if existing_user:
            return existing_user  # Don't update, just return existing user

        # Only create new user if doesn't exist
        user_data = {
            'telegram_id': telegram_id,
            'username': username
        }
        # Remove None values to avoid column errors
        user_data = {k: v for k, v in user_data.items() if v is not None}
        
        try:
            response = await asyncio.to_thread(
                lambda: self.client.table('users').insert(user_data).execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    async def update_user_payment_status(self, telegram_id: int, payment_status: bool, payment_amount: float = None, payment_currency: str = None) -> bool:
        """Update user payment status"""
        try:
            from datetime import datetime
            
            update_data = {
                'payment_status': payment_status,
                'payment_date': datetime.now().isoformat() if payment_status else None
            }
            
            if payment_amount is not None:
                update_data['payment_amount'] = payment_amount
            if payment_currency is not None:
                update_data['payment_currency'] = payment_currency
            
            response = await asyncio.to_thread(
                lambda: self.client.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
            )
            
            if response.data:
                print(f"✅ Updated payment status for user {telegram_id}: {payment_status}")
                return True
            else:
                print(f"❌ Failed to update payment status for user {telegram_id}")
                return False
                
        except Exception as e:
            print(f"Error updating payment status: {e}")
            return False
    
    async def update_user_payment_status_by_email(self, email: str, payment_status: bool, payment_amount: float = None, payment_currency: str = None) -> bool:
        """Update user payment status by email (if email field exists)"""
        try:
            from datetime import datetime
            
            update_data = {
                'payment_status': payment_status,
                'payment_date': datetime.now().isoformat() if payment_status else None
            }
            
            if payment_amount is not None:
                update_data['payment_amount'] = payment_amount
            if payment_currency is not None:
                update_data['payment_currency'] = payment_currency
            
            # Note: This assumes you have an email field in users table
            # You might need to add email field to users table first
            response = await asyncio.to_thread(
                lambda: self.client.table('users').update(update_data).eq('email', email).execute()
            )
            
            if response.data:
                print(f"✅ Updated payment status for user with email {email}: {payment_status}")
                return True
            else:
                print(f"❌ Failed to update payment status for user with email {email}")
                return False
                
        except Exception as e:
            print(f"Error updating payment status by email: {e}")
            return False

    async def update_user_subscription(self, subscription_data: Dict[str, Any]) -> bool:
        """
        Update user subscription status

        Args:
            subscription_data: Dictionary containing subscription fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            telegram_id = subscription_data.get('telegram_id')
            if not telegram_id:
                print("Error: telegram_id is required for subscription update")
                return False

            response = await asyncio.to_thread(
                lambda: self.client.table('users').update(subscription_data).eq('telegram_id', telegram_id).execute()
            )

            if response.data:
                print(f"✅ Updated subscription for user {telegram_id}: {subscription_data.get('subscription_status', 'unknown')}")
                return True
            else:
                print(f"❌ Failed to update subscription for user {telegram_id}")
                return False

        except Exception as e:
            print(f"Error updating user subscription: {e}")
            return False