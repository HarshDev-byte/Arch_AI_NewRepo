-- ============================================================
-- ArchAI — Supabase Storage Bucket
-- 002_storage_bucket.sql
-- Run in Supabase SQL editor (requires storage extension)
-- ============================================================

-- Create the archai-models bucket for .glb / .fbx / thumbnail files
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'archai-models',
  'archai-models',
  true,                    -- public read (signed URLs used for writes)
  524288000,               -- 500 MB max file size
  ARRAY[
    'model/gltf-binary',   -- .glb
    'model/gltf+json',     -- .gltf
    'application/octet-stream',
    'image/png',
    'image/jpeg',
    'image/webp'
  ]
)
ON CONFLICT (id) DO NOTHING;

-- Allow authenticated users to upload to their own project folder
CREATE POLICY "auth_upload_models" ON storage.objects
  FOR INSERT TO authenticated
  WITH CHECK (bucket_id = 'archai-models');

-- Allow public read of all models
CREATE POLICY "public_read_models" ON storage.objects
  FOR SELECT TO public
  USING (bucket_id = 'archai-models');

-- Allow users to delete their own files
CREATE POLICY "auth_delete_own_models" ON storage.objects
  FOR DELETE TO authenticated
  USING (bucket_id = 'archai-models' AND auth.uid()::text = (storage.foldername(name))[1]);
