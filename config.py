import os

# --- Recipients ---
EMAIL_RECIPIENT = "jwlee12236@gmail.com"

# --- Timezone ---
LOCAL_TZ = "America/New_York"

# --- Calendar ---
# How many days ahead to pull for daily / weekly
DAILY_LOOKAHEAD_DAYS = 1
WEEKLY_LOOKAHEAD_DAYS = 7

# --- Gmail ---
# Labels to include when pulling recent threads (None = all)
GMAIL_LABELS = None
# Max threads to surface per email
GMAIL_MAX_THREADS = 10

# --- Claude model ---
CLAUDE_MODEL = "claude-sonnet-4-6"

# --- System prompt injected into every Claude call ---
SYSTEM_PROMPT = """\
You are Josh's personal executive assistant. Josh is a driven, busy person \
who values concise, actionable information. Your job is to synthesize his \
calendar events and email threads into a clean, readable agenda email.

Tone: warm but efficient — no fluff, no filler. Use bullet points and \
short paragraphs. Surface what actually matters. Flag anything that needs \
attention or follow-up. Never hallucinate details that aren't in the data.

Output format:
- Plain text with light markdown (bold for section headers, bullets for lists).
- No HTML.
- Keep the whole email under ~400 words unless the day is genuinely packed.
"""

# --- Google API scopes ---
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# --- Paths ---
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "token.json")
CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "credentials.json")
GOALS_PATH = os.path.join(os.path.dirname(__file__), "goals.md")
