#!/usr/bin/env python3
"""
interface/tui.py — Yuna TUI v3.2

Interfaz terminal con textual, conectada al agente real.
- Avatar PNG proporcional (sin recorte, fit_inside)
- Agente real en threads (no bloquea la UI)
- Voz con toggle F2
- Comandos: /chat, /agent, /voz, /clear, /salir

Uso:
    python app.py          → abre este TUI
    python app.py menu     → menú clásico (rich)
"""
from __future__ import annotations

import json
import os
import base64
import sys
import threading
import time
from pathlib import Path
from typing import Iterable

sys.path.insert(0, os.path.expanduser("~/yuna"))

from PIL import Image, ImageOps
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, RichLog, ProgressBar, Static

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_CONFIG_PATH = os.path.expanduser("~/yuna/config/yuna_tui_config.json")

_DEFAULT_CONFIG = {
    "titulo": "Y  U  N  A",
    "subtitulo": "AGENTE IA LOCAL",
    "version": "v3.2",
    "colores": {
        "primario": "bright_magenta",
        "secundario": "bright_cyan",
        "acento": "bright_white",
        "borde": "bright_blue",
        "texto_dim": "grey50",
        "ok": "bright_green",
        "warn": "bright_yellow",
        "error": "bright_red",
    },
    "avatar_ascii": [
        '    .-""""""-.',
        "   /  .-..-.  \\",
        "  |  / o  o \\  |",
        "  |  \\  __  /  |",
        "   \\  '----'  /",
        "    '-......-'",
    ],
    "mostrar_stats": True,
    "mostrar_avatar": True,
    "avatar_width": 26,
    "avatar_height": 20,
    "voz_enabled": True,
}


def load_config() -> dict:
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            user = json.load(f)
        cfg = dict(_DEFAULT_CONFIG)
        cfg.update({k: v for k, v in user.items() if k != "colores"})
        cfg["colores"] = {**_DEFAULT_CONFIG["colores"], **user.get("colores", {})}
        return cfg
    except Exception:
        return dict(_DEFAULT_CONFIG)


CONFIG = load_config()


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------
def find_avatar() -> Path | None:
    """Busca Avatar.png (mayúscula primero), luego variantes."""
    home = Path.home()
    candidates = [
        home / "yuna" / "Avatar.png",   # ← el archivo real del proyecto
        home / "yuna" / "avatar.png",
        home / "yuna" / "avatar.gif",
        home / "yuna" / "avatar.jpg",
        home / "yuna" / "avatar.jpeg",
        home / "yuna" / "avatar.webp",
        Path("Avatar.png"),
        Path("avatar.png"),
    ]
    return next((p for p in candidates if p.exists() and p.is_file()), None)


def hexrgb(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def crop_to_subject(im, tol=100, density=0.03, margin=0.03):
    """Recorta en memoria el fondo liso alrededor de la figura."""
    import numpy as np
    rgb = im.convert("RGB")
    a = np.asarray(rgb).astype(int)
    h, w, _ = a.shape
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(border, axis=0)
    m = np.abs(a - bg).sum(axis=2) > tol
    cols = np.where(m.sum(axis=0) > h * density)[0]
    rows = np.where(m.sum(axis=1) > w * density)[0]
    if cols.size == 0 or rows.size == 0:
        return rgb
    mx, my = int(w * margin), int(h * margin)
    return rgb.crop((max(int(cols.min()) - mx, 0), max(int(rows.min()) - my, 0),
                     min(int(cols.max()) + 1 + mx, w), min(int(rows.max()) + 1 + my, h)))


def png_to_rich(path: Path, max_w: int, max_h: int) -> Text:
    """
    Render de alta calidad para terminales de texto.

    Usa un carácter de medio bloque por celda, aprovechando dos píxeles
    verticales independientes y color RGB verdadero. El PNG original
    nunca se modifica.
    """
    try:
        img = Image.open(path).convert("RGBA")
        img = crop_to_subject(img).convert("RGBA")
    except Exception as exc:
        return Text(f"PNG ERROR: {exc}", style="bold red")

    # El ancho de una celda suele ser aproximadamente la mitad de su alto.
    # Compensamos esa geometría para evitar que el avatar se vea aplastado.
    src_w, src_h = img.size

    cell_aspect = 0.50

    available_w = max(8, int(max_w))
    available_h = max(4, int(max_h))

    # Dos píxeles verticales por carácter.
    pixel_w = available_w
    pixel_h = available_h * 2

    scale_w = pixel_w / src_w
    scale_h = pixel_h / src_h

    scale = min(scale_w, scale_h)

    new_w = max(8, int(src_w * scale))
    new_h = max(2, int(src_h * scale))

    # Ajuste fino de aspecto para la geometría física de la terminal.
    new_h = max(2, int(new_h * cell_aspect * 2))

    img = img.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS,
    )

    px = img.load()
    out = Text()

    background = (5, 7, 13, 255)

    for y in range(0, img.height, 2):
        for x in range(img.width):
            top = px[x, y]
            bottom = px[x, min(y + 1, img.height - 1)]

            if top[3] < 128:
                top = background

            if bottom[3] < 128:
                bottom = background

            out.append(
                "▀",
                style=(
                    f"{hexrgb(top[:3])} "
                    f"on {hexrgb(bottom[:3])}"
                ),
            )

        out.append("\n")

    return out


