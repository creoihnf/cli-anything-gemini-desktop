import json
import sys
from pathlib import Path
import click
from cli_anything.gemini_desktop.core import backend, session, settings
from cli_anything.gemini_desktop.utils.repl_skin import ReplSkin


def json_option(f):
    """Decorator to add --json flag at both group level and command level."""
    def callback(ctx, param, value):
        ctx.ensure_object(dict)
        if value or ctx.obj.get("json_mode"):
            ctx.obj["json_mode"] = True
        return value
    return click.option(
        "--json", "json_mode", is_flag=True, is_eager=True, expose_value=False,
        help="Output responses as structured JSON.", callback=callback
    )(f)


def emit(data: dict, json_mode: bool, human_formatter=None):
    if json_mode:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        if human_formatter:
            human_formatter(data)
        else:
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))


@click.group(invoke_without_command=True)
@json_option
@click.pass_context
def cli(ctx):
    """CLI-Anything: Agent-native CLI harness for Google Gemini Desktop."""
    ctx.ensure_object(dict)
    json_mode = ctx.obj.get("json_mode", False)

    if ctx.invoked_subcommand is None:
        if json_mode or not sys.stdin.isatty():
            ctx.invoke(status)
        else:
            ctx.invoke(repl)


@cli.command("status")
@json_option
@click.pass_context
def status(ctx):
    """Check Gemini Desktop process status, memory, and configuration."""
    json_mode = ctx.obj.get("json_mode", False)
    data = backend.get_gemini_status()

    def format_human(d):
        state = "ONLINE (Running)" if d["running"] else "OFFLINE (Not running)"
        click.echo(f"Gemini Desktop Status: {state}")
        click.echo(f"  Executable:     {d['executable'] or 'Not found'}")
        click.echo(f"  Process Count:  {d['process_count']}")
        click.echo(f"  Total Memory:   {d['total_memory_mb']} MB")
        click.echo(f"  Global Shortcut:{d['shortcut']}")
        if d.get("window_handle"):
            click.echo(f"  Window Handle:  0x{d['window_handle']:X}")
        if d["processes"]:
            click.echo("  Processes:")
            for p in d["processes"]:
                click.echo(f"    - PID {p['pid']}: {p['name']} ({p['memory_mb']} MB)")

    emit(data, json_mode, format_human)


@cli.command("launch")
@click.option("--force", is_flag=True, help="Force launch even if an instance is detected.")
@click.option("--background", is_flag=True, help="Launch silently in background.")
@json_option
@click.pass_context
def launch(ctx, force: bool, background: bool):
    """Launch Gemini Desktop or bring active window to foreground."""
    json_mode = ctx.obj.get("json_mode", False)
    data = backend.launch_gemini(force=force, background=background)

    def format_human(d):
        if d.get("success"):
            click.echo(f"Gemini Desktop: {d.get('action')}")
        else:
            click.echo(f"Launch failed: {d.get('error')}", err=True)

    emit(data, json_mode, format_human)


@cli.command("shortcut")
@click.option("--keys", default=None, help="Custom shortcut keys (defaults to settings.json).")
@json_option
@click.pass_context
def shortcut(ctx, keys: str):
    """Trigger the global hotkey (e.g. Alt+Space) to toggle Gemini Desktop."""
    json_mode = ctx.obj.get("json_mode", False)
    data = backend.send_shortcut(keys=keys)

    def format_human(d):
        if d.get("success"):
            click.echo(f"Shortcut triggered: {d.get('shortcut')}")
        else:
            click.echo(f"Shortcut failed: {d.get('error')}", err=True)

    emit(data, json_mode, format_human)


@cli.command("send")
@click.argument("text", required=True)
@click.option("--submit/--no-submit", default=True, help="Automatically press Enter after pasting.")
@click.option("--focus/--keep-focus", default=False, help="Leave Gemini in focus (default is to keep your current window).")
@click.option("--offscreen/--visible", default=True, help="Keep Gemini window off-screen without occupying screen (default).")
@json_option
@click.pass_context
def send(ctx, text: str, submit: bool, focus: bool, offscreen: bool):
    """Send text/prompt into Gemini Desktop window non-intrusively."""
    json_mode = ctx.obj.get("json_mode", False)
    data = backend.send_prompt(text=text, submit=submit, keep_focus=not focus, offscreen=offscreen)

    def format_human(d):
        if d.get("success"):
            sub_status = "submitted (Enter pressed)" if d.get("submitted") else "pasted into input box"
            focus_info = " (foco retornado ao seu terminal)" if d.get("focus_restored") else ""
            click.echo(f"Prompt sent: {d.get('prompt_length')} characters ({sub_status}){focus_info}.")
        else:
            click.echo(f"Send failed: {d.get('error')}", err=True)

    emit(data, json_mode, format_human)


