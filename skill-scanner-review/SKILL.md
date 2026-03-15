---
name: skill-scanner-review
license: Apache-2.0
description: Use when reviewing Codex, Cursor, or agent skill directories for prompt injection, data exfiltration, suspicious scripts, unsafe pipelines, or CI-ready security scanning. This skill wraps the external `skill-scanner` CLI with a conservative workflow and translates findings into actionable review notes.
---

# Skill Scanner Review

Use this skill when the task is to scan a skill directory or a repository full of skills, not when the task is to install or develop the scanner itself.

This skill provides:
- A safe default scan flow for one skill or many skills
- A small wrapper script so commands are reproducible
- Guidance for deciding when to use `--use-behavioral`, `--use-llm`, `--enable-meta`, and CI-oriented outputs
- A review rubric for separating real threats from likely false positives

## When To Use It

Trigger this skill when the user asks to:
- scan a Codex skill, Cursor skill, or directory of skills
- check for prompt injection, exfiltration, malware, or suspicious command behavior
- review a third-party skill before installation
- produce JSON, Markdown, SARIF, or HTML scan output
- wire skill scanning into pre-commit or GitHub Actions

Do not use this skill when:
- the task is generic repository security review unrelated to skill formats
- the repository is a normal application and not a skill package
- the user needs exploit analysis beyond scanner coverage; do manual review too

## Workflow

1. Confirm the target path:
   - one skill directory: use `scan`
   - many skills under one root: use `scan-all`

2. Start conservative:
   - run the wrapper script in `basic` mode first
   - only add LLM or cloud-backed analyzers if the user wants deeper coverage and accepts the extra dependencies/API use

3. Escalate based on need:
   - add `behavioral` for Python-heavy skills or command/dataflow concerns
   - add `deep` for semantic checks and false-positive filtering
   - use `sarif` or `html` only when the result needs to be published or shared

4. Review findings manually:
   - prioritize `critical` and `high`
   - inspect the exact file and line context
   - treat “no findings” as “no known detections,” not as proof of safety

5. Report clearly:
   - summarize by severity
   - call out likely real threats
   - note likely false positives
   - list residual gaps such as missing LLM/VirusTotal coverage or unsupported file types

## Quick Commands

Use the wrapper in `scripts/run-skill-scanner.sh`.

Examples:

```bash
# Scan one skill with static defaults
./scripts/run-skill-scanner.sh basic /path/to/skill

# Scan one skill with dataflow analysis
./scripts/run-skill-scanner.sh behavioral /path/to/skill

# Scan one skill with LLM + meta analyzer
./scripts/run-skill-scanner.sh deep /path/to/skill

# Scan a skills directory recursively
./scripts/run-skill-scanner.sh all /path/to/skills

# Emit SARIF for GitHub code scanning
./scripts/run-skill-scanner.sh sarif /path/to/skills results.sarif
```

If `skill-scanner` is not installed, read [`references/install-and-modes.md`](references/install-and-modes.md) and install it first.

## Review Rules

- Treat changes under `.github/workflows/`, `scripts/`, `agents/`, and `SKILL.md` as higher risk than cosmetic files.
- Flag commands that download remote content and execute it, write secrets, disable checks, or hide shell behavior.
- Pay attention to prompt instructions that push the model to exfiltrate context, bypass policy, or expand scope silently.
- For third-party skills, prefer scanning before installation and then doing spot manual review of any `high` or `critical` findings.

## References

- Installation, CLI modes, and output choices: [`references/install-and-modes.md`](references/install-and-modes.md)
- How to triage findings and write up results: [`references/review-playbook.md`](references/review-playbook.md)
