"""Callback handlers for the bot"""

from .language_callbacks import language_router
from .settings_callbacks import settings_router
from .marketplace_callbacks import marketplace_router

__all__ = ['language_router', 'settings_router', 'marketplace_router']