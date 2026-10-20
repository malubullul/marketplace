-- Existing stores: run this in Supabase SQL Editor before enabling Google.
-- Private application tables; never expose these through the Data API.
BEGIN;
SET LOCAL search_path TO anredseller, pg_catalog;
CREATE TABLE IF NOT EXISTS customer_google_identities (
  subject TEXT PRIMARY KEY,
  customer_id BIGINT UNIQUE NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
  created_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS customer_oauth_flows (
  state_hash TEXT PRIMARY KEY,
  browser_hash TEXT NOT NULL,
  document TEXT NOT NULL,
  expires_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS customer_oauth_expiry ON customer_oauth_flows(expires_at);
ALTER TABLE customer_google_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE customer_oauth_flows ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON customer_google_identities, customer_oauth_flows FROM PUBLIC;
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
    REVOKE ALL ON customer_google_identities, customer_oauth_flows FROM anon;
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
    REVOKE ALL ON customer_google_identities, customer_oauth_flows FROM authenticated;
  END IF;
END $$;
COMMIT;
