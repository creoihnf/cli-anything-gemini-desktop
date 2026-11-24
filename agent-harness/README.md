# CLI-Anything: Gemini Desktop Agent Harness

Agent-native Command Line Interface (CLI) harness for Google Gemini Desktop on Windows, adhering to HKUDS/CLI-Anything standards.

## Usage

```bash
# Check status
cli-anything-gemini-desktop status
cli-anything-gemini-desktop status --json

# Launch or bring to front
cli-anything-gemini-desktop launch

# Send shortcut (Alt+Space or Alt+Shift+D)
cli-anything-gemini-desktop shortcut

# Send prompt
cli-anything-gemini-desktop send "Analise o arquivo X" --submit

# Request a Deep Research plan (review and start research in Gemini)
cli-anything-gemini-desktop deep-research "Compare opcoes de energia solar" --json

# Read or update settings
cli-anything-gemini-desktop settings --list
cli-anything-gemini-desktop settings --get shortcut
cli-anything-gemini-desktop settings --set minichatEnabled true

# Inspect session and cache stats
cli-anything-gemini-desktop session

# Interactive REPL shell
cli-anything-gemini-desktop repl
```

`deep-research` selects the actual Gemini tool before submitting. If the tool is
unavailable or cannot be confirmed through Windows accessibility APIs, it exits
with an error without sending a regular prompt. Review the plan and start research
in Gemini; the CLI does not collect the final report. Use `--no-submit` for a draft.

Delegated orders are saved only when `GEMINI_DESKTOP_QUEUE_DIR` points to an
existing directory. Without it, `delegate` returns the response without saving tasks.
