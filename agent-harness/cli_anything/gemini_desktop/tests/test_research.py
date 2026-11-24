import json
import subprocess
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

from cli_anything.gemini_desktop.core import backend, research
from cli_anything.gemini_desktop.gemini_cli import cli


@pytest.mark.parametrize("json_args", [["--json", "deep-research"], ["deep-research", "--json"]])
def test_research_requests_native_mode_without_waiting(monkeypatch, json_args):
    calls = []

    def send(**kwargs):
        calls.append(kwargs)
        return {"success": True, "submitted": kwargs["submit"]}

    monkeypatch.setattr(backend, "send_prompt", send)
    monkeypatch.setattr(backend, "wait_for_gemini_response", lambda **kw: pytest.fail("Must not treat the plan as a completed report"))
    result = CliRunner().invoke(cli, json_args + ["Compare energy options"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"] == "requested"
    assert data["research_completed"] is False
    assert calls == [{
        "text": "Compare energy options", "submit": True,
        "keep_focus": True, "offscreen": False, "deep_research": True,
    }]


def test_research_draft_and_window_options(monkeypatch):
    calls = []

    def send(**kwargs):
        calls.append(kwargs)
        return {"success": True, "submitted": False}

    monkeypatch.setattr(backend, "send_prompt", send)
    result = CliRunner().invoke(cli, ["deep-research", "Market", "--no-submit", "--focus", "--offscreen", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "draft"
    assert calls[0]["submit"] is False
    assert calls[0]["keep_focus"] is False
    assert calls[0]["offscreen"] is True


def test_research_failure_has_nonzero_exit(monkeypatch):
    monkeypatch.setattr(backend, "send_prompt", lambda **kw: {"success": False, "error": "Tool unavailable"})
    result = CliRunner().invoke(cli, ["deep-research", "Market", "--json"])
    assert result.exit_code == 1
    assert json.loads(result.output) == {"success": False, "error": "Tool unavailable"}


def test_research_missing_prompt_does_not_send(monkeypatch):
    monkeypatch.setattr(backend, "send_prompt", lambda **kw: pytest.fail("Should not send"))
    assert CliRunner().invoke(cli, ["deep-research"]).exit_code == 2


def test_failed_selection_never_pastes_or_submits(monkeypatch):
    restored = []
    monkeypatch.setattr(backend, "_ensure_default_desktop", lambda: None)
    monkeypatch.setattr(backend, "user32", SimpleNamespace(GetCursorPos=lambda pt: None, GetForegroundWindow=lambda: 50))
    monkeypatch.setattr(backend, "get_clipboard", lambda: "original clipboard")
    monkeypatch.setattr(backend, "ensure_gemini_window", lambda **kw: 123)
    monkeypatch.setattr(backend, "show_research_window", lambda hwnd: None)
    monkeypatch.setattr(backend, "select_deep_research", lambda hwnd: {"success": False, "error": "Unavailable"})
    monkeypatch.setattr(backend, "restore_foreground_window", restored.append)
    monkeypatch.setattr(backend, "set_clipboard", lambda text: pytest.fail("Must not paste after selection failure"))
    result = backend.send_prompt("Research", deep_research=True, offscreen=False)
    assert result == {"success": False, "error": "Unavailable"}
    assert restored == [50]


def test_selector_confirms_native_mode(monkeypatch):
    def run(args, **kwargs):
        assert "FromHandle([IntPtr]123)" in args[-1]
        assert "__HWND__" not in args[-1]
        assert kwargs["timeout"] == 15
        return SimpleNamespace(returncode=0, stdout='{"success":true,"mode":"deep-research"}', stderr="")

    monkeypatch.setattr(research.subprocess, "run", run)
    assert research.select_deep_research(123)["success"] is True


@pytest.mark.parametrize("stdout", ["", "not json", "[]", "null", '{"success":true}', '{"success":false}'])
def test_selector_rejects_invalid_confirmation(monkeypatch, stdout):
    monkeypatch.setattr(research.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0, stdout=stdout, stderr=""))
    assert research.select_deep_research(123)["success"] is False


def test_selector_reports_unavailable_tool(monkeypatch):
    monkeypatch.setattr(research.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=1, stdout="", stderr="Tool unavailable"))
    assert research.select_deep_research(123) == {"success": False, "error": "Tool unavailable"}


def test_selector_timeout(monkeypatch):
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired("powershell", 15)

    monkeypatch.setattr(research.subprocess, "run", run)
    assert research.select_deep_research(123)["success"] is False


def test_selector_powershell_syntax():
    # Parse only: never execute the script or touch the Gemini UI during tests.
    parser = (
        "$tokens = $null; $errors = $null; "
        "[void][System.Management.Automation.Language.Parser]::ParseInput("
        "[Console]::In.ReadToEnd(), [ref]$tokens, [ref]$errors); "
        "if ($errors.Count) { $errors | Out-String | Write-Error; exit 1 }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", parser],
        input=research._SELECT_TOOL_SCRIPT.replace("__HWND__", "123"),
        capture_output=True, text=True, timeout=10, creationflags=0x08000000,
    )
    assert result.returncode == 0, result.stderr


def test_research_restores_window_left_offscreen(monkeypatch):
    moved = []
    focused = []

    def get_rect(hwnd, rect):
        rect._obj.left = backend.OFFSCREEN_X
        rect._obj.top = backend.OFFSCREEN_Y

    monkeypatch.setattr(backend, "user32", SimpleNamespace(
        ShowWindow=lambda hwnd, mode: None, GetWindowRect=get_rect,
        SetWindowPos=lambda *args: moved.append(args),
    ))
    monkeypatch.setattr(backend, "force_foreground_window", focused.append)
    backend.show_research_window(123)
    assert moved == [(123, 0, 100, 100, 0, 0, 0x0015)]
    assert focused == [123]


def test_queue_requires_explicit_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_DESKTOP_QUEUE_DIR", raising=False)
    assert backend.get_fila_dir() is None
    monkeypatch.setenv("GEMINI_DESKTOP_QUEUE_DIR", str(tmp_path))
    assert backend.get_fila_dir() == tmp_path
    monkeypatch.setenv("GEMINI_DESKTOP_QUEUE_DIR", str(tmp_path / "missing"))
    assert backend.get_fila_dir() is None


def test_dispatch_uses_current_project_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_DESKTOP_QUEUE_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    orders = backend.dispatch_delegated_orders('```json\n{"id":"task","peso":"peso_2","prompt":"Run tests"}\n```')
    assert len(orders) == 1
    assert json.loads((tmp_path / "task.json").read_text(encoding="utf-8"))["cwd"] == str(tmp_path)
