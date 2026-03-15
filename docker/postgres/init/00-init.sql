-- Local dev bootstrap for SPS + Temporal.
-- Idempotent-ish: safe to re-run on a new empty volume.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sps') THEN
    CREATE ROLE sps LOGIN PASSWORD 'sps';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'temporal') THEN
    CREATE ROLE temporal LOGIN PASSWORD 'temporal';
  END IF;
END
$$;

-- Databases must be created outside transaction blocks.
-- `CREATE DATABASE` cannot run inside a DO $$ ... $$ block.

SELECT format('CREATE DATABASE %I OWNER %I', 'sps', 'sps')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'sps')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', 'temporal', 'temporal')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'temporal')\gexec

SELECT format('CREATE DATABASE %I OWNER %I', 'temporal_visibility', 'temporal')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'temporal_visibility')\gexec
