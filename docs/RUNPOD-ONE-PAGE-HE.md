# RunPod — דף אחד: הפעלה אוטומטית ככל האפשר

מטרה: אחרי איפוס פוד או קונטיינר חדש, להריץ פקודות מינימליות. הקוד וה־volume ב־`/workspace` נשמרים בין אתחולים (אם הגדרת volume ל־`/workspace`).

## מה **לא** אוטומטי

עדיין צריך **לערוך ידנית** את `.env` עם סודות אמיתיים (Supabase, ElevenLabs, `API_KEY`, `WEBHOOK_HMAC_SECRET`). בלי זה `runpod-start.sh` ייעצר עם הודעת שגיאה.

ב־**RunPod → Edit Pod**: חשוף **HTTP** גם ל־**4100** (בנוסף ל־8888 אם צריך Jupyter).

ב־**Vercel**: `VIDEO_SERVICE_URL`, `VIDEO_SERVICE_API_KEY`, `VIDEO_SERVICE_WEBHOOK_SECRET`, `USE_EXTERNAL_VIDEO=true`, `NEXT_PUBLIC_APP_URL`.

---

## פקודות (העתקה ל-Web terminal)

### פעם אחת אחרי פוד חדש / מערכת ריקה

```bash
cd /workspace
curl -fsSL -o /tmp/bootstrap.sh https://raw.githubusercontent.com/topamcc/kadmoo-video-service/main/scripts/runpod-bootstrap.sh \
  && bash /tmp/bootstrap.sh
```

אם אין רשת ל־raw GitHub או העתקה נכשלת — אחרי `git clone` ידני לתיקייה:

```bash
cd /workspace/kadmoo-video-service
bash ./scripts/runpod-bootstrap.sh
```

### עריכת סודות

```bash
nano /workspace/kadmoo-video-service/.env
```

### הפעלה (API + Worker ברקע)

```bash
cd /workspace/kadmoo-video-service
bash ./scripts/runpod-start.sh
```

### עצירה

```bash
cd /workspace/kadmoo-video-service
bash ./scripts/runpod-stop.sh
```

### סטטוס

```bash
cd /workspace/kadmoo-video-service
bash ./scripts/runpod-status.sh
```

---

## קבצים ולוגים

| קובץ | תיאור |
|------|--------|
| `/tmp/kadmoo-runpod-api.pid` | PID של uvicorn |
| `/tmp/kadmoo-runpod-worker.pid` | PID של Celery |
| `/tmp/kadmoo-video-api.log` | לוג API |
| `/tmp/kadmoo-video-worker.log` | לוג worker |

---

## משתני סביבה אופציונליים ל־bootstrap

| משתנה | ברירת מחדל |
|--------|------------|
| `KADMOO_WORKSPACE_PARENT` | `/workspace` |
| `KADMOO_REPO_DIR` | `kadmoo-video-service` |
| `KADMOO_VIDEO_SERVICE_GIT_URL` | `https://github.com/topamcc/kadmoo-video-service.git` |

---

## LTX אמיתי (GPU)

אחרי ש־stub עובד מקצה לקצה: [LTX2-INSTALL-RUNPOD.md](./LTX2-INSTALL-RUNPOD.md).

---

## מסמך מורחב

- [RUNPOD-NATIVE.md](./RUNPOD-NATIVE.md) — הסבר למה בלי Docker
- [DEPLOY-RUNPOD.md](./DEPLOY-RUNPOD.md) — צ’ק־ליסט כללי + Vercel
