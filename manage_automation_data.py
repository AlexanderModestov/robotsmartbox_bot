#!/usr/bin/env python3
"""
Management script for automation data processing pipeline
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.vector_pipeline import VectorPipeline
from services.summarization_service import SummarizationService
from bot.supabase_client import SupabaseClient
from bot.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomationDataManager:
    def __init__(self):
        self.supabase_client = SupabaseClient(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        self.vector_pipeline = VectorPipeline(self.supabase_client)
        self.summarization_service = SummarizationService()

    async def process_all_data(self, batch_size: int = 5, start_from: int = 0):
        """Process all automation data through the complete pipeline"""
        logger.info("🚀 Starting complete automation data processing pipeline")
        
        try:
            # Validate configuration
            Config.validate()
            logger.info("✅ Configuration validated")
            
            # Update database schema
            logger.info("🔧 Updating database schema...")
            schema_result = await self.vector_pipeline.update_database_schema()
            logger.info(f"Schema update result: {schema_result}")
            
            # Process automation files
            logger.info(f"📊 Processing automation files (batch_size={batch_size}, start_from={start_from})")
            result = await self.vector_pipeline.process_automation_files(
                batch_size=batch_size,
                start_from=start_from
            )
            
            if result.get('success'):
                processing_log = result.get('processing_log', {})
                logger.info(f"✅ Processing completed successfully!")
                logger.info(f"📈 Statistics:")
                logger.info(f"   - Total files processed: {processing_log.get('processed_files', 0)}")
                logger.info(f"   - Successful: {processing_log.get('successful_files', 0)}")
                logger.info(f"   - Failed: {processing_log.get('failed_files', 0)}")
                logger.info(f"   - Documents stored: {processing_log.get('stored_documents', 0)}")
                logger.info(f"   - Log saved: {result.get('log_path', 'N/A')}")
                
                return True
            else:
                logger.error(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}")
            return False

    async def test_summarization(self, sample_size: int = 3):
        """Test summarization service with sample files"""
        logger.info(f"🧪 Testing summarization with {sample_size} sample files")
        
        try:
            # Load sample files
            files_data = await self.vector_pipeline.load_json_files()
            
            if not files_data:
                logger.error("No JSON files found to test")
                return False
            
            # Take sample
            sample_files = files_data[:sample_size]
            logger.info(f"Testing with files: {[f[0] for f in sample_files]}")
            
            # Test summarization
            for filename, content, metadata in sample_files:
                logger.info(f"📝 Summarizing: {filename}")
                
                summary_data = await self.summarization_service.summarize_automation(content, metadata)
                
                logger.info(f"✅ Summary completed for {filename}")
                logger.info(f"   - Title: {summary_data.get('title', 'N/A')}")
                logger.info(f"   - Categories: {summary_data.get('categories', [])}")
                logger.info(f"   - Complexity: {summary_data.get('complexity_level', 'N/A')}")
                logger.info(f"   - Tools: {len(summary_data.get('tools_used', []))} tools")
                logger.info(f"   - Summary tokens: {summary_data.get('summary_tokens', 0)}")
                
                if summary_data.get('error'):
                    logger.warning(f"   - Error: {summary_data['error']}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Summarization test failed: {e}")
            return False

    async def get_processing_stats(self):
        """Get and display processing statistics"""
        logger.info("📊 Retrieving processing statistics")
        
        try:
            stats = self.vector_pipeline.get_processing_stats()
            
            if stats.get('success'):
                latest_processing = stats.get('latest_processing', {})
                
                print("\n" + "="*50)
                print("📊 AUTOMATION DATA PROCESSING STATISTICS")
                print("="*50)
                
                print(f"📅 Last Processing: {latest_processing.get('processed_at', 'N/A')}")
                print(f"📁 Total Files: {latest_processing.get('total_files', 0)}")
                print(f"✅ Processed Files: {latest_processing.get('processed_files', 0)}")
                print(f"🎯 Successful Files: {latest_processing.get('successful_files', 0)}")
                print(f"❌ Failed Files: {latest_processing.get('failed_files', 0)}")
                print(f"💾 Documents Stored: {latest_processing.get('stored_documents', 0)}")
                print(f"🔧 Batch Size: {latest_processing.get('batch_size', 'N/A')}")
                print(f"🚀 Started From: {latest_processing.get('start_from', 0)}")
                
                storage_errors = latest_processing.get('storage_errors', [])
                if storage_errors:
                    print(f"\n⚠️  Storage Errors ({len(storage_errors)}):")
                    for error in storage_errors[:5]:  # Show first 5 errors
                        print(f"   - {error}")
                    if len(storage_errors) > 5:
                        print(f"   ... and {len(storage_errors) - 5} more errors")
                
                print(f"\n📄 Log File: {stats.get('log_file', 'N/A')}")
                print("="*50)
                
            else:
                logger.warning("No processing statistics available")
                
        except Exception as e:
            logger.error(f"❌ Failed to get statistics: {e}")

    async def check_database_status(self):
        """Check database connection and document count"""
        logger.info("🔍 Checking database status")
        
        try:
            # Test connection
            response = self.supabase_client.client.table('documents').select('id').limit(1).execute()
            
            if response.data is not None:
                logger.info("✅ Database connection successful")
                
                # Get document count
                count_response = self.supabase_client.client.table('documents').select('id', count='exact').execute()
                total_docs = count_response.count if hasattr(count_response, 'count') else 0
                
                # Get automation documents count
                automation_response = self.supabase_client.client.table('documents').select('id', count='exact').eq('workflow_type', 'n8n-workflow').execute()
                automation_docs = automation_response.count if hasattr(automation_response, 'count') else 0
                
                print(f"\n📊 DATABASE STATUS")
                print(f"📄 Total Documents: {total_docs}")
                print(f"🤖 Automation Documents: {automation_docs}")
                print(f"🔗 Database URL: {Config.SUPABASE_URL}")
                
                return True
            else:
                logger.error("❌ Database connection failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Database check failed: {e}")
            return False

async def main():
    parser = argparse.ArgumentParser(description="Automation Data Management Script")
    parser.add_argument('action', choices=['process', 'test', 'stats', 'check'], 
                       help='Action to perform')
    parser.add_argument('--batch-size', type=int, default=5, 
                       help='Batch size for processing (default: 5)')
    parser.add_argument('--start-from', type=int, default=0,
                       help='Start processing from file index (default: 0)')
    parser.add_argument('--sample-size', type=int, default=3,
                       help='Sample size for testing (default: 3)')
    
    args = parser.parse_args()
    
    manager = AutomationDataManager()
    
    if args.action == 'process':
        success = await manager.process_all_data(args.batch_size, args.start_from)
        if success:
            print("\n🎉 Processing completed successfully!")
            print("You can now use the /automate and /knowledge commands in the bot.")
        else:
            print("\n💥 Processing failed. Check the logs for details.")
            sys.exit(1)
    
    elif args.action == 'test':
        success = await manager.test_summarization(args.sample_size)
        if success:
            print("\n✅ Summarization test completed!")
        else:
            print("\n❌ Summarization test failed!")
            sys.exit(1)
    
    elif args.action == 'stats':
        await manager.get_processing_stats()
    
    elif args.action == 'check':
        success = await manager.check_database_status()
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())