-- Fix RLS policies for existing tables
-- Run this in your Supabase SQL editor to add missing INSERT/UPDATE policies

-- Categories table policies
CREATE POLICY "Enable insert access for all users" ON categories FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON categories FOR UPDATE USING (true);

-- Documents table policies  
CREATE POLICY "Enable insert access for all users" ON documents FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON documents FOR UPDATE USING (true);

-- Automations table policies
CREATE POLICY "Enable insert access for all users" ON automations FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update access for all users" ON automations FOR UPDATE USING (true);