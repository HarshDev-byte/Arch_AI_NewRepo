-- Migration 005: Add floor plan editor support fields
-- Adds plot dimensions and FSI fields to projects table

ALTER TABLE projects 
ADD COLUMN plot_width_m REAL,
ADD COLUMN plot_depth_m REAL,
ADD COLUMN fsi_allowed REAL DEFAULT 2.0;

-- Update existing projects with default values based on plot_area_sqm
-- Assume square plots for existing data
UPDATE projects 
SET 
    plot_width_m = SQRT(COALESCE(plot_area_sqm, 300)),
    plot_depth_m = SQRT(COALESCE(plot_area_sqm, 300))
WHERE plot_width_m IS NULL;

-- Add index for faster queries
CREATE INDEX idx_projects_plot_dimensions ON projects(plot_width_m, plot_depth_m);