#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"

FILE="interface/tui.py"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP="${FILE}.backup_attach_${STAMP}"

echo "=============================================="
echo " YUNA // INSTALACIÓN DE ADJUNTOS"
echo "=============================================="
echo

if [[ ! -f "$FILE" ]]; then
    echo "ERROR: no existe $FILE"
    exit 1
fi

echo "→ Creando respaldo:"
echo "  $BACKUP"
cp "$FILE" "$BACKUP"

echo "→ Verificando estructura actual..."

grep -q 'from textual.widgets import' "$FILE" || {
    echo "ERROR: no encontré los imports de Textual."
    exit 1
}

grep -q 'def on_input_submitted' "$FILE" || {
    echo "ERROR: no encontré on_input_submitted()."
    exit 1
}

grep -q 'id="command"' "$FILE" || {
    echo "ERROR: no encontré el Input #command."
    exit 1
}

echo "✓ Estructura reconocida"
echo

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
    "import os"
)

replace_once(
    "from textual.widgets import Footer, Header, Input, RichLog, ProgressBar, Static\n",
    "from textual.widgets import Button, Footer, Header, Input, RichLog, ProgressBar, Static\n",
    "widgets Textual"
)

# ------------------------------------------------------------
# 2. Selector nativo de archivos macOS
# ------------------------------------------------------------

anchor = "class AvatarWidget(Static):\n"

if "def choose_files_macos()" not in s:
    helper = """def choose_files_macos() -> list[Path]:
    # Abre el selector nativo de archivos de macOS.
    if sys.platform != "darwin":
        return []

    script = r'''
set selectedFiles to choose file with prompt "Adjuntar archivos a Yuna" with multiple selections allowed
set output to ""
repeat with selectedFile in selectedFiles
    set output to output & (POSIX path of selectedFile) & linefeed
end repeat
return output
'''

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


"""
    if anchor not in s:
        raise SystemExit("ERROR: no encontré AvatarWidget para insertar helper.")
    s = s.replace(anchor, helper + anchor, 1)

# ------------------------------------------------------------
# 3. CSS para adjuntos y botón +
# ------------------------------------------------------------

css_anchor = '#command { height: 3; margin-top: 1; border: solid #ff2ed1; background: #070811; color: #ffffff; }\n'

css_new = css_anchor + '''#attachments {
    height: auto;
    min-height: 1;
    max-height: 4;
    margin-top: 1;
    color: #9cb0bf;
    padding: 0 1;
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
    margin-top: 0;
}
'''

replace_once(
    css_anchor,
    css_new,
    "CSS #command"
)

# ------------------------------------------------------------
# 4. Binding opcional Ctrl+O
# ------------------------------------------------------------

binding_anchor = '        Binding("escape", "focus_command", "FOCUS"),\n'

replace_once(
    binding_anchor,
    '        Binding("escape", "focus_command", "FOCUS"),\n'
    '        Binding("ctrl+o", "attach_files", "ATTACH"),\n',
    "binding escape"
)

# ------------------------------------------------------------
# 5. Estado de archivos adjuntos
# ------------------------------------------------------------

init_anchor = "        self._turns = 0\n"

replace_once(
    init_anchor,
    "        self._turns = 0\n"
    "        self._attached_files: list[Path] = []\n",
    "estado _attached_files"
)

# ------------------------------------------------------------
# 6. Reemplazar Input por fila con botón +
# ------------------------------------------------------------

old_input = '''    yield Input(
        placeholder="> instrucción para Yuna... (/chat /agent /voz /clear /salir)",
        id="command",
    )
'''

new_input = '''    yield Static("", id="attachments")
    with Horizontal(id="command-row"):
        yield Button("+", id="attach", flat=True, compact=True)
        yield Input(
            placeholder="> instrucción para Yuna... (/chat /agent /voz /clear /salir)",
            id="command",
        )
'''

replace_once(
    old_input,
    new_input,
    "Input #command"
)

# ------------------------------------------------------------
# 7. Handler del botón
# ------------------------------------------------------------

handler_anchor = "    def on_input_submitted(self, event: Input.Submitted) -> None:\n"

button_handler = '''    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "attach":
            self.action_attach_files()

'''

replace_once(
    handler_anchor,
    button_handler + handler_anchor,
    "on_input_submitted"
)

# ------------------------------------------------------------
# 8. Métodos de adjuntos
# ------------------------------------------------------------

methods_anchor = "    def action_focus_command(self) -> None:\n"

