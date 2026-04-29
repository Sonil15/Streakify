# Streakify 🔥

> **Gamified habit tracking for two — with streaks, freezes, accountability, and Telegram reminders.**

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red?style=flat-square)
![Firebase](https://img.shields.io/badge/Firebase-Firestore%20%2B%20Auth-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Auth** | Email/password sign-up & login via Firebase Auth |
| 🌀 **Spheres → Categories → Tasks** | Nested habit hierarchy |
| 🔥 **Streaks** | Tracked per Category; extends when ≥1 task is done daily |
| ❄️ **Freezes** | Earned every 7 consecutive days; auto-protects streaks on missed days |
| 👥 **Accountability** | Link a partner and view their progress in read-only mode |
| 📊 **Heatmaps** | GitHub-style contribution calendar per category |
| 🤖 **Telegram Reminders** | Daily 8 PM IST nudge via GitHub Actions cron |
| 🎨 **Cute UI** | Pastel theme, rounded cards, balloons on completion |

---

## 🗂️ File Structure

```
Streakify/
├── app.py                    # Main Streamlit app
├── auth.py                   # Firebase Auth (pyrebase4)
├── database.py               # Firestore CRUD (firebase-admin)
├── streak_logic.py           # Streak & freeze mechanics
├── styles.py                 # Custom CSS (pastel theme)
├── ui_components.py          # Heatmap, cards, checklists
├── reminder_job.py           # Telegram bot reminder script
├── .github/
│   └── workflows/
│       └── cron.yml          # GitHub Actions daily cron
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Local Setup

### 1. Prerequisites

- Python 3.11+
- A Firebase project (free Spark plan is fine)
- A Telegram Bot (optional, for reminders)

### 2. Clone & install

```bash
git clone https://github.com/your-username/streakify.git
cd streakify
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Firebase setup

#### 3a. Create a Firebase project
1. Go to [Firebase Console](https://console.firebase.google.com/) → **Add project**.
2. Disable Google Analytics (optional) → **Create project**.

#### 3b. Enable Firebase Auth
1. In the console: **Build → Authentication → Get started**.
2. Enable **Email/Password** provider.

#### 3c. Create a Firestore database
1. **Build → Firestore Database → Create database**.
2. Choose **Start in production mode** → select a region close to India (e.g., `asia-south1`).
3. Go to **Rules** tab and paste:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId}/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    // Allow authenticated users to read any user profile (for accountability)
    match /users/{userId} {
      allow read: if request.auth != null;
    }
  }
}
```

#### 3d. Get your Web App credentials
1. **Project Settings (⚙️) → Your apps → Add app → Web (</>)**.
2. Register the app and copy the `firebaseConfig` object values.

#### 3e. Generate a Service Account key
1. **Project Settings → Service accounts → Generate new private key**.
2. Save the downloaded JSON as `serviceAccountKey.json` in the project root.
3. **Add `serviceAccountKey.json` to your `.gitignore`!**

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your actual Firebase values
```

### 5. Run locally

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🤖 Telegram Bot Setup

### Step 1 — Create a bot with BotFather

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot`.
3. Follow the prompts: choose a name (e.g., `Streakify Bot`) and a username (e.g., `@streakify_remind_bot`).
4. BotFather will reply with your **Bot Token** (looks like `7123456789:AAF...`).
5. Add this token to your `.env` as `TELEGRAM_BOT_TOKEN`.

### Step 2 — Find your personal Chat ID

1. Search for **@userinfobot** on Telegram.
2. Start the bot (`/start`).
3. It will immediately reply with your **Chat ID** (a number like `123456789`).
4. Paste this in the **⚙️ Settings** tab of Streakify under "Telegram Chat ID".

### Step 3 — Test the reminder locally

```bash
python reminder_job.py
```

---

## ☁️ Deploying to Streamlit Community Cloud

### Step 1 — Push to GitHub

```bash
git init   # if not already done
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/streakify.git
git push -u origin main
```

> **Important:** Make sure `serviceAccountKey.json` and `.env` are in `.gitignore`.

### Step 2 — Connect to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
2. Connect your GitHub account.
3. Select: Repository → `streakify`, Branch → `main`, Main file → `app.py`.
4. Click **Deploy!**

### Step 3 — Add secrets to Streamlit Cloud

Streamlit Cloud uses a TOML-format secrets manager instead of `.env`.

1. In your deployed app dashboard, click **⋮ → Settings → Secrets**.
2. Paste the following, filling in your real values:

```toml
# Firebase Web App config
[firebase_client]
apiKey            = "AIzaSy..."
authDomain        = "your-project.firebaseapp.com"
databaseURL       = "https://your-project-default-rtdb.firebaseio.com"
projectId         = "your-project"
storageBucket     = "your-project.appspot.com"
messagingSenderId = "1234567890"
appId             = "1:1234567890:web:abcdef"

# Firebase service account (paste the ENTIRE JSON as key = value pairs)
[firebase_service_account]
type                        = "service_account"
project_id                  = "your-project"
private_key_id              = "abc123..."
private_key                 = "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----\n"
client_email                = "firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com"
client_id                   = "1234567890"
auth_uri                    = "https://accounts.google.com/o/oauth2/auth"
token_uri                   = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url        = "https://www.googleapis.com/robot/v1/metadata/x509/..."

# Telegram
TELEGRAM_BOT_TOKEN = "7123456789:AAF..."
```

> **Tip for `private_key`:** Copy the entire key from your `serviceAccountKey.json` and preserve the `\n` line breaks. Streamlit handles the TOML escaping automatically.

3. Click **Save**. Streamlit will restart the app with the new secrets.

---

## ⏰ GitHub Actions Cron (Telegram Reminders)

The `reminder_job.py` script runs automatically via `.github/workflows/cron.yml` every day at **8:00 PM IST (14:30 UTC)**.

### Add GitHub Secrets

Go to your repo on GitHub → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value |
|---|---|
| `FIREBASE_SERVICE_ACCOUNT_JSON` | The entire contents of `serviceAccountKey.json` (paste as-is) |
| `TELEGRAM_BOT_TOKEN` | Your bot token from BotFather |

### Manual trigger

You can trigger the workflow manually from **Actions → Daily Streak Reminder → Run workflow**.

---

## 📐 Streak & Freeze Logic Reference

| Event | Result |
|---|---|
| Complete ≥1 task today | Streak +1, `consecutive_days` +1 |
| 7 consecutive completed days | Earn 1 ❄️ Freeze (auto, on the 7th day) |
| Miss a day (0 tasks), freeze available | 1 Freeze deducted, streak preserved |
| Miss a day (0 tasks), no freezes | Streak resets to 0 |
| Un-check all tasks for today | Streak extension rolled back |
| Freezes are category-specific | A "Health" freeze cannot protect a "Prep" streak |

---

## 🛠️ Local Development Tips

- To reset a user's streak in testing, update the Firestore document directly in the [Firebase Console](https://console.firebase.google.com/).
- The heatmap shows the last 26 weeks (≈6 months) of activity.
- The `reconcile_streak` function runs on every page load, so missed days are always handled — even if the reminder job didn't run.

---

## 🤝 Contributing

Pull requests welcome! Please open an issue first to discuss what you'd like to change.

---

## 📄 License

MIT © 2024
