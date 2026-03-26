-- Add shareable links support to projects table
ALTER TABLE projects ADD COLUMN share_token TEXT UNIQUE;
ALTER TABLE projects ADD COLUMN is_public BOOLEAN DEFAULT false;

-- Index for fast token lookups
CREATE INDEX idx_projects_share_token ON projects(share_token);