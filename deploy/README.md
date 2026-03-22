# Health Agent Deploy Notes

This directory contains starter materials for the current Health Agent stack.

Included files:

- `health-agent.env.example` — example environment variables for a private `n8n` deployment
- `n8n-webhook-example.json` — example normalized webhook payload and routing notes

These are templates, not a one-click production deployment.

Before using them:

- review all webhook and Telegram settings
- keep the final `.env` outside git
- prefer private networking or HTTPS