def terminal_supports_native_avatar() -> bool:
    """True cuando el terminal admite imágenes inline OSC 1337."""
    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    return term_program == "iterm.app"


_CHAT_PROMPT_PATH = Path.home() / "yuna" / "config" / "prompts" / "chat_system.txt"
_CHAT_PROMPT_FALLBACK = (
    "Eres Yuna, asistente personal de Luis. "
    "Eres inteligente, directa y hablas en español mexicano."
)


def load_chat_prompt() -> str:
    try:
        return _CHAT_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except Exception:
        return _CHAT_PROMPT_FALLBACK


_AVATAR_B64 = {}


def emit_iterm_avatar(
    app,
    path: Path,
    x: int,
    y: int,
    width: int,
    height: int,
) -> None:
    """
    Envía el PNG original directamente al driver de Textual.

    iTerm2 interpreta OSC 1337 como una imagen raster real.
    No se usa Pillow ni se convierte la imagen a caracteres.
    """
    try:
        key = (str(path), path.stat().st_mtime_ns)
        data = _AVATAR_B64.get(key)
        if data is None:
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            _AVATAR_B64.clear()
            _AVATAR_B64[key] = data
    except Exception:
        return

    sequence = (
        "\x1b7"
        f"\033[{y + 1};{x + 1}H"
        "\033]1337;File="
        "inline=1;"
        "preserveAspectRatio=1;"
        f"width={width};"
        f"height={height}:"
        f"{data}\a"
        "\x1b8"
    )

    try:
        driver = getattr(app, "_driver", None)
        if driver is not None:
            driver.write(sequence)
            driver.flush()
    except Exception:
        pass



class AvatarWidget(Static):
    avatar_path: reactive[Path | None] = reactive(None)

    def __init__(self, path: Path | None, ascii_avatar: Iterable[str], **kwargs):
        super().__init__(**kwargs)
        self.avatar_path = path
        self.ascii_avatar = list(ascii_avatar)

    def on_mount(self) -> None:
        self.refresh_avatar()

    def render_lines(self, *args, **kwargs):
        lines = super().render_lines(*args, **kwargs)
        if terminal_supports_native_avatar():
            self._schedule_emit()
        return lines

    def _schedule_emit(self) -> None:
        timer = getattr(self, "_emit_timer", None)
        if timer is not None:
            timer.stop()
        self._emit_timer = self.set_timer(0.12, self._emit_native_avatar)

    def _emit_native_avatar(self) -> None:
        if not self.avatar_path or not self.avatar_path.exists():
            return

        region = self.content_region
        width = max(8, region.width)
        height = max(4, region.height)

        emit_iterm_avatar(
            self.app,
            self.avatar_path,
            region.x,
            region.y,
            width,
            height,
        )

    def on_resize(self, event) -> None:
        size = (self.content_size.width, self.content_size.height)
        if size != getattr(self, "_last_avatar_size", None):
            self._last_avatar_size = size
            self.refresh_avatar()

    def refresh_avatar(self) -> None:
        if self.avatar_path and self.avatar_path.exists():
            cs = self.content_size
            max_w = cs.width if cs.width >= 8 else CONFIG.get("avatar_width", 26)
            max_h = cs.height if cs.height >= 4 else CONFIG.get("avatar_height", 20)

            if terminal_supports_native_avatar():
                # Dejamos el área del widget limpia y emitimos el PNG
                # original directamente a iTerm2 después del refresh.
                self.update("")
                self.call_after_refresh(self._emit_native_avatar)
            else:
                self.update(
                    png_to_rich(
                        self.avatar_path,
                        max_w,
                        max_h,
                    )
                )
            return

        # Fallback ASCII
        text = Text()
        for line in self.ascii_avatar:
            text.append(line + "\n", style="bright_cyan")
        self.update(text)


