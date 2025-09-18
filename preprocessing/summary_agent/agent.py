#!/usr/bin/env python3
"""
N8N Workflow Summary Agent

This agent processes JSON files from the n8n folder, extracts content using OpenAI,
and updates the documents table in Supabase with short_description, description, and tags.
"""

import os
import json
import logging
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bot.config import Config

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class N8NSummaryAgent:
    """Agent for processing N8N workflow files and updating documents table"""

    def __init__(self):
        """Initialize the agent with API clients"""
        try:
            self.supabase_url = Config.SUPABASE_URL
            self.supabase_key = Config.SUPABASE_KEY
            self.openai_key = Config.OPENAI_API_KEY
            self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Fallback to environment variables
            self.supabase_url = os.getenv('SUPABASE_URL')
            self.supabase_key = os.getenv('SUPABASE_KEY')
            self.openai_key = os.getenv('OPENAI_API_KEY')
            self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')

        if not all([self.supabase_url, self.supabase_key, self.openai_key]):
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY")

        # Initialize clients
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.openai_client = OpenAI(api_key=self.openai_key)

        logger.info("Initialized N8N Summary Agent")

    def load_n8n_files(self, n8n_dir: str = "n8n") -> List[Dict[str, Any]]:
        """Load all JSON files from the n8n directory"""
        n8n_files = []
        n8n_path = Path(n8n_dir)

        if not n8n_path.exists():
            raise FileNotFoundError(f"N8N directory '{n8n_dir}' not found")

        json_files = list(n8n_path.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files in n8n directory")

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract required fields
                og_url = data.get('metadata', {}).get('ogUrl', '')
                markdown_content = data.get('content', {}).get('markdown', '')

                if og_url and markdown_content:
                    n8n_files.append({
                        'filename': json_file.name,
                        'og_url': og_url,
                        'markdown_content': markdown_content
                    })
                else:
                    logger.warning(f"Missing required fields in {json_file.name}: ogUrl or markdown")

            except Exception as e:
                logger.error(f"Error loading {json_file.name}: {e}")
                continue

        logger.info(f"Successfully loaded {len(n8n_files)} n8n workflow files with required fields")
        return n8n_files

    async def extract_content_with_openai(self, markdown_content: str, filename: str) -> Dict[str, Any]:
        """Extract tags, short_description, and description using OpenAI API"""
        try:
            # Truncate content if too long to avoid token limits
            content = markdown_content[:4000] if len(markdown_content) > 4000 else markdown_content

            system_message = """You are an information-extraction assistant. You receive an unstructured block of text that may contain HTML. Your goal is to identify the single primary service/automation described on the page and return a structured summary.

Tasks

Strip/ignore HTML and boilerplate (navigation, menus, cookie banners, footers, newsletter/signup, unrelated posts).

Identify the single primary service/automation (choose the most prominent: title/emphasis/detail).

Write a concise description of that service (≤ 3000 characters), in the same language as the input.

Produce a short_description (2–3 words) suitable for a Telegram inline button (no punctuation/emojis).

Extract category terms:

Use only explicit terms from the text (no inference or synonyms).

If the input has a dedicated block titled "Categories", "Tags", "Technologies" (or similar), only use terms from that block.

If no such block exists, you may use explicit category-like terms from the main content (e.g., domain, tools, channels, data sources, actions, industries).

Normalize to lowercase, each item 1–3 words, deduplicate, and sort alphabetically.

Rules

Do not invent facts; rely only on the provided text.

If nothing clear is described, set: "description": null, "short_description": null, and "tags": [].

Return only valid JSON (no extra text, code fences, or comments).

Keys must exactly match the schema below.

Output JSON schema (and nothing else)

{
"tags": string[],
"short_description": string|null,
"description": string|null
}"""

            assistant_message = """Acknowledge the input internally and output only the JSON object per the schema.
Constraints:

short_description: 2–3 words, same language as input, no punctuation/emojis.

description: up to 3000 characters, same language as input, focuses on what the service automates and how it works (no marketing fluff).

tags: explicit terms only; prefer "Categories/Tags/Technologies" block if present; otherwise use explicit category-like terms from main content; lowercase, 1–3 words, deduped, sorted.

If unclear, output:
{
"tags": [],
"short_description": null,
"description": null
}

Return nothing besides the JSON."""

            user_message = f"Please analyze the following unstructured text with HTML and return the JSON per the rules: {content}"

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "assistant", "content": assistant_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3
            )

            response_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                # Extract JSON from response
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    extracted_data = json.loads(json_str)
                else:
                    raise ValueError("No JSON found in response")

                # Validate required fields
                required_fields = ['tags', 'short_description', 'description']
                for field in required_fields:
                    if field not in extracted_data:
                        raise ValueError(f"Missing field: {field}")

                # Ensure tags is a list
                if not isinstance(extracted_data['tags'], list):
                    extracted_data['tags'] = []

                logger.info(f"Successfully extracted content for {filename}")
                return extracted_data

            except (json.JSONDecodeError, ValueError) as parse_error:
                logger.error(f"Error parsing OpenAI response for {filename}: {parse_error}")
                logger.error(f"Raw response: {response_text}")

                # Return fallback data
                return {
                    "tags": [],
                    "short_description": "",
                    "description": ""
                }

        except Exception as e:
            logger.error(f"Error extracting content for {filename}: {e}")
            # Return fallback data
            return {
                "tags": [],
                "short_description": "",
                "description": ""
            }

    async def update_document_in_supabase(self, og_url: str, extracted_data: Dict[str, Any]) -> bool:
        """Update document in Supabase using ogUrl to match with url column"""
        try:
            # Update document where url matches og_url
            result = await asyncio.to_thread(
                lambda: self.supabase.table('documents').update({
                    'short_description': extracted_data['short_description'],
                    'description': extracted_data['description'],
                    'tags': extracted_data['tags']
                }).eq('url', og_url).execute()
            )

            if result.data:
                logger.info(f"Successfully updated document with URL: {og_url}")
                return True
            else:
                logger.warning(f"No document found with URL: {og_url}")
                return False

        except Exception as e:
            logger.error(f"Error updating document with URL {og_url}: {e}")
            return False

    async def process_workflow_file(self, file_data: Dict[str, Any]) -> bool:
        """Process a single workflow file"""
        filename = file_data['filename']
        og_url = file_data['og_url']
        markdown_content = file_data['markdown_content']

        try:
            logger.info(f"Processing workflow: {filename}")

            # Extract content using OpenAI
            extracted_data = await self.extract_content_with_openai(markdown_content, filename)

            # Update document in Supabase
            success = await self.update_document_in_supabase(og_url, extracted_data)

            return success

        except Exception as e:
            logger.error(f"Error processing workflow {filename}: {e}")
            return False

    async def process_all_workflows(self, n8n_dir: str = "n8n", batch_size: int = 5):
        """Process all workflow files and update documents table"""
        logger.info("Starting N8N workflow processing")

        try:
            # Load all files
            n8n_files = self.load_n8n_files(n8n_dir)
            if not n8n_files:
                logger.warning("No n8n files found to process")
                return

            total_files = len(n8n_files)
            processed = 0
            updated = 0
            failed = 0

            # Process files in batches to avoid overwhelming the APIs
            for i in range(0, total_files, batch_size):
                batch = n8n_files[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(total_files + batch_size - 1)//batch_size}")

                # Process batch
                tasks = []
                for file_data in batch:
                    tasks.append(self.process_workflow_file(file_data))

                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count results
                for result in results:
                    processed += 1
                    if result is True:
                        updated += 1
                    else:
                        failed += 1
                        if isinstance(result, Exception):
                            logger.error(f"Processing error: {result}")

                # Small delay between batches
                await asyncio.sleep(1)

            logger.info(f"Processing completed: {processed} processed, {updated} updated, {failed} failed")

        except Exception as e:
            logger.error(f"Error during workflow processing: {e}")
            raise

async def main():
    """Main entry point"""
    try:
        agent = N8NSummaryAgent()
        await agent.process_all_workflows()
        logger.info("N8N workflow processing completed successfully!")

    except Exception as e:
        logger.error(f"Failed to process n8n workflows: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())