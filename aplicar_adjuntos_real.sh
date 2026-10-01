#!/bin/bash
set -euo pipefail

FILE="interface/tui.py"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="interface/tui.py.backup_adjuntos_real_${STAMP}"

cp "$FILE" "$BACKUP"

python3 - <<'PY'
from pathlib import Path

p = Path("interface/tui.py")
s = p.read_text()

def once(old, new, name):
    global s
    n = s.count(old)
    if n != 1:
        raise SystemExit(
            f"ERROR: {name}: esperaba 1 coincidencia, encontré {n}"
        )
    s = s.replace(old, new, 1)

# ------------------------------------------------------------
# IMPORTS
# ------------------------------------------------------------

if "import subprocess\n" not in s:
    once(
        "import os\n",
        "import os\nimport subprocess\n",
        "import subprocess",
    )

if "from textual.widgets import Button," not in s:
    once(
        "from textual.widgets import Footer, Header, Input, RichLog, ProgressBar, Static\n",
        "from textual.widgets import Button, Footer, Header, Input, RichLog, ProgressBar, Static\n",
        "Button",
    )

# ------------------------------------------------------------
# SELECTOR NATIVO macOS
# ------------------------------------------------------------

if "def choose_files_macos() -> list[Path]:" not in s:
    anchor = "class AvatarWidget(Static):\n"

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

    once(anchor, helper + anchor, "selector macOS")

# ------------------------------------------------------------
# ESTADO DE ADJUNTOS
# ------------------------------------------------------------

if "self._attached_files: list[Path] = []" not in s:
    once(
        "        self._turns = 0\n",
        "        self._turns = 0\n"
        "        self._attached_files: list[Path] = []\n",
        "_attached_files",
    )

# ------------------------------------------------------------
# CSS
# ------------------------------------------------------------

if "#attachments {" not in s:
    old_css = """    #command {
        height: 3;
        margin-top: 1;
        border: solid #ff2ed1;
        background: #070811;
        color: #ffffff;
    }"""

    new_css = """    #attachments {
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

    once(old_css, new_css, "CSS")

# ------------------------------------------------------------
# COMPOSE
# ------------------------------------------------------------

if 'yield Button("+", id="attach"' not in s:
    old_input = """                yield Input(
                    placeholder="> instrucción para Yuna... (/chat /agent /voz /clear /salir)",
                    id="command",
                )"""

    new_input = """                yield Static("", id="attachments")
                with Horizontal(id="command-row"):
                    yield Button("+", id="attach", flat=True, compact=True)
                    yield Input(
                        placeholder="> instrucción para Yuna... (/chat /agent /voz /clear /salir)",
                        id="command",
                    )"""

    once(old_input, new_input, "compose Input")

# ------------------------------------------------------------
# CTRL+O
# ------------------------------------------------------------

if 'Binding("ctrl+o", "attach_files", "ATTACH")' not in s:
    once(
        "    BINDINGS = [\n",
        '    BINDINGS = [\n'
        '        Binding("ctrl+o", "attach_files", "ATTACH"),\n',
        "Ctrl+O",
    )

# ------------------------------------------------------------
# ACCIONES DE ADJUNTOS
# ------------------------------------------------------------

if "def action_attach_files(self) -> None:" not in s:
    anchor = "    def action_clear_log(self) -> None:\n"

    code = """    def on_button_pressed(self, event: Button.Pressed) -> None:
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

        lines = ["[#13e7ff]ADJUNTOS[/]"]

        for path in self._attached_files:
            lines.append(f"[#9cb0bf]•[/] {path.name}")

        widget.update("\\n".join(lines), markup=True)

"""

    once(anchor, code + anchor, "acciones")

# ------------------------------------------------------------
# INPUT SUBMITTED
# ------------------------------------------------------------

if "ARCHIVOS ADJUNTOS DISPONIBLES:" not in s:
    old_normal = """        # Input normal → agente
        self._turns += 1
        self._log(f"\\n[#ff2ed1]YOU[/]  > {command}")
        self.bridge.process(command)
"""

    new_normal = """        # Input normal → agente
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

    once(old_normal, new_normal, "Input normal")

# ------------------------------------------------------------
# ESCRITURA ATÓMICA AL FINAL
# ------------------------------------------------------------

p.write_text(s)

print("OK: adjuntos instalados en interface/tui.py")
PY

echo
echo "=== PYCOMPILE ==="
.venv/bin/python -m py_compile interface/tui.py

echo
echo "=== GIT CHECK ==="
git diff --check

echo
echo "=== CAMBIOS RELEVANTES ==="
git diff -- interface/tui.py | sed -n '1,260p'

echo
echo "Backup: $BACKUP"
echo "========================================"
echo "INSTALACION COMPLETADA"
echo "========================================"
