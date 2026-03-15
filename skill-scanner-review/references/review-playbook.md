# Review Playbook

## High-Signal Findings

Treat these as likely important until disproven:

- instructions to reveal system prompts, secrets, or prior conversation state
- shell commands that fetch remote content and execute it immediately
- hidden or obfuscated shell fragments
- CI workflow changes that broaden permissions or write security events unexpectedly
- scripts that read sensitive files and send them over the network
- prompt text that asks the model to ignore policy or change role silently

## Likely False Positives

These still need a look, but are often benign:

- package-manager install commands in setup docs
- examples that mention environment variables without hardcoded secrets
- simple shell pipelines used for formatting or filtering local files
- test fixtures that intentionally contain suspicious strings

## Reporting Format

When reporting results back to the user:

1. State the scan mode used.
2. Summarize count and highest severity.
3. List confirmed or likely-real findings first.
4. List probable false positives separately.
5. Note residual risks:
   - scanner coverage limits
   - analyzers not enabled
   - files not manually reviewed
