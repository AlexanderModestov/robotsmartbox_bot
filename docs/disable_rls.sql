-- Temporarily disable RLS for testing/development
-- WARNING: This removes security restrictions - only use in development

-- Disable RLS on all tables
ALTER TABLE categories DISABLE ROW LEVEL SECURITY;
ALTER TABLE documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE automations DISABLE ROW LEVEL SECURITY;

-- To re-enable RLS later, run:
-- ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE automations ENABLE ROW LEVEL SECURITY;