-- FIBO Omni-Director Pro Database Schema
-- SQLite compatible

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    brand_logo_path TEXT,
    negative_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assets table (every generated image)
CREATE TABLE IF NOT EXISTS assets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    parent_id TEXT,
    prompt TEXT NOT NULL,
    seed INTEGER NOT NULL,
    aspect_ratio TEXT NOT NULL DEFAULT '1:1',
    image_url TEXT,
    image_path TEXT,
    json_payload TEXT NOT NULL,
    matrix_position TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES assets(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_assets_project ON assets(project_id);
CREATE INDEX IF NOT EXISTS idx_assets_parent ON assets(parent_id);
CREATE INDEX IF NOT EXISTS idx_assets_seed ON assets(seed);
CREATE INDEX IF NOT EXISTS idx_assets_matrix_position ON assets(matrix_position);
CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at);
