# CLI-Anything: Gemini Desktop

Agent-native Command Line Interface (CLI) harness for Google Gemini Desktop on Windows.

## Overview
- **0 IDE Tokens:** Delegates reasoning and architectural tasks to the official Gemini Desktop app.
- **Stealth & Clean UX:** Runs off-screen and restores clipboard and window focus.
- **LLM-OS Integration:** Directly creates structured task items in `00-Sistema/fila/`.
- **Supported Commands:** `ask`, `delegate`, `status`, `launch`, `shortcut`, `send`, `settings`, `session`, `repl`.

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

# Task delegation
cli-anything-gemini-desktop delegate "Refatorar pipeline de video"
```
