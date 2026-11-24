import json
import pytest
from pathlib import Path
from cli_anything.gemini_desktop.core import settings


def test_load_settings_fallback(monkeypatch, tmp_path):
    fake_path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "get_settings_path", lambda: fake_path)
    res = settings.load_settings()
    assert res == {}


def test_save_and_load_settings(monkeypatch, tmp_path):
    fake_path = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "get_settings_path", lambda: fake_path)

    sample = {"shortcut": "Alt+Space", "openAtLogin": True}
    assert settings.save_settings(sample) is True
    assert fake_path.is_file()

    loaded = settings.load_settings()
    assert loaded["shortcut"] == "Alt+Space"
    assert loaded["openAtLogin"] is True


def test_set_setting_value(monkeypatch, tmp_path):
    fake_path = tmp_path / "settings.json"
    fake_path.write_text(json.dumps({"shortcut": "Alt+Space"}), encoding="utf-8")
    monkeypatch.setattr(settings, "get_settings_path", lambda: fake_path)

    updated = settings.set_setting_value("minichatEnabled", "true")
    assert updated["minichatEnabled"] is True
    assert fake_path.with_suffix(".json.bak").is_file()
