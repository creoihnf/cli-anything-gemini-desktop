import json
from click.testing import CliRunner
from cli_anything.gemini_desktop.gemini_cli import cli


def test_cli_status_json_prefix():
    runner = CliRunner()
    result = runner.invoke(cli, ["--json", "status"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "running" in data
    assert "process_count" in data


def test_cli_status_json_suffix():
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "running" in data
    assert "process_count" in data


def test_cli_settings_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["settings", "--list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "settings" in data


def test_cli_session_json():
    runner = CliRunner()
    result = runner.invoke(cli, ["session", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "exists" in data


def test_cli_bridge_file_json(tmp_path):
    fake_file = tmp_path / "spec.md"
    fake_file.write_text("# Spec de Teste", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["bridge", "Como estruturar isso?", "-f", str(fake_file), "--no-submit", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["bridge"] is True
    assert data["submitted"] is False
    assert data["prompt_length"] > 0


def test_cli_ask(monkeypatch):
    from cli_anything.gemini_desktop.core import backend
    monkeypatch.setattr(backend, "send_prompt", lambda *args, **kwargs: {"success": True, "prompt_length": len(args[0] if args else kwargs.get("text", ""))})
    monkeypatch.setattr(backend, "wait_for_gemini_response", lambda *args, **kwargs: "A resposta do Gemini em texto puro.")

    runner = CliRunner()
    result = runner.invoke(cli, ["ask", "Qual a previsão do tempo?"])
    assert result.exit_code == 0
    assert "A resposta do Gemini em texto puro." in result.output

    # JSON mode
    result_json = runner.invoke(cli, ["ask", "Qual a previsão do tempo?", "--json"])
    assert result_json.exit_code == 0
    data = json.loads(result_json.output)
    assert data["success"] is True
    assert data["response"] == "A resposta do Gemini em texto puro."


def test_cli_delegate(monkeypatch, tmp_path):
    from cli_anything.gemini_desktop.core import backend
    mock_order = {
        "id": "ordem_123",
        "file": str(tmp_path / "ordem_123.json"),
        "titulo": "Implementar rota",
        "peso": "peso_3",
        "comando": "claude",
    }
    monkeypatch.setattr(backend, "send_prompt", lambda *args, **kwargs: {"success": True, "prompt_length": len(args[0] if args else kwargs.get("text", ""))})
    monkeypatch.setattr(backend, "wait_for_gemini_response", lambda *args, **kwargs: "Aqui está o plano.\n```json\n{\"id\":\"ordem_123\"}\n```")
    monkeypatch.setattr(backend, "dispatch_delegated_orders", lambda text: [mock_order])

    runner = CliRunner()
    result = runner.invoke(cli, ["delegate", "Refatore as rotas da API"])
    assert result.exit_code == 0
    assert "Resposta do Gemini Desktop" in result.output
    assert "ordem_123" in result.output
    assert "claude" in result.output

    # JSON mode
    result_json = runner.invoke(cli, ["delegate", "Refatore as rotas da API", "--json"])
    assert result_json.exit_code == 0
    data = json.loads(result_json.output)
    assert data["success"] is True
    assert data["orders_count"] == 1
    assert data["orders"][0]["id"] == "ordem_123"
