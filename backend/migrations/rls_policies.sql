-- ============================================================
-- ArchAI — Supabase Row Level Security Policies
-- Run this in Supabase SQL Editor (Database → SQL Editor → New query)
-- ============================================================

-- ── 1. Enable RLS on all tables ─────────────────────────────
ALTER TABLE users             ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects          ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs        ENABLE ROW LEVEL SECURITY;
ALTER TABLE design_variants   ENABLE ROW LEVEL SECURITY;
ALTER TABLE cost_estimates    ENABLE ROW LEVEL SECURITY;
ALTER TABLE geo_analysis      ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_checks ENABLE ROW LEVEL SECURITY;

-- ── 2. project_members — team collaboration table ────────────
CREATE TABLE IF NOT EXISTS project_members (
  project_id  UUID         NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  user_id     UUID         NOT NULL,
  role        TEXT         NOT NULL DEFAULT 'viewer',  -- viewer | editor | owner
  invited_by  UUID,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  PRIMARY KEY (project_id, user_id)
);
ALTER TABLE project_members ENABLE ROW LEVEL SECURITY;


-- ── 3. Users table ───────────────────────────────────────────
-- Users can see and update only their own row
CREATE POLICY "users_own_row_select" ON users
  FOR SELECT USING (id = auth.uid());

CREATE POLICY "users_own_row_update" ON users
  FOR UPDATE USING (id = auth.uid());


-- ── 4. Projects ──────────────────────────────────────────────
-- Owner OR team member can SELECT
CREATE POLICY "projects_select" ON projects
  FOR SELECT USING (
    user_id = auth.uid()
    OR id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid()
    )
  );

-- Only owner can INSERT
CREATE POLICY "projects_insert" ON projects
  FOR INSERT WITH CHECK (user_id = auth.uid());

-- Owner OR editor can UPDATE
CREATE POLICY "projects_update" ON projects
  FOR UPDATE USING (
    user_id = auth.uid()
    OR id IN (
      SELECT project_id FROM project_members
      WHERE user_id = auth.uid() AND role IN ('editor', 'owner')
    )
  );

-- Only owner can DELETE
CREATE POLICY "projects_delete" ON projects
  FOR DELETE USING (user_id = auth.uid());


-- ── 5. Agent runs (cascaded through project ownership) ───────
CREATE POLICY "agent_runs_select" ON agent_runs
  FOR SELECT USING (
    project_id IN (
      SELECT id FROM projects
      WHERE user_id = auth.uid()
         OR id IN (SELECT project_id FROM project_members WHERE user_id = auth.uid())
    )
  );

CREATE POLICY "agent_runs_insert" ON agent_runs
  FOR INSERT WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

CREATE POLICY "agent_runs_update" ON agent_runs
  FOR UPDATE USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );


-- ── 6. Design variants ───────────────────────────────────────
CREATE POLICY "variants_select" ON design_variants
  FOR SELECT USING (
    project_id IN (
      SELECT id FROM projects
      WHERE user_id = auth.uid()
         OR id IN (SELECT project_id FROM project_members WHERE user_id = auth.uid())
    )
  );

CREATE POLICY "variants_write" ON design_variants
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );


-- ── 7. Cost estimates ────────────────────────────────────────
CREATE POLICY "costs_select" ON cost_estimates
  FOR SELECT USING (
    project_id IN (
      SELECT id FROM projects
      WHERE user_id = auth.uid()
         OR id IN (SELECT project_id FROM project_members WHERE user_id = auth.uid())
    )
  );

CREATE POLICY "costs_write" ON cost_estimates
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );


-- ── 8. Geo analysis ──────────────────────────────────────────
CREATE POLICY "geo_select" ON geo_analysis
  FOR SELECT USING (
    project_id IN (
      SELECT id FROM projects
      WHERE user_id = auth.uid()
         OR id IN (SELECT project_id FROM project_members WHERE user_id = auth.uid())
    )
  );

CREATE POLICY "geo_write" ON geo_analysis
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );


-- ── 9. Compliance checks ─────────────────────────────────────
CREATE POLICY "compliance_select" ON compliance_checks
  FOR SELECT USING (
    project_id IN (
      SELECT id FROM projects
      WHERE user_id = auth.uid()
         OR id IN (SELECT project_id FROM project_members WHERE user_id = auth.uid())
    )
  );

CREATE POLICY "compliance_write" ON compliance_checks
  FOR ALL USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );


-- ── 10. Project members ──────────────────────────────────────
-- Members can see their own membership rows
CREATE POLICY "members_select_own" ON project_members
  FOR SELECT USING (
    user_id = auth.uid()
    OR project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

-- Owners can invite members
CREATE POLICY "members_insert" ON project_members
  FOR INSERT WITH CHECK (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

-- Owners can remove members / update roles
CREATE POLICY "members_update" ON project_members
  FOR UPDATE USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
  );

CREATE POLICY "members_delete" ON project_members
  FOR DELETE USING (
    project_id IN (SELECT id FROM projects WHERE user_id = auth.uid())
    OR user_id = auth.uid()   -- members can remove themselves
  );
