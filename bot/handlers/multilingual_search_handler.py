#!/usr/bin/env python3
"""
Multilingual Search Handler

Handles user queries in multiple languages by:
1. Detecting the query language
2. Translating to English for database search
3. Performing vector search
4. Translating results back to user's language
"""

import logging
from typing import List, Dict, Any, Optional
from aiogram import types
from aiogram.filters import BaseFilter

from bot.services.translation_service import TranslationService
from bot.supabase_client.client import SupabaseClient

logger = logging.getLogger(__name__)

class MultilingualSearchHandler:
    """Handler for multilingual search functionality"""

    def __init__(self, supabase_client: SupabaseClient):
        """
        Initialize the multilingual search handler

        Args:
            supabase_client (SupabaseClient): Supabase client for database operations
        """
        self.supabase_client = supabase_client
        self.translation_service = TranslationService()
        logger.info("Multilingual search handler initialized")

    async def process_multilingual_query(self, query: str, user_language: str = None) -> Dict[str, Any]:
        """
        Process a multilingual query and return search results

        Args:
            query (str): User's query in their language
            user_language (str): User's preferred language from database

        Returns:
            Dict[str, Any]: Search results with translation info
        """
        try:
            # Process the query for translation
            translation_result = self.translation_service.process_multilingual_query(query, user_language)

            logger.info(f"Processing query: {translation_result['original_query']}")
            logger.info(f"Detected language: {translation_result['detected_language']}")
            logger.info(f"English query: {translation_result['english_query']}")

            # Perform vector search with English query
            search_results = await self.perform_vector_search(translation_result['english_query'])

            # Format results in user's language
            formatted_results = await self.format_search_results(
                search_results,
                translation_result['user_language']
            )

            return {
                'translation_info': translation_result,
                'search_results': search_results,
                'formatted_results': formatted_results,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error processing multilingual query: {e}")
            return {
                'translation_info': None,
                'search_results': [],
                'formatted_results': [],
                'success': False,
                'error': str(e)
            }

    async def perform_vector_search(self, english_query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Perform vector search using English query

        Args:
            english_query (str): Query in English
            limit (int): Maximum number of results to return

        Returns:
            List[Dict[str, Any]]: Search results from database
        """
        try:
            # This is a placeholder - you'll need to implement actual vector search
            # based on your existing search functionality

            # Example implementation:
            # 1. Generate embedding for english_query
            # 2. Search documents table using cosine similarity
            # 3. Return top results

            # For now, returning a mock result
            search_results = [
                {
                    'id': 1,
                    'name': 'Example Workflow',
                    'description': 'This is an example workflow description',
                    'url': 'https://example.com',
                    'similarity': 0.85
                }
            ]

            logger.info(f"Found {len(search_results)} results for query: {english_query}")
            return search_results

        except Exception as e:
            logger.error(f"Error performing vector search: {e}")
            return []

    async def format_search_results(self, results: List[Dict[str, Any]], target_language: str) -> List[Dict[str, Any]]:
        """
        Format search results in user's language

        Args:
            results (List[Dict[str, Any]]): Search results in English
            target_language (str): Target language for translation

        Returns:
            List[Dict[str, Any]]: Formatted results in user's language
        """
        try:
            formatted_results = []

            for result in results:
                # Translate description to user's language
                original_description = result.get('description', '')
                translated_description = self.translation_service.format_response(
                    original_description,
                    target_language
                )

                # Create formatted result
                formatted_result = {
                    'id': result.get('id'),
                    'name': result.get('name'),
                    'original_description': original_description,
                    'translated_description': translated_description,
                    'url': result.get('url'),
                    'similarity': result.get('similarity', 0.0)
                }

                formatted_results.append(formatted_result)

            logger.info(f"Formatted {len(formatted_results)} results for language: {target_language}")
            return formatted_results

        except Exception as e:
            logger.error(f"Error formatting search results: {e}")
            return results  # Return original results as fallback

    def create_response_message(self, results: Dict[str, Any]) -> str:
        """
        Create a response message for the user

        Args:
            results (Dict[str, Any]): Search results with translation info

        Returns:
            str: Formatted response message
        """
        try:
            if not results['success']:
                error_msg = "Sorry, there was an error processing your request."
                target_lang = 'en'  # Default to English for error messages
                return self.translation_service.format_response(error_msg, target_lang)

            translation_info = results['translation_info']
            formatted_results = results['formatted_results']
            target_language = translation_info['user_language']

            if not formatted_results:
                no_results_msg = "No relevant workflows found for your query."
                return self.translation_service.format_response(no_results_msg, target_language)

            # Build response message
            response_parts = []

            # Add header
            header = f"Found {len(formatted_results)} workflow(s) for your query:"
            translated_header = self.translation_service.format_response(header, target_language)
            response_parts.append(translated_header)
            response_parts.append("")  # Empty line

            # Add results
            for i, result in enumerate(formatted_results, 1):
                result_text = f"{i}. **{result['name']}**\n"
                result_text += f"{result['translated_description']}\n"
                result_text += f"🔗 {result['url']}\n"
                response_parts.append(result_text)

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(f"Error creating response message: {e}")
            return "An error occurred while processing your request."

# Example usage in your bot handlers
class MultilingualFilter(BaseFilter):
    """Filter to detect multilingual queries"""

    def __init__(self, translation_service: TranslationService):
        self.translation_service = translation_service

    async def __call__(self, message: types.Message) -> bool:
        """Check if message needs multilingual processing"""
        if not message.text:
            return False

        # Detect if message is not in English
        detected_lang = self.translation_service.detect_language(message.text)
        return detected_lang and detected_lang != 'en'

# Example handler function (to be integrated into your existing handlers)
async def handle_multilingual_search(message: types.Message, multilingual_handler: MultilingualSearchHandler, user_language: str = None):
    """
    Handle multilingual search request

    Args:
        message (types.Message): Telegram message
        multilingual_handler (MultilingualSearchHandler): Handler instance
        user_language (str): User's preferred language from database
    """
    try:
        query = message.text

        # Process the multilingual query
        results = await multilingual_handler.process_multilingual_query(query, user_language)

        # Create response message
        response_text = multilingual_handler.create_response_message(results)

        # Send response
        await message.reply(response_text, parse_mode="Markdown")

        # Log the interaction
        logger.info(f"Processed multilingual query from user {message.from_user.id}")

    except Exception as e:
        logger.error(f"Error handling multilingual search: {e}")
        await message.reply("Sorry, there was an error processing your request.")

if __name__ == "__main__":
    # Test the multilingual handler
    import asyncio

    async def test_handler():
        # This would be your actual supabase client
        supabase_client = None  # Replace with actual client

        handler = MultilingualSearchHandler(supabase_client)

        # Test Russian query
        russian_query = "Как создать чатбота с искусственным интеллектом?"
        results = await handler.process_multilingual_query(russian_query, 'ru')

        print("Translation Info:", results['translation_info'])
        print("Formatted Response:", handler.create_response_message(results))

    # asyncio.run(test_handler())