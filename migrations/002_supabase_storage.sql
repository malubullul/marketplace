-- Supabase SQL Editor only. Private product bucket; backend service_role
-- reads/writes objects, and browsers receive images through /uploads/.
INSERT INTO storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
VALUES ('product-photos','product-photos',false,4194304,ARRAY['image/webp'])
ON CONFLICT (id) DO UPDATE SET public=false, file_size_limit=4194304, allowed_mime_types=ARRAY['image/webp'];
-- No public INSERT/UPDATE/DELETE storage policies are required.
