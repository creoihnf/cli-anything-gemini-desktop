# Gemini Desktop Harness Documentation

## Architecture
- **CLI Framework:** Click 8.x
- **Target OS:** Windows 10/11 x64
- **Backend:** Process and window management via Win32 APIs and PowerShell helpers
- **Settings Store:** `%APPDATA%\Gemini\settings.json`
- **Binary Path:** Dynamically resolved from `%LOCALAPPDATA%\Google\Gemini\app-*\Gemini.exe`
- **Output:** Human-readable or structured JSON (`--json`)
