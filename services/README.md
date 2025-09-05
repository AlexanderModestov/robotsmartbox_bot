# Automation Services Documentation

This directory contains the complete automation pipeline implementation for the Telegram bot, including summarization, vector search, RAG (Retrieval Augmented Generation), and recommendation systems.

## 🏗️ Architecture Overview

```
services/
├── summarization_service.py    # AI-powered content summarization
├── vector_pipeline.py         # Data processing and vector database creation
├── rag_service.py             # RAG query system for automation search  
├── automation_categories.py   # Category classification and management
├── workflow_recommender.py    # Personalized recommendation system
└── bot/services/
    └── automation_handler.py  # Bot integration layer
```

## 📚 Components

### 1. Summarization Service (`summarization_service.py`)

**Purpose**: Generates concise, structured summaries of n8n automation workflows within 2000 tokens.

**Features**:
- Multi-provider support (OpenAI GPT-4 + Anthropic Claude)
- Token-aware processing with tiktoken
- Structured output with categories, tools, and complexity
- Batch processing with concurrency control
- Automatic fallback between providers

**Usage**:
```python
from services.summarization_service import SummarizationService

service = SummarizationService(provider="openai")
summary = await service.summarize_automation(content, metadata)
```

### 2. Vector Pipeline (`vector_pipeline.py`)

**Purpose**: Processes n8n JSON files into a searchable vector database.

**Features**:
- Loads and validates 150+ JSON automation files
- Creates overlapping text chunks for better context
- Generates embeddings using OpenAI text-embedding-3-large
- Stores in Supabase with rich metadata
- Batch processing with error handling
- Processing logs and statistics

**Usage**:
```python
from services.vector_pipeline import VectorPipeline

pipeline = VectorPipeline(supabase_client)
result = await pipeline.process_automation_files(batch_size=5)
```

### 3. RAG Service (`rag_service.py`)

**Purpose**: Intelligent search and retrieval system for automation workflows.

**Features**:
- Vector similarity search with filtering
- Query embedding generation
- Results grouping by automation workflow
- Contextual response generation using GPT
- Category and tool-based filtering
- Similarity threshold management

**Usage**:
```python
from services.rag_service import AutomationRAG

rag = AutomationRAG(supabase_client)
result = await rag.query_automations("email automation", filters={'category': 'productivity'})
```

### 4. Automation Categories (`automation_categories.py`)

**Purpose**: Classification and categorization system for automation workflows.

**Features**:
- 10 main categories with subcategories
- Tool classification (automation-platforms, databases, etc.)
- Complexity level determination (beginner/intermediate/advanced)
- Keyword-based content classification
- Category information and descriptions

**Categories**:
- 📱 Social Media
- 🧠 AI & Machine Learning
- 💼 Business Automation
- 📊 Data Processing
- 💬 Communication
- ⚡ Productivity
- 🕷️ Web Scraping
- 📈 Marketing
- 🔗 API Integration
- 🛒 E-commerce

### 5. Workflow Recommender (`workflow_recommender.py`)

**Purpose**: Personalized recommendation system with user preference learning.

**Features**:
- Personalized recommendations based on user history
- Multi-factor scoring (similarity, category, complexity, tools)
- Trending automation detection
- Beginner-friendly workflow filtering
- Similar workflow detection
- User interaction logging

**Usage**:
```python
from services.workflow_recommender import WorkflowRecommender

recommender = WorkflowRecommender(supabase_client)
result = await recommender.get_personalized_recommendations(user_id, "social media automation")
```

### 6. Bot Integration Handler (`bot/services/automation_handler.py`)

**Purpose**: Integration layer between services and Telegram bot commands.

**Features**:
- User query processing
- Category browsing
- Trending automations
- Telegram message formatting
- Interactive keyboards
- User interaction logging

## 🚀 Setup and Installation

### 1. Install Dependencies

```bash
# Install additional requirements for automation services
pip install -r services/requirements.txt
```

### 2. Environment Variables

Add to your `.env` file:

```env
# Required
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Optional
ANTHROPIC_API_KEY=your_anthropic_api_key
EMBEDDING_MODEL=text-embedding-3-large
GPT_MODEL=gpt-4o-mini
SEARCH_LIMIT=5
```

### 3. Database Schema