@cli.command("bridge")
@click.argument("message", required=False, default="")
@click.option("--file", "-f", "file_path", default=None, help="Attach file content as context.")
@click.option("--submit/--no-submit", default=True, help="Automatically press Enter after pasting.")
@click.option("--focus/--keep-focus", default=False, help="Leave Gemini in focus (default is to keep your current window).")
@click.option("--offscreen/--visible", default=True, help="Keep Gemini window off-screen without occupying screen (default).")
@json_option
@click.pass_context
def bridge(ctx, message: str, file_path: str, submit: bool, focus: bool, offscreen: bool):
    """Bridge context/files and prompts from Alethe into Gemini Desktop non-intrusively."""
    json_mode = ctx.obj.get("json_mode", False)

    content_parts = []
    if file_path:
        p = Path(file_path).resolve()
        if not p.is_file():
            emit({"success": False, "error": f"File not found: {file_path}"}, json_mode)
            return
        try:
            file_text = p.read_text(encoding="utf-8", errors="replace")
            content_parts.append(f"--- CONTEXTO DO ARQUIVO ({p.name}) ---\n{file_text}\n--- FIM DO CONTEXTO ---")
        except Exception as e:
            emit({"success": False, "error": f"Failed to read file {file_path}: {e}"}, json_mode)
            return

    if message:
        content_parts.append(message)

    if not content_parts:
        emit({"success": False, "error": "Provide a message and/or a --file to bridge."}, json_mode)
        return

    full_payload = "\n\n".join(content_parts)
    data = backend.send_prompt(text=full_payload, submit=submit, keep_focus=not focus, offscreen=offscreen)
    data["file"] = file_path
    data["bridge"] = True

    def format_human(d):
        if d.get("success"):
            sub_status = "enviado para o Gemini Desktop" if d.get("submitted") else "colado na caixa de entrada"
            focus_info = " (foco retornado ao seu terminal)" if d.get("focus_restored") else ""
            msg = f"Ponte Alethe ➔ Gemini Desktop: {d.get('prompt_length')} caracteres ({sub_status}){focus_info}."
            if d.get("file"):
                msg += f"\n  Contexto anexado: {d.get('file')}"
            click.echo(msg)
        else:
            click.echo(f"Falha na ponte: {d.get('error')}", err=True)

    emit(data, json_mode, format_human)


@cli.command("settings")
@click.option("--list", "list_all", is_flag=True, help="List all configuration keys.")
@click.option("--get", "get_key", default=None, help="Get specific setting value.")
@click.option("--set", "set_pair", nargs=2, default=None, help="Set key value pair: --set KEY VALUE.")
@json_option
@click.pass_context
def settings_cmd(ctx, list_all: bool, get_key: str, set_pair: tuple):
    """View and update local settings (settings.json)."""
    json_mode = ctx.obj.get("json_mode", False)

    if set_pair:
        key, value = set_pair
        res = settings.set_setting_value(key, value)
        data = {"action": "set", "key": key, "value": value, "settings": res}
    elif get_key:
        val = settings.get_setting_value(get_key)
        data = {"action": "get", "key": get_key, "value": val}
    else:
        all_s = settings.load_settings()
        data = {"action": "list", "settings": all_s}

    def format_human(d):
        if d.get("action") == "set":
            click.echo(f"Setting updated: {d['key']} = {d['value']}")
        elif d.get("action") == "get":
            click.echo(f"{d['key']}: {d['value']}")
        else:
            click.echo("Gemini Desktop Settings:")
            for k, v in d.get("settings", {}).items():
                click.echo(f"  {k}: {v}")

    emit(data, json_mode, format_human)


@cli.command("session")
@click.option("--detailed", is_flag=True, help="Include detailed folder breakdown.")
@json_option
@click.pass_context
def session_cmd(ctx, detailed: bool):
    """Audit local session files, storage, and caches."""
    json_mode = ctx.obj.get("json_mode", False)
    data = session.get_session_info(detailed=detailed)

    def format_human(d):
        if not d.get("exists"):
            click.echo("Session path not found.")
            return
        click.echo("Gemini Desktop Session Summary:")
        click.echo(f"  Path:            {d['path']}")
        click.echo(f"  Total Files:     {d['total_files']}")
        click.echo(f"  Total Size:      {d['total_size_mb']} MB")
        click.echo(f"  Storage Folders: {d['directories_count']}")
        if "directories" in d:
            click.echo("  Directories:")
            for sub in d["directories"]:
                click.echo(f"    - {sub['name']}: {sub['files']} files ({sub['size_mb']} MB)")

    emit(data, json_mode, format_human)


