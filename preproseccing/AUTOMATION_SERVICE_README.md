# Automation Document Processing Service

This service processes JSON files containing automation descriptions and creates a searchable database in Supabase with semantic search capabilities using OpenAI embeddings.

## Database Structure

The service creates three main tables:

### 1. `documents` table
- `id` (Primary Key)
- `url` - Original URL from JSON
- `short_description` - Short description from JSON
- `description` - Full description from JSON
- `embedding` - Vector embedding for semantic search (3072 dimensions)
- `filename` - Source filename
- Timestamps

### 2. `categories` table
- `id` (Primary Key)
- `name` - Unique category name
- Timestamps

### 3. `automations` table (Junction table)
- `id` (Primary Key)
- `automatization` - Foreign key to documents(id)
- `category` - Foreign key to categories(id)
- Unique constraint on (automatization, category)

## Setup

### 1. Prerequisites
- Python 3.8+
- Supabase account
- OpenAI API key

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Required variables:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anonymous/public key
- `OPENAI_API_KEY`: Your OpenAI API key

### 4. Database Setup
1. Run the schema creation script in your Supabase SQL editor:
```sql
-- Copy contents of database_schema.sql
```

2. Enable the vector extension (required for embeddings):
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

3. Create the semantic search function:
```sql
-- Copy the MATCH_DOCUMENTS_FUNCTION from automation_search.py
```

## Usage

### Processing Automation Files

#### Basic usage:
```bash
python run_processor.py
```

#### With custom data directory:
```bash
python run_processor.py --data-dir /path/to/json/files
```

#### Dry run (preview what will be processed):
```bash
python run_processor.py --dry-run
```

### Searching Documents

#### Using the search service directly:
```python
from automation_search import AutomationSearch

search = AutomationSearch()

# Semantic search
results = search.semantic_search("AI chatbot automation", limit=5)

# Search by category
results = search.search_by_category("ai chatbot", limit=10)

# Get all categories
categories = search.get_all_categories()
```

#### Demo search functionality:
```bash
python automation_search.py
```

## JSON File Format

Each JSON file should contain:
```json
{
  "url": "https://example.com/workflow",
  "categories": [
    "category1",
    "category2"
  ],
  "description": "Full description of the automation...",
  "short_description": "Brief description",
  "filename": "optional-filename.json"
}
```

## Features

### Semantic Search
- Uses OpenAI's text-embedding-3-large model (3072 dimensions)
- Vector similarity search with cosine distance
- Configurable similarity threshold
- **Note**: Vector indexes are limited to 2000 dimensions in pgvector, so searches use sequential scan
- Performance is still acceptable for datasets under ~100k documents

### Category Management
- Automatic category extraction and deduplication
- Many-to-many relationship between documents and categories
- Category-based filtering

### Error Handling
- Comprehensive logging
- Graceful handling of malformed JSON files
- Transaction safety for database operations

## API Integration

The service is designed to work with:
- **Supabase**: For database and vector search
- **OpenAI**: For text embeddings
- **PostgreSQL with pgvector**: For efficient vector operations

## Performance Considerations

- Batch processing of embeddings
- **Vector searches without index**: Due to 3072-dimension embeddings exceeding pgvector's 2000-dimension index limit
- Sequential scan performance is acceptable for datasets under 100k documents
- Consider pagination for large result sets
- Connection pooling
- Configurable batch sizes

### Performance Tips for Large Datasets

1. **Pre-filter by category** when possible to reduce search space
2. **Implement pagination** for search results
3. **Use connection pooling** for database connections
4. **Consider upgrading to newer pgvector versions** that may support higher dimensions

## Security

- Row Level Security (RLS) enabled on all tables
- Environment variable configuration
- API key protection
- Input validation and sanitization

## Monitoring

- Structured logging throughout the application
- Error tracking and reporting
- Processing statistics and metrics

## Troubleshooting

### Common Issues

1. **"Missing required environment variables"**
   - Ensure all required variables are set in your `.env` file

2. **"Vector extension not found"**
   - Enable the vector extension in your Supabase database

3. **"OpenAI API rate limit"**
   - Implement rate limiting or use a higher tier API key

4. **"Embedding dimension mismatch"**
   - Ensure you're using the text-embedding-3-large model (3072 dimensions)

### Debug Mode
Enable debug logging by setting:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Follow the existing code structure
2. Add comprehensive error handling
3. Include logging for all operations
4. Update documentation for new features
5. Test with sample data before deploying