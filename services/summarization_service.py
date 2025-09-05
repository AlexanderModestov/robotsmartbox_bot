import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
import openai
from anthropic import Anthropic
import tiktoken
from bot.config import Config

logger = logging.getLogger(__name__)

class SummarizationService:
    def __init__(self, provider: str = "openai"):
        self.provider = provider
        self.max_tokens = 2000
        
        if provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = Config.GPT_MODEL or "gpt-4o-mini"
            self.tokenizer = tiktoken.encoding_for_model("gpt-4")
        elif provider == "anthropic":
            self.client = Anthropic(api_key=getattr(Config, 'ANTHROPIC_API_KEY', None))
            self.model = "claude-3-haiku-20240307"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using appropriate tokenizer"""
        if self.provider == "openai":
            return len(self.tokenizer.encode(text))
        else:
            # Rough approximation for Anthropic
            return len(text.split()) * 1.3

    def extract_categories_from_content(self, content: str, metadata: Dict) -> List[str]:
        """Extract and normalize categories from workflow content"""
        categories = []
        
        # From metadata categories
        if metadata.get('categories'):
            if isinstance(metadata['categories'], list):
                categories.extend(metadata['categories'])
            elif isinstance(metadata['categories'], str):
                categories.append(metadata['categories'])
        
        # Extract from content keywords
        content_lower = content.lower()
        keyword_categories = {
            'social-media': ['social media', 'linkedin', 'twitter', 'facebook', 'instagram'],
            'ai-ml': ['ai', 'openai', 'gpt', 'claude', 'machine learning', 'artificial intelligence'],
            'automation': ['automation', 'workflow', 'n8n', 'automate'],
            'data-processing': ['data', 'database', 'sql', 'postgres', 'mongodb'],
            'communication': ['email', 'slack', 'telegram', 'discord', 'whatsapp'],
            'business': ['crm', 'sales', 'hubspot', 'pipedrive', 'business'],
            'productivity': ['productivity', 'task', 'calendar', 'schedule'],
            'web-scraping': ['scraping', 'scrape', 'web scraping', 'data extraction'],
            'marketing': ['marketing', 'seo', 'analytics', 'campaign'],
            'api-integration': ['api', 'webhook', 'integration', 'http']
        }
        
        for category, keywords in keyword_categories.items():
            if any(keyword in content_lower for keyword in keywords):
                categories.append(category)
        
        # Remove duplicates and normalize
        normalized_categories = list(set([cat.lower().replace(' ', '-') for cat in categories]))
        return normalized_categories[:5]  # Limit to top 5 categories

    def extract_tools_and_integrations(self, content: str) -> List[str]:
        """Extract tools and integrations mentioned in the workflow"""
        tools = []
        content_lower = content.lower()
        
        # Common tools and services
        tool_patterns = {
            'google-sheets', 'google-calendar', 'gmail', 'google-drive',
            'slack', 'discord', 'telegram', 'whatsapp', 'twitter',
            'hubspot', 'pipedrive', 'salesforce', 'asana', 'trello',
            'openai', 'anthropic', 'perplexity', 'gpt',
            'postgres', 'mongodb', 'mysql', 'supabase',
            'stripe', 'paypal', 'mailchimp', 'sendgrid',
            'aws', 'azure', 'digitalocean', 'heroku',
            'zapier', 'n8n', 'make', 'airtable'
        }
        
        for tool in tool_patterns:
            if tool.replace('-', ' ') in content_lower or tool in content_lower:
                tools.append(tool)
        
        return list(set(tools))[:10]  # Limit to top 10 tools

    def determine_complexity(self, content: str, tools: List[str]) -> str:
        """Determine workflow complexity based on content analysis"""
        content_lower = content.lower()
        
        # Count complexity indicators
        complexity_score = 0
        
        # Multiple API calls
        if content_lower.count('api') > 3:
            complexity_score += 2
        
        # Multiple tools/integrations
        if len(tools) > 5:
            complexity_score += 2
        elif len(tools) > 2:
            complexity_score += 1
        
        # Advanced features
        advanced_features = ['ai', 'machine learning', 'vector', 'embedding', 'webhook', 'automation']
        complexity_score += sum(1 for feature in advanced_features if feature in content_lower)
        
        # Long content indicates complexity
        if len(content) > 5000:
            complexity_score += 1
        
        if complexity_score >= 5:
            return "advanced"
        elif complexity_score >= 3:
            return "intermediate"
        else:
            return "beginner"

    async def summarize_with_openai(self, content: str) -> Dict:
        """Summarize content using OpenAI"""
        # Truncate content if too long
        if self.count_tokens(content) > 15000:
            content = content[:50000]  # Rough character limit
        
        system_prompt = """You are an expert at summarizing automation workflows. From the following content, extract the main URL and a concise description describing what the automation/workflow does, tools it uses, and the key purpose. Reply ONLY with JSON."""
        
        user_prompt = f"""
        {content}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            return {"summary": response.choices[0].message.content}
        except Exception as e:
            logger.error(f"OpenAI summarization failed: {e}")
            return {"summary": "Automation workflow: Unable to generate summary"}

    async def summarize_with_anthropic(self, content: str) -> Dict:
        """Summarize content using Anthropic Claude"""
        if not self.client:
            return await self.summarize_with_openai(content)
        
        # Truncate content if too long
        if len(content) > 100000:
            content = content[:100000]
        
        prompt = f"""From the following content, extract the main URL and a concise description describing what the automation/workflow does, tools it uses, and the key purpose. Reply ONLY with JSON.

{content}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1200,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            return {"summary": response.content[0].text}
        except Exception as e:
            logger.error(f"Anthropic summarization failed: {e}")
            # Fallback to OpenAI
            return await self.summarize_with_openai(content)

    async def summarize_automation(self, json_data: Dict) -> Dict:
        """Main method to summarize an automation workflow from JSON data"""
        try:
            # Extract content and metadata from JSON
            content = json_data.get('content', {}).get('markdown', '')
            metadata = json_data.get('metadata', {})
            
            logger.info(f"Summarizing automation: {metadata.get('title', 'Untitled')}")
            
            if not content:
                logger.warning("No content found in JSON data")
                content = metadata.get('description', '')
            
            # Generate summary based on provider
            if self.provider == "openai":
                summary_result = await self.summarize_with_openai(content)
            else:
                summary_result = await self.summarize_with_anthropic(content)
            
            # Extract categories from content
            categories = self.extract_categories_from_content(content, metadata)
            
            result = {
                'title': metadata.get('title', 'Untitled Automation'),
                'description': metadata.get('description', '')[:500],  # Limit description
                'summary': summary_result.get('summary', ''),
                'categories': categories,
                'url': metadata.get('ogUrl', ''),
                'original_content_length': len(content)
            }
            
            logger.info(f"Successfully summarized: {result['title']}")
            return result
            
        except Exception as e:
            logger.error(f"Error summarizing automation: {e}")
            # Fallback using metadata if available
            metadata = json_data.get('metadata', {})
            return {
                'title': metadata.get('title', 'Untitled Automation'),
                'description': metadata.get('description', ''),
                'summary': f"N8n automation workflow: {metadata.get('title', 'Automation workflow')}. {metadata.get('description', '')}",
                'categories': ['automation'],
                'url': metadata.get('ogUrl', ''),
                'original_content_length': 0,
                'error': str(e)
            }

    async def batch_summarize(self, json_files: List[Dict], concurrency: int = 3) -> List[Dict]:
        """Batch process multiple JSON files with concurrency control"""
        logger.info(f"Starting batch summarization of {len(json_files)} files with concurrency {concurrency}")
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_single_file(json_data: Dict) -> Dict:
            async with semaphore:
                return await self.summarize_automation(json_data)
        
        tasks = [process_single_file(json_data) for json_data in json_files]
        
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                results.append(result)
                logger.info(f"Completed {i+1}/{len(json_files)}: {result['title']}")
            except Exception as e:
                logger.error(f"Failed to process file {i+1}: {e}")
                results.append({
                    'title': f'Failed automation {i+1}',
                    'summary': 'Processing failed',
                    'error': str(e)
                })
        
        logger.info(f"Batch summarization completed: {len(results)} processed")
        return results