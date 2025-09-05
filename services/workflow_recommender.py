import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import numpy as np
from .rag_service import AutomationRAG
from .automation_categories import AutomationCategory
from bot.supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

class WorkflowRecommender:
    """Intelligent workflow recommendation system"""
    
    def __init__(self, supabase_client: SupabaseClient = None):
        self.rag_service = AutomationRAG(supabase_client)
        self.supabase_client = self.rag_service.supabase_client
        
        # Recommendation weights
        self.weights = {
            'similarity': 0.4,
            'user_history': 0.2,
            'category_preference': 0.15,
            'complexity_match': 0.1,
            'popularity': 0.1,
            'recency': 0.05
        }

    async def get_user_preferences(self, user_id: int) -> Dict:
        """Analyze user's automation preferences from interaction history"""
        try:
            # Get user data
            user = await self.supabase_client.get_user_by_telegram_id(user_id)
            
            if not user:
                return self._get_default_preferences()
            
            # TODO: In future, implement user interaction tracking
            # For now, return default preferences
            preferences = {
                'preferred_categories': ['productivity', 'business-automation'],
                'complexity_level': 'intermediate',
                'preferred_tools': ['n8n', 'google-sheets', 'slack'],
                'interaction_count': 0,
                'last_interaction': None
            }
            
            return preferences
            
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return self._get_default_preferences()

    def _get_default_preferences(self) -> Dict:
        """Get default user preferences for new users"""
        return {
            'preferred_categories': ['productivity', 'automation'],
            'complexity_level': 'beginner',
            'preferred_tools': ['n8n'],
            'interaction_count': 0,
            'last_interaction': None
        }

    def calculate_recommendation_score(self, automation: Dict, user_preferences: Dict, query_context: Dict = None) -> float:
        """Calculate recommendation score for an automation"""
        scores = {
            'similarity': 0,
            'user_history': 0,
            'category_preference': 0,
            'complexity_match': 0,
            'popularity': 0,
            'recency': 0
        }
        
        # Similarity score (from vector search)
        scores['similarity'] = automation.get('similarity_score', 0)
        
        # Category preference match
        automation_category = automation.get('category', '')
        preferred_categories = user_preferences.get('preferred_categories', [])
        if automation_category in preferred_categories:
            scores['category_preference'] = 1.0
        elif any(cat in automation_category for cat in preferred_categories):
            scores['category_preference'] = 0.7
        else:
            scores['category_preference'] = 0.3
        
        # Complexity level match
        user_complexity = user_preferences.get('complexity_level', 'intermediate')
        automation_complexity = automation.get('complexity', 'intermediate')
        
        if user_complexity == automation_complexity:
            scores['complexity_match'] = 1.0
        elif (user_complexity == 'beginner' and automation_complexity == 'intermediate') or \
             (user_complexity == 'intermediate' and automation_complexity == 'beginner'):
            scores['complexity_match'] = 0.8
        elif (user_complexity == 'intermediate' and automation_complexity == 'advanced') or \
             (user_complexity == 'advanced' and automation_complexity == 'intermediate'):
            scores['complexity_match'] = 0.6
        else:
            scores['complexity_match'] = 0.3
        
        # Tool preference match
        automation_tools = automation.get('tools', [])
        preferred_tools = user_preferences.get('preferred_tools', [])
        if automation_tools and preferred_tools:
            tool_matches = len(set(automation_tools) & set(preferred_tools))
            tool_score = min(tool_matches / len(preferred_tools), 1.0)
            scores['user_history'] = tool_score
        
        # Popularity score (based on total chunks - more chunks = more detailed/popular)
        total_chunks = automation.get('total_chunks', 1)
        scores['popularity'] = min(total_chunks / 10, 1.0)  # Normalize to max 1.0
        
        # Recency score (newer automations get slight boost)
        # TODO: Implement when we have creation dates
        scores['recency'] = 0.5  # Neutral score for now
        
        # Calculate weighted final score
        final_score = sum(scores[key] * self.weights[key] for key in scores)
        
        return final_score

    async def get_personalized_recommendations(self, user_id: int, query: str, max_results: int = 5) -> Dict:
        """Get personalized automation recommendations for a user"""
        try:
            logger.info(f"Getting personalized recommendations for user {user_id}")
            
            # Get user preferences
            user_preferences = await self.get_user_preferences(user_id)
            
            # Get base recommendations from RAG service
            rag_results = await self.rag_service.query_automations(
                query=query,
                max_results=max_results * 2  # Get more to re-rank
            )
            
            if not rag_results.get('success'):
                return rag_results
            
            base_recommendations = rag_results.get('recommendations', [])
            
            if not base_recommendations:
                return rag_results
            
            # Calculate personalized scores
            personalized_recommendations = []
            
            for automation in base_recommendations:
                personalized_score = self.calculate_recommendation_score(
                    automation, 
                    user_preferences,
                    {'query': query}
                )
                
                # Add personalization metadata
                automation_with_score = {
                    **automation,
                    'personalized_score': round(personalized_score, 3),
                    'personalization_factors': {
                        'category_match': automation.get('category') in user_preferences.get('preferred_categories', []),
                        'complexity_match': automation.get('complexity') == user_preferences.get('complexity_level'),
                        'tool_preference_match': bool(set(automation.get('tools', [])) & set(user_preferences.get('preferred_tools', [])))
                    }
                }
                
                personalized_recommendations.append(automation_with_score)
            
            # Sort by personalized score
            personalized_recommendations.sort(key=lambda x: x['personalized_score'], reverse=True)
            
            # Limit results
            final_recommendations = personalized_recommendations[:max_results]
            
            # Update the response
            result = {
                **rag_results,
                'recommendations': final_recommendations,
                'personalization': {
                    'user_preferences': user_preferences,
                    'applied': True,
                    'reranked': len(base_recommendations) != len(final_recommendations) or 
                              any(rec['personalized_score'] != rec['similarity_score'] for rec in final_recommendations)
                }
            }
            
            logger.info(f"Personalized recommendations completed: {len(final_recommendations)} results")
            return result
            
        except Exception as e:
            logger.error(f"Error in personalized recommendations: {e}")
            # Fallback to non-personalized recommendations
            return await self.rag_service.query_automations(query, max_results=max_results)

    async def get_category_recommendations(self, category: str, user_id: int = None, max_results: int = 10) -> Dict:
        """Get recommended automations for a specific category"""
        try:
            # Get category info
            category_info = AutomationCategory.get_category_info(category)
            
            if not category_info:
                return {
                    'success': False,
                    'error': f'Category "{category}" not found',
                    'available_categories': list(AutomationCategory.get_all_categories().keys())
                }
            
            # Create category-specific query
            query = f"{category_info['description']} {category_info['name']}"
            
            # Get user preferences if user_id provided
            user_preferences = {}
            if user_id:
                user_preferences = await self.get_user_preferences(user_id)
            
            # Get recommendations
            if user_id:
                results = await self.get_personalized_recommendations(user_id, query, max_results)
            else:
                results = await self.rag_service.query_automations(
                    query=query,
                    filters={'category': category},
                    max_results=max_results
                )
            
            # Add category context
            if results.get('success'):
                results['category_info'] = {
                    'category': category,
                    'name': category_info['name'],
                    'description': category_info['description'],
                    'subcategories': category_info.get('subcategories', []),
                    'typical_complexity': category_info.get('complexity', 'intermediate').value if hasattr(category_info.get('complexity'), 'value') else 'intermediate'
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting category recommendations: {e}")
            return {
                'success': False,
                'error': str(e),
                'category': category
            }

    async def get_trending_automations(self, time_period: str = 'week', max_results: int = 10) -> Dict:
        """Get trending automations (mock implementation for now)"""
        try:
            # For now, return popular categories based on general automation trends
            trending_queries = {
                'week': [
                    'AI automation workflows',
                    'social media automation',
                    'business process automation',
                    'data processing workflows',
                    'productivity automation'
                ],
                'month': [
                    'advanced AI integration',
                    'marketing automation',
                    'customer service automation',
                    'inventory management',
                    'reporting automation'
                ]
            }
            
            queries = trending_queries.get(time_period, trending_queries['week'])
            
            # Get diverse results from different trending topics
            all_results = []
            results_per_query = max(2, max_results // len(queries))
            
            for query in queries:
                query_results = await self.rag_service.query_automations(
                    query=query,
                    max_results=results_per_query
                )
                
                if query_results.get('success'):
                    recommendations = query_results.get('recommendations', [])
                    for rec in recommendations:
                        rec['trending_topic'] = query
                        rec['trending_score'] = rec.get('similarity_score', 0) + 0.1  # Small boost for trending
                    all_results.extend(recommendations)
            
            # Remove duplicates based on title
            seen_titles = set()
            unique_results = []
            for result in all_results:
                title = result.get('title', '')
                if title not in seen_titles:
                    seen_titles.add(title)
                    unique_results.append(result)
            
            # Sort by trending score and limit
            unique_results.sort(key=lambda x: x.get('trending_score', 0), reverse=True)
            final_results = unique_results[:max_results]
            
            return {
                'success': True,
                'query': f'trending automations ({time_period})',
                'results_found': len(final_results),
                'recommendations': final_results,
                'trending_info': {
                    'time_period': time_period,
                    'trending_topics': queries,
                    'unique_workflows': len(final_results)
                },
                'contextual_response': f'Вот {len(final_results)} популярных автоматизаций за последний {time_period}. Эти workflow особенно актуальны сейчас и могут значительно повысить вашу эффективность.'
            }
            
        except Exception as e:
            logger.error(f"Error getting trending automations: {e}")
            return {
                'success': False,
                'error': str(e),
                'time_period': time_period
            }

    async def get_similar_workflows(self, workflow_title: str, max_results: int = 5) -> Dict:
        """Find workflows similar to a given one"""
        try:
            return await self.rag_service.get_similar_automations(workflow_title, max_results)
            
        except Exception as e:
            logger.error(f"Error finding similar workflows: {e}")
            return {
                'success': False,
                'error': str(e),
                'workflow_title': workflow_title
            }

    async def get_beginner_friendly_automations(self, category: str = None, max_results: int = 8) -> Dict:
        """Get automations suitable for beginners"""
        try:
            query = "simple easy beginner automation workflow"
            if category:
                query += f" {category}"
            
            filters = {'complexity': 'beginner'}
            if category:
                filters['category'] = category
            
            results = await self.rag_service.query_automations(
                query=query,
                filters=filters,
                max_results=max_results
            )
            
            if results.get('success'):
                # Add beginner-specific context
                results['beginner_info'] = {
                    'complexity_level': 'beginner',
                    'recommended_for': 'Пользователи без опыта автоматизации',
                    'typical_setup_time': '15-30 минут',
                    'support_level': 'Подробные инструкции и примеры'
                }
                
                # Enhance contextual response for beginners
                original_response = results.get('contextual_response', '')
                results['contextual_response'] = f"""🚀 Отличный выбор для начала работы с автоматизацией!

{original_response}

💡 **Советы для начинающих:**
- Начните с простых автоматизаций
- Изучите каждый шаг перед настройкой
- Не бойтесь экспериментировать в тестовой среде
- Обращайтесь за помощью в сообществе n8n"""
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting beginner automations: {e}")
            return {
                'success': False,
                'error': str(e),
                'category': category
            }

    def get_recommendation_stats(self) -> Dict:
        """Get statistics about the recommendation system"""
        return {
            'available_categories': len(AutomationCategory.get_all_categories()),
            'supported_tools': len(AutomationCategory.TOOL_CATEGORIES),
            'complexity_levels': ['beginner', 'intermediate', 'advanced'],
            'recommendation_weights': self.weights,
            'features': [
                'Personalized recommendations',
                'Category-based filtering',
                'Complexity matching',
                'Tool preference matching',
                'Trending analysis',
                'Similar workflow detection'
            ]
        }