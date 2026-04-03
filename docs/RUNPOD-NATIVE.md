# RunPod: הרצה בלי Docker (חובה בתבניות PyTorch / קונטיינר ללא הרשאות)

## אוטומציה (מומלץ)

מסמך עברית + סקריפטים:

- **[RUNPOD-ONE-PAGE-HE.md](./RUNPOD-ONE-PAGE-HE.md)** — צ’ק־ליסט קצר
- `scripts/runpod-bootstrap.sh` — התקנת חבילות, `git clone`/`pull`, `pip`, יצירת `.env`, תיקון `REDIS_URL` ל־localhost
- `scripts/runpod-start.sh` — Redis + API + Worker ברקע (`nohup`)
- `scripts/runpod-stop.sh` / `scripts/runpod-status.sh`

## למה Docker נכשל

בלוג של `dockerd` מופיעים בדרך כלל:

- `failed to mount overlay: operation not permitted`
- `iptables ... Permission denied`

הפוד של RunPod רץ **בתוך קונטיינר** ללא הרשאות מלאות לרשת/מערכת קבצים — **Docker-in-Docker לא נתמך** שם. אל תנסה להתקין `docker.io` שוב על אותה תבנית.

## מה כן עושים: Redis + Uvicorn + Celery (מקומי)

הנחה: Ubuntu 22.04, משתמש `root`, הפרויקט ב־`/root/kadmoo-video-service` (אם הנתיב אחר — החלף).

### 1. חבילות

```bash
apt-get update
apt-get install -y redis-server ffmpeg curl python3-pip
```

### 2. קוד ו-.env

```bash
cd ~
git clone https://github.com/topamcc/kadmoo-video-service.git 2>/dev/null || (cd kadmoo-video-service && git pull)
cd ~/kadmoo-video-service
pip3 install -r requirements.txt
cp -n .env.example .env
nano .env
```

ב־`.env` חובה:

- `REDIS_URL=redis://127.0.0.1:6379/0`
- `API_KEY`, `WEBHOOK_HMAC_SECRET`, `SUPABASE_*`, `ELEVENLABS_*`, וכו'

### 3. Redis

```bash
redis-server --daemonize yes
redis-cli ping
```

צריך `PONG`.

### 4. שני תהליכים (שני חלונות טרמינל ב-RunPod)

**חלון A — Worker:**

```bash
cd ~/kadmoo-video-service
export PYTHONPATH="$HOME/kadmoo-video-service/src"
set -a && . ./.env && set +a
celery -A worker.celery_app worker -l info -c 1 -Q video-jobs
```

**חלון B — API:**

```bash
cd ~/kadmoo-video-service
export PYTHONPATH="$HOME/kadmoo-video-service/src"
set -a && . ./.env && set +a
uvicorn main:app --host 0.0.0.0 --port 4100 --app-dir "$HOME/kadmoo-video-service/src"
```

### 5. בדיקה

```bash
curl -s http://127.0.0.1:4100/health
```

### 6. Vercel

הוסף ב-RunPod **HTTP לפורט 4100**, העתק את ה-URL ל־`VIDEO_SERVICE_URL`.

---

## אופציה עתידית: פוד עם Docker אמיתי

תבנית RunPod שמספקת **privileged** / **Docker מובנה** / גישה ל־`/var/run/docker.sock` של המארח — רק אז `docker compose` הגיוני. על תבנית PyTorch רגילה — השתמש במדריך הזה.
