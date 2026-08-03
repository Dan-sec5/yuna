import os
import threading

import customtkinter as ctk
from PIL import Image

from interface.actions import (
    abrir_chat,
    abrir_agente,
    abrir_aprendizaje,
    cerrar_yuna,
)


# ============================================================
# YUNA UI V2
# Prototipo visual
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============================================================
# PALETA VISUAL YUNA
# ============================================================

BG = "#08080d"
SURFACE = "#101017"
PANEL = "#13131c"
PANEL_2 = "#191923"

ACCENT = "#9b6cff"
ACCENT_HOVER = "#8555ed"
ACCENT_SOFT = "#241a3a"

TEXT = "#faf9ff"
TEXT_SECONDARY = "#d2cedf"
MUTED = "#858193"
MUTED_DARK = "#5d5968"

SUCCESS = "#42e6a4"
SUCCESS_SOFT = "#142c25"

BORDER = "#252431"

# ============================================================
# ESTADOS VISUALES DE YUNA
# ============================================================

YUNA_STATES = {
    "ready": {
        "symbol": "●",
        "text": "Yuna está activa",
        "color": SUCCESS,
    },
    "thinking": {
        "symbol": "◐",
        "text": "Yuna está pensando...",
        "color": ACCENT,
    },
    "executing": {
        "symbol": "◉",
        "text": "Yuna está ejecutando...",
        "color": ACCENT,
    },
    "done": {
        "symbol": "✓",
        "text": "Yuna terminó",
        "color": SUCCESS,
    },
    "offline": {
        "symbol": "○",
        "text": "Yuna desconectada",
        "color": MUTED,
    },
}



def buscar_avatar():
    for patron in [
        "avatar.gif",
        "avatar.png",
        "avatar.jpg",
        "avatar.jpeg",
        "avatar.webp",
    ]:
        ruta = os.path.expanduser(f"~/yuna/{patron}")
        if os.path.exists(ruta):
            return ruta

    return None



