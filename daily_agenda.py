"""
Daily agenda — runs every weekday at 7 am ET via GitHub Actions.
Pulls today's calendar events + recent email threads, asks Claude to
synthesise them, then sends the result to EMAIL_RECIPIENT.
"""

import base64
import datetime
import email.mime.text
import os

import anthropic
import pytz
from googleapiclient.errors import HttpError

from config import (
    CLAUDE_MODEL,
    DAILY_LOOKAHEAD_DAYS,
    EMAIL_RECIPIENT,
    GMAIL_MAX_THREADS,
    GOALS_PATH,
    LOCAL_TZ,
    SYSTEM_PROMPT,
)
from google_auth import get_calendar_service, get_gmail_service


# ---------------------------------------------------------------------------
# Calendar helpers
# ---------------------------------------------------------------------------

def fetch_todays_events(service) -> list[dict]:
    tz = pytz.timezone(LOCAL_TZ)
    now = datetime.datetime.now(tz)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + datetime.timedelta(days=DAILY_LOOKAHEAD_DAYS)

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=start_of_day.isoformat(),
            timeMax=end_of_day.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return result.get("items", [])


def format_events(events: list[dict]) -> str:
    if not events:
        return "No events on the calendar today."

    lines = []
    tz = pytz.timezone(LOCAL_TZ)
    for e in events:
        start = e.get("start", {})
        if "dateTime" in start:
            dt = datetime.datetime.fromisoformat(start["dateTime"]).astimezone(tz)
            time_str = dt.strftime("%-I:%M %p")
        else:
            time_str = "All day"

        summary = e.get("summary", "(no title)")
        location = e.get("location", "")
        desc = e.get("description", "")

        line = f"- {time_str}: {summary}"
        if location:
            line += f" @ {location}"
        if desc:
            line += f"\n  {desc[:200]}"
        lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gmail helpers
# ---------------------------------------------------------------------------

def fetch_recent_threads(service) -> list[dict]:
    result = (
        service.users()
        .threads()
        .list(userId="me", maxResults=GMAIL_MAX_THREADS, labelIds=["INBOX"])
        .execute()
    )
    threads = result.get("threads", [])
    detailed = []
    for t in threads:
        thread = (
            service.users()
            .threads()
            .get(userId="me", id=t["id"], format="metadata",
                 metadataHeaders=["Subject", "From", "Date"])
            .execute()
        )
        detailed.append(thread)
    return detailed


def format_threads(threads: list[dict]) -> str:
    if not threads:
        return "No recent email threads."

    lines = []
    for t in threads:
        messages = t.get("messages", [])
        if not messages:
            continue
        headers = {h["name"]: h["value"] for h in messages[0].get("payload", {}).get("headers", [])}
        subject = headers.get("Subject", "(no subject)")
        sender = headers.get("From", "unknown")
        msg_count = len(messages)
        lines.append(f"- [{msg_count} msg{'s' if msg_count != 1 else ''}] {subject} — from {sender}")

    return "\n".join(lines) if lines else "No recent email threads."


# ---------------------------------------------------------------------------
# Goals loader
# ---------------------------------------------------------------------------

def load_goals() -> str:
    try:
        with open(GOALS_PATH, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


# ---------------------------------------------------------------------------
# Claude
# ---------------------------------------------------------------------------

def generate_agenda(events_text: str, threads_text: str, date_str: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=60.0)

    goals_text = load_goals()
    goals_section = f"\n=== JOSH'S GOALS & LEARNING CONTEXT ===\n{goals_text}\n" if goals_text else ""

    user_message = f"""\
Today is {date_str}.

=== CALENDAR EVENTS ===
{events_text}

=== RECENT EMAIL THREADS ===
{threads_text}
{goals_section}
Please write Josh's daily agenda email. Use this structure:

**DAY SUMMARY**
One sentence on the overall feel of today.

**CALENDAR**
Today's events. Flag if any conflict with the scheduled morning learning block for this day of the week.

**INBOX**
Email threads needing attention or follow-up today.

**TODAY'S LEARNING BLOCK**
Based on the day of the week and Josh's goals context, state which pillar is scheduled and suggest one specific task or topic for the session. If it's a "build" day, name a concrete output. Keep this to 2–3 lines.

**TODAY'S FOCUS**
One sharp sentence — the single most important thing to accomplish today given the calendar, inbox, job search, and learning goals.
"""

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# Gmail send
# ---------------------------------------------------------------------------

def send_email(service, subject: str, body: str) -> None:
    msg = email.mime.text.MIMEText(body, "plain")
    msg["To"] = EMAIL_RECIPIENT
    msg["From"] = "me"
    msg["Subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tz = pytz.timezone(LOCAL_TZ)
    today = datetime.datetime.now(tz)
    date_str = today.strftime("%A, %B %-d, %Y")

    cal_service = get_calendar_service()
    gmail_service = get_gmail_service()

    events = fetch_todays_events(cal_service)
    threads = fetch_recent_threads(gmail_service)

    events_text = format_events(events)
    threads_text = format_threads(threads)

    body = generate_agenda(events_text, threads_text, date_str)

    subject = f"Daily Agenda — {date_str}"
    send_email(gmail_service, subject, body)
    print(f"Sent: {subject}")


if __name__ == "__main__":
    main()
