-- Safe to rerun. Run after 001_supabase.sql in the Supabase SQL Editor.
CREATE TABLE IF NOT EXISTS anredseller.order_items (
    order_id TEXT NOT NULL REFERENCES anredseller.orders(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL, quantity BIGINT NOT NULL CHECK(quantity>0),
    PRIMARY KEY(order_id,product_id));
CREATE INDEX IF NOT EXISTS order_items_product ON anredseller.order_items(product_id,order_id);
-- Backfill previous orders; quantities across size/color variants count together.
INSERT INTO anredseller.order_items(order_id,product_id,quantity)
SELECT o.id,(item->>'id')::bigint,SUM((item->>'jumlah')::bigint)
FROM anredseller.orders o CROSS JOIN LATERAL jsonb_array_elements(COALESCE(o.document::jsonb->'items','[]'::jsonb)) item
GROUP BY o.id,(item->>'id')::bigint
ON CONFLICT(order_id,product_id) DO NOTHING;
CREATE TABLE IF NOT EXISTS anredseller.product_reviews (
    customer_id BIGINT NOT NULL REFERENCES anredseller.customers(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES anredseller.products(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL CHECK(length(comment)<=1000),
    created_at BIGINT NOT NULL, updated_at BIGINT NOT NULL,
    PRIMARY KEY(customer_id,product_id));
CREATE INDEX IF NOT EXISTS product_reviews_latest ON anredseller.product_reviews(product_id,created_at,customer_id);
CREATE TABLE IF NOT EXISTS anredseller.password_resets (
    token_hash TEXT PRIMARY KEY,
    customer_id BIGINT REFERENCES anredseller.customers(id) ON DELETE CASCADE,
    expires_at BIGINT NOT NULL);
CREATE INDEX IF NOT EXISTS password_resets_customer ON anredseller.password_resets(customer_id);
CREATE INDEX IF NOT EXISTS password_resets_expiry ON anredseller.password_resets(expires_at);
ALTER TABLE anredseller.order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE anredseller.product_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE anredseller.password_resets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON anredseller.order_items, anredseller.product_reviews, anredseller.password_resets FROM PUBLIC;
-- Some Supabase projects set default grants to these Data API roles.
DO $$ BEGIN
    IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon') THEN
        REVOKE ALL ON anredseller.order_items, anredseller.product_reviews, anredseller.password_resets FROM anon;
    END IF;
    IF EXISTS(SELECT 1 FROM pg_roles WHERE rolname='authenticated') THEN
        REVOKE ALL ON anredseller.order_items, anredseller.product_reviews, anredseller.password_resets FROM authenticated;
    END IF;
END $$;
