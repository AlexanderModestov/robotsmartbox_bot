import asyncio
import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import openai
import numpy as np
from .summarization_service import SummarizationService
from bot.config import Config
from bot.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class VectorPipeline:
    def __init__(self, supabase_client: SupabaseClient = None):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.embedding_model = Config.EMBEDDING_MODEL or "text-embedding-3-large"
        self.data_dir = "/home/alex/Projects/RobotSmart/telegramBot/data/n8n"
        self.processed_dir = "/home/alex/Projects/RobotSmart/telegramBot/data/processed"
        
        # Initialize services
        self.summarization_service = SummarizationService()
        self.openai_client = openai.AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Initialize or use provided Supabase client
        if supabase_client:
            self.supabase_client = supabase_client
        else:
            self.supabase_client = SupabaseClient(
                Config.SUPABASE_URL, 
                Config.SUPABASE_KEY
            )
        
        # Create processed directory if it doesn't exist
        os.makedirs(self.processed_dir, exist_ok=True)

    async def load_json_files(self) -> List[Tuple[str, Dict]]:
        """Load all JSON files from the n8n data directory"""
        logger.info(f"Loading JSON files from {self.data_dir}")
        files_data = []
        
        try:
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.data_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        
                        # Validate that we have the required structure
                        content = json_data.get('content', {}).get('markdown', '')
                        metadata = json_data.get('metadata', {})
                        
                        if content and metadata:
                            files_data.append((filename, json_data))
                        else:
                            logger.warning(f"Skipping {filename}: missing content or metadata")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing {filename}: {e}")
                    except Exception as e:
                        logger.error(f"Error reading {filename}: {e}")
            
            logger.info(f"Loaded {len(files_data)} valid JSON files")
            return files_data
            
        except Exception as e:
            logger.error(f"Error loading JSON files: {e}")
            return []

    def create_chunks(self, content: str, metadata: Dict) -> List[Dict]:
        """Split content into overlapping chunks with metadata"""
        chunks = []
        
        # Simple sentence-based chunking to preserve context
        sentences = content.split('. ')
        current_chunk = ""
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                    'content': current_chunk.strip(),
                    'metadata': {
                        **metadata,
                        'chunk_index': len(chunks),
                        'chunk_size': len(current_chunk)
                    }
                })
                
                # Start new chunk with overlap
                overlap_sentences = current_chunk.split('. ')[-2:]  # Last 2 sentences for overlap
                current_chunk = '. '.join(overlap_sentences) + '. ' + sentence + '.'
                current_size = len(current_chunk)
            else:
                current_chunk += sentence + '. '
                current_size += sentence_size + 2
        
        # Add the last chunk if there's content
        if current_chunk.strip():
            chunks.append({
                'content': current_chunk.strip(),
                'metadata': {
                    **metadata,
                    'chunk_index': len(chunks),
                    'chunk_size': len(current_chunk)
                }
            })
        
        logger.info(f"Created {len(chunks)} chunks from content")
        return chunks

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text using OpenAI"""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text[:8000]  # Limit text length for embedding
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    async def process_single_automation(self, filename: str, json_data: Dict) -> Dict:
        """Process a single automation file through the complete pipeline"""
        try:
            logger.info(f"Processing automation: {filename}")
            
            # Extract content and metadata for processing
            content = json_data.get('content', {}).get('markdown', '')
            metadata = json_data.get('metadata', {})
            
            # Step 1: Generate summary
            summary_data = await self.summarization_service.summarize_automation(json_data)
            
            # Step 2: Create chunks from both original content and summary
            content_chunks = self.create_chunks(content, {
                **metadata,
                'source_type': 'original_content',
                'file_name': filename
            })
            
            # Add summary as a special chunk
            summary_chunk = {
                'content': summary_data['summary'],
                'metadata': {
                    **metadata,
                    'source_type': 'summary',
                    'file_name': filename,
                    'chunk_index': -1  # Special index for summary
                }
            }
            
            all_chunks = content_chunks + [summary_chunk]
            
            # Step 3: Generate embeddings for all chunks
            processed_chunks = []
            for chunk in all_chunks:
                embedding = await self.generate_embedding(chunk['content'])
                if embedding:
                    processed_chunk = {
                        'content': chunk['content'],
                        'embedding': embedding,
                        'metadata': {
                            **chunk['metadata'],
                            **summary_data,  # Include summary metadata
                            'processed_at': datetime.now().isoformat()
                        }
                    }
                    processed_chunks.append(processed_chunk)
                else:
                    logger.warning(f"Failed to generate embedding for chunk in {filename}")
            
            logger.info(f"Successfully processed {filename}: {len(processed_chunks)} chunks with embeddings")
            return {
                'filename': filename,
                'summary_data': summary_data,
                'chunks': processed_chunks,
                'total_chunks': len(processed_chunks),
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            return {
                'filename': filename,
                'status': 'error',
                'error': str(e)
            }

    async def store_in_supabase(self, processed_data: List[Dict]) -> Dict:
        """Store processed automation data in Supabase"""
        logger.info("Storing processed data in Supabase")
        
        stored_documents = 0
        errors = []
        
        for automation in processed_data:
            if automation['status'] != 'success':
                continue
                
            try:
                filename = automation['filename']
                summary_data = automation['summary_data']
                chunks = automation['chunks']
                
                # Store each chunk as a separate document
                for chunk in chunks:
                    # Prepare document data for Supabase
                    document_data = {
                        'content': chunk['content'],
                        'embedding': chunk['embedding'],
                        'metadata': {
                            'file_name': filename,
                            'title': summary_data['title'],
                            'description': summary_data['description'],
                            'source_type': chunk['metadata'].get('source_type', 'content'),
                            'chunk_index': chunk['metadata'].get('chunk_index', 0),
                            'file_id': filename.replace('.json', ''),
                            'type': 'automation_workflow',
                            'workflow_type': summary_data.get('workflow_type', 'n8n-workflow'),
                            'author': summary_data.get('author', ''),
                            'source_url': summary_data.get('source_url', ''),
                            'tools_used': summary_data.get('tools_used', []),
                            'complexity_level': summary_data.get('complexity_level', 'intermediate'),
                            'summary_tokens': summary_data.get('summary_tokens', 0)
                        },
                        'category': summary_data.get('categories', ['automation'])[0] if summary_data.get('categories') else 'automation',
                        'url': summary_data.get('source_url', ''),
                        'ingestion_date': datetime.now().isoformat()
                    }
                    
                    # Insert into Supabase documents table
                    try:
                        response = self.supabase_client.client.table('documents').insert(document_data).execute()
                        if response.data:
                            stored_documents += 1
                        else:
                            logger.warning(f"No data returned when storing chunk from {filename}")
                    except Exception as e:
                        error_msg = f"Error storing chunk from {filename}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error processing automation {automation.get('filename', 'unknown')}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        result = {
            'stored_documents': stored_documents,
            'total_processed': len([a for a in processed_data if a['status'] == 'success']),
            'errors': errors,
            'success': len(errors) == 0
        }
        
        logger.info(f"Storage complete: {stored_documents} documents stored, {len(errors)} errors")
        return result

    async def process_automation_files(self, batch_size: int = 5, start_from: int = 0) -> Dict:
        """Main method to process all automation files"""
        logger.info(f"Starting automation files processing (batch_size={batch_size}, start_from={start_from})")
        
        try:
            # Step 1: Load all JSON files
            files_data = await self.load_json_files()
            
            if not files_data:
                return {
                    'success': False,
                    'error': 'No valid JSON files found'
                }
            
            # Apply start_from offset
            if start_from > 0:
                files_data = files_data[start_from:]
                logger.info(f"Processing from index {start_from}, {len(files_data)} files remaining")
            
            # Step 2: Process files in batches
            all_processed_data = []
            
            for i in range(0, len(files_data), batch_size):
                batch = files_data[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}: files {i+1}-{min(i+batch_size, len(files_data))}")
                
                # Process batch concurrently
                tasks = [
                    self.process_single_automation(filename, content, metadata)
                    for filename, content, metadata in batch
                ]
                
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch processing exception: {result}")
                        all_processed_data.append({
                            'status': 'error',
                            'error': str(result)
                        })
                    else:
                        all_processed_data.append(result)
                
                # Small delay between batches to avoid rate limiting
                await asyncio.sleep(1)
            
            # Step 3: Store all processed data in Supabase
            storage_result = await self.store_in_supabase(all_processed_data)
            
            # Step 4: Save processing log
            processing_log = {
                'processed_at': datetime.now().isoformat(),
                'total_files': len(files_data) + start_from,
                'processed_files': len(all_processed_data),
                'successful_files': len([d for d in all_processed_data if d['status'] == 'success']),
                'failed_files': len([d for d in all_processed_data if d['status'] == 'error']),
                'stored_documents': storage_result['stored_documents'],
                'batch_size': batch_size,
                'start_from': start_from,
                'storage_errors': storage_result['errors']
            }
            
            # Save log to processed directory
            log_path = os.path.join(self.processed_dir, f"processing_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(log_path, 'w') as f:
                json.dump(processing_log, f, indent=2)
            
            logger.info(f"Processing completed. Log saved to {log_path}")
            
            return {
                'success': True,
                'processing_log': processing_log,
                'log_path': log_path
            }
            
        except Exception as e:
            logger.error(f"Pipeline processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def update_database_schema(self) -> Dict:
        """Update database schema to support automation workflows"""
        logger.info("Updating database schema for automation workflows")
        
        try:
            # SQL commands to update the documents table
            schema_updates = [
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS workflow_type VARCHAR(50);",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS complexity_level VARCHAR(20);",
                "ALTER TABLE documents ADD COLUMN IF NOT EXISTS tools_used TEXT[];",
                "CREATE INDEX IF NOT EXISTS idx_documents_workflow_type ON documents(workflow_type);",
                "CREATE INDEX IF NOT EXISTS idx_documents_complexity ON documents(complexity_level);",
                "CREATE INDEX IF NOT EXISTS idx_documents_category_workflow ON documents(category, workflow_type);"
            ]
            
            results = []
            for sql in schema_updates:
                try:
                    # Note: Supabase Python client doesn't directly support schema changes
                    # These would need to be run via SQL editor or migration scripts
                    results.append(f"SQL prepared: {sql}")
                    logger.info(f"Schema update prepared: {sql}")
                except Exception as e:
                    results.append(f"Error preparing {sql}: {e}")
                    logger.error(f"Schema update error: {e}")
            
            return {
                'success': True,
                'schema_updates': results,
                'message': 'Schema updates prepared. Run these SQL commands in Supabase SQL editor.'
            }
            
        except Exception as e:
            logger.error(f"Schema update failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_processing_stats(self) -> Dict:
        """Get statistics about processed files"""
        try:
            # Look for the most recent processing log
            log_files = [f for f in os.listdir(self.processed_dir) if f.startswith('processing_log_')]
            
            if not log_files:
                return {'message': 'No processing logs found'}
            
            # Get the most recent log
            latest_log = sorted(log_files)[-1]
            log_path = os.path.join(self.processed_dir, latest_log)
            
            with open(log_path, 'r') as f:
                stats = json.load(f)
            
            return {
                'success': True,
                'latest_processing': stats,
                'log_file': latest_log
            }
            
        except Exception as e:
            logger.error(f"Error getting processing stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }