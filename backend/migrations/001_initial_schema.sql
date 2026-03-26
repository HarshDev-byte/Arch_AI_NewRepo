-- ============================================================
-- ArchAI — Initial Schema Migration
-- 001_initial_schema.sql
-- ============================================================

-- Enable UUID generation (Postgres 13+ has this built-in)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ─────────────────────────────────────────────────────────────
-- users
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE NOT NULL,
  name        TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- projects
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
  name                TEXT NOT NULL,
  status              TEXT NOT NULL DEFAULT 'pending',
                        -- pending | processing | complete | error

  -- Location
  latitude            DOUBLE PRECISION,
  longitude           DOUBLE PRECISION,

  -- Plot brief
  plot_area_sqm       DOUBLE PRECISION,
  budget_inr          BIGINT,
  floors              INTEGER NOT NULL DEFAULT 2,
  style_preferences   JSONB NOT NULL DEFAULT '[]',

  -- Design DNA
  design_seed         TEXT,
  design_dna          JSONB,

  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS projects_set_updated_at ON projects;
CREATE TRIGGER projects_set_updated_at
  BEFORE UPDATE ON projects
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ─────────────────────────────────────────────────────────────
-- agent_runs
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_runs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  agent_name      TEXT NOT NULL,
                    -- geo|cost|layout|design|threed|vr|compliance|sustainability
  status          TEXT NOT NULL DEFAULT 'pending',
                    -- pending|running|complete|error
  input_data      JSONB,
  output_data     JSONB,
  error_message   TEXT,
  started_at      TIMESTAMPTZ,
  completed_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- design_variants
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS design_variants (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  variant_number  INTEGER,
  dna             JSONB,
  score           DOUBLE PRECISION,
  is_selected     BOOLEAN NOT NULL DEFAULT false,
  floor_plan_svg  TEXT,
  model_url       TEXT,        -- Supabase Storage .glb URL
  thumbnail_url   TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- cost_estimates
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cost_estimates (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  breakdown             JSONB,
  total_cost_inr        BIGINT,
  cost_per_sqft         DOUBLE PRECISION,
  roi_estimate          JSONB,
  land_value_estimate   BIGINT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- geo_analysis
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS geo_analysis (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id        UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  plot_data         JSONB,
  zoning_type       TEXT,
  fsi_allowed       DOUBLE PRECISION,
  road_access       JSONB,
  nearby_amenities  JSONB,
  elevation_profile JSONB,
  solar_irradiance  DOUBLE PRECISION,
  wind_data         JSONB,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- compliance_checks
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS compliance_checks (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id            UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  fsi_used              DOUBLE PRECISION,
  fsi_allowed           DOUBLE PRECISION,
  setback_compliance    JSONB,
  height_compliance     BOOLEAN,
  parking_required      INTEGER,
  green_area_required   DOUBLE PRECISION,
  issues                JSONB NOT NULL DEFAULT '[]',
  passed                BOOLEAN,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Indexes for common query patterns
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_projects_user_id      ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_status       ON projects(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_project    ON agent_runs(project_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status     ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_design_variants_proj  ON design_variants(project_id);
CREATE INDEX IF NOT EXISTS idx_cost_estimates_proj   ON cost_estimates(project_id);
CREATE INDEX IF NOT EXISTS idx_geo_analysis_proj     ON geo_analysis(project_id);
CREATE INDEX IF NOT EXISTS idx_compliance_proj       ON compliance_checks(project_id);

-- ─────────────────────────────────────────────────────────────
-- Supabase Row-Level Security (RLS) — enable but allow all
-- for now; tighten per-row policies in production
-- ─────────────────────────────────────────────────────────────
ALTER TABLE users             ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects          ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs        ENABLE ROW LEVEL SECURITY;
ALTER TABLE design_variants   ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_estimates    ENABLE ROW LEVEL SECURITY;
ALTER TABLE geo_analysis      ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_checks ENABLE ROW LEVEL SECURITY;

-- Service-role bypass (backend uses service key → bypasses RLS)
-- Anon / auth policies — users own their projects
CREATE POLICY "users_own_projects" ON projects
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "projects_own_agent_runs" ON agent_runs
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

CREATE POLICY "projects_own_variants" ON design_variants
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

CREATE POLICY "projects_own_costs" ON cost_estimates
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

CREATE POLICY "projects_own_geo" ON geo_analysis
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

CREATE POLICY "projects_own_compliance" ON compliance_checks
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );
