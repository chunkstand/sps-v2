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

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'sps') THEN
    CREATE DATABASE sps OWNER sps;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'temporal') THEN
    CREATE DATABASE temporal OWNER temporal;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'temporal_visibility') THEN
    CREATE DATABASE temporal_visibility OWNER temporal;
  END IF;
END
$$;
