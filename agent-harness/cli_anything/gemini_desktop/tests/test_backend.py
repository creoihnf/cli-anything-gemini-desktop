from cli_anything.gemini_desktop.core import backend


def test_find_gemini_executable():
    # Should either find an exe path or return None safely
    exe = backend.find_gemini_executable()
    if exe is not None:
        assert "Gemini.exe" in exe


def test_get_gemini_status():
    status = backend.get_gemini_status()
    assert isinstance(status, dict)
    assert "running" in status
    assert "executable" in status
    assert "process_count" in status
    assert "processes" in status


def test_extract_response():
    full_text = (
        "Conversa com o Gemini\n\n"
        "Qual a capital da França?\n\n"
        "A capital da França é Paris.\n\n"
        "O Gemini é uma IA e pode cometer erros."
    )
    res = backend.extract_response(full_text, "Qual a capital da França?")
    assert res == "A capital da França é Paris."


def test_extract_response_multiline():
    prompt = (
        "Você é o arquiteto chefe do sistema LLM-OS.\n"
        "Analise o sistema e delegue ordens.\n"
        "Solicitação:\n"
        "Crie a navbar"
    )
    full_text = f"Historico antigo...\n\n{prompt}\n\nAqui está o plano da navbar.\n\n```json\n{{\"id\": \"ordem_nav\"}}\n```\n\nGemini may display inaccurate info"
    res = backend.extract_response(full_text, prompt)
    assert "Aqui está o plano da navbar." in res
    assert "Gemini may display inaccurate info" not in res
    assert "Você é o arquiteto" not in res


def test_dispatch_delegated_orders(tmp_path, monkeypatch):
    monkeypatch.setattr(backend, "get_fila_dir", lambda: tmp_path)
    sample_response = """
Aqui está minha análise técnica.
Vou criar uma ordem para o Claude Code executar.

```json
{
  "id": "ordem_navbar_refactor",
  "titulo": "Refatorar navbar responsiva",
  "peso": "peso_3",
  "comando": "claude",
  "prompt": "Implementar menu hamburguer no componente Navbar.tsx"
}
```

E mais uma ordem secundária:

```json
{
  "id": "ordem_test_nav",
  "titulo": "Testar componente",
  "peso": "peso_2",
  "comando": "agy",
  "prompt": "pytest tests/test_navbar.py"
}
```
"""
    orders = backend.dispatch_delegated_orders(sample_response)
    assert len(orders) == 2
    assert orders[0]["id"] == "ordem_navbar_refactor"
    assert orders[0]["comando"] == "claude"
    assert (tmp_path / "ordem_navbar_refactor.json").is_file()
    assert (tmp_path / "ordem_test_nav.json").is_file()


def test_move_gemini_offscreen_none():
    assert backend.move_gemini_offscreen(0) is False
    assert backend.move_gemini_offscreen(None) is False


def test_hide_gemini_none(monkeypatch):
    monkeypatch.setattr(backend, "find_gemini_window", lambda: None)
    assert backend.hide_gemini(None) is False
