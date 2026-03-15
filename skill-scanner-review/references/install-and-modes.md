# Install And Modes

## Installation

Prefer installing the published package instead of cloning the full repository into a skills folder.

Examples:

```bash
uv pip install cisco-ai-skill-scanner
```

```bash
pip install cisco-ai-skill-scanner
```

Verify:

```bash
skill-scanner --help
```

## Mode Selection

- `basic`
  - Runs a single-skill scan with default analyzers.
  - Use first when you need a quick safety pass.

- `behavioral`
  - Adds dataflow analysis with `--use-behavioral`.
  - Use for Python-heavy skills or when scripts and pipelines look suspicious.

- `deep`
  - Adds `--use-behavioral --use-llm --enable-meta`.
  - Use for high-risk third-party skills when an API-backed semantic pass is acceptable.

- `all`
  - Uses `scan-all --recursive`.
  - Use for scanning a folder of skills, such as a repo-level `skills/` tree.

- `sarif`
  - Uses `scan-all --recursive --format sarif`.
  - Use for GitHub Code Scanning or CI artifacts.

## Coverage Caveats

- No findings do not prove the skill is safe.
- LLM, VirusTotal, and cloud analyzers require credentials and add external dependencies.
- Prefer the lowest-complexity mode that answers the user request.
