import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import openai
from datetime import datetime
import numpy as np
from .summarization_service import SummarizationService
from bot.config import Config
from bot.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class AutomationRAG:
    def __init__(self, supabase_client: SupabaseClient = None):
        self.embedding_model = Config.EMBEDDING_MODEL or "text-embedding-3-large"
        self.gpt_model = Config.GPT_MODEL or "gpt-4o-mini"
        self.search_limit = Config.SEARCH_LIMIT or 5
        self.similarity_threshold = 0.7
        
        # Initialize OpenAI client
        self.openai_client = openai.AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Initialize or use provided Supabase client
        if supabase_client:
            self.supabase_client = supabase_client
        else:
            self.supabase_client = SupabaseClient(
                Config.SUPABASE_URL, 
                Config.SUPABASE_KEY
            )

    async def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for user query"""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return None

    def create_search_filters(self, filters: Dict = None) -> Dict:
        """Create search filters for automation queries"""
        search_filters = {}
        
        if not filters:
            return search_filters
        
        # Category filter
        if 'category' in filters:
            search_filters['category'] = filters['category']
        
        # Complexity level filter
        if 'complexity' in filters:
            search_filters['complexity_level'] = filters['complexity']
        
        # Workflow type filter
        if 'workflow_type' in filters:
            search_filters['workflow_type'] = filters['workflow_type']
        
        # Tools filter
        if 'tools' in filters and isinstance(filters['tools'], list):
            search_filters['tools_used'] = filters['tools']
        
        return search_filters

    async def vector_search(self, query_embedding: List[float], filters: Dict = None, limit: int = None) -> List[Dict]:
        """Perform vector similarity search with optional filters"""
        try:
            search_limit = limit or self.search_limit
            
            logger.info(f"Performing vector search with limit {search_limit}")
            
            # Use the existing search_content method from SupabaseClient
            # which handles vector similarity search
            results = await self.supabase_client.search_content(
                user_id=0,  # Not user-specific for automation search
                query_embedding=query_embedding,
                limit=search_limit,
                threshold=self.similarity_threshold
            )
            
            # Apply additional filters if specified
            if filters:
                filtered_results = []
                for result in results:
                    # Check category filter
                    if 'category' in filters:
                        if result.get('category') != filters['category']:
                            continue
                    
                    # Check complexity filter
                    if 'complexity' in filters:
                        metadata = result.get('metadata', {})
                        if metadata.get('complexity_level') != filters['complexity']:
                            continue
                    
                    # Check tools filter
                    if 'tools' in filters:
                        metadata = result.get('metadata', {})
                        tools_used = metadata.get('tools_used', [])
                        if not any(tool in tools_used for tool in filters['tools']):
                            continue
                    
                    filtered_results.append(result)
                
                results = filtered_results[:search_limit]
            
            logger.info(f"Vector search returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    def group_results_by_automation(self, results: List[Dict]) -> Dict[str, Dict]:
        """Group search results by automation workflow"""
        grouped = {}
        
        for result in results:
            file_id = result.get('id') or result.get('file_id', 'unknown')
            title = result.get('title', 'Untitled')
            
            if file_id not in grouped:
                grouped[file_id] = {
                    'title': title,
                    'chunks': [],
                    'max_similarity': 0,
                    'summary': None,
                    'metadata': {}
                }
            
            chunk_data = {
                'content': result.get('content_text', ''),
                'similarity': result.get('similarity', 0),
                'type': result.get('type', 'content')
            }
            
            grouped[file_id]['chunks'].append(chunk_data)
            
            # Update max similarity
            if chunk_data['similarity'] > grouped[file_id]['max_similarity']:
                grouped[file_id]['max_similarity'] = chunk_data['similarity']
            
            # Set summary if this is a summary chunk
            if chunk_data['type'] == 'summary':
                grouped[file_id]['summary'] = chunk_data['content']
            
            # Update metadata (take from highest similarity chunk)
            if chunk_data['similarity'] == grouped[file_id]['max_similarity']:
                # Extract metadata from result if available
                result_metadata = result.get('metadata', {})
                grouped[file_id]['metadata'] = {
                    'category': result.get('category', 'automation'),
                    'complexity_level': result_metadata.get('complexity_level', 'intermediate'),
                    'tools_used': result_metadata.get('tools_used', []),
                    'source_url': result_metadata.get('source_url', ''),
                    'author': result_metadata.get('author', ''),
                    'workflow_type': result_metadata.get('workflow_type', 'n8n-workflow')
                }
        
        # Sort by max similarity
        return dict(sorted(grouped.items(), key=lambda x: x[1]['max_similarity'], reverse=True))

    async def generate_contextual_response(self, query: str, grouped_results: Dict, max_results: int = 3) -> str:
        """Generate a contextual response based on search results"""
        try:
            # Take top results
            top_results = list(grouped_results.values())[:max_results]
            
            if not top_results:
                return "Я не нашел подходящих автоматизаций для вашего запроса. Попробуйте перефразировать вопрос или использовать другие ключевые слова."
            
            # Prepare context for GPT
            context_parts = []
            
            for i, result in enumerate(top_results, 1):
                title = result['title']
                summary = result.get('summary', '')
                metadata = result['metadata']
                
                # Get the most relevant content chunk
                best_chunk = max(result['chunks'], key=lambda x: x['similarity']) if result['chunks'] else None
                content_snippet = best_chunk['content'][:500] if best_chunk else ''
                
                context_part = f"""