methods = '''    def action_attach_files(self) -> None:
        files = choose_files_macos()

        if not files:
            return

        existing = set()

        for path in self._attached_files:
            try:
                existing.add(path.expanduser().resolve())
            except Exception:
                existing.add(path.expanduser())

        added = []

        for path in files:
            try:
                resolved = path.expanduser().resolve()
            except Exception:
                resolved = path.expanduser()

            if not resolved.exists() or not resolved.is_file():
                continue

            if resolved in existing:
                continue

            self._attached_files.append(resolved)
            existing.add(resolved)
            added.append(resolved)

        if not added:
            return

        self._update_attachments()

        names = ", ".join(path.name for path in added)

        self._log(
            f"[#13e7ff]ATTACH[/] "
            f"{len(added)} archivo(s): {names}"
        )

        self.query_one("#command", Input).focus()

    def _update_attachments(self) -> None:
        widget = self.query_one("#attachments", Static)

        if not self._attached_files:
            widget.update("")
            return

        shown = self._attached_files[:3]

        lines = [
            f"[#13e7ff]📎 {len(self._attached_files)} adjunto(s)[/]"
        ]

        lines.extend(
            f"  [#94a6b4]{path.name}[/]"
            for path in shown
        )

        remaining = len(self._attached_files) - len(shown)

        if remaining > 0:
            lines.append(
                f"  [#647a8a]+ {remaining} más[/]"
            )

        widget.update("\\n".join(lines))

'''

replace_once(
    methods_anchor,
    methods + methods_anchor,
    "action_focus_command"
)

# ------------------------------------------------------------
# 9. Acción Ctrl+O
# ------------------------------------------------------------

focus_anchor = "    def action_focus_command(self) -> None:\n"

replace_once(
    focus_anchor,
    "    def action_attach_files(self) -> None:\n"
    "        files = choose_files_macos()\n"
    "\n"
    "        if not files:\n"
    "            return\n"
    "\n"
    "        existing = {\n"
    "            path.expanduser().resolve()\n"
    "            for path in self._attached_files\n"
    "        }\n"
    "\n"
    "        for path in files:\n"
    "            try:\n"
    "                resolved = path.expanduser().resolve()\n"
    "            except Exception:\n"
    "                resolved = path.expanduser()\n"
    "\n"
    "            if resolved.exists() and resolved.is_file() and resolved not in existing:\n"
    "                self._attached_files.append(resolved)\n"
    "                existing.add(resolved)\n"
    "\n"
    "        self._update_attachments()\n"
    "        self.query_one('#command', Input).focus()\n"
    "\n"
    + focus_anchor,
    "action_focus_command"
)

# ------------------------------------------------------------
# 10. El bloque anterior creó dos action_attach_files.
#     Conservamos el primero, más completo.
# ------------------------------------------------------------

first = s.find("    def action_attach_files(self) -> None:\n")
second = s.find(
    "    def action_attach_files(self) -> None:\n",
    first + 1
)

if first != -1 and second != -1:
    end_second = s.find(
        "    def action_focus_command(self) -> None:\n",
        second
    )

    if end_second == -1:
        raise SystemExit(
            "ERROR: no pude delimitar action_attach_files duplicado."
        )

    s = s[:second] + s[end_second:]

# ------------------------------------------------------------
# 11. Integrar adjuntos en on_input_submitted
# ------------------------------------------------------------

old_process = '''    self._turns += 1
    self._log(f"\\n[#ff2ed1]YOU[/]  > {command}")
    self.bridge.process(command)
'''

new_process = '''    attached = list(self._attached_files)

    self._turns += 1
    self._log(f"\\n[#ff2ed1]YOU[/]  > {command}")

    if attached:
        attachment_block = "\\n".join(
            f"- {path}"
            for path in attached
        )

        command_for_agent = (
            f"{command}\\n\\n"
            "ARCHIVOS ADJUNTOS DISPONIBLES:\\n"
            f"{attachment_block}\\n\\n"
            "Usa las herramientas de archivos apropiadas "
            "para analizar los adjuntos cuando sea necesario."
        )

        self._attached_files.clear()
        self._update_attachments()
    else:
        command_for_agent = command

    self.bridge.process(command_for_agent)
'''

replace_once(
    old_process,
    new_process,
    "procesamiento del comando"
)

# ------------------------------------------------------------
# 12. Actualizar contador real de herramientas
# ------------------------------------------------------------

s = s.replace(
    "TOOLS [#ffe66d]07",
    "TOOLS [#ffe66d]17"
)

# ------------------------------------------------------------
# 13. Escribir
# ------------------------------------------------------------

p.write_text(s)

print("✓ interface/tui.py actualizado")
PY

echo
echo "→ Verificando sintaxis con el Python del proyecto..."
.venv/bin/python -m py_compile interface/tui.py

echo "✓ Sintaxis correcta"

echo
echo "→ Comprobando cambios..."
git diff --check

echo
echo "=============================================="
echo " INSTALACIÓN COMPLETADA"
echo "=============================================="
echo
echo "Backup:"
echo "  $BACKUP"
echo
echo "Archivo modificado:"
echo "  $FILE"
echo
echo "Siguiente paso:"
echo "  .venv/bin/python -m interface.tui"
echo
echo "También puedes usar:"
echo "  Ctrl+O  → seleccionar archivos"
echo "  +       → seleccionar archivos"
echo
echo "IMPORTANTE:"
echo "  No se modificó Avatar.png"
echo "  No se instalaron dependencias"
echo