@cli.command("ask")
@click.argument("prompt", required=True)
@click.option("--timeout", default=90, type=int, help="Maximum seconds to wait for generation.")
@click.option("--focus/--keep-focus", default=False, help="Leave Gemini in focus (default is to keep your current window).")
@click.option("--offscreen/--visible", default=True, help="Keep Gemini window off-screen without occupying screen (default).")
@json_option
@click.pass_context
def ask(ctx, prompt: str, timeout: int, focus: bool, offscreen: bool):
    """Converse directly with Gemini Desktop and receive full text response in stdout."""
    json_mode = ctx.obj.get("json_mode", False)

    send_res = backend.send_prompt(text=prompt, submit=True, keep_focus=not focus, offscreen=offscreen)
    if not send_res.get("success"):
        emit({"success": False, "error": f"Failed to send prompt: {send_res.get('error')}"}, json_mode)
        return

    resp = backend.wait_for_gemini_response(prompt=prompt, max_wait=float(timeout), hide_when_done=offscreen)
    if not resp:
        emit({"success": False, "error": "Timeout or failed to capture response from Gemini Desktop.", "prompt": prompt}, json_mode)
        return

    data = {
        "success": True,
        "prompt": prompt,
        "response": resp,
        "length": len(resp)
    }

    def format_human(d):
        click.echo(d["response"])

    emit(data, json_mode, format_human)


@cli.command("delegate")
@click.argument("instruction", required=True)
@click.option("--file", "-f", "file_path", default=None, help="Attach file content as context for delegation.")
@click.option("--timeout", default=90, type=int, help="Maximum seconds to wait for generation.")
@click.option("--focus/--keep-focus", default=False, help="Leave Gemini in focus (default is to keep your current window).")
@click.option("--offscreen/--visible", default=True, help="Keep Gemini window off-screen without occupying screen (default).")
@json_option
@click.pass_context
def delegate(ctx, instruction: str, file_path: str, timeout: int, focus: bool, offscreen: bool):
    """Delegate high-level instruction to Gemini Desktop (0 IDE tokens), auto-dispatching operational JSON orders to queue."""
    json_mode = ctx.obj.get("json_mode", False)

    content_parts = []
    if file_path:
        p = Path(file_path).resolve()
        if not p.is_file():
            emit({"success": False, "error": f"File not found: {file_path}"}, json_mode)
            return
        try:
            file_text = p.read_text(encoding="utf-8", errors="replace")
            content_parts.append(f"--- CONTEXTO DO ARQUIVO ({p.name}) ---\n{file_text}\n--- FIM DO CONTEXTO ---")
        except Exception as e:
            emit({"success": False, "error": f"Failed to read file {file_path}: {e}"}, json_mode)
            return

    content_parts.append(instruction)
    body = "\n\n".join(content_parts)
    full_prompt = f"{backend.DELEGATION_PROMPT_PREFIX}\n{body}"

    send_res = backend.send_prompt(text=full_prompt, submit=True, keep_focus=not focus, offscreen=offscreen)
    if not send_res.get("success"):
        emit({"success": False, "error": f"Failed to send prompt: {send_res.get('error')}"}, json_mode)
        return

    resp = backend.wait_for_gemini_response(prompt=full_prompt, max_wait=float(timeout), hide_when_done=offscreen)
    if not resp:
        emit({"success": False, "error": "Timeout or failed to capture response from Gemini Desktop.", "instruction": instruction}, json_mode)
        return

    orders = backend.dispatch_delegated_orders(resp)

    data = {
        "success": True,
        "instruction": instruction,
        "file": file_path,
        "response": resp,
        "orders_count": len(orders),
        "orders": orders
    }

    def format_human(d):
        click.echo("=== Resposta do Gemini Desktop ===")
        click.echo(d["response"])
        click.echo("\n=== Ordens Despachadas para a Fila (00-Sistema/fila/) ===")
        if d["orders"]:
            for o in d["orders"]:
                click.echo(f"  [+] Ordem: {o['id']} ({o['titulo']})")
                click.echo(f"      Agente: {o['comando']} | Peso: {o['peso']}")
                click.echo(f"      Arquivo: {o['file']}")
        else:
            click.echo("  (Nenhuma ordem em bloco ```json detectada para despacho automático)")

    emit(data, json_mode, format_human)


@cli.command("repl")
@click.pass_context
def repl(ctx):
    """Start interactive REPL shell with command completion."""
    skin = ReplSkin(cli)
    skin.run()


if __name__ == "__main__":
    cli()
