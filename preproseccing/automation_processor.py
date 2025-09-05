#!/usr/bin/env python3
"""
Automation Document Processor for Supabase

This service processes JSON files containing automation descriptions
and populates a Supabase database with structured data including embeddings.
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AutomationDocument:
    """Data class for automation document"""
    url: str
    categories: List[str]
    description: str
    short_description: str
    filename: str

class AutomationProcessor:
    """Main processor class for automation documents"""
    
    def __init__(self):
        """Initialize the processor with API clients"""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        
        if not all([self.supabase_url, self.supabase_key, self.openai_key]):
            raise ValueError("Missing required environment variables: SUPABASE_URL, SUPABASE_ANON_KEY, OPENAI_API_KEY")
        
        # Initialize clients
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.openai_client = OpenAI(api_key=self.openai_key)
        
        logger.info("Initialized AutomationProcessor")
    
    def load_json_files(self, data_dir: str = "data") -> List[AutomationDocument]:
        """Load all JSON files from the data directory"""
        documents = []
        data_path = Path(data_dir)
        
        if not data_path.exists():
            raise FileNotFoundError(f"Data directory '{data_dir}' not found")
        
        json_files = list(data_path.glob("*.json"))
        logger.info(f"Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate required fields
                required_fields = ['url', 'categories', 'description', 'short_description']
                if not all(field in data for field in required_fields):
                    logger.warning(f"Skipping {json_file.name}: missing required fields")
                    continue
                
                doc = AutomationDocument(
                    url=data['url'],
                    categories=data['categories'],
                    description=data['description'],
                    short_description=data['short_description'],
                    filename=json_file.name
                )
                documents.append(doc)
                
            except Exception as e:
                logger.error(f"Error loading {json_file.name}: {e}")
                continue
        
        logger.info(f"Successfully loaded {len(documents)} automation documents")
        return documents
    
    def extract_all_categories(self, documents: List[AutomationDocument]) -> Set[str]:
        """Extract all unique categories from documents"""
        categories = set()
        for doc in documents:
            categories.update(doc.categories)
        
        logger.info(f"Found {len(categories)} unique categories")
        return categories
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI API"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    def insert_categories(self, categories: Set[str]) -> Dict[str, int]:
        """Insert categories into database and return mapping of name -> id"""
        category_map = {}
        
        for category in categories:
            try:
                # Try to insert category (ignore if already exists due to unique constraint)
                result = self.supabase.table('categories').upsert({
                    'name': category
                }, on_conflict='name').execute()
                
                # Get the category ID
                category_result = self.supabase.table('categories').select('id').eq('name', category).execute()
                if category_result.data:
                    category_map[category] = category_result.data[0]['id']
                    logger.info(f"Processed category: {category}")
                
            except Exception as e:
                logger.error(f"Error inserting category '{category}': {e}")
                continue
        
        logger.info(f"Processed {len(category_map)} categories")
        return category_map
    
    def insert_documents(self, documents: List[AutomationDocument], category_map: Dict[str, int]):
        """Insert documents and their category relationships"""
        
        for doc in documents:
            try:
                # Generate embedding for description
                logger.info(f"Generating embedding for {doc.filename}")
                embedding = self.generate_embedding(doc.description)
                
                # Insert document
                doc_result = self.supabase.table('documents').insert({
                    'url': doc.url,
                    'short_description': doc.short_description,
                    'description': doc.description,
                    'embedding': embedding,
                    'filename': doc.filename
                }).execute()
                
                if not doc_result.data:
                    logger.error(f"Failed to insert document {doc.filename}")
                    continue
                
                document_id = doc_result.data[0]['id']
                logger.info(f"Inserted document {doc.filename} with ID {document_id}")
                
                # Insert category relationships
                for category_name in doc.categories:
                    if category_name in category_map:
                        category_id = category_map[category_name]
                        
                        try:
                            self.supabase.table('automations').insert({
                                'automatization': document_id,
                                'category': category_id
                            }).execute()
                            
                        except Exception as e:
                            logger.error(f"Error linking document {document_id} to category {category_id}: {e}")
                
                logger.info(f"Successfully processed document: {doc.filename}")
                
            except Exception as e:
                logger.error(f"Error processing document {doc.filename}: {e}")
                continue
    
    def process_all(self, data_dir: str = "data"):
        """Main method to process all automation documents"""
        logger.info("Starting automation document processing")
        
        try:
            # Load documents
            documents = self.load_json_files(data_dir)
            if not documents:
                logger.warning("No documents found to process")
                return
            
            # Extract categories
            categories = self.extract_all_categories(documents)
            
            # Insert categories
            category_map = self.insert_categories(categories)
            
            # Insert documents and relationships
            self.insert_documents(documents, category_map)
            
            logger.info("Successfully completed automation document processing")
            
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            raise

def main():
    """Main entry point"""
    try:
        processor = AutomationProcessor()
        processor.process_all()
    except Exception as e:
        logger.error(f"Failed to process automation documents: {e}")
        raise

if __name__ == "__main__":
    main()