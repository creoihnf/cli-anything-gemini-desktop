import os
from pathlib import Path
from typing import Any, Dict


def get_gemini_roaming_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Gemini"
    return Path.home() / "AppData" / "Roaming" / "Gemini"


def get_session_info(detailed: bool = False) -> Dict[str, Any]:
    root = get_gemini_roaming_dir()
    if not root.is_dir():
        return {
            "exists": False,
            "path": str(root),
            "directories": [],
            "total_files": 0,
            "total_size_mb": 0.0,
        }

    total_files = 0
    total_size = 0
    dirs_info = []

    for item in root.iterdir():
        if item.is_dir():
            dir_files = 0
            dir_size = 0
            try:
                for sub in item.rglob("*"):
                    if sub.is_file():
                        dir_files += 1
                        try:
                            dir_size += sub.stat().st_size
                        except OSError:
                            pass
            except Exception:
                pass

            total_files += dir_files
            total_size += dir_size
            dirs_info.append({
                "name": item.name,
                "files": dir_files,
                "size_mb": round(dir_size / (1024 * 1024), 2),
            })
        elif item.is_file():
            total_files += 1
            try:
                total_size += item.stat().st_size
            except OSError:
                pass

    result: Dict[str, Any] = {
        "exists": True,
        "path": str(root),
        "total_files": total_files,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "directories_count": len(dirs_info),
    }

    if detailed:
        result["directories"] = dirs_info

    return result