The system requires additional columns in your `documents` table:

```sql
-- Run in Supabase SQL Editor
ALTER TABLE documents ADD COLUMN IF NOT EXISTS workflow_type VARCHAR(50);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS complexity_level VARCHAR(20);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS tools_used TEXT[];

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_workflow_type ON documents(workflow_type);
CREATE INDEX IF NOT EXISTS idx_documents_complexity ON documents(complexity_level);
CREATE INDEX IF NOT EXISTS idx_documents_category_workflow ON documents(category, workflow_type);
```

### 4. Data Processing

Use the management script to process your automation data:

```bash
# Process all automation files
python manage_automation_data.py process

# Test summarization on sample files
python manage_automation_data.py test --sample-size 5

# Check processing statistics
python manage_automation_data.py stats

# Check database status
python manage_automation_data.py check
```

## 📖 Bot Commands

The system adds these new commands to your bot:

### `/automate [query]`
Find automation solutions for specific tasks.

**Examples**:
- `/automate email notifications`
- `/automate social media posting`
- `/automate data sync between Google Sheets and database`

### `/knowledge`
Browse the automation knowledge base by categories.

**Features**:
- 🔥 Trending automations
- 🚀 Beginner-friendly workflows
- 📂 Category browsing

## 🔧 Management Script

The `manage_automation_data.py` script provides complete pipeline management:

### Commands

```bash
# Process all data (recommended for first run)
python manage_automation_data.py process --batch-size 5

# Resume processing from specific file index
python manage_automation_data.py process --start-from 50

# Test summarization service
python manage_automation_data.py test --sample-size 3

# View processing statistics
python manage_automation_data.py stats

# Check database connectivity
python manage_automation_data.py check
```

### Processing Flow

1. **Validation**: Checks configuration and API keys
2. **Schema Update**: Updates database schema if needed
3. **File Loading**: Loads and validates JSON files from `/data/n8n/`
4. **Summarization**: Generates AI summaries for each automation
5. **Chunking**: Creates overlapping text chunks for better search
6. **Embedding**: Generates vector embeddings using OpenAI
7. **Storage**: Stores in Supabase with rich metadata
8. **Logging**: Creates detailed processing logs

## 📊 Performance & Scaling

### Batch Processing
- Default batch size: 5 files
- Concurrent processing within batches
- Rate limiting between batches
- Resumable from any point

### Token Management
- Summary limit: 2000 tokens
- Chunking with overlap: 1000 tokens per chunk
- Embedding input limit: 8000 characters

### Database Optimization
- Indexes on key fields for fast queries
- Vector similarity search using Supabase
- Chunked storage for better retrieval

## 🛠️ Customization

### Adding New Categories

Edit `automation_categories.py`:

```python
'your-category': {
    'name': 'Your Category',
    'description': 'Description',
    'keywords': ['keyword1', 'keyword2'],
    'subcategories': ['sub1', 'sub2'],
    'complexity': ComplexityLevel.INTERMEDIATE
}
```

### Adjusting Recommendation Weights

Modify weights in `workflow_recommender.py`:

```python
self.weights = {
    'similarity': 0.4,
    'user_history': 0.2,
    'category_preference': 0.15,
    'complexity_match': 0.1,
    'popularity': 0.1,
    'recency': 0.05
}
```

### Custom Summarization Prompts

Update prompts in `summarization_service.py` for domain-specific summaries.

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Database Connection**: Check Supabase URL and key
3. **API Rate Limits**: Adjust batch size and delays
4. **Memory Issues**: Reduce batch size for large datasets

### Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check processing logs in `data/processed/` directory.

## 📈 Monitoring

### Processing Logs
- Located in `data/processed/processing_log_*.json`
- Contains statistics and error details
- Includes processing timestamps and batch info

### Bot Analytics
- User interaction logging
- Query classification
- Popular categories tracking

## 🔮 Future Enhancements

1. **User Learning**: Enhanced personalization based on interaction history
2. **Real-time Updates**: Webhook-based updates for new automations
3. **Multi-language**: Support for multiple languages
4. **Advanced Filtering**: More granular filtering options
5. **Analytics Dashboard**: Web interface for monitoring and analytics

## 📄 License

This automation services system is part of the RobotSmart Telegram bot project.