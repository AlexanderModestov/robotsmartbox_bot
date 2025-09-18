#!/usr/bin/env python3
"""
Script to upload workflows from workflows.csv into the documents table.
This script reads the main workflows.csv file and inserts each workflow as a document.
"""

import asyncio
import csv
import os
import sys
from typing import List, Dict, Any

# Add the root directory to the path so we can import bot modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from bot.supabase_client.client import SupabaseClient
from bot.supabase_client.models import Document

class WorkflowUploader:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.client = SupabaseClient(supabase_url, supabase_key)

    def read_workflows_csv(self, csv_path: str) -> List[Dict[str, str]]:
        """Read workflows from CSV file"""
        workflows = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    workflows.append({
                        'category': row.get('category', '').strip(),
                        'subcategory': row.get('subcategory', '').strip(),
                        'name': row.get('name', '').strip(),
                        'url': row.get('url', '').strip()
                    })
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return []

        return workflows

    def workflow_to_document(self, workflow: Dict[str, str]) -> Dict[str, Any]:
        """Convert workflow data to document format"""

        name = workflow['name']

        return {
            'name': name,
            'category': workflow['category'],
            'subcategory': workflow['subcategory'],
            'url': workflow['url'],
            'embedding': None  # Will be generated later
        }

    async def upload_workflow(self, document_data: Dict[str, Any]) -> bool:
        """Upload a single workflow as a document"""
        try:
            response = await asyncio.to_thread(
                lambda: self.client.client.table('documents').insert(document_data).execute()
            )

            if response.data:
                print(f"[SUCCESS] Uploaded: {document_data['name'][:50]}...")
                return True
            else:
                print(f"[ERROR] Failed to upload: {document_data['name'][:50]}...")
                return False

        except Exception as e:
            print(f"[ERROR] Error uploading workflow: {e}")
            return False

    async def upload_all_workflows(self, csv_path: str) -> None:
        """Upload all workflows from CSV file"""
        print(f"Reading workflows from: {csv_path}")
        workflows = self.read_workflows_csv(csv_path)

        if not workflows:
            print("No workflows found in CSV file")
            return

        print(f"Found {len(workflows)} workflows to upload")

        successful_uploads = 0
        failed_uploads = 0

        for i, workflow in enumerate(workflows, 1):
            print(f"\nProcessing workflow {i}/{len(workflows)}")
            document_data = self.workflow_to_document(workflow)

            success = await self.upload_workflow(document_data)
            if success:
                successful_uploads += 1
            else:
                failed_uploads += 1

        print(f"\n[SUCCESS] Upload completed!")
        print(f"[SUCCESS] Successful uploads: {successful_uploads}")
        print(f"[ERROR] Failed uploads: {failed_uploads}")
        print(f"[TOTAL] Total workflows: {len(workflows)}")

async def main():
    """Main function to run the workflow uploader"""

    try:
        # Import Config to use the same configuration as the bot
        from bot.config import Config

        supabase_url = Config.SUPABASE_URL
        supabase_key = Config.SUPABASE_KEY

        if not supabase_url or not supabase_key:
            print("[ERROR] Error: SUPABASE_URL and SUPABASE_KEY not configured in Config")
            print("Make sure your .env file has these variables set")
            return
    except Exception as e:
        print(f"[ERROR] Error loading configuration: {e}")
        print("Make sure you have a .env file with SUPABASE_URL and SUPABASE_KEY")
        return

    # Path to the main workflows.csv file
    csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'workflows.csv')

    if not os.path.exists(csv_path):
        print(f"[ERROR] Error: workflows.csv not found at {csv_path}")
        return

    # Create uploader and upload workflows
    uploader = WorkflowUploader(supabase_url, supabase_key)
    await uploader.upload_all_workflows(csv_path)

if __name__ == "__main__":
    asyncio.run(main())