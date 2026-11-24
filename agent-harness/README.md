# CLI-Anything: Gemini Desktop Agent Harness

Agent-native Command Line Interface (CLI) harness for Google Gemini Desktop on Windows, adhering to HKUDS/CLI-Anything standards and LLM-OS 3-Camadas governance.

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

# Read or update settings
cli-anything-gemini-desktop settings --list
cli-anything-gemini-desktop settings --get shortcut
cli-anything-gemini-desktop settings --set minichatEnabled true

# Inspect session and cache stats
cli-anything-gemini-desktop session

# Interactive REPL shell
cli-anything-gemini-desktop repl
```
