# josh-agenda-automation

Automated daily (Mon–Fri 7 am ET) and weekly (Sunday 8 pm ET) agenda emails pulled from Google Calendar + Gmail, synthesised by Claude, sent via Gmail.

---

## Files

| File | Purpose |
|---|---|
| `config.py` | Constants, Claude system prompt, email recipient |
| `google_auth.py` | OAuth credential loading (local + GitHub Actions) |
| `daily_agenda.py` | Today's events + inbox → Claude → email |
| `weekly_agenda.py` | Week-ahead events + inbox → Claude → email |
| `.github/workflows/daily.yml` | Cron: Mon–Fri 7 am ET |
| `.github/workflows/weekly.yml` | Cron: Sunday 8 pm ET |

---

## One-time setup

### 1. Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a new project.
2. Enable **Google Calendar API** and **Gmail API**.
3. OAuth consent screen → External → add your Gmail address as a test user.
4. Credentials → Create OAuth client ID → Desktop app → download `credentials.json`.
5. Place `credentials.json` in the repo root (it is gitignored).

### 2. Get a token locally

```bash
pip install -r requirements.txt
python google_auth.py   # or run either script — it will open the browser
```

This writes `token.json`. Authorise all requested scopes (Calendar read, Gmail read, Gmail send).

### 3. Base64-encode the token for GitHub Actions

```bash
base64 -i token.json | tr -d '\n' | pbcopy   # macOS — copies to clipboard
```

### 4. Add GitHub Actions secrets

In your repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `TOKEN_JSON_B64` | Base64 string from step 3 |

> **Token expiry:** Google OAuth refresh tokens don't expire unless revoked or unused for 6 months. If you ever get auth errors, re-run step 2–3 and update the secret.

### 5. Push to GitHub

```bash
git init
git add .
git commit -m "initial commit"
gh repo create josh-agenda-automation --private --push --source .
```

GitHub Actions will pick up the cron schedules automatically.

---

## Running locally

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python daily_agenda.py
python weekly_agenda.py
```

`token.json` must exist (see setup step 2).

---

## Customising

- **Recipient:** `EMAIL_RECIPIENT` in `config.py`
- **Tone / format:** `SYSTEM_PROMPT` in `config.py`
- **Schedule:** edit the `cron:` lines in `.github/workflows/*.yml`
- **Number of inbox threads surfaced:** `GMAIL_MAX_THREADS` in `config.py`

---

## Gitignore reminder

Add to `.gitignore`:

```
credentials.json
token.json
__pycache__/
*.pyc
.env
```
