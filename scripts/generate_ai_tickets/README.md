# Generate AI Tickets

Quick scripts to create tickets in HubSpot and Jira from AI-generated JSON (ai_generated_issues_*.json).

## HubSpot
- OAuth helper: scripts/hubspot_oauth.py
- Run: python3 scripts/generate_ai_tickets/create_hubspot_tickets.py

## Jira
- OAuth helper: scripts/jira_oauth.py
- Optional env: JIRA_PROJECT_KEY=YOURKEY
- Run: python3 scripts/generate_ai_tickets/create_jira_issues.py
