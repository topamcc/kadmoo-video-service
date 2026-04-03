# End-to-end checklist (720p fast path)

1. Apply Supabase migration `20260403200000_video_jobs.sql` (includes Realtime publication).
2. Set **Next.js** env: `VIDEO_SERVICE_*`, `USE_EXTERNAL_VIDEO=true`, `NEXT_PUBLIC_APP_URL` (webhook must reach Vercel / tunnel).
3. Set **video service** `.env`: `API_KEY`, `REDIS_URL`, `WEBHOOK_HMAC_SECRET`, `SUPABASE_*`, `ELEVENLABS_API_KEY`, `ELEVENLABS_DEFAULT_VOICE_ID` (or provide `voice_sample_url` from app later), `LTX_STUB_MODE=true`.
4. `docker compose up --build` (API + worker + Redis).
5. Studio → SMB wizard: generate a video. Expect: `video_jobs` row → worker → Supabase upload → webhook → `studio_assets` row → UI shows result.

Scale to 1080p/4K: set `resolution` in `createExternalVideoJob` (adapter) and disable stub mode when LTX-2 is wired.
