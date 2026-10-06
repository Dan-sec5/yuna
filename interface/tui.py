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
import subprocess
import base64
import sys
import threading
import time
from pathlib import Path
from typing import Iterable

sys.path.insert(0, os.path.expanduser("~/yuna"))

from PIL import Image, ImageOps

from tools.registry import TOOLS
from interface.weather import weather_provider
from interface.avatar_context import (
    avatar_state,
    avatar_resolver,
)
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Button, Footer, Header, Input, RichLog, ProgressBar, Static

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
    """
    Devuelve el avatar apropiado para el contexto actual.
    """
    return avatar_resolver.resolve(
        avatar_state.get()
    )

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



def choose_files_macos() -> list[Path]:
    if sys.platform != "darwin":
        return []

    script = (
        'set selectedFiles to choose file with prompt "Adjuntar archivos a Yuna" '
        'with multiple selections allowed\n'
        'set output to ""\n'
        'repeat with selectedFile in selectedFiles\n'
        'set output to output & (POSIX path of selectedFile) & linefeed\n'
        'end repeat\n'
        'return output'
    )

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    return [
        Path(line.strip())
        for line in result.stdout.splitlines()
        if line.strip()
    ]


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

    def __init__(
        self,
        log_callback,
        status_callback,
        done_callback,
        state_callback=None,
    ):
        self.log = log_callback
        self.status = status_callback
        self.done = done_callback
        self.state = state_callback or (
            lambda **kwargs: None
        )
        self._agent = None
        self._chat_messages = []
        self._mode = "agent"  # "agent" | "chat"
        self._busy = False

        # Confirmaciones pendientes de herramientas CONFIRM.
        # El worker del agente espera aquí mientras la TUI
        # recibe el siguiente "sí" o "no" del usuario.
        self._confirm_lock = threading.Lock()
        self._confirm_event = None
        self._confirm_result = None
        self._pending_confirm = None

    def _confirm_tool(self, tool_name: str, args: dict) -> bool:
        """
        Espera una confirmación introducida desde la propia TUI.

        IMPORTANTE:
        Este método se ejecuta dentro del thread del agente.
        No usa input(), porque eso rompería el flujo de Textual.
        """
        event = threading.Event()

        with self._confirm_lock:
            self._confirm_event = event
            self._confirm_result = None
            self._pending_confirm = {
                "tool": tool_name,
                "args": args,
            }

        self.log(
            "[bold yellow]CONFIRMAR[/]  > "
            f"{tool_name}({args})\n"
            "[yellow]Escribe sí o no.[/]"
        )
        self.status(f"Esperando confirmación: {tool_name}")

        # Cinco minutos para responder.
        confirmado = event.wait(timeout=300)

        with self._confirm_lock:
            resultado = bool(self._confirm_result) if confirmado else False

            self._confirm_event = None
            self._confirm_result = None
            self._pending_confirm = None

        if not confirmado:
            self.log(
                "[yellow]⚠ Confirmación expirada. "
                "Operación cancelada.[/]"
            )

        return resultado

    def set_mode(self, mode: str):
        self._mode = mode
        if mode == "agent" and self._agent is None:
            self.status("Inicializando agente...")
            try:
                from core.agent import YunaAgent
                from core.llm import preload_model
                preload_model()
                self._agent = YunaAgent(
                    confirm_callback=self._confirm_tool
                )
                self.status("Agente listo")
            except Exception as e:
                self.status(f"Error agente: {e}")
                self._agent = None

    def process(self, user_input: str):
        # -----------------------------------------------------
        # CONFIRMACIÓN PENDIENTE
        # -----------------------------------------------------
        #
        # Si una herramienta CONFIRM está esperando respuesta,
        # este texto NO se envía a Qwen como una conversación
        # nueva. Se entrega directamente al ToolExecutor.
        # -----------------------------------------------------

        with self._confirm_lock:
            pendiente = self._pending_confirm is not None
            event = self._confirm_event

        if pendiente:
            respuesta = user_input.strip().lower()

            afirmativos = {
                "si", "sí", "s",
                "yes", "y",
                "acepto",
                "confirmo",
            }

            negativos = {
                "no", "n",
                "cancelar",
                "cancela",
            }

            if respuesta in afirmativos:
                with self._confirm_lock:
                    self._confirm_result = True

                self.status("Confirmado. Ejecutando herramienta...")

                if event:
                    event.set()

                return

            if respuesta in negativos:
                with self._confirm_lock:
                    self._confirm_result = False

                self.status("Operación cancelada")

                if event:
                    event.set()

                return

            self.log(
                "[yellow]Hay una operación esperando confirmación. "
                "Responde únicamente sí o no.[/]"
            )
            return

        if self._busy:
            self.log("[yellow]⏳ Espera, estoy procesando...[/]")
            return

        self._busy = True

        self.state(
            agent_state="thinking",
            mood="focused",
        )

        self.status("Procesando...")
        threading.Thread(
            target=self._process_thread,
            args=(user_input,),
            daemon=True,
        ).start()

    def _process_thread(self, user_input: str):
        try:
            self.state(
                agent_state="working",
                mood="focused",
            )
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

            self.log(
                f"[bold #ff2ed1]YUNA[/]  > {respuesta}"
            )

            self.state(
                agent_state="success",
                mood="happy",
            )

            self.status("Listo")
            self.done(respuesta)
        except Exception as e:

            self.state(
                agent_state="error",
                mood="concerned",
            )

            self.log(
                f"[bold red]ERROR[/]  {e}"
            )

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
        height: 20;
        border: solid #ff2ed1;
        background: #000000;
        content-align: center middle;
        padding: 0;
    }
    #identity { height: 8; color: #c4d3dc; padding: 1; }
    #stats {
        height: 1fr;
        min-height: 16;
        color: #94a6b4;
        padding: 1;
        overflow-y: auto;
    }

    #conversation {
        height: 1fr;
        border: solid #183b63;
        background: #02040a;
    }
    #log { height: 1fr; padding: 1; }

    #attachments {
        height: auto;
        min-height: 1;
        max-height: 4;
        margin-top: 1;
        padding: 0 1;
        color: #9cb0bf;
    }

    #command-row {
        height: 3;
        margin-top: 1;
    }

    #command-row #attach {
        width: 5;
        min-width: 5;
        height: 3;
        margin-right: 1;
        border: solid #13e7ff;
        color: #13e7ff;
        background: #070811;
    }

    #command-row #command {
        width: 1fr;
        height: 3;
        margin-top: 0;
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
        Binding("ctrl+o", "attach_files", "ATTACH"),
        Binding("ctrl+l", "clear_log", "CLEAR"),
        Binding("ctrl+r", "reload_avatar", "RELOAD"),
        Binding("f1", "focus_command", "COMMAND"),
        Binding("f2", "toggle_voz", "VOZ"),
        Binding("escape", "focus_command", "FOCUS"),
        Binding("ctrl+q", "quit", "QUIT"),
    ]

    def __init__(self):
        super().__init__()


        # WeatherProvider se actualiza fuera del thread gráfico.
        self._weather_refreshing = False
        self._weather_last_check = 0.0
        self.avatar_path = find_avatar()
        self.voz_enabled = CONFIG.get("voz_enabled", True)
        self.bridge = AgentBridge(
            log_callback=self._log,
            status_callback=self._status,
            done_callback=self._on_agent_done,
        )
        self._turns = 0
        self._attached_files: list[Path] = []

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
                ctx = avatar_state.get()

                yield Static(
                    "SYSTEM\n"
                    "──────────────────\n"
                    f"MODEL     [#13e7ff]{(CONFIG.get('models') or {}).get('chat', 'maid:latest')}[/]\n"
                    "MEMORY    [#48ff91]READY[/]\n"
                    f"TOOLS     [#ffe66d]{len(TOOLS):02d}[/]\n"
                    "VOZ       [#48ff91]ON[/]\n"
                    "\n"
                    "AVATAR CONTEXT\n"
                    "──────────────────\n"
                    f"STATE     [#13e7ff]{ctx.agent_state.upper()}[/]\n"
                    f"HUMOR     [#ff2ed1]{ctx.mood.upper()}[/]\n"
                    f"HORA      [#ffe66d]{ctx.time_of_day.upper()}[/]\n"
                    f"CLIMA     [#48ff91]{ctx.weather.upper()}[/]\n"
                    "\n"
                    "COMANDOS\n"
                    "/chat  /agent\n"
                    "/voz   /clear\n"
                    "/salir",
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

                yield Static("", id="attachments")
                with Horizontal(id="command-row"):
                    yield Button("+", id="attach", flat=True, compact=True)
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

        # Inicializar realmente el agente.
        #
        # _mode comienza como "agent", pero eso por sí solo no
        # crea YunaAgent. Sin esta llamada self._agent permanece
        # en None y AgentBridge termina usando chat_simple().
        self.bridge.set_mode("agent")
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

    def _set_avatar_context(
        self,
        *,
        agent_state: str | None = None,
        mood: str | None = None,
        weather: str | None = None,
        mood_ttl: float | None = None,
    ) -> None:
        """
        Actualiza el contexto lógico del avatar.

        La actualización visual se realiza desde _heartbeat(),
        dentro del thread principal de Textual.
        """
        avatar_state.update(
            agent_state=agent_state,
            mood=mood,
            weather=weather,
            mood_ttl=mood_ttl,
        )


    def _refresh_weather_async(self) -> None:
        """
        Actualiza clima fuera del thread de Textual.
        """

        if self._weather_refreshing:
            return

        self._weather_refreshing = True

        def worker():
            try:
                snapshot = weather_provider.get()

                avatar_state.update(
                    weather=snapshot.condition
                )

            finally:
                self._weather_refreshing = False

        threading.Thread(
            target=worker,
            daemon=True,
        ).start()


    def _maybe_refresh_weather(self) -> None:
        """
        Comprueba periódicamente si conviene consultar clima.

        El proveedor tiene su propia caché; esta comprobación
        solamente evita crear threads innecesarios.
        """

        now = time.monotonic()

        if (
            now - self._weather_last_check
            < 60
        ):
            return

        self._weather_last_check = now
        self._refresh_weather_async()


    def _heartbeat(self) -> None:
        """
        Refresca el estado operativo y el contexto visual.

        Este método corre desde el ciclo de Textual, así que
        aquí se realizan las modificaciones de widgets.
        """
        stamp = time.strftime("%H:%M:%S")

        # Clima: consulta asíncrona con caché.
        self._maybe_refresh_weather()


        # Hora / humor ambiental.
        avatar_state.update()
        ctx = avatar_state.get()
        mood_remaining = avatar_state.mood_remaining()

        # -----------------------------------------------------
        # Avatar
        # -----------------------------------------------------

        current_avatar = find_avatar()

        if current_avatar != self.avatar_path:
            self.avatar_path = current_avatar

            try:
                widget = self.query_one(
                    AvatarWidget
                )

                widget.avatar_path = current_avatar
                widget.refresh_avatar()

            except Exception:
                pass

        # -----------------------------------------------------
        # Estado del agente
        # -----------------------------------------------------

        mode = self.bridge._mode.upper()

        busy = (
            "BUSY"
            if self.bridge._busy
            else "IDLE"
        )

        self.query_one(
            "#activity",
            Static,
        ).update(
            "ACTIVITY\n"
            "──────────────────\n"
            f"[#647a8a]{stamp}[/] heartbeat    [#48ff91]OK[/]\n"
            f"[#647a8a]{stamp}[/] mode         [#13e7ff]{mode}[/]\n"
            f"[#647a8a]{stamp}[/] agent        [#13e7ff]{busy}[/]"
        )

        # -----------------------------------------------------
        # Panel contextual
        # -----------------------------------------------------

        voice_status = (
            "[#48ff91]ON[/]"
            if self.voz_enabled
            else "[#647a8a]OFF[/]"
        )

        model = (
            CONFIG.get("models")
            or {}
        ).get(
            "chat",
            "maid:latest",
        )

        self.query_one(
            "#stats",
            Static,
        ).update(
            "SYSTEM\n"
            "──────────────────\n"
            f"MODEL     [#13e7ff]{model}[/]\n"
            "MEMORY    [#48ff91]READY[/]\n"
            f"TOOLS     [#ffe66d]{len(TOOLS):02d}[/]\n"
            f"VOZ       {voice_status}\n"
            "\n"
            "AVATAR CONTEXT\n"
            "──────────────────\n"
            f"STATE     [#13e7ff]{ctx.agent_state.upper()}[/]\n"
            f"HUMOR     [#ff2ed1]{ctx.mood.upper()}[/]\n"
            f"MOOD TTL  [#647a8a]{mood_remaining:4.0f}s[/]\n"
            f"HORA      [#ffe66d]{ctx.time_of_day.upper()}[/]\n"
            f"CLIMA     [#48ff91]{ctx.weather.upper()}[/]\n"
            "\n"
            "COMANDOS\n"
            "/chat  /agent\n"
            "/voz   /clear\n"
            "/salir"
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _dispatch_ui(self, callback, *args) -> None:
        """
        Ejecuta modificaciones visuales en el thread de Textual.

        AgentBridge procesa solicitudes en un thread secundario.
        Los widgets, timers y demás operaciones de Textual deben
        regresar al thread principal de la aplicación.
        """
        if threading.current_thread() is threading.main_thread():
            callback(*args)
            return

        self.call_from_thread(
            callback,
            *args,
        )


    def _log(self, message: str):
        self._dispatch_ui(
            self._log_ui,
            message,
        )


    def _log_ui(self, message: str):
        self.query_one(
            "#log",
            RichLog,
        ).write(message)


    def _status(self, message: str):
        self._dispatch_ui(
            self._status_ui,
            message,
        )


    def _status_ui(self, message: str):
        progress = (
            50
            if "Procesando" in message
            else 0
        )

        self.query_one(
            "#progressbar",
            ProgressBar,
        ).update(
            progress=progress
        )


    def _on_agent_done(self, respuesta: str):
        """
        AgentBridge llama este método desde su worker.

        Redirigimos todo el trabajo visual al event loop
        principal de Textual.
        """
        self._dispatch_ui(
            self._on_agent_done_ui,
            respuesta,
        )


    def _on_agent_done_ui(self, respuesta: str):
        bar = self.query_one(
            "#progressbar",
            ProgressBar,
        )

        bar.update(
            progress=100
        )

        # El estado SUCCESS/HAPPY permanece brevemente.
        # Después solo regresamos el agente a IDLE.
        # El humor conserva su TTL propio.
        self.set_timer(
            2.5,
            lambda: self._set_avatar_context(
                agent_state="idle",
            ),
        )

        if respuesta and self.voz_enabled:
            try:
                from interface.voice import hablar

                # Voz en thread separado para no congelar TUI.
                threading.Thread(
                    target=hablar,
                    args=(respuesta,),
                    daemon=True,
                ).start()

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
        attached = list(self._attached_files)
        self._attached_files.clear()
        self._update_attachments()

        command_for_agent = command

        if attached:
            command_for_agent += (
                "\n\n"
                "ARCHIVOS ADJUNTOS DISPONIBLES:\n"
                + "\n".join(f"- {path}" for path in attached)
                + "\n\n"
                "Usa las herramientas de archivos apropiadas para analizar "
                "los adjuntos cuando sea necesario."
            )

        self._turns += 1
        self._log(f"\n[#ff2ed1]YOU[/]  > {command}")

        if attached:
            self._log(
                f"[#13e7ff]ATTACH[/] {len(attached)} archivo(s) disponible(s)"
            )

        # -----------------------------------------------------
        # PROJECT MODE
        # -----------------------------------------------------
        # Comandos locales: no pasan por Ollama ni por AgentBridge.
        # Si hay una confirmación de herramienta pendiente,
        # se respeta primero el flujo de confirmación.
        # -----------------------------------------------------
        raw_command = event.value.strip()

        is_project_command = (
            raw_command == "/project"
            or raw_command.startswith("/project ")
        )

        if (
            is_project_command
            and getattr(
                self.bridge,
                "_pending_confirm",
                None,
            ) is None
        ):
            from core.project_commands import project_commands
            from rich.markup import escape

            result = project_commands.handle(raw_command)

            self._log(
                "[bold #13e7ff]PROJECT[/]\n"
                + escape(result)
            )

            return

        self.bridge.process(command_for_agent)

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
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "attach":
            self.action_attach_files()

    def action_attach_files(self) -> None:
        files = choose_files_macos()
        if not files:
            return

        existing = set()

        for path in self._attached_files:
            try:
                existing.add(path.resolve())
            except Exception:
                existing.add(path)

        for path in files:
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path

            if resolved not in existing:
                self._attached_files.append(path)
                existing.add(resolved)

        self._update_attachments()
        self.query_one("#command", Input).focus()

    def _update_attachments(self) -> None:
        widget = self.query_one("#attachments", Static)

        if not self._attached_files:
            widget.update("")
            return

        content = Text("ADJUNTOS", style="#13e7ff")

        for path in self._attached_files:
            content.append("\n• ", style="#9cb0bf")
            content.append(path.name, style="#9cb0bf")

        widget.update(content)

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
            f"MODEL     [#13e7ff]{(CONFIG.get('models') or {}).get('chat', 'maid:latest')}[/]\n"
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