# ---------------------------------------------------------------------------
# Agente bridge
# ---------------------------------------------------------------------------
class AgentBridge:
    """
    Conecta el TUI con YunaAgent / chat_simple sin bloquear la UI.
    Corre el procesamiento en threads y notifica al TUI vía callback.
    """

    def __init__(self, log_callback, status_callback, done_callback):
        self.log = log_callback
        self.status = status_callback
        self.done = done_callback
        self._agent = None
        self._chat_messages = []
        self._mode = "agent"  # "agent" | "chat"
        self._busy = False

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == "agent" and self._agent is None:
            self.status("Inicializando agente...")
            try:
                from core.agent import YunaAgent
                from core.llm import preload_model
                preload_model()
                self._agent = YunaAgent()
                self.status("Agente listo")
            except Exception as e:
                self.status(f"Error agente: {e}")
                self._agent = None

    def process(self, user_input: str):
        if self._busy:
            self.log("[yellow]⏳ Espera, estoy procesando...[/]")
            return
        self._busy = True
        self.status("Procesando...")
        threading.Thread(
            target=self._process_thread,
            args=(user_input,),
            daemon=True,
        ).start()

    def _process_thread(self, user_input: str):
        try:
            if self._mode == "agent" and self._agent:
                from memory.manager import add_episodic
                respuesta = self._agent.process(user_input)
                add_episodic("agente", f"Luis: {user_input[:100]} | Yuna: {respuesta[:100]}")
            else:
                from core.llm import chat_simple, clean_response
                from memory.manager import get_relevant_memory, add_episodic, init_db
                init_db()
                if not self._chat_messages:
                    memoria = get_relevant_memory("contexto general")
                    self._chat_messages = [{
                        "role": "system",
                        "content": load_chat_prompt() + f"\n\nMEMORIA:\n{memoria}",
                    }]
                self._chat_messages.append({"role": "user", "content": user_input})
                contexto = [self._chat_messages[0]] + self._chat_messages[-6:]
                resp = chat_simple(contexto, temperature=0.6, num_predict=700)
                respuesta = clean_response(resp)
                self._chat_messages.append({"role": "assistant", "content": respuesta})
                add_episodic("chat", f"Luis: {user_input[:100]} | Yuna: {respuesta[:100]}")

            self.log(f"[bold #ff2ed1]YUNA[/]  > {respuesta}")
            self.status("Listo")
            self.done(respuesta)
        except Exception as e:
            self.log(f"[bold red]ERROR[/]  {e}")
            self.status("Error")
            self.done("")
        finally:
            self._busy = False


