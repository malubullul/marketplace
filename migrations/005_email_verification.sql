-- Run after 001 and 004. Existing accounts remain unverified until email proof.
CREATE TABLE IF NOT EXISTS anredseller.verified_customer_emails (
  customer_id BIGINT PRIMARY KEY REFERENCES anredseller.customers(id) ON DELETE CASCADE,
  verified_at BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS anredseller.email_verification_tokens (
  token_hash TEXT PRIMARY KEY, email TEXT NOT NULL,
  customer_id BIGINT REFERENCES anredseller.customers(id) ON DELETE CASCADE,
  expires_at BIGINT NOT NULL);
CREATE INDEX IF NOT EXISTS verification_email ON anredseller.email_verification_tokens(email);
CREATE INDEX IF NOT EXISTS verification_expiry ON anredseller.email_verification_tokens(expires_at);
ALTER TABLE anredseller.verified_customer_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE anredseller.email_verification_tokens ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON anredseller.verified_customer_emails, anredseller.email_verification_tokens FROM PUBLIC;
DO $$ BEGIN
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
    REVOKE ALL ON anredseller.verified_customer_emails, anredseller.email_verification_tokens FROM anon;
  END IF;
  IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
    REVOKE ALL ON anredseller.verified_customer_emails, anredseller.email_verification_tokens FROM authenticated;
  END IF;
END $$;
