import ctypes
from ctypes import wintypes
import os
import subprocess
import time
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from cli_anything.gemini_desktop.core.settings import load_settings


# Configure 64-bit safe Win32 API prototypes
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

OFFSCREEN_X = 30000
OFFSCREEN_Y = 30000

DELEGATION_PROMPT_PREFIX = """Você é o arquiteto chefe do sistema LLM-OS.
Analise a solicitação abaixo e tome as decisões de arquitetura e alinhamento.
Para quaisquer tarefas que precisem ser executadas pelos agentes operacionais (Claude Code, Codex ou IDE/Antigravity), gere ao final da sua resposta um ou mais blocos ```json com o seguinte schema de ordem para o nosso despachante:

```json
{
  "id": "ordem_<identificador_curto>",
  "titulo": "<titulo da tarefa>",
  "peso": "peso_3",
  "comando": "claude",
  "cwd": "C:\\\\Users\\\\ferna\\\\llm-os",
  "prompt": "<instruções completas para o agente executar>"
}
```
(Use peso_3 e comando "claude" para front-end/sites/UX; peso_3 e comando "codex" para auditoria crítica; peso_2 e comando "agy" para scripts/testes na IDE).

Solicitação:
"""


def _ensure_default_desktop():
    """Ensure current thread can access interactive Default desktop."""
    h_desk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
    if h_desk:
        user32.SetThreadDesktop(h_desk)


def set_clipboard(text: str) -> bool:
    """Sets unicode text to Windows clipboard with retry loop and pure Win32 API."""
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002
    for _ in range(12):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.04)
    else:
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Set-Clipboard -Value $args[0]"],
                args=[text],
                check=True,
                timeout=3,
            )
            return True
        except Exception:
            return False

    try:
        user32.EmptyClipboard()
        data = text.encode("utf-16le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h_mem:
            return False
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            return False
        ctypes.memmove(ptr, data, len(data))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        user32.CloseClipboard()


def get_clipboard() -> str:
    """Reads unicode text from Windows clipboard via Win32 API with PowerShell fallback."""
    CF_UNICODETEXT = 13
    for _ in range(8):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.03)
    else:
        try:
            return subprocess.check_output(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-Clipboard"],
                text=True,
                timeout=3
            )
        except Exception:
            return ""

    try:
        h_mem = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_mem:
            return ""
        ptr = kernel32.GlobalLock(h_mem)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(h_mem)
    finally:
        user32.CloseClipboard()


def force_foreground_window(hwnd: int) -> bool:
    """Safely and reliably brings target window to foreground using Win32 thread input attachment."""
    _ensure_default_desktop()
    if not hwnd:
        return False
    cur_tid = kernel32.GetCurrentThreadId()
    fg_hwnd = user32.GetForegroundWindow()
    if fg_hwnd == hwnd:
        return True

    fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)

    attached_fg = False
    attached_target = False

    try:
        if fg_tid and fg_tid != cur_tid:
            attached_fg = bool(user32.AttachThreadInput(cur_tid, fg_tid, True))
        if target_tid and target_tid != cur_tid:
            attached_target = bool(user32.AttachThreadInput(cur_tid, target_tid, True))

        SW_RESTORE = 9
        user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        res = user32.SetForegroundWindow(hwnd)
        return bool(res)
    finally:
        if attached_fg:
            user32.AttachThreadInput(cur_tid, fg_tid, False)
        if attached_target:
            user32.AttachThreadInput(cur_tid, target_tid, False)


def restore_foreground_window(orig_hwnd: int) -> bool:
    """Safely restores the previously active window."""
    _ensure_default_desktop()
    if not orig_hwnd:
        return False
    cur_fg = user32.GetForegroundWindow()
    if cur_fg == orig_hwnd:
        return True

    cur_tid = kernel32.GetCurrentThreadId()
    fg_tid = user32.GetWindowThreadProcessId(cur_fg, None) if cur_fg else 0
    orig_tid = user32.GetWindowThreadProcessId(orig_hwnd, None)

    attached_cur = False
    attached_orig = False
    try:
        if fg_tid and fg_tid != cur_tid:
            attached_cur = bool(user32.AttachThreadInput(cur_tid, fg_tid, True))
        if orig_tid and orig_tid != cur_tid:
            attached_orig = bool(user32.AttachThreadInput(cur_tid, orig_tid, True))

        user32.BringWindowToTop(orig_hwnd)
        res = user32.SetForegroundWindow(orig_hwnd)
        return bool(res)
    finally:
        if attached_cur:
            user32.AttachThreadInput(cur_tid, fg_tid, False)
        if attached_orig:
            user32.AttachThreadInput(cur_tid, orig_tid, False)