Автоматизация {i}: {title}
Категория: {metadata.get('category', 'Не указана')}
Сложность: {metadata.get('complexity_level', 'Средняя')}
Инструменты: {', '.join(metadata.get('tools_used', [])[:5])}
URL: {metadata.get('source_url', 'Не указан')}

Описание:
{summary or content_snippet}
"""
                context_parts.append(context_part.strip())
            
            context = "\n\n" + "\n\n".join(context_parts)
            
            # Generate response
            system_prompt = """Ты - эксперт по автоматизации и помощник пользователя. 
На основе найденных автоматизаций дай практический ответ на вопрос пользователя.

Инструкции:
1. Отвечай на русском языке
2. Будь конкретным и практичным
3. Упоминай названия найденных автоматизаций
4. Объясняй, как они могут решить задачу пользователя
5. Указывай уровень сложности и необходимые инструменты
6. Если есть URL, предлагай перейти для детального изучения
7. Если нашлось несколько вариантов, кратко опиши каждый

Формат ответа:
- Краткий ответ на вопрос
- Рекомендуемые автоматизации с объяснением
- Практические советы по реализации"""

            user_prompt = f"""Вопрос пользователя: {query}

Найденные автоматизации:
{context}

Дай практический ответ и рекомендации по автоматизации."""

            response = await self.openai_client.chat.completions.create(
                model=self.gpt_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return f"Найдено {len(grouped_results)} автоматизаций, но произошла ошибка при генерации ответа. Попробуйте переформулировать вопрос."

    def create_workflow_recommendations(self, grouped_results: Dict, limit: int = 5) -> List[Dict]:
        """Create structured workflow recommendations"""
        recommendations = []
        
        for file_id, result in list(grouped_results.items())[:limit]:
            metadata = result['metadata']
            
            # Calculate recommendation score based on similarity and completeness
            base_score = result['max_similarity']
            completeness_bonus = 0.1 if result.get('summary') else 0
            tools_bonus = min(len(metadata.get('tools_used', [])) * 0.02, 0.1)
            
            recommendation_score = base_score + completeness_bonus + tools_bonus
            
            recommendation = {
                'title': result['title'],
                'similarity_score': round(result['max_similarity'], 3),
                'recommendation_score': round(recommendation_score, 3),
                'category': metadata.get('category', 'automation'),
                'complexity': metadata.get('complexity_level', 'intermediate'),
                'tools': metadata.get('tools_used', [])[:5],  # Limit to top 5 tools
                'url': metadata.get('source_url', ''),
                'author': metadata.get('author', ''),
                'summary': result.get('summary', ''),
                'workflow_type': metadata.get('workflow_type', 'n8n-workflow'),
                'total_chunks': len(result['chunks'])
            }
            
            # Add complexity level description
            complexity_descriptions = {
                'beginner': 'Простая настройка, подходит для начинающих',
                'intermediate': 'Средняя сложность, требует базовых знаний',
                'advanced': 'Сложная настройка, для опытных пользователей'
            }
            recommendation['complexity_description'] = complexity_descriptions.get(
                recommendation['complexity'], 
                'Средняя сложность'
            )
            
            recommendations.append(recommendation)
        
        return recommendations

    async def query_automations(self, query: str, filters: Dict = None, max_results: int = 5) -> Dict:
        """Main method to query automation knowledge base"""
        try:
            logger.info(f"Querying automations for: '{query}'")
            
            # Step 1: Generate query embedding
            query_embedding = await self.generate_query_embedding(query)
            if not query_embedding:
                return {
                    'success': False,
                    'error': 'Failed to generate query embedding'
                }
            
            # Step 2: Perform vector search
            search_filters = self.create_search_filters(filters)
            search_results = await self.vector_search(
                query_embedding, 
                search_filters, 
                limit=max_results * 2  # Get more results to improve grouping
            )
            
            if not search_results:
                return {
                    'success': True,
                    'query': query,
                    'results_found': 0,
                    'message': 'Не найдено подходящих автоматизаций для вашего запроса.',
                    'recommendations': [],
                    'contextual_response': 'Попробуйте использовать другие ключевые слова или уточните запрос.'
                }
            
            # Step 3: Group results by automation workflow
            grouped_results = self.group_results_by_automation(search_results)
            
            # Step 4: Generate contextual response
            contextual_response = await self.generate_contextual_response(
                query, grouped_results, max_results
            )
            
            # Step 5: Create structured recommendations
            recommendations = self.create_workflow_recommendations(grouped_results, max_results)
            
            result = {
                'success': True,
                'query': query,
                'results_found': len(grouped_results),
                'contextual_response': contextual_response,
                'recommendations': recommendations,
                'search_metadata': {
                    'similarity_threshold': self.similarity_threshold,
                    'search_limit': max_results,
                    'filters_applied': search_filters,
                    'total_chunks_found': len(search_results),
                    'unique_workflows': len(grouped_results)
                }
            }
            
            logger.info(f"Query completed: {len(recommendations)} recommendations generated")
            return result
            
        except Exception as e:
            logger.error(f"Error in query_automations: {e}")
            return {
                'success': False,
                'error': str(e),
                'query': query
            }

    async def get_automation_by_category(self, category: str, limit: int = 10) -> Dict:
        """Get automations filtered by category"""
        try:
            # Create a general query for the category
            category_query = f"automation workflows for {category}"
            
            return await self.query_automations(
                query=category_query,
                filters={'category': category},
                max_results=limit
            )
            
        except Exception as e:
            logger.error(f"Error getting automations by category: {e}")
            return {
                'success': False,
                'error': str(e),
                'category': category
            }

    async def get_similar_automations(self, automation_title: str, limit: int = 5) -> Dict:
        """Find similar automations to a given one"""
        try:
            # Use the title as query to find similar automations
            return await self.query_automations(
                query=automation_title,
                max_results=limit
            )
            
        except Exception as e:
            logger.error(f"Error finding similar automations: {e}")
            return {
                'success': False,
                'error': str(e),
                'automation_title': automation_title
            }

    def get_available_categories(self) -> List[str]:
        """Get list of available automation categories"""
        return [
            'social-media',
            'ai-ml',
            'automation',
            'data-processing',
            'communication',
            'business',
            'productivity',
            'web-scraping',
            'marketing',
            'api-integration'
        ]

    def get_available_tools(self) -> List[str]:
        """Get list of commonly used automation tools"""
        return [
            'n8n', 'zapier', 'make',
            'google-sheets', 'airtable',
            'slack', 'discord', 'telegram',
            'hubspot', 'pipedrive', 'salesforce',
            'openai', 'anthropic', 'gpt',
            'postgres', 'mongodb', 'supabase',
            'stripe', 'paypal',
            'aws', 'azure', 'digitalocean'
        ]