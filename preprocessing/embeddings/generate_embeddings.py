#!/usr/bin/env python3
"""
Embedding Generation Script

This script generates embeddings for documents in the Supabase documents table
where description is not null but embedding is null.
"""

import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from bot.config import Config
from bot.supabase_client.client import SupabaseClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """Generator for creating embeddings for documents"""

    def __init__(self):
        """Initialize the generator with API clients"""
        try:
            self.supabase_url = Config.SUPABASE_URL
            self.supabase_key = Config.SUPABASE_KEY
            self.openai_key = Config.OPENAI_API_KEY
            self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            # Fallback to environment variables
            self.supabase_url = os.getenv('SUPABASE_URL')
            self.supabase_key = os.getenv('SUPABASE_KEY')
            self.openai_key = os.getenv('OPENAI_API_KEY')
            self.embedding_model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-large')

        if not all([self.supabase_url, self.supabase_key, self.openai_key]):
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY")

        # Initialize clients
        self.supabase_client = SupabaseClient(self.supabase_url, self.supabase_key)
        self.openai_client = OpenAI(api_key=self.openai_key)

        # Initialize failed documents list
        self.failed_documents = []

        logger.info(f"Initialized Embedding Generator with model: {self.embedding_model}")

    async def get_documents_without_embeddings(self) -> List[Dict[str, Any]]:
        """Get all documents where description is not null but embedding is null"""
        try:
            all_documents = []
            page_size = 1000
            start = 0

            logger.info("Fetching all documents without embeddings using pagination...")

            while True:
                end = start + page_size - 1
                logger.info(f"Fetching documents {start} to {end}...")

                response = await asyncio.to_thread(
                    lambda: self.supabase_client.client.table('documents')\
                        .select('id, name, description')\
                        .is_('embedding', 'null')\
                        .not_.is_('description', 'null')\
                        .neq('description', '')\
                        .range(start, end)\
                        .execute()
                )

                documents = response.data if response.data else []

                if not documents:
                    logger.info("No more documents found, pagination complete")
                    break

                all_documents.extend(documents)
                logger.info(f"Fetched {len(documents)} documents (total so far: {len(all_documents)})")

                # If we got fewer documents than page_size, we've reached the end
                if len(documents) < page_size:
                    logger.info("Reached end of documents (partial page)")
                    break

                start += page_size

            logger.info(f"Found {len(all_documents)} total documents without embeddings")
            return all_documents

        except Exception as e:
            logger.error(f"Error fetching documents: {e}")
            return []

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI API"""
        try:
            response = await asyncio.to_thread(
                lambda: self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=text
                )
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def update_document_embedding(self, doc_id: int, embedding: List[float]) -> bool:
        """Update document with generated embedding"""
        try:
            response = await asyncio.to_thread(
                lambda: self.supabase_client.client.table('documents')\
                    .update({'embedding': embedding})\
                    .eq('id', doc_id)\
                    .execute()
            )

            if response.data:
                logger.info(f"Successfully updated embedding for document ID: {doc_id}")
                return True
            else:
                logger.warning(f"No document updated for ID: {doc_id}")
                return False

        except Exception as e:
            logger.error(f"Error updating document {doc_id}: {e}")
            return False

    async def process_document(self, document: Dict[str, Any]) -> bool:
        """Process a single document to generate and store embedding"""
        doc_id = document['id']
        name = document['name']
        description = document['description']

        try:
            logger.info(f"Processing document {doc_id}: {name[:50]}...")

            # Generate embedding for the description
            embedding = await self.generate_embedding(description)

            if embedding is None:
                error_msg = f"Failed to generate embedding for document {doc_id}: {name}"
                logger.error(error_msg)
                self.failed_documents.append({
                    'id': doc_id,
                    'name': name,
                    'error': 'Embedding generation failed'
                })
                return False

            # Update document with embedding
            success = await self.update_document_embedding(doc_id, embedding)

            if not success:
                error_msg = f"Failed to update document {doc_id} in database: {name}"
                logger.error(error_msg)
                self.failed_documents.append({
                    'id': doc_id,
                    'name': name,
                    'error': 'Database update failed'
                })

            return success

        except Exception as e:
            error_msg = f"Exception processing document {doc_id}: {e}"
            logger.error(error_msg)
            self.failed_documents.append({
                'id': doc_id,
                'name': name,
                'error': str(e)
            })
            return False

    async def generate_all_embeddings(self, batch_size: int = 10):
        """Generate embeddings for all documents that need them"""
        logger.info("Starting embedding generation process")

        try:
            # Get documents without embeddings
            documents = await self.get_documents_without_embeddings()

            if not documents:
                logger.info("No documents found that need embeddings")
                return

            total_docs = len(documents)
            processed = 0
            successful = 0
            failed = 0

            # Process documents in batches
            for i in range(0, total_docs, batch_size):
                batch = documents[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}")

                # Process batch
                tasks = []
                for document in batch:
                    tasks.append(self.process_document(document))

                # Wait for batch to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count results
                for result in results:
                    processed += 1
                    if result is True:
                        successful += 1
                    else:
                        failed += 1
                        if isinstance(result, Exception):
                            logger.error(f"Processing error: {result}")

                # Small delay between batches to avoid rate limits
                await asyncio.sleep(1)

            logger.info(f"Embedding generation completed!")
            logger.info(f"Total processed: {processed}")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")

            # Save failed documents to file
            if self.failed_documents:
                from datetime import datetime
                failed_file_path = "failed_embeddings.txt"
                with open(failed_file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Failed Embedding Generation Report\n")
                    f.write(f"Total failed: {len(self.failed_documents)}\n")
                    f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                    for doc in self.failed_documents:
                        f.write(f"ID: {doc['id']}\n")
                        f.write(f"Name: {doc['name']}\n")
                        f.write(f"Error: {doc['error']}\n")
                        f.write("-" * 50 + "\n")

                logger.info(f"Saved {len(self.failed_documents)} failed document details to {failed_file_path}")

        except Exception as e:
            logger.error(f"Error during embedding generation: {e}")
            raise

async def main():
    """Main entry point"""
    try:
        generator = EmbeddingGenerator()
        await generator.generate_all_embeddings()
        logger.info("Embedding generation completed successfully!")

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())