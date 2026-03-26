-- Simple SQL script to add sharing columns to projects table
-- Run this directly against your database

-- Add sharing columns if they don't exist
DO $$ 
BEGIN
    -- Add share_token column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'projects' AND column_name = 'share_token') THEN
        ALTER TABLE projects ADD COLUMN share_token TEXT UNIQUE;
    END IF;
    
    -- Add is_public column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'projects' AND column_name = 'is_public') THEN
        ALTER TABLE projects ADD COLUMN is_public BOOLEAN DEFAULT false;
    END IF;
END $$;

-- Create index for fast token lookups
CREATE INDEX IF NOT EXISTS idx_projects_share_token ON projects(share_token);

-- Verify the columns were added
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'projects' 
AND column_name IN ('share_token', 'is_public')
ORDER BY column_name;