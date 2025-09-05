import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime
from services.rag_service import AutomationRAG
from services.workflow_recommender import WorkflowRecommender
from services.vector_pipeline import VectorPipeline
from services.automation_categories import AutomationCategory
from bot.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class AutomationHandler:
    """Handler for automation-related bot interactions"""
    
    def __init__(self, supabase_client: SupabaseClient):
        self.supabase_client = supabase_client
        self.rag_service = AutomationRAG(supabase_client)
        self.recommender = WorkflowRecommender(supabase_client)
        self.vector_pipeline = VectorPipeline(supabase_client)

    async def handle_automation_query(self, user_id: int, query: str, filters: Dict = None) -> Dict:
        """Handle user automation query"""
        try:
            logger.info(f"Processing automation query from user {user_id}: {query}")
            
            # Get personalized recommendations
            result = await self.recommender.get_personalized_recommendations(
                user_id=user_id,
                query=query,
                max_results=5
            )
            
            # Log user interaction (for future personalization improvements)
            await self._log_user_interaction(user_id, query, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling automation query: {e}")
            return {
                'success': False,
                'error': 'Произошла ошибка при поиске автоматизаций. Попробуйте еще раз.',
                'technical_error': str(e)
            }

    async def handle_category_browse(self, user_id: int, category: str) -> Dict:
        """Handle category browsing request"""
        try:
            logger.info(f"User {user_id} browsing category: {category}")
            
            # Get category recommendations
            result = await self.recommender.get_category_recommendations(
                category=category,
                user_id=user_id,
                max_results=8
            )
            
            # Log interaction
            await self._log_user_interaction(user_id, f"category:{category}", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling category browse: {e}")
            return {
                'success': False,
                'error': f'Ошибка при загрузке категории "{category}"',
                'technical_error': str(e)
            }

    async def get_trending_automations(self, user_id: int = None) -> Dict:
        """Get trending automations"""
        try:
            result = await self.recommender.get_trending_automations(
                time_period='week',
                max_results=6
            )
            
            if user_id:
                await self._log_user_interaction(user_id, "trending:week", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting trending automations: {e}")
            return {
                'success': False,
                'error': 'Ошибка при загрузке популярных автоматизаций',
                'technical_error': str(e)
            }

    async def get_beginner_automations(self, user_id: int, category: str = None) -> Dict:
        """Get beginner-friendly automations"""
        try:
            result = await self.recommender.get_beginner_friendly_automations(
                category=category,
                max_results=6
            )
            
            await self._log_user_interaction(user_id, f"beginner:{category or 'all'}", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting beginner automations: {e}")
            return {
                'success': False,
                'error': 'Ошибка при загрузке автоматизаций для начинающих',
                'technical_error': str(e)
            }

    def get_available_categories(self) -> List[Dict]:
        """Get list of available automation categories with descriptions"""
        categories = AutomationCategory.get_all_categories()
        
        category_list = []
        for key, data in categories.items():
            category_list.append({
                'key': key,
                'name': data['name'],
                'description': data['description'],
                'complexity': data.get('complexity', 'intermediate').value if hasattr(data.get('complexity'), 'value') else 'intermediate',
                'subcategories': data.get('subcategories', [])
            })
        
        # Sort by name
        category_list.sort(key=lambda x: x['name'])
        return category_list

    def format_automation_for_telegram(self, automation: Dict, include_details: bool = True) -> str:
        """Format automation data for Telegram message"""
        try:
            title = automation.get('title', 'Untitled')
            category = automation.get('category', 'automation')
            complexity = automation.get('complexity', 'intermediate')
            tools = automation.get('tools', [])
            url = automation.get('url', '')
            
            # Create main message
            message = f"🤖 **{title}**\n\n"
            
            # Add category and complexity
            category_info = AutomationCategory.get_category_info(category)
            if category_info:
                message += f"📂 **Категория:** {category_info['name']}\n"
            else:
                message += f"📂 **Категория:** {category}\n"
            
            complexity_desc = AutomationCategory.get_complexity_description(complexity)
            message += f"⚡ **Сложность:** {complexity_desc}\n"
            
            # Add tools (limit to 5)
            if tools:
                tools_text = ', '.join(tools[:5])
                if len(tools) > 5:
                    tools_text += f" и еще {len(tools) - 5}"
                message += f"🛠️ **Инструменты:** {tools_text}\n"
            
            if include_details:
                # Add summary if available
                summary = automation.get('summary', '')
                if summary and len(summary) > 100:
                    # Truncate summary for Telegram
                    summary_short = summary[:300] + "..." if len(summary) > 300 else summary
                    message += f"\n📝 **Описание:**\n{summary_short}\n"
                
                # Add similarity score if available
                similarity_score = automation.get('similarity_score', 0)
                if similarity_score > 0:
                    message += f"\n🎯 **Соответствие запросу:** {int(similarity_score * 100)}%\n"
            
            # Add URL if available
            if url:
                message += f"\n🔗 [Подробнее на n8n.io]({url})"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting automation for Telegram: {e}")
            return f"🤖 **{automation.get('title', 'Automation')}**\nОшибка форматирования"

    def format_category_list_for_telegram(self, categories: List[Dict]) -> str:
        """Format category list for Telegram message"""
        message = "📚 **Доступные категории автоматизации:**\n\n"
        
        for category in categories:
            emoji_map = {
                'social-media': '📱',
                'ai-ml': '🧠',
                'business-automation': '💼',
                'data-processing': '📊',
                'communication': '💬',
                'productivity': '⚡',
                'web-scraping': '🕷️',
                'marketing': '📈',
                'api-integration': '🔗',
                'e-commerce': '🛒'
            }
            
            emoji = emoji_map.get(category['key'], '⚙️')
            message += f"{emoji} **{category['name']}**\n"
            message += f"   {category['description']}\n\n"
        
        return message

    async def process_data_pipeline(self, batch_size: int = 5, start_from: int = 0) -> Dict:
        """Process the data pipeline (admin function)"""
        try:
            logger.info(f"Starting data pipeline processing (batch_size={batch_size}, start_from={start_from})")
            
            result = await self.vector_pipeline.process_automation_files(
                batch_size=batch_size,
                start_from=start_from
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in data pipeline: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def get_pipeline_stats(self) -> Dict:
        """Get data pipeline statistics (admin function)"""
        try:
            return self.vector_pipeline.get_processing_stats()
        except Exception as e:
            logger.error(f"Error getting pipeline stats: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    async def search_automations_by_tool(self, user_id: int, tool_name: str, max_results: int = 5) -> Dict:
        """Search automations that use a specific tool"""
        try:
            query = f"automation workflow using {tool_name}"
            filters = {'tools': [tool_name]}
            
            result = await self.rag_service.query_automations(
                query=query,
                filters=filters,
                max_results=max_results
            )
            
            if result.get('success') and result.get('recommendations'):
                # Enhance response with tool-specific information
                result['tool_info'] = {
                    'tool_name': tool_name,
                    'found_automations': len(result['recommendations']),
                    'message': f'Найдено {len(result["recommendations"])} автоматизаций, использующих {tool_name}'
                }
            
            await self._log_user_interaction(user_id, f"tool:{tool_name}", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching by tool: {e}")
            return {
                'success': False,
                'error': f'Ошибка при поиске автоматизаций с инструментом "{tool_name}"',
                'technical_error': str(e)
            }

    def create_quick_reply_keyboard(self, automation: Dict) -> List[List[str]]:
        """Create quick reply keyboard for automation"""
        keyboard = []
        
        # Add category button
        category = automation.get('category', '')
        if category:
            keyboard.append([f"📂 Категория: {category}"])
        
        # Add similar automations button
        keyboard.append(["🔍 Похожие автоматизации"])
        
        # Add tools button if tools available
        tools = automation.get('tools', [])
        if tools:
            keyboard.append([f"🛠️ Инструменты ({len(tools)})"])
        
        return keyboard

    async def _log_user_interaction(self, user_id: int, query: str, result: Dict) -> None:
        """Log user interaction for analytics and personalization"""
        try:
            # Simple logging for now - could be enhanced with dedicated analytics table
            interaction_data = {
                'user_id': user_id,
                'query': query,
                'timestamp': datetime.now().isoformat(),
                'success': result.get('success', False),
                'results_count': len(result.get('recommendations', [])),
                'query_type': self._classify_query_type(query)
            }
            
            logger.info(f"User interaction logged: {interaction_data}")
            
            # TODO: Store in analytics table when implemented
            
        except Exception as e:
            logger.warning(f"Failed to log user interaction: {e}")

    def _classify_query_type(self, query: str) -> str:
        """Classify the type of user query"""
        query_lower = query.lower()
        
        if query.startswith('category:'):
            return 'category_browse'
        elif query.startswith('tool:'):
            return 'tool_search'
        elif query.startswith('trending:'):
            return 'trending'
        elif query.startswith('beginner:'):
            return 'beginner'
        elif any(word in query_lower for word in ['how', 'как', 'что', 'где']):
            return 'question'
        elif any(word in query_lower for word in ['automate', 'automation', 'автоматизация']):
            return 'automation_search'
        else:
            return 'general_search'

    def get_help_message(self) -> str:
        """Get help message for automation features"""
        return """🤖 **Помощник по автоматизации**

**Доступные команды:**
• `/automate [описание задачи]` - Найти автоматизацию для вашей задачи
• `/knowledge` - Открыть базу знаний по автоматизации
• `/categories` - Просмотреть все категории автоматизации

**Примеры запросов:**
• "Автоматизировать отправку email"
• "Интеграция Telegram с Google Sheets"  
• "Обработка данных с помощью AI"
• "Автоматизация социальных сетей"

**Поддерживаемые категории:**
📱 Социальные сети
🧠 ИИ и машинное обучение  
💼 Бизнес процессы
📊 Обработка данных
💬 Коммуникации
⚡ Продуктивность
🕷️ Веб-скрейпинг
📈 Маркетинг
🔗 API интеграции
🛒 E-commerce

Просто опишите вашу задачу, и я найду подходящие решения автоматизации!"""