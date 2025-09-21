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

        # Initialize failed files list
        self.failed_files = []

        logger.info("Initialized N8N Summary Agent")

    def load_n8n_files(self, n8n_dir: str = "n8n") -> List[Dict[str, Any]]:
        """Load all JSON files from the n8n directory"""
        n8n_files = []
        n8n_path = Path(n8n_dir)

        if not n8n_path.exists():
            raise FileNotFoundError(f"N8N directory '{n8n_dir}' not found")

        json_files = list(n8n_path.glob("*.json"))
        print("Всего json файлов: ", len(json_files))
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
            system_message = """You are an expert at analyzing n8n workflow documentation and extracting structured information. You will receive markdown content from an n8n workflow template page and must extract specific fields in JSON format.

Your task is to analyze the content and extract:
1. The workflow name and purpose
2. Categories/tags from the page
3. Technology stack (nodes, services, APIs used)
4. Descriptions in both English and Russian

Follow these extraction rules carefully:

TAGS: Extract from "Categories" section only. Use exact category names as shown, convert to lowercase, remove special characters. If no Categories section exists, return empty array.

STACK: Extract all mentioned nodes, services, APIs, and tools from the workflow description. Look for:
- Node types (e.g., "HTTP Request Node", "Webhook Node", "Switch Node")
- Services and APIs (e.g., "Fastmail API", "OpenAI")
- Tools and platforms mentioned
- Convert to lowercase, use 1-2 words per item, sort alphabetically

NAME: Extract the exact workflow title as it appears in the content

DESCRIPTIONS:
- short_description: 2-3 words describing the main function
- description: Detailed explanation of what the workflow does and how it works (max 3000 chars)

Provide both English and Russian translations for names and descriptions."""

            user_message = f"""Analyze this n8n workflow template content and extract the required fields in JSON format:

{markdown_content}

Return ONLY a valid JSON object with this exact structure:
{{
  "name": "string|null",
  "name_ru": "string|null",
  "short_description": "string|null",
  "short_description_ru": "string|null",
  "description": "string|null",
  "description_ru": "string|null",
  "tags": ["array of strings"],
  "stack": ["array of strings"]
}}

Guidelines:
- name: Exact workflow title as it appears in the content
- name_ru: Russian translation of the exact name
- short_description: 2-3 words describing main function (no punctuation)
- short_description_ru: Russian translation of short_description
- description: Detailed explanation of workflow functionality (max 3000 chars)
- description_ru: Russian translation of description
- tags: Categories from "Categories" section only, lowercase
- stack: All nodes/services/APIs/tools mentioned, lowercase, 1-2 words each, sorted

For the example file, expected output should have:
- tags: ["personal productivity"]
- stack: ["fastmail", "html", "http request", "switch", "webhook"]"""

            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,  # Lower temperature for more consistent extraction
                max_tokens=2000,
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            response_text = response.choices[0].message.content.strip()

            try:
                # Parse the JSON response
                extracted_data = json.loads(response_text)

                # Validate required fields exist
                required_fields = ["name", "name_ru", "short_description", "short_description_ru",
                                 "description", "description_ru", "tags", "stack"]

                for field in required_fields:
                    if field not in extracted_data:
                        extracted_data[field] = None if field not in ["tags", "stack"] else []

                # Clean and normalize arrays
                if extracted_data.get("tags"):
                    extracted_data["tags"] = sorted(list(set([
                        tag.lower().strip() for tag in extracted_data["tags"] if tag and tag.strip()
                    ])))

                if extracted_data.get("stack"):
                    extracted_data["stack"] = sorted(list(set([
                        item.lower().strip() for item in extracted_data["stack"] if item and item.strip()
                    ])))

                logger.info(f"Successfully extracted content for {filename}")
                return extracted_data

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for {filename}: {e}")
                logger.error(f"Response was: {response_text}")
                raise

        except Exception as e:
            logger.error(f"Error extracting content for {filename}: {e}")
            return {
                "name": None,
                "name_ru": None,
                "short_description": None,
                "short_description_ru": None,
                "description": None,
                "description_ru": None,
                "tags": [],
                "stack": []
            }

    async def update_document_in_supabase(self, og_url: str, extracted_data: Dict[str, Any]) -> bool:
        """Update document in Supabase using ogUrl to match with url column"""
        try:
            # Update document where url matches og_url
            result = await asyncio.to_thread(
                lambda: self.supabase.table('documents').update({
                    'name_ru': extracted_data['name_ru'],
                    'short_description': extracted_data['short_description'],
                    'short_description_ru': extracted_data['short_description_ru'],
                    'description': extracted_data['description'],
                    'description_ru': extracted_data['description_ru'],
                    'tags': extracted_data['tags'],
                    'stack': extracted_data['stack']
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

            if not success:
                self.failed_files.append(filename)

            return success

        except Exception as e:
            logger.error(f"Error processing workflow {filename}: {e}")
            self.failed_files.append(filename)
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

            # Save failed files to txt file
            if self.failed_files:
                failed_files_path = "failed_files.txt"
                with open(failed_files_path, 'w', encoding='utf-8') as f:
                    for filename in self.failed_files:
                        f.write(f"{filename}\n")
                logger.info(f"Saved {len(self.failed_files)} failed filenames to {failed_files_path}")

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