def find_gemini_executable() -> Optional[str]:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        base = Path.home() / "AppData" / "Local" / "Google" / "Gemini"
    else:
        base = Path(local_appdata) / "Google" / "Gemini"

    if not base.is_dir():
        return None

    app_dirs = sorted(
        [d for d in base.glob("app-*") if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    for app_dir in app_dirs:
        exe = app_dir / "Gemini.exe"
        if exe.is_file():
            return str(exe)

    direct_exe = base / "Gemini.exe"
    if direct_exe.is_file():
        return str(direct_exe)

    return None


def get_active_processes() -> List[Dict[str, Any]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "Get-Process -Name Gemini, GeminiAppLauncher, GeminiCrashpadHandler -ErrorAction SilentlyContinue | "
        "Select-Object Id, ProcessName, WorkingSet64, Path | ConvertTo-Json -Compress"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        out = res.stdout.strip()
        if not out:
            return []
        data = json.loads(out)
        if isinstance(data, dict):
            data = [data]
        processes = []
        for p in data:
            ws = p.get("WorkingSet64", 0) or 0
            processes.append({
                "pid": p.get("Id"),
                "name": p.get("ProcessName"),
                "memory_mb": round(ws / (1024 * 1024), 2),
                "path": p.get("Path"),
            })
        return processes
    except Exception:
        return []


def find_gemini_window() -> Optional[int]:
    """Locate the active Gemini Desktop window handle."""
    _ensure_default_desktop()
    hwnd = user32.FindWindowW("Chrome_WidgetWin_1", "Gemini")
    if hwnd:
        return hwnd

    processes = get_active_processes()
    pids = [p["pid"] for p in processes]
    if not pids:
        return None

    found = []
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def enum_cb(h, _):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and user32.IsWindowVisible(h):
            cname = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(h, cname, 256)
            if "Chrome" in cname.value:
                found.append(h)
        return True

    user32.EnumWindows(WNDENUMPROC(enum_cb), 0)
    return found[0] if found else None


def get_gemini_status() -> Dict[str, Any]:
    processes = get_active_processes()
    running = len(processes) > 0
    exe_path = find_gemini_executable()
    total_memory = sum(p.get("memory_mb", 0) for p in processes)

    settings = load_settings()
    shortcut = settings.get("shortcut", "Alt+Space")
    hwnd = find_gemini_window()

    return {
        "running": running,
        "executable": exe_path,
        "process_count": len(processes),
        "total_memory_mb": round(total_memory, 2),
        "processes": processes,
        "shortcut": shortcut,
        "settings_loaded": bool(settings),
        "window_handle": hwnd,
    }


def launch_gemini(force: bool = False, background: bool = False) -> Dict[str, Any]:
    status = get_gemini_status()
    if status["running"] and not force:
        if not background:
            focus_gemini()
        return {
            "success": True,
            "action": "already_running",
            "status": status,
        }

    exe = status["executable"] or find_gemini_executable()
    if not exe:
        return {
            "success": False,
            "error": "Gemini.exe not found in AppData/Local/Google/Gemini",
        }

    try:
        DETACHED_PROCESS = 0x00000008
        subprocess.Popen(
            [exe],
            creationflags=DETACHED_PROCESS,
            close_fds=True,
        )
        time.sleep(1.0)
        new_status = get_gemini_status()
        return {
            "success": True,
            "action": "launched",
            "executable": exe,
            "status": new_status,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def focus_gemini() -> Dict[str, Any]:
    hwnd = find_gemini_window()
    if not hwnd:
        return {"success": False, "error": "Gemini window not found"}

    SW_RESTORE = 9
    user32.ShowWindow(hwnd, SW_RESTORE)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    return {"success": True, "hwnd": hwnd}


def send_shortcut(keys: Optional[str] = None) -> Dict[str, Any]:
    if not keys:
        settings = load_settings()
        keys = settings.get("shortcut", "Alt+Space")

    send_keys_pattern = "%{SPACE}"
    k_lower = keys.lower().replace(" ", "")
    if "shift" in k_lower and "d" in k_lower:
        send_keys_pattern = "+%{d}"
    elif "alt+space" in k_lower or "alt+espaço" in k_lower:
        send_keys_pattern = "%{SPACE}"

    ps_cmd = (
        f"$wshell = New-Object -ComObject WScript.Shell; "
        f"$wshell.SendKeys('{send_keys_pattern}'); "
        f"@{{ Success = $true; Shortcut = '{keys}' }} | ConvertTo-Json -Compress"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {"success": True, "shortcut": keys}
    except Exception as e:
        return {"success": False, "error": str(e), "shortcut": keys}


def move_gemini_offscreen(hwnd: int) -> bool:
    """Move a janela do Gemini Desktop para fora da área visível do monitor (30000, 30000)."""
    if not hwnd:
        return False
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = max(958, rect.right - rect.left)
    h = max(800, rect.bottom - rect.top)
    SWP_NOACTIVATE = 0x0010
    return bool(user32.SetWindowPos(hwnd, 0, OFFSCREEN_X, OFFSCREEN_Y, w, h, SWP_NOACTIVATE))


def hide_gemini(hwnd: Optional[int] = None) -> bool:
    """Oculta completamente a janela do Gemini Desktop de volta à bandeja do sistema."""
    if not hwnd:
        hwnd = find_gemini_window()
    if not hwnd:
        return False
    SW_HIDE = 0
    return bool(user32.ShowWindow(hwnd, SW_HIDE))


def ensure_gemini_window(offscreen: bool = True) -> Optional[int]:
    """Garante que a janela do Gemini Desktop esteja instanciada (e fora da tela por padrão)."""
    hwnd = find_gemini_window()
    if not hwnd:
        exe = find_gemini_executable()
        if exe:
            try:
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen([exe], creationflags=DETACHED_PROCESS, close_fds=True)
            except Exception:
                pass
        for _ in range(25):
            time.sleep(0.08)
            hwnd = find_gemini_window()
            if hwnd:
                break

    if hwnd and offscreen:
        move_gemini_offscreen(hwnd)

    return hwnd


def send_prompt(text: str, submit: bool = True, keep_focus: bool = True, offscreen: bool = True) -> Dict[str, Any]:
    """Injeta prompt no Gemini Desktop sem perturbar o usuário, restaurando mouse, foco e clipboard imediatamente."""
    if not text:
        return {"success": False, "error": "Prompt text cannot be empty"}

    _ensure_default_desktop()

    # 1. Salvar estado original do usuário (cursor, foco e clipboard)
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    orig_fg = user32.GetForegroundWindow()
    orig_clip = get_clipboard()

    # 2. Localizar/instanciar janela e garantir que fique fora da tela (30000, 30000)
    hwnd = ensure_gemini_window(offscreen=offscreen)
    if not hwnd:
        return {"success": False, "error": "Gemini Desktop window not found"}

    if offscreen:
        move_gemini_offscreen(hwnd)

    # 3. Colocar prompt na área de transferência para injeção rápida
    if not set_clipboard(text):
        return {"success": False, "error": "Failed to set clipboard text"}

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = max(958, rect.right - rect.left)
    h = max(800, rect.bottom - rect.top)

    # Ativar brevemente a janela offscreen
    force_foreground_window(hwnd)
    time.sleep(0.08)

    # Coordenadas do clique na caixa de entrada
    click_x = rect.left + int(w * 0.53)
    click_y = max(rect.top + 50, rect.bottom - 105)

    # Clicar na caixa de entrada e restaurar cursor imediatamente (<10ms)
    user32.SetCursorPos(click_x, click_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.02)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    user32.SetCursorPos(pt.x, pt.y)

    time.sleep(0.10)

    VK_CONTROL = 0x11
    VK_A = 0x41
    VK_BACK = 0x08
    VK_V = 0x56
    VK_RETURN = 0x0D
    KEYUP = 0x0002

    # Limpar rascunho anterior
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_A, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_A, 0, KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
    time.sleep(0.02)

    user32.keybd_event(VK_BACK, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_BACK, 0, KEYUP, 0)
    time.sleep(0.04)

    # Colar prompt
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_V, 0, KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
    time.sleep(0.08)

    if submit:
        user32.keybd_event(VK_RETURN, 0, 0, 0)
        time.sleep(0.02)
        user32.keybd_event(VK_RETURN, 0, KEYUP, 0)

    # 4. Restaurar IMEDIATAMENTE a janela ativa do usuário (<20ms)
    restored = False
    if keep_focus and orig_fg and orig_fg != hwnd:
        time.sleep(0.04)
        restored = restore_foreground_window(orig_fg)

    # 5. Restaurar IMEDIATAMENTE a área de transferência original do usuário
    if orig_clip:
        time.sleep(0.05)
        set_clipboard(orig_clip)

    return {
        "success": True,
        "prompt_length": len(text),
        "submitted": submit,
        "focus_restored": restored,
        "hwnd": hwnd,
        "offscreen": offscreen,
    }


def copy_chat_history(offscreen: bool = True) -> str:
    """Captura o histórico visível do Gemini Desktop de forma cirúrgica e off-screen."""
    _ensure_default_desktop()
    hwnd = find_gemini_window()
    if not hwnd:
        return ""

    if offscreen:
        move_gemini_offscreen(hwnd)

    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    orig_fg = user32.GetForegroundWindow()
    orig_clip = get_clipboard()

    force_foreground_window(hwnd)
    time.sleep(0.06)

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    click_x = rect.left + int((rect.right - rect.left) * 0.55)
    click_y = rect.top + 320

    # Focar área de conteúdo e restaurar cursor
    user32.SetCursorPos(click_x, click_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.01)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    user32.SetCursorPos(pt.x, pt.y)
    time.sleep(0.06)

    VK_CONTROL = 0x11
    VK_A = 0x41
    VK_C = 0x43
    KEYUP = 0x0002

    # Selecionar tudo e copiar
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_A, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_A, 0, KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
    time.sleep(0.04)

    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_C, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(VK_C, 0, KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
    time.sleep(0.04)

    # Desfazer seleção
    user32.keybd_event(0x1B, 0, 0, 0)
    time.sleep(0.01)
    user32.keybd_event(0x1B, 0, KEYUP, 0)

    # Restaurar janela do usuário IMEDIATAMENTE
    if orig_fg and orig_fg != hwnd:
        restore_foreground_window(orig_fg)

    captured_text = get_clipboard()

    # Restaurar clipboard original do usuário
    if orig_clip:
        set_clipboard(orig_clip)

    return captured_text


def extract_response(full_text: str, prompt: str) -> str:
    """Extrai apenas a resposta gerada correspondente ao prompt."""
    if not full_text:
        return ""

    lines = [l.strip() for l in prompt.splitlines() if l.strip()]
    first_needle = lines[0][:40] if lines else prompt.strip()[:40]
    last_needle = lines[-1][:40] if lines else first_needle

    idx = full_text.rfind(first_needle) if first_needle else -1
    if idx != -1:
        last_idx = full_text.find(last_needle, idx)
        if last_idx != -1:
            after_prompt = full_text[last_idx + len(last_needle):].strip()
        else:
            newline_idx = full_text.find("\n", idx)
            after_prompt = full_text[newline_idx:].strip() if newline_idx != -1 else full_text[idx:].strip()
        res = after_prompt
    else:
        parts = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        res = parts[-1] if parts else full_text

    disclaimers = [
        "O Gemini é uma IA e pode cometer erros",
        "O Gemini pode apresentar informações imprecisas",
        "Gemini may display inaccurate info",
        "Gemini is an AI",
    ]
    for d in disclaimers:
        if d in res:
            res = res.split(d)[0].strip()

    return res.strip()


def wait_for_gemini_response(prompt: str, max_wait: float = 90.0, callback=None, hide_when_done: bool = True) -> str:
    """Aguarda o Gemini Desktop gerar a resposta de forma stealth e oculta a janela ao finalizar."""
    start_time = time.time()
    last_len = 0
    stable_count = 0

    # Espera inicial silenciosa: deixa o modelo gerar tokens sem qualquer perturbação
    time.sleep(4.0)

    resp = ""
    while time.time() - start_time < max_wait:
        chat = copy_chat_history(offscreen=True)
        resp = extract_response(chat, prompt)
        cur_len = len(resp)

        if callback:
            callback(cur_len)

        if cur_len > 10:
            if cur_len == last_len:
                stable_count += 1
                if stable_count >= 2:
                    break
            else:
                stable_count = 0
                last_len = cur_len

        # Intervalo calmo para não atrapalhar ciclos de usuário
        time.sleep(3.0)

    if hide_when_done:
        hide_gemini()

    return resp


def get_fila_dir() -> Optional[Path]:
    """Localiza o diretório 00-Sistema/fila/ do vault."""
    try:
        import sys
        llmos_path = Path("C:/Users/ferna/llm-os")
        if str(llmos_path) not in sys.path:
            sys.path.insert(0, str(llmos_path))
        from llmos import caminhos_vault as cv
        fila = cv.VAULT_ROOT / "00-Sistema" / "fila"
        if fila.is_dir():
            return fila
    except Exception:
        pass

    fallback = Path(r"G:\O meu disco\Hermes + Code(x) + CLI\00-Sistema\fila")
    if fallback.is_dir():
        return fallback
    return None


def dispatch_delegated_orders(response_text: str) -> List[Dict[str, Any]]:
    """Extrai blocos de código JSON de ordens e grava na fila do despachante."""
    fila_dir = get_fila_dir()
    if not fila_dir or not fila_dir.is_dir():
        return []

    # Extrai blocos ```json { ... } ```
    blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", response_text)
    dispatched = []

    for idx, block in enumerate(blocks):
        try:
            data = json.loads(block)
            if "peso" in data and ("comando" in data or "prompt" in data):
                order_id = data.get("id") or f"ordem_gemini_{int(time.time())}_{idx+1}"
                data["id"] = order_id
                if "cwd" not in data:
                    data["cwd"] = r"C:\Users\ferna\llm-os"

                file_path = fila_dir / f"{order_id}.json"
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                dispatched.append({
                    "id": order_id,
                    "file": str(file_path),
                    "titulo": data.get("titulo", order_id),
                    "peso": data.get("peso"),
                    "comando": data.get("comando", "claude"),
                })
        except Exception:
            pass

    return dispatched
