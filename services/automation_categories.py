from typing import Dict, List, Optional
from enum import Enum
import re

class ComplexityLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"

class AutomationCategory:
    """Automation category management and classification"""
    
    # Main categories with their subcategories and keywords
    CATEGORIES = {
        'social-media': {
            'name': 'Социальные сети',
            'description': 'Автоматизация для социальных платформ',
            'keywords': [
                'social media', 'linkedin', 'twitter', 'facebook', 'instagram',
                'tiktok', 'youtube', 'posting', 'content creation', 'social posting'
            ],
            'subcategories': ['content-creation', 'posting', 'analytics', 'engagement'],
            'complexity': ComplexityLevel.INTERMEDIATE
        },
        'ai-ml': {
            'name': 'ИИ и машинное обучение',
            'description': 'Автоматизация с использованием ИИ',
            'keywords': [
                'ai', 'artificial intelligence', 'openai', 'gpt', 'claude', 'anthropic',
                'machine learning', 'ml', 'chatbot', 'llm', 'neural network'
            ],
            'subcategories': ['chatbots', 'text-generation', 'image-processing', 'data-analysis'],
            'complexity': ComplexityLevel.ADVANCED
        },
        'business-automation': {
            'name': 'Бизнес автоматизация',
            'description': 'Автоматизация бизнес-процессов',
            'keywords': [
                'business', 'crm', 'sales', 'leads', 'pipeline', 'workflow',
                'process automation', 'business process', 'enterprise'
            ],
            'subcategories': ['crm', 'sales', 'hr', 'finance', 'operations'],
            'complexity': ComplexityLevel.INTERMEDIATE
        },
        'data-processing': {
            'name': 'Обработка данных',
            'description': 'Автоматизация работы с данными',
            'keywords': [
                'data', 'database', 'sql', 'postgres', 'mongodb', 'mysql',
                'data processing', 'etl', 'data migration', 'analytics'
            ],
            'subcategories': ['extraction', 'transformation', 'loading', 'analysis'],
            'complexity': ComplexityLevel.ADVANCED
        },
        'communication': {
            'name': 'Коммуникации',
            'description': 'Автоматизация коммуникаций',
            'keywords': [
                'email', 'slack', 'telegram', 'discord', 'whatsapp', 'sms',
                'notification', 'messaging', 'communication', 'chat'
            ],
            'subcategories': ['email', 'messaging', 'notifications', 'alerts'],
            'complexity': ComplexityLevel.BEGINNER
        },
        'productivity': {
            'name': 'Продуктивность',
            'description': 'Автоматизация личной эффективности',
            'keywords': [
                'productivity', 'task', 'calendar', 'schedule', 'reminder',
                'todo', 'time management', 'personal', 'organization'
            ],
            'subcategories': ['task-management', 'scheduling', 'reminders', 'organization'],
            'complexity': ComplexityLevel.BEGINNER
        },
        'web-scraping': {
            'name': 'Веб-скрейпинг',
            'description': 'Автоматический сбор данных с веб-сайтов',
            'keywords': [
                'scraping', 'scrape', 'web scraping', 'data extraction',
                'crawling', 'parsing', 'web data', 'brightdata'
            ],
            'subcategories': ['data-extraction', 'monitoring', 'research', 'competitive-analysis'],
            'complexity': ComplexityLevel.INTERMEDIATE
        },
        'marketing': {
            'name': 'Маркетинг',
            'description': 'Автоматизация маркетинговых процессов',
            'keywords': [
                'marketing', 'seo', 'analytics', 'campaign', 'advertising',
                'content marketing', 'email marketing', 'lead generation'
            ],
            'subcategories': ['seo', 'content-marketing', 'email-marketing', 'analytics'],
            'complexity': ComplexityLevel.INTERMEDIATE
        },
        'api-integration': {
            'name': 'API интеграции',
            'description': 'Интеграция различных сервисов через API',
            'keywords': [
                'api', 'integration', 'webhook', 'http', 'rest api',
                'graphql', 'service integration', 'third party'
            ],
            'subcategories': ['rest-api', 'webhooks', 'service-integration', 'data-sync'],
            'complexity': ComplexityLevel.ADVANCED
        },
        'e-commerce': {
            'name': 'Электронная коммерция',
            'description': 'Автоматизация для интернет-магазинов',
            'keywords': [
                'ecommerce', 'e-commerce', 'shop', 'store', 'product',
                'inventory', 'orders', 'shopify', 'woocommerce'
            ],
            'subcategories': ['inventory', 'orders', 'customers', 'analytics'],
            'complexity': ComplexityLevel.INTERMEDIATE
        }
    }

    # Tool categories and their associated tools
    TOOL_CATEGORIES = {
        'automation-platforms': [
            'n8n', 'zapier', 'make', 'integromat', 'power-automate'
        ],
        'cloud-storage': [
            'google-drive', 'dropbox', 'onedrive', 'box', 'nextcloud'
        ],
        'spreadsheets': [
            'google-sheets', 'excel', 'airtable', 'notion', 'smartsheet'
        ],
        'communication': [
            'slack', 'discord', 'telegram', 'whatsapp', 'teams'
        ],
        'crm-systems': [
            'hubspot', 'pipedrive', 'salesforce', 'zoho', 'agile-crm'
        ],
        'databases': [
            'postgres', 'mongodb', 'mysql', 'supabase', 'firebase'
        ],
        'ai-services': [
            'openai', 'anthropic', 'gpt', 'claude', 'perplexity'
        ],
        'payment-systems': [
            'stripe', 'paypal', 'square', 'chargebee', 'paddle'
        ],
        'email-marketing': [
            'mailchimp', 'sendgrid', 'postmark', 'convertkit', 'activecampaign'
        ],
        'social-media': [
            'linkedin', 'twitter', 'facebook', 'instagram', 'youtube'
        ]
    }

    @classmethod
    def classify_content(cls, title: str, description: str, content: str) -> Dict:
        """Classify automation content into categories"""
        text = f"{title} {description} {content}".lower()
        
        # Score each category
        category_scores = {}
        for category_key, category_data in cls.CATEGORIES.items():
            score = 0
            for keyword in category_data['keywords']:
                # Count keyword occurrences with different weights
                keyword_count = text.count(keyword.lower())
                if keyword_count > 0:
                    # Title has higher weight
                    if keyword.lower() in title.lower():
                        score += keyword_count * 3
                    # Description has medium weight
                    elif keyword.lower() in description.lower():
                        score += keyword_count * 2
                    # Content has base weight
                    else:
                        score += keyword_count
            
            if score > 0:
                category_scores[category_key] = score
        
        # Get primary category (highest score)
        primary_category = max(category_scores, key=category_scores.get) if category_scores else 'automation'
        
        # Get all categories above threshold
        threshold = max(category_scores.values()) * 0.3 if category_scores else 0
        relevant_categories = [cat for cat, score in category_scores.items() if score >= threshold]
        
        return {
            'primary_category': primary_category,
            'all_categories': relevant_categories[:5],  # Limit to top 5
            'category_scores': category_scores,
            'category_info': cls.CATEGORIES.get(primary_category, {})
        }

    @classmethod
    def extract_tools(cls, content: str) -> Dict:
        """Extract and categorize tools mentioned in content"""
        content_lower = content.lower()
        found_tools = {}
        
        for tool_category, tools in cls.TOOL_CATEGORIES.items():
            category_tools = []
            for tool in tools:
                # Check for tool mentions (handle both hyphenated and spaced versions)
                tool_variations = [tool, tool.replace('-', ' '), tool.replace('-', '')]
                
                for variation in tool_variations:
                    if variation in content_lower:
                        category_tools.append(tool)
                        break
            
            if category_tools:
                found_tools[tool_category] = list(set(category_tools))
        
        # Flatten all tools for backward compatibility
        all_tools = []
        for tools_list in found_tools.values():
            all_tools.extend(tools_list)
        
        return {
            'by_category': found_tools,
            'all_tools': list(set(all_tools)),
            'tool_count': len(set(all_tools))
        }

    @classmethod
    def determine_complexity(cls, content: str, tools_data: Dict, categories: List[str]) -> str:
        """Determine automation complexity level"""
        complexity_score = 0
        content_lower = content.lower()
        
        # Base complexity from categories
        for category in categories:
            if category in cls.CATEGORIES:
                category_complexity = cls.CATEGORIES[category].get('complexity', ComplexityLevel.INTERMEDIATE)
                if category_complexity == ComplexityLevel.ADVANCED:
                    complexity_score += 3
                elif category_complexity == ComplexityLevel.INTERMEDIATE:
                    complexity_score += 2
                else:
                    complexity_score += 1
        
        # Tool complexity
        tool_count = tools_data.get('tool_count', 0)
        if tool_count >= 8:
            complexity_score += 3
        elif tool_count >= 5:
            complexity_score += 2
        elif tool_count >= 3:
            complexity_score += 1
        
        # Advanced feature indicators
        advanced_patterns = [
            'api', 'webhook', 'database', 'sql', 'embedding', 'vector',
            'machine learning', 'ai model', 'authentication', 'oauth',
            'rate limiting', 'pagination', 'error handling'
        ]
        
        for pattern in advanced_patterns:
            if pattern in content_lower:
                complexity_score += 1
        
        # Content length indicator
        if len(content) > 10000:
            complexity_score += 1
        elif len(content) > 5000:
            complexity_score += 0.5
        
        # Determine final complexity
        if complexity_score >= 8:
            return ComplexityLevel.ADVANCED.value
        elif complexity_score >= 4:
            return ComplexityLevel.INTERMEDIATE.value
        else:
            return ComplexityLevel.BEGINNER.value

    @classmethod
    def get_category_info(cls, category_key: str) -> Optional[Dict]:
        """Get information about a specific category"""
        return cls.CATEGORIES.get(category_key)

    @classmethod
    def get_all_categories(cls) -> Dict:
        """Get all available categories"""
        return cls.CATEGORIES

    @classmethod
    def suggest_categories(cls, query: str) -> List[str]:
        """Suggest categories based on user query"""
        query_lower = query.lower()
        suggestions = []
        
        for category_key, category_data in cls.CATEGORIES.items():
            for keyword in category_data['keywords']:
                if keyword in query_lower:
                    suggestions.append(category_key)
                    break
        
        return list(set(suggestions))

    @classmethod
    def get_complexity_description(cls, complexity: str) -> str:
        """Get human-readable complexity description"""
        descriptions = {
            'beginner': 'Простая настройка, подходит для начинающих',
            'intermediate': 'Средняя сложность, требует базовых знаний автоматизации',
            'advanced': 'Сложная настройка, для опытных пользователей'
        }
        return descriptions.get(complexity, 'Неизвестная сложность')

    @classmethod
    def categorize_automation(cls, title: str, description: str, content: str) -> Dict:
        """Main method to categorize an automation workflow"""
        
        # Classify content
        classification = cls.classify_content(title, description, content)
        
        # Extract tools
        tools_data = cls.extract_tools(content)
        
        # Determine complexity
        complexity = cls.determine_complexity(
            content, 
            tools_data, 
            classification['all_categories']
        )
        
        return {
            'primary_category': classification['primary_category'],
            'all_categories': classification['all_categories'],
            'category_info': classification['category_info'],
            'tools': tools_data['all_tools'],
            'tools_by_category': tools_data['by_category'],
            'complexity_level': complexity,
            'complexity_description': cls.get_complexity_description(complexity),
            'classification_confidence': len(classification['all_categories']) / len(cls.CATEGORIES)
        }