"""
N8N Workflow Summary Agent Package

This package contains the agent for processing n8n workflow files
and updating the documents table in Supabase.
"""

from .agent import N8NSummaryAgent

__all__ = ['N8NSummaryAgent']