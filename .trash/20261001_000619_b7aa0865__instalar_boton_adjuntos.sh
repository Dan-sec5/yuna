#!/bin/bash
set -euo pipefail

FILE="interface/tui.py"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="interface/tui.py.backup_plus_${STAMP}"

cp "$FILE" "$BACKUP"
echo "Backup: $BACKUP"

python3 - <<'PY'
from pathlib import Path

p = Path("interface/tui.py")
s = p.read_text()

def replace_once(old, new, label):
    global s
    count = s.count(old)
    if count != 1:
        raise SystemExit(
            f"ERROR: esperaba exactamente 1 coincidencia para {label}, encontré {count}"
        )
    s = s.replace(old, new, 1)

# ------------------------------------------------------------
# 1. Imports
# ------------------------------------------------------------

replace_once(
    "import os\n",
    "import os\nimport subprocess\n",
    "import subprocess",
)

replace_once(
    "from textual.widgets import Footer, Header, Input, RichLog, ProgressBar, Static\n",
    "from textual.widgets import Button, Footer, Header, Input, RichLog, ProgressBar, Static\n",
    "Button import",
)

# ------------------------------------------------------------
# 2. Selector nativo de archivos macOS
# ------------------------------------------------------------

anchor = "class AvatarWidget(Static):\n"

if s.count(anchor) != 1:
    raise SystemExit(
        f"ERROR: esperaba exactamente 1 clase AvatarWidget, encontré {s.count(anchor)}"
    )

helper = (
    "def choose_files_macos() -> list[Path]:\n"
    "    if sys.platform != \"darwin\":\n"
    "        return []\n"
    "\n"
    "    script = (\n"
    "        'set selectedFiles to choose file with prompt \"Adjuntar archivos a Yuna\" '\n"
    "        'with multiple selections allowed\\n'\n"
    "        'set output to \"\"\\n'\n"
    "        'repeat with selectedFile in selectedFiles\\n'\n"
    "        'set output to output & (POSIX path of selectedFile) & linefeed\\n'\n"
    "        'end repeat\\n'\n"
    "        'return output'\n"
    "    )\n"
    "\n"
    "    try:\n"
    "        result = subprocess.run(\n"
    "            [\"osascript\", \"-e\", script],\n"
    "            capture_output=True,\n"
    "            text=True,\n"
    "            check=False,\n"
    "        )\n"
    "    except Exception:\n"
    "        return []\n"
    "\n"
    "    if result.returncode != 0:\n"
    "        return []\n"
    "\n"
    "    return [\n"
    "        Path(line.strip())\n"
    "        for line in result.stdout.splitlines()\n"
    "        if line.strip()\n"
    "    ]\n"
    "\n\n"
)

s = s.replace(anchor, helper + anchor, 1)

# ------------------------------------------------------------
# 3. Estado de archivos adjuntos
# ------------------------------------------------------------

replace_once(
    "        self._turns = 0\n",
    "        self._turns = 0\n"
    "        self._attached_files: list[Path] = []\n",
    "estado _attached_files",
)

# ------------------------------------------------------------
# 4. CSS
# ------------------------------------------------------------

old_css = """#command {
    height: 3;
    margin-top: 1;
    border: solid #ff2ed1;
    background: #070811;
    color: #ffffff;
}"""

new_css = """#attachments {
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
}"""

replace_once(old_css, new_css, "CSS #command")

# ------------------------------------------------------------
# 5. Input + botón +
# ------------------------------------------------------------

old_input = """            yield Input(
                placeholder="> instrucción para Yuna... (/chat /agent /voz /clear /salir)",
                id="command",
            )"""

new_input = """            yield Static("", id="attachments")
            with Horizontal(id="command-row"):
                yield Button("+", id="attach", flat=True, compact=True)
                yield Input(
                    placeholder="> instrucción para Yuna... (/chat /agent /voz /clear /salir)",
                    id="command",
                )"""

replace_once(old_input, new_input, "Input command")

# ------------------------------------------------------------
# 6. Binding Ctrl+O
# ------------------------------------------------------------

old_binding = '    BINDINGS = [\n'

if old_binding in s:
    # Insertamos únicamente si todavía no existe.
    if 'Binding("ctrl+o", "attach_files", "ATTACH")' not in s:
        replace_once(
            old_binding,
            '    BINDINGS = [\n'
            '        Binding("ctrl+o", "attach_files", "ATTACH"),\n',
            "BINDINGS",
        )
else:
    raise SystemExit("ERROR: no encontré BINDINGS")

# ------------------------------------------------------------
# 7. Acción del botón
# ------------------------------------------------------------

action_anchor = "    def action_clear_log(self) -> None:\n"

action_code = """    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "attach":
            self.action_attach_files()

    def action_attach_files(self) -> None:
        files = choose_files_macos()
        if not files:
            return

        existing = {path.resolve() for path in self._attached_files}

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

        lines = ["[#13e7ff]ADJUNTOS[/]"]

        for path in self._attached_files:
            lines.append(f"[#9cb0bf]•[/] {path.name}")

        widget.update("\\n".join(lines), markup=True)

"""

replace_once(
    action_anchor,
    action_code + action_anchor,
    "acciones de adjuntos",
)

# ------------------------------------------------------------
# 8. Sustituir on_input_submitted
# ------------------------------------------------------------

old_submit = """    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return
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
        self._turns += 1
        self._log(f"\\n[#ff2ed1]YOU[/]  > {command}")
        self.bridge.process(command)
"""

new_submit = """    def on_input_submitted(self, event: Input.Submitted) -> None:
        command = event.value.strip()
        event.input.value = ""
        if not command:
            return

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

        attached = list(self._attached_files)
        self._attached_files.clear()
        self._update_attachments()

        command_for_agent = command

        if attached:
            command_for_agent += (
                "\\n\\n"
                "ARCHIVOS ADJUNTOS DISPONIBLES:\\n"
                + "\\n".join(f"- {path}" for path in attached)
                + "\\n\\n"
                "Usa las herramientas de archivos apropiadas para analizar "
                "los adjuntos cuando sea necesario."
            )

        self._turns += 1
        self._log(f"\\n[#ff2ed1]YOU[/]  > {command}")

        if attached:
            self._log(
                f"[#13e7ff]ATTACH[/] {len(attached)} archivo(s) disponible(s)"
            )

        self.bridge.process(command_for_agent)
"""

replace_once(
    old_submit,
    new_submit,
    "on_input_submitted",
)

# ------------------------------------------------------------
# 9. Escribir solo cuando TODO salió bien
# ------------------------------------------------------------

p.write_text(s)
print("OK: interface/tui.py actualizado")

PY

echo
echo "== VALIDACION PYTHON =="
.venv/bin/python -m py_compile interface/tui.py

echo
echo "== VALIDACION GIT =="
git diff --check

echo
echo "== CAMBIOS =="
git diff -- interface/tui.py

echo
echo "========================================"
echo "Boton + instalado correctamente."
echo "Backup: $BACKUP"
echo "========================================"