# ---------------------------------------------------------------------------
# TUI App
# ---------------------------------------------------------------------------
class YunaTUI(App):
    TITLE = "YUNA // LOCAL AGENT"
    SUB_TITLE = CONFIG.get("subtitulo", "AGENTE IA LOCAL")

    CSS = """
    Screen { background: #03040a; color: #e9f7ff; }
    Header {
        height: 3;
        background: #080914;
        color: #ff4de1;
        text-style: bold;
        border-bottom: solid #13e7ff;
    }
    Footer { height: 1; background: #05060c; color: #647a8a; }

    #root { height: 1fr; padding: 1 1; }

    .panel {
        background: #05070d;
        border: solid #183b63;
        padding: 0 1;
        margin-right: 1;
    }
    .panel-title {
        height: 2;
        color: #13e7ff;
        text-style: bold;
        padding: 0 1;
        border-bottom: solid #112d49;
    }

    #left { width: 48; }
    #center { width: 1fr; }
    #right { width: 30; margin-right: 0; }

    #avatar {
        height: 24;
        border: solid #ff2ed1;
        background: #000000;
        content-align: center middle;
        padding: 0;
    }
    #identity { height: 10; color: #c4d3dc; padding: 1; }
    #stats { height: 1fr; color: #94a6b4; padding: 1; }

    #conversation {
        height: 1fr;
        border: solid #183b63;
        background: #02040a;
    }
    #log { height: 1fr; padding: 1; }

    #command {
        height: 3;
        margin-top: 1;
        border: solid #ff2ed1;
        background: #070811;
        color: #ffffff;
    }
    #progress {
        height: 5;
        padding: 0 1;
        margin-top: 1;
        border: solid #183b63;
        background: #05070d;
    }
    #progressbar { margin-top: 1; }
    #diagnostics { height: 1fr; padding: 1; color: #9cb0bf; }
    #activity {
        height: 10;
        padding: 1;
        color: #8195a4;
        border-top: solid #112d49;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_log", "CLEAR"),
        Binding("ctrl+r", "reload_avatar", "RELOAD"),
        Binding("f1", "focus_command", "COMMAND"),
        Binding("f2", "toggle_voz", "VOZ"),
        Binding("escape", "focus_command", "FOCUS"),
        Binding("ctrl+q", "quit", "QUIT"),
    ]

    def __init__(self):
        super().__init__()
        self.avatar_path = find_avatar()
        self.voz_enabled = CONFIG.get("voz_enabled", True)
        self.bridge = AgentBridge(
            log_callback=self._log,
            status_callback=self._status,
            done_callback=self._on_agent_done,
        )
        self._turns = 0

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="root"):
            # LEFT: avatar + identity + stats
            with Vertical(classes="panel", id="left"):
                yield Static("◈  YUNA / IDENTITY", classes="panel-title")
                yield AvatarWidget(
                    self.avatar_path,
                    CONFIG.get("avatar_ascii", []),
                    id="avatar",
                )
                yield Static(
                    "[b]YUNA[/b]\n"
                    "LOCAL INTELLIGENCE NODE\n"
                    "[#ff2ed1]TYPE ZERO / AGENT[/]\n"
                    "──────────────────\n"
                    f"[#13e7ff]STATUS[/]  [#48ff91]● ONLINE[/]\n"
                    f"[#13e7ff]MODE[/]    {self.bridge._mode.upper()}\n"
                    f"[#13e7ff]VERSION[/] {CONFIG.get('version', 'v3.2')}",
                    id="identity",
                    markup=True,
                )
                yield Static(
                    "SYSTEM\n"
                    "──────────────────\n"
                    "MODEL     [#13e7ff]qwen3:8b[/]\n"
                    "MEMORY    [#48ff91]READY[/]\n"
                    "PLANNER   [#48ff91]READY[/]\n"
                    "TOOLS     [#ffe66d]07[/]\n"
                    "VOZ       [#48ff91]ON[/]\n\n"
                    "COMANDOS\n"
                    "/chat  /agent\n/voz   /clear\n/salir",
                    id="stats",
                    markup=True,
                )

            # CENTER: conversation + progress + input
            with Vertical(id="center"):
                with Vertical(classes="panel", id="conversation"):
                    yield Static(
                        "◉  LIVE AGENT CONSOLE   //   LOCAL CHANNEL",
                        classes="panel-title",
                    )
                    yield RichLog(id="log", markup=True, highlight=True)

                with Vertical(id="progress"):
                    yield Static(
                        "TASK MATRIX  //  CURRENT OPERATION",
                        classes="panel-title",
                    )
                    yield ProgressBar(total=100, show_eta=False, id="progressbar")

                yield Input(
                    placeholder="> instrucción para Yuna... (/chat /agent /voz /clear /salir)",
                    id="command",
                )

            # RIGHT: telemetry + activity
            with Vertical(classes="panel", id="right"):
                yield Static("◈  NEURAL TELEMETRY", classes="panel-title")
                yield Static(
                    "CORE\n"
                    "  [#48ff91]●[/] inference      ONLINE\n"
                    "  [#48ff91]●[/] planner        ONLINE\n"
                    "  [#48ff91]●[/] memory         ONLINE\n"
                    "  [#48ff91]●[/] tool-router    ONLINE\n\n"
                    "SIGNAL\n"
                    "  latency       [#13e7ff]-- ms[/]\n"
                    "  context       [#13e7ff]-- %[/]\n"
                    "  confidence    [#ffe66d]-- %[/]\n\n"
                    "PIPELINE\n"
                    "  [#48ff91]01[/] INPUT\n"
                    "  [#48ff91]02[/] PLAN\n"
                    "  [#48ff91]03[/] TOOL\n"
                    "  [#48ff91]04[/] VERIFY\n"
                    "  [#13e7ff]05[/] RESPONSE",
                    id="diagnostics",
                    markup=True,
                )
                yield Static(
                    "ACTIVITY\n"
                    "──────────────────\n"
                    "[#647a8a]boot[/] handshake    [#48ff91]OK[/]\n"
                    "[#647a8a]boot[/] memory       [#48ff91]OK[/]\n"
                    "[#647a8a]boot[/] agent        [#13e7ff]IDLE[/]",
                    id="activity",
                    markup=True,
                )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#command", Input).focus()
        log = self.query_one("#log", RichLog)
        log.write(
            f"[bold #ff2ed1]╔══ {CONFIG.get('titulo', 'Y  U  N  A')} ══╗[/]"
        )
        log.write(
            f"[#13e7ff]{CONFIG.get('subtitulo', 'AGENTE IA LOCAL')}[/] // "
            "[#647a8a]secure local channel[/]"
        )
        log.write("[#48ff91]● SYSTEM[/] core modules initialized.")
        log.write("[#48ff91]● VOICE[/] " + ("ON" if self.voz_enabled else "OFF"))
        log.write("[#13e7ff]◈ INPUT[/] waiting for command...")
        self.set_interval(1.0, self._heartbeat)

    def _heartbeat(self) -> None:
        stamp = time.strftime("%H:%M:%S")
        mode = self.bridge._mode.upper()
        busy = "BUSY" if self.bridge._busy else "IDLE"
        self.query_one("#activity", Static).update(
            "ACTIVITY\n"
            "──────────────────\n"
            f"[#647a8a]{stamp}[/] heartbeat    [#48ff91]OK[/]\n"
            f"[#647a8a]{stamp}[/] mode         [#13e7ff]{mode}[/]\n"
            f"[#647a8a]{stamp}[/] agent        [#13e7ff]{busy}[/]",
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _log(self, message: str):
        self.query_one("#log", RichLog).write(message)

    def _status(self, message: str):
        self.query_one("#progressbar", ProgressBar).update(
            progress=50 if "Procesando" in message else 0
        )

    def _on_agent_done(self, respuesta: str):
        bar = self.query_one("#progressbar", ProgressBar)
        bar.update(progress=100)
        if respuesta and self.voz_enabled:
            try:
                from interface.voice import hablar
                hablar(respuesta)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return

        # Comandos especiales
        low = command.lower()
        if low in ("/salir", "/exit", "/quit"):
            self.exit()
            return
        if low == "/clear":
            self.action_clear_log()
            return
        if low == "/voz":
            self.action_toggle_voz()
            return
        if low == "/chat":
            self.bridge.set_mode("chat")
            self._log("[#13e7ff]MODE[/] chat conversacional")
            self._update_identity()
            return
        if low == "/agent":
            self.bridge.set_mode("agent")
            self._log("[#13e7ff]MODE[/] agente autónomo")
            self._update_identity()
            return

        # Input normal → agente
        self._turns += 1
        self._log(f"\n[#ff2ed1]YOU[/]  > {command}")
        self.bridge.process(command)

    def _update_identity(self):
        self.query_one("#identity", Static).update(
            "[b]YUNA[/b]\n"
            "LOCAL INTELLIGENCE NODE\n"
            "[#ff2ed1]TYPE ZERO / AGENT[/]\n"
            "──────────────────\n"
            f"[#13e7ff]STATUS[/]  [#48ff91]● ONLINE[/]\n"
            f"[#13e7ff]MODE[/]    {self.bridge._mode.upper()}\n"
            f"[#13e7ff]VERSION[/] {CONFIG.get('version', 'v3.2')}",
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_clear_log(self) -> None:
        self.query_one("#log", RichLog).clear()
        self._log("[#48ff91]● LOG[/] cleared")

    def action_reload_avatar(self) -> None:
        self.avatar_path = find_avatar()
        self.query_one(AvatarWidget).avatar_path = self.avatar_path
        self.query_one(AvatarWidget).refresh_avatar()
        self._log(
            f"[#13e7ff]AVATAR[/] reloaded: "
            f"{self.avatar_path.name if self.avatar_path else 'ASCII fallback'}"
        )

    def action_toggle_voz(self) -> None:
        self.voz_enabled = not self.voz_enabled
        estado = "ON" if self.voz_enabled else "OFF"
        self._log(f"[#48ff91]● VOICE[/] {estado}")
        # Actualizar panel stats
        stats = self.query_one("#stats", Static)
        stats.update(
            "SYSTEM\n"
            "──────────────────\n"
            "MODEL     [#13e7ff]qwen3:8b[/]\n"
            "MEMORY    [#48ff91]READY[/]\n"
            "PLANNER   [#48ff91]READY[/]\n"
            "TOOLS     [#ffe66d]07[/]\n"
            f"VOZ       [{'#48ff91' if self.voz_enabled else '#ff2ed1'}]{estado}[/]\n\n"
            "COMANDOS\n"
            "/chat  /agent\n/voz   /clear\n/salir",
        )

    def action_focus_command(self) -> None:
        self.query_one("#command", Input).focus()


def main() -> None:
    YunaTUI().run()


if __name__ == "__main__":
    main()
