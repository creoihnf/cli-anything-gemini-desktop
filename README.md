# CLI-Anything: Gemini Desktop

Agent-native Command Line Interface (CLI) harness for Google Gemini Desktop on Windows.

## Overview
- **0 IDE Tokens:** Delegates reasoning and architectural tasks to the official Gemini Desktop app.
- **Stealth & Clean UX:** Runs off-screen and restores clipboard and window focus.
- **Deep Research:** Selects Gemini's research tool and submits a request for a research plan.
- **Optional Task Queue:** Exports structured task items to a directory you configure.
- **Supported Commands:** `ask`, `deep-research`, `delegate`, `bridge`, `status`, `launch`, `shortcut`, `send`, `settings`, `session`, `repl`.

## Installation
```bash
cd agent-harness
pip install -e .
```

## Quick Start
```bash
# Check status
cli-anything-gemini-desktop status --json

# Direct prompt
cli-anything-gemini-desktop ask "Qual a melhor abordagem para este componente?"

# Request Deep Research
cli-anything-gemini-desktop deep-research "Compare ferramentas de automacao para pequenas empresas"

# Task delegation
cli-anything-gemini-desktop delegate "Refatorar pipeline de video"
```

## Deep Research

Open Gemini Desktop and sign in to an account with Deep Research available.
The command selects **Tools > Deep Research**, confirms that the mode is selected,
and submits your prompt. It fails without sending a regular chat message if the
tool cannot be selected through Windows accessibility APIs. English and Portuguese
tool labels are supported; other interface languages may not be recognized.

Review the plan in Gemini and click **Start research** when ready. The command
requests a plan; it does not automatically approve it, wait for the final report,
or claim that research is complete. Gemini remains visible by default for review.

```powershell
# Prepare a draft without submitting it
cli-anything-gemini-desktop deep-research "Pesquise este mercado" --no-submit

# Structured result for automation
cli-anything-gemini-desktop deep-research "Compare as alternativas" --json
```

## Optional Task Queue

To save delegated orders, set `GEMINI_DESKTOP_QUEUE_DIR` to an existing directory:

```powershell
$env:GEMINI_DESKTOP_QUEUE_DIR = 'C:\tasks\queue'
```

Without this setting, `delegate` prints Gemini's response without saving orders.
Any external worker that executes these files must be configured separately.
