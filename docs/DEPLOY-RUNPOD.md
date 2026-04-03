# פריסה על RunPod (או שרת GPU אחר) — צ’ק־ליסט

מסמך זה מפריד בין מה שאתה עושה ב-UI / בטרמינל שלך, לבין מה שהקוד כבר תומך בו.

---

## חלק א’ — רק אתה (לא אוטומטי)

### A1. חשב RunPod

- [ ] פוד רץ עם לינוקס ו-Docker (או התקנת Docker ידנית).
- [ ] **HTTP Service על פורט 4100** — חובה. בלי זה Vercel לא יגיע ל-`VIDEO_SERVICE_URL`.
- [ ] **אל תחשוף פורט 6379 (Redis) לעולם** — ב-`docker-compose` שלנו Redis כבר לא ממופה החוצה (רק רשת פנימית).

### A2. מפתחות וסודות

צור והעתק (שמור במקום בטוח):

| שם בשרת הווידאו (`.env`) | שם ב-Vercel / `.env.local` |
|--------------------------|----------------------------|
| `API_KEY` | `VIDEO_SERVICE_API_KEY` (אותו ערך) |
| `WEBHOOK_HMAC_SECRET` | `VIDEO_SERVICE_WEBHOOK_SECRET` (אותו ערך) |

- [ ] `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` (מ-Supabase → Settings → API)
- [ ] `ELEVENLABS_API_KEY`
- [ ] `ELEVENLABS_DEFAULT_VOICE_ID` — **חובה** אם אין דגימת קול מהאפליקציה (מצב נוכחי)

### A3. אפליקציית Next (Vercel)

הוסף משתני סביבה:

```env
VIDEO_SERVICE_URL=https://<מה-ש-RunPod-נותן-לפורט-4100>
VIDEO_SERVICE_API_KEY=<אותו-API_KEY>
VIDEO_SERVICE_WEBHOOK_SECRET=<אותו-WEBHOOK_HMAC_SECRET>
USE_EXTERNAL_VIDEO=true
NEXT_PUBLIC_APP_URL=https://<הדומיין-הציבורי-של-האפליקציה>
```

- [ ] `NEXT_PUBLIC_APP_URL` חייב להיות **כתובת ציבורית HTTPS** של האפליקציה — כי השרת שולח webhook ל־`/api/webhooks/video`.

### A4. Git על השרת

```bash
git clone https://github.com/topamcc/kadmoo-video-service.git
cd kadmoo-video-service
cp .env.example .env
nano .env   # או עורך אחר — מלא את כל הערכים
```

---

## חלק ב’ — פקודות על הפוד (אחרי `.env` מלא)

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f video-api --tail 50
docker compose logs -f video-worker --tail 50
```

### בדיקות “הכל תקין”

1. **בריאות API (בלי מפתח):** מהדפדפן או מהפוד:
   ```bash
   curl -s http://127.0.0.1:4100/health
   ```
   צפוי JSON עם `status`, `redis`, `queue_depth`.

2. **מפתח תקין:** (החלף `YOUR_KEY`):
   ```bash
   curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: YOUR_KEY" http://127.0.0.1:4100/jobs/fake/status
   ```
   צפוי `404` (לא 401) — כי אין job, אבל האימות עבר.

3. **מבחוץ (RunPod public URL ל-4100):** אותו `/health` בדפדפן.

---

## חלק ג’ — בדיקה מקצה לקצה עם Kadmoo Studio

- [ ] ב-Supabase יש טבלה `video_jobs` (הרצת מיגרציה כבר בוצעה אצלך).
- [ ] בסטודיו → אשף SMB → יצירה: אמורה להופיע שורה ב-`video_jobs`, התקדמות, ואז סרטון בסיום.
- [ ] אם נתקע ב-`failed` — קרא `error_message` בטבלה ו-`docker compose logs video-worker`.

---

## תקלות נפוצות

| תסמין | כיוון בדיקה |
|--------|-------------|
| `NO_CALLBACK` / שגיאה על webhook | `NEXT_PUBLIC_APP_URL` חסר או לא ציבורי ב-Vercel |
| 401 מול השירות | `API_KEY` ≠ `VIDEO_SERVICE_API_KEY` |
| Webhook נדחה (403) | `WEBHOOK_HMAC_SECRET` ≠ `VIDEO_SERVICE_WEBHOOK_SECRET` |
| ElevenLabs / TTS | `ELEVENLABS_API_KEY` + `ELEVENLABS_DEFAULT_VOICE_ID` |
| העלאה ל-Supabase נכשלת | `SUPABASE_SERVICE_ROLE_KEY` + bucket `studio-assets` קיים |

---

## LTX אמיתי (אחרי ש-stub עובד)

- הגדר `LTX_STUB_MODE=false`, משקלי מודל, והרחב את `pipelines/video_render.py`.
- אימג’ Docker הנוכחי הוא **CPU-friendly** ל-stub; ל-GPU אמיתי תצטרך בסיס `nvidia/cuda` + NVIDIA Container Toolkit על הפוד.