class YunaAvatar:

    def __init__(self):

        img_path = buscar_avatar()

        self.app = ctk.CTk()

        self.app.title("Yuna")
        self.app.geometry("410x700+70+90")
        self.app.minsize(380, 620)

        self.app.configure(
            fg_color=BG
        )

        self.app.attributes(
            "-topmost",
            True
        )

        self.app.attributes(
            "-alpha",
            0.985
        )

        self.app.overrideredirect(True)

        self.frames = []
        self.frame_idx = 0

        # Estado visual actual de Yuna.
        self.current_status = "ready"

        self._drag_x = 0
        self._drag_y = 0

        self._build_titlebar()
        self._build_header()
        self._build_avatar(img_path)
        self._build_status()
        self.set_status("ready")
        self._build_actions()
        self._build_footer()

        self.app.bind(
            "<Button-1>",
            self._start_drag
        )

        self.app.bind(
            "<B1-Motion>",
            self._drag
        )

        self.app.mainloop()


    # ========================================================
    # TITLE BAR
    # ========================================================

    def _build_titlebar(self):

        bar = ctk.CTkFrame(
            self.app,
            fg_color=BG,
            corner_radius=0,
            height=38,
        )

        bar.pack(
            fill="x",
            padx=10,
            pady=(10, 0),
        )

        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text="YUNA  /  LOCAL",
            font=("Helvetica", 10, "bold"),
            text_color=MUTED,
        ).pack(
            side="left",
            padx=10,
        )

        ctk.CTkButton(
            bar,
            text="×",
            width=30,
            height=28,
            corner_radius=14,
            fg_color="transparent",
            hover_color="#26151b",
            text_color=MUTED,
            font=("Helvetica", 18),
            command=self.cerrar_yuna,
        ).pack(
            side="right"
        )


    # ========================================================
    # HEADER
    # ========================================================

    def _build_header(self):

        header = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
        )

        header.pack(
            fill="x",
            padx=30,
            pady=(14, 0),
        )

        ctk.CTkLabel(
            header,
            text="Yuna",
            font=("Helvetica", 28, "bold"),
            text_color=TEXT,
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            header,
            text="✦",
            font=("Helvetica", 21, "bold"),
            text_color=ACCENT,
        ).pack(
            side="right",
            padx=4,
        )


    # ========================================================
    # AVATAR
    # ========================================================

    def _build_avatar(self, img_path):

        self.avatar_card = ctk.CTkFrame(
            self.app,
            fg_color=PANEL,
            corner_radius=32,
            border_width=1,
            border_color="#211f2b",
            width=350,
            height=330,
        )

        self.avatar_card.pack(
            fill="x",
            padx=30,
            pady=(22, 18),
        )

        self.avatar_card.pack_propagate(False)

        if not img_path:

            ctk.CTkLabel(
                self.avatar_card,
                text="Y",
                font=("Helvetica", 104, "bold"),
                text_color=ACCENT,
            ).pack(
                expand=True
            )

            return

        img_original = Image.open(img_path)

        max_size = 280

        ratio = min(
            max_size / img_original.width,
            max_size / img_original.height,
        )

        size = (
            max(1, int(img_original.width * ratio)),
            max(1, int(img_original.height * ratio)),
        )

        self.es_gif = img_path.lower().endswith(".gif")

        if self.es_gif:

            try:

                gif = Image.open(img_path)

                while True:

                    frame = (
                        gif.copy()
                        .convert("RGBA")
                        .resize(
                            size,
                            Image.LANCZOS
                        )
                    )

                    self.frames.append(
                        ctk.CTkImage(
                            frame,
                            frame,
                            size=size,
                        )
                    )

                    gif.seek(
                        gif.tell() + 1
                    )

            except EOFError:
                pass

            if self.frames:

                self.label_img = ctk.CTkLabel(
                    self.avatar_card,
                    image=self.frames[0],
                    text="",
                    fg_color="transparent",
                )

                self.label_img.pack(
                    expand=True
                )

                self.animar()

                return

        img = (
            img_original
            .convert("RGBA")
            .resize(
                size,
                Image.LANCZOS
            )
        )

        foto = ctk.CTkImage(
            img,
            img,
            size=size,
        )

        self.label_img = ctk.CTkLabel(
            self.avatar_card,
            image=foto,
            text="",
            fg_color="transparent",
        )

        self.label_img.pack(
            expand=True
        )


    def animar(self):

        if self.frames:

            self.frame_idx = (
                self.frame_idx + 1
            ) % len(self.frames)

            self.label_img.configure(
                image=self.frames[self.frame_idx]
            )

            self.app.after(
                80,
                self.animar
            )


    # ========================================================
    # STATUS
    # ========================================================

    def _build_status(self):

        row = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
        )

        row.pack(
            fill="x",
            padx=34,
            pady=(0, 22),
        )

        self.status_symbol = ctk.CTkLabel(
            row,
            text="●",
            font=("Helvetica", 10, "bold"),
            text_color=SUCCESS,
            width=13,
        )

        self.status_symbol.pack(
            side="left",
        )

        self.status_label = ctk.CTkLabel(
            row,
            text="Yuna está activa",
            font=("Helvetica", 11, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w",
        )

        self.status_label.pack(
            side="left",
            padx=(5, 0),
        )

        self.model_label = ctk.CTkLabel(
            row,
            text="Qwen",
            font=("Helvetica", 10),
            text_color=MUTED,
        )

        self.model_label.pack(
            side="right",
        )


    def set_status(self, state: str):
        """
        Cambia únicamente el estado visual de Yuna.

        Esta función es deliberadamente independiente del backend.
        Más adelante core/agent.py podrá comunicar estados mediante
        una capa intermedia sin depender de CustomTkinter.
        """

        if state not in YUNA_STATES:
            state = "ready"

        config = YUNA_STATES[state]

        self.current_status = state

        if hasattr(self, "status_symbol"):
            self.status_symbol.configure(
                text=config["symbol"],
                text_color=config["color"],
            )

        if hasattr(self, "status_label"):
            self.status_label.configure(
                text=config["text"],
            )

    # ========================================================
    # ACTIONS
    # ========================================================

    def _build_actions(self):

        title = ctk.CTkLabel(
            self.app,
            text="ACCIONES RÁPIDAS",
            font=("Helvetica", 10, "bold"),
            text_color=MUTED,
            anchor="w",
        )

        title.pack(
            fill="x",
            padx=34,
            pady=(0, 8),
        )

        actions = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
        )

        actions.pack(
            fill="x",
            padx=30,
        )

        self._button(
            actions,
            "◌",
            "Chat",
            "Conversación con Yuna",
            abrir_chat,
        )

        self._button(
            actions,
            "◈",
            "Agente",
            "Herramientas y automatización",
            abrir_agente,
            accent=True,
        )

        self._button(
            actions,
            "✦",
            "Aprender",
            "Memoria y aprendizaje",
            abrir_aprendizaje,
        )


    def _button(
        self,
        parent,
        icon,
        title,
        subtitle,
        command,
        accent=False,
    ):
        """
        Botón visual principal de Yuna.

        La acción recibida por command pertenece a interface.actions.
        Esta función solo controla presentación e interacción visual.
        """

        normal = ACCENT_SOFT if accent else PANEL_2
        hover = "#30244b" if accent else "#20202b"
        border = "#382957" if accent else BORDER

        frame = ctk.CTkFrame(
            parent,
            fg_color=normal,
            corner_radius=18,
            border_width=1,
            border_color=border,
            height=66,
        )

        frame.pack(
            fill="x",
            pady=5,
        )

        frame.pack_propagate(False)

        # ----------------------------------------------------
        # Icono
        # ----------------------------------------------------

        icon_box = ctk.CTkFrame(
            frame,
            width=40,
            height=40,
            corner_radius=12,
            fg_color=(
                "#33244f" if accent
                else "#22222d"
            ),
        )

        icon_box.pack(
            side="left",
            padx=(10, 11),
            pady=12,
        )

        icon_box.pack_propagate(False)

        icon_label = ctk.CTkLabel(
            icon_box,
            text=icon,
            font=("Helvetica", 17, "bold"),
            text_color=(
                ACCENT if accent
                else TEXT_SECONDARY
            ),
        )

        icon_label.pack(
            expand=True
        )

        # ----------------------------------------------------
        # Texto
        # ----------------------------------------------------

        text_frame = ctk.CTkFrame(
            frame,
            fg_color="transparent",
        )

        text_frame.pack(
            side="left",
            fill="both",
            expand=True,
            pady=10,
        )

        ctk.CTkLabel(
            text_frame,
            text=title,
            font=("Helvetica", 11, "bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(
            fill="x",
        )

        ctk.CTkLabel(
            text_frame,
            text=subtitle,
            font=("Helvetica", 9),
            text_color=MUTED,
            anchor="w",
        ).pack(
            fill="x",
            pady=(3, 0),
        )

        # ----------------------------------------------------
        # Acción
        # ----------------------------------------------------

        arrow = ctk.CTkButton(
            frame,
            text="›",
            width=30,
            height=30,
            corner_radius=15,
            fg_color=(
                ACCENT if accent
                else "#242431"
            ),
            hover_color=ACCENT_HOVER,
            text_color=TEXT,
            font=("Helvetica", 19),
            command=command,
        )

        arrow.pack(
            side="right",
            padx=(6, 11),
        )

        # ----------------------------------------------------
        # Hover de toda la superficie
        # ----------------------------------------------------

        widgets = (
            frame,
            icon_box,
            icon_label,
            text_frame,
        )

        def enter(_event=None):
            frame.configure(
                fg_color=hover
            )

        def leave(_event=None):
            frame.configure(
                fg_color=normal
            )

        def activate(_event=None):
            command()

        for widget in widgets:
            widget.bind(
                "<Enter>",
                enter,
                add="+",
            )

            widget.bind(
                "<Leave>",
                leave,
                add="+",
            )

            widget.bind(
                "<Button-1>",
                activate,
                add="+",
            )


    # ========================================================
    # FOOTER
    # ========================================================

    def _build_footer(self):

        footer = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
            height=34,
        )

        footer.pack(
            fill="x",
            padx=30,
            pady=(14, 16),
        )

        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text="Yuna AI",
            font=("Helvetica", 9, "bold"),
            text_color=MUTED,
        ).pack(
            side="left",
        )

        ctk.CTkLabel(
            footer,
            text="LOCAL",
            font=("Helvetica", 8, "bold"),
            text_color=MUTED_DARK,
        ).pack(
            side="left",
            padx=(7, 0),
        )

        ctk.CTkButton(
            footer,
            text="Cerrar",
            width=62,
            height=26,
            corner_radius=13,
            fg_color="transparent",
            hover_color="#25171d",
            text_color=MUTED,
            font=("Helvetica", 9),
            command=self.cerrar_yuna,
        ).pack(
            side="right",
        )


    # ========================================================
    # DRAG WINDOW
    # ========================================================

    def _start_drag(self, event):

        self._drag_x = event.x
        self._drag_y = event.y


    def _drag(self, event):

        x = (
            self.app.winfo_x()
            + event.x
            - self._drag_x
        )

        y = (
            self.app.winfo_y()
            + event.y
            - self._drag_y
        )

        self.app.geometry(
            f"+{x}+{y}"
        )


    # ========================================================
    # CLOSE
    # ========================================================

    def cerrar_yuna(self):
        cerrar_yuna()
        self.app.destroy()


def main():
    YunaAvatar()


if __name__ == "__main__":
    main()
