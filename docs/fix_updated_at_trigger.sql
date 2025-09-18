-- Fix updated_at trigger to handle both INSERT and UPDATE operations
-- Run this in your Supabase SQL editor

-- Drop existing triggers
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_documents_updated_at ON documents;

-- Create or replace the function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for both INSERT and UPDATE operations
CREATE TRIGGER update_users_updated_at
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Test the triggers
-- INSERT test
INSERT INTO documents (name, url) VALUES ('Test Document', 'https://test.com') RETURNING id, name, created_at, updated_at;

-- UPDATE test (replace 'YOUR_DOC_ID' with actual ID from INSERT above)
-- UPDATE documents SET name = 'Updated Test Document' WHERE id = YOUR_DOC_ID RETURNING id, name, created_at, updated_at;

-- Verify triggers are active
SELECT
    trigger_name,
    event_manipulation,
    event_object_table,
    action_timing
FROM information_schema.triggers
WHERE trigger_name IN ('update_users_updated_at', 'update_documents_updated_at');