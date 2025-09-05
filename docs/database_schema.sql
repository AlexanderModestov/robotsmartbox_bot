-- Supabase database schema for automation documents

-- Table: categories
-- Stores unique category names
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: documents
-- Stores automation document information with embeddings
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) NOT NULL,
    short_description TEXT NOT NULL,
    description TEXT NOT NULL,
    embedding VECTOR(3072), -- OpenAI ada-002 embeddings are 1536 dimensions
    filename VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table: automations
-- Junction table linking documents to categories (many-to-many relationship)
CREATE TABLE IF NOT EXISTS automations (
    id SERIAL PRIMARY KEY,
    automatization INTEGER REFERENCES documents(id) ON DELETE CASCADE,
    category INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique combinations
    UNIQUE(automatization, category)
);

-- Indexes for better performance
-- Note: Vector indexes in pgvector are limited to 2000 dimensions
-- For 3072-dimensional embeddings, we'll rely on sequential scan for now
-- CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);
CREATE INDEX IF NOT EXISTS idx_automations_doc ON automations(automatization);
CREATE INDEX IF NOT EXISTS idx_automations_cat ON automations(category);

-- Enable RLS (Row Level Security) for Supabase
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE automations ENABLE ROW LEVEL SECURITY;

-- RLS policies for full access (adjust based on your authentication needs)
-- Categories table policies
CREATE POLICY "Enable read access for all users" ON categories FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON categories FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON categories FOR UPDATE USING (true);

-- Documents table policies  
CREATE POLICY "Enable read access for all users" ON documents FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON documents FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON documents FOR UPDATE USING (true);

-- Automations table policies
CREATE POLICY "Enable read access for all users" ON automations FOR SELECT USING (true);
CREATE POLICY "Enable insert access for all users" ON automations FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON automations FOR UPDATE USING (true);