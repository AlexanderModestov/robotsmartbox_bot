#!/usr/bin/env python3
"""
Translation Service for RoboSmartBox Bot

Handles language detection and translation using Google Translate API
for supporting multilingual queries and responses.
"""

import os
import logging
from typing import Optional, Dict, Any
from deep_translator import GoogleTranslator
from deep_translator.constants import GOOGLE_LANGUAGES_TO_CODES
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TranslationService:
    """Service for handling language detection and translation"""

    def __init__(self):
        """Initialize the translation service"""
        self.supported_languages = {
            'en': 'english',
            'ru': 'russian',
            'es': 'spanish',
            'fr': 'french',
            'de': 'german',
            'it': 'italian',
            'pt': 'portuguese',
            'zh': 'chinese',
            'ja': 'japanese',
            'ko': 'korean'
        }
        logger.info("Translation service initialized")

    def detect_language(self, text: str) -> Optional[str]:
        """
        Detect the language of the given text

        Args:
            text (str): Text to analyze

        Returns:
            Optional[str]: Language code (e.g., 'ru', 'en') or None if detection fails
        """
        try:
            if not text or not text.strip():
                return None

            # Use simple heuristics for common languages
            # Cyrillic script detection for Russian
            if any('\u0400' <= char <= '\u04FF' for char in text):
                logger.info("Detected language: ru (Cyrillic script)")
                return 'ru'

            # Default to English if no other language detected
            logger.info("Detected language: en (default)")
            return 'en'

        except Exception as e:
            logger.error(f"Error detecting language: {e}")
            return None

    def translate_text(self, text: str, target_language: str, source_language: str = 'auto') -> Optional[str]:
        """
        Translate text from source language to target language

        Args:
            text (str): Text to translate
            target_language (str): Target language code (e.g., 'en', 'ru')
            source_language (str): Source language code (default: 'auto' for auto-detection)

        Returns:
            Optional[str]: Translated text or None if translation fails
        """
        try:
            if not text or not text.strip():
                return text

            # Skip translation if source and target are the same
            if source_language == target_language:
                return text

            # Auto-detect source language if needed
            if source_language == 'auto':
                source_language = self.detect_language(text) or 'en'

            translator = GoogleTranslator(source=source_language, target=target_language)
            translated_text = translator.translate(text)

            logger.info(f"Translated from {source_language} to {target_language}")
            return translated_text

        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return None

    def translate_to_english(self, text: str, source_language: str = 'auto') -> Optional[str]:
        """
        Translate text to English (for database search)

        Args:
            text (str): Text to translate
            source_language (str): Source language code (default: 'auto')

        Returns:
            Optional[str]: English translation or None if translation fails
        """
        return self.translate_text(text, 'en', source_language)

    def translate_from_english(self, text: str, target_language: str) -> Optional[str]:
        """
        Translate text from English to target language (for response)

        Args:
            text (str): English text to translate
            target_language (str): Target language code

        Returns:
            Optional[str]: Translated text or None if translation fails
        """
        return self.translate_text(text, target_language, 'en')

    def process_multilingual_query(self, query: str, user_language: str = None) -> Dict[str, Any]:
        """
        Process a multilingual query for database search

        Args:
            query (str): User's query in their language
            user_language (str): User's preferred language (optional)

        Returns:
            Dict[str, Any]: Contains original_query, detected_language, english_query, and user_language
        """
        try:
            # Detect language if not provided
            detected_language = self.detect_language(query)

            # Use detected language or fallback to user's language or English
            query_language = detected_language or user_language or 'en'

            # Translate to English for database search (if not already English)
            if query_language == 'en':
                english_query = query
            else:
                english_query = self.translate_to_english(query, query_language)
                if not english_query:
                    english_query = query  # Fallback to original if translation fails

            return {
                'original_query': query,
                'detected_language': detected_language,
                'query_language': query_language,
                'english_query': english_query,
                'user_language': user_language or query_language
            }

        except Exception as e:
            logger.error(f"Error processing multilingual query: {e}")
            return {
                'original_query': query,
                'detected_language': None,
                'query_language': 'en',
                'english_query': query,
                'user_language': 'en'
            }

    def format_response(self, english_response: str, target_language: str) -> str:
        """
        Format response in the user's language

        Args:
            english_response (str): Response in English
            target_language (str): User's language code

        Returns:
            str: Response in user's language
        """
        try:
            # Return English response if target is English
            if target_language == 'en':
                return english_response

            # Translate response to user's language
            translated_response = self.translate_from_english(english_response, target_language)

            # Return translated response or fallback to English
            return translated_response if translated_response else english_response

        except Exception as e:
            logger.error(f"Error formatting response: {e}")
            return english_response  # Fallback to English

    def get_language_name(self, language_code: str) -> str:
        """
        Get human-readable language name from code

        Args:
            language_code (str): Language code (e.g., 'ru', 'en')

        Returns:
            str: Language name (e.g., 'Russian', 'English')
        """
        return self.supported_languages.get(language_code, language_code).title()

    def is_supported_language(self, language_code: str) -> bool:
        """
        Check if language is supported

        Args:
            language_code (str): Language code to check

        Returns:
            bool: True if supported, False otherwise
        """
        return language_code in self.supported_languages

# Example usage and testing
if __name__ == "__main__":
    # Test the translation service
    service = TranslationService()

    # Test Russian query
    russian_query = "Как создать чатбота с искусственным интеллектом?"
    result = service.process_multilingual_query(russian_query)
    print(f"Original: {result['original_query']}")
    print(f"Detected: {result['detected_language']}")
    print(f"English: {result['english_query']}")

    # Test response formatting
    english_response = "You can create an AI chatbot using n8n workflows and OpenAI integration."
    russian_response = service.format_response(english_response, 'ru')
    print(f"Response in Russian: {russian_response}")