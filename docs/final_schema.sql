-- Final Data Architecture for RoboSmartBox Bot
-- Simplified schema with documents table for workflow storage

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table (existing structure)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    language VARCHAR(10) DEFAULT 'en',
    isAudio BOOLEAN DEFAULT FALSE,
    notification BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Documents table (new structure for workflows)
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500),
    name_ru VARCHAR(500),
    category_id VARCHAR(100),
    subdirectory_id VARCHAR(100),
    url VARCHAR(500) NOT NULL,
    short_description TEXT NOT NULL,
    short_description_ru TEXT,
    description TEXT NOT NULL,
    description_ru TEXT,
    tags TEXT[],
    stack TEXT[],
    embedding VECTOR(3072),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User messages table (existing structure)
CREATE TABLE IF NOT EXISTS user_messages (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    message_type VARCHAR(50) NOT NULL,
    content TEXT,
    audio_file_path VARCHAR(1000),
    transcription TEXT,
    is_forwarded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_documents_category_id ON documents(category);
CREATE INDEX IF NOT EXISTS idx_documents_subdirectory_id ON documents(subcategory);
CREATE INDEX IF NOT EXISTS idx_documents_tags ON documents USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_documents_stack ON documents USING gin(stack);
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops);
-- Note: pgvector indexes are limited to 2000 dimensions, text-embedding-3-large uses 3072

-- Triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE INSERT OR UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE INSERT OR UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- RLS policies for full access
CREATE POLICY "Enable full access for all users" ON users FOR ALL USING (true);
CREATE POLICY "Enable full access for all users" ON documents FOR ALL USING (true);