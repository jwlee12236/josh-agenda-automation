## THIS PROJECT
Building an automated daily + weekly agenda email system that:
- Pulls Google Calendar via Google Calendar API
- Pulls Gmail threads via Gmail API  
- Generates personalized agenda emails via Anthropic API (claude-sonnet-4-6)
- Sends emails automatically via Gmail API
- Runs on a schedule via GitHub Actions (daily 7am ET, weekly Sunday 8pm ET)

## STACK
- Python 3.11+
- google-auth, google-api-python-client (Calendar + Gmail)
- anthropic (Claude API)
- GitHub Actions for scheduling

## CREDENTIALS NEEDED
- ANTHROPIC_API_KEY
- Google OAuth credentials (Calendar + Gmail scopes)
- All stored as GitHub Actions secrets — never hardcoded