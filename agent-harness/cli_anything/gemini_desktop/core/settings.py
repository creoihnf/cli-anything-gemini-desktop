import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional


def get_settings_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Gemini" / "settings.json"
    return Path.home() / "AppData" / "Roaming" / "Gemini" / "settings.json"


def load_settings() -> Dict[str, Any]:
    path = get_settings_path()
    if not path.is_file():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data: Dict[str, Any]) -> bool:
    path = get_settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Backup existing
    if path.is_file():
        backup_path = path.with_suffix(".json.bak")
        try:
            shutil.copy2(path, backup_path)
        except Exception:
            pass

    # Atomic write via temp
    tmp_path = path.with_suffix(".json.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path.replace(path)
        return True
    except Exception as e:
        if tmp_path.exists():
            tmp_path.unlink()
        raise IOError(f"Failed to save settings: {e}")


def get_setting_value(key: str, default: Optional[Any] = None) -> Any:
    settings = load_settings()
    return settings.get(key, default)


def set_setting_value(key: str, value: Any) -> Dict[str, Any]:
    settings = load_settings()

    # Convert common string booleans/ints
    if isinstance(value, str):
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

    settings[key] = value
    save_settings(settings)
    return settings
