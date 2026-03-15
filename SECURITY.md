# Security Policy

## Reporting a Vulnerability

If you discover a security issue, please do not open a public issue with sensitive details.

Instead, share a private report with:

- a description of the issue
- affected component
- reproduction steps
- impact assessment if known

## Sensitive Data

This project may interact with:

- personal health data
- webhook endpoints
- Telegram credentials
- Apple signing material

Please never publish:

- health samples
- tokens
- credentials
- provisioning profiles
- private certificates

## Hardening Guidance

- keep webhook endpoints private when possible
- rotate exposed tokens immediately
- avoid committing `.env` secrets
- prefer local infrastructure over third-party forwarding services
