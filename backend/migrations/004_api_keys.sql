-- 004_api_keys.sql
-- Stores encrypted API keys per user and per-agent assignments

CREATE TABLE api_keys (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider    TEXT NOT NULL,
  label       TEXT NOT NULL,
  key_preview TEXT NOT NULL,
  key_enc     TEXT NOT NULL,
  is_active   BOOLEAN DEFAULT TRUE,
  last_tested TIMESTAMPTZ,
  test_ok     BOOLEAN,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_keys" ON api_keys
  FOR ALL USING (auth.uid() = user_id);

CREATE TABLE agent_key_assignments (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  agent_name TEXT NOT NULL,
  provider   TEXT NOT NULL,
  api_key_id UUID REFERENCES api_keys(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE agent_key_assignments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_own_assignments" ON agent_key_assignments
  FOR ALL USING (auth.uid() = user_id);

-- Ensure a single assignment per user+agent
CREATE UNIQUE INDEX IF NOT EXISTS ux_user_agent ON agent_key_assignments (user_id, agent_name);
