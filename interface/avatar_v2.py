import os

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
# UI visual desacoplada del backend
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ============================================================
# PALETA
# ============================================================

BG = "#09090f"
SURFACE = "#0d0d13"
SURFACE_HOVER = "#171720"

ACCENT = "#a78bfa"
ACCENT_HOVER = "#ae86ff"
ACCENT_SOFT = "#211735"

TEXT = "#f7f5fc"
TEXT_SECONDARY = "#c8c3d4"
MUTED = "#777284"

SUCCESS = "#43dfa0"

BORDER = "#1c1b25"


# ============================================================
# ESTADOS
# ============================================================

YUNA_STATES = {
    "ready": {
        "symbol": "●",
        "text": "Lista para ayudarte",
        "color": SUCCESS,
    },
    "thinking": {
        "symbol": "◐",
        "text": "Pensando...",
        "color": ACCENT,
    },
    "executing": {
        "symbol": "◉",
        "text": "Ejecutando...",
        "color": ACCENT,
    },
    "done": {
        "symbol": "✓",
        "text": "Listo",
        "color": SUCCESS,
    },
    "offline": {
        "symbol": "○",
        "text": "Desconectada",
        "color": MUTED,
    },
}


# ============================================================
# AVATAR
# ============================================================

def buscar_avatar():
    for patron in (
        "avatar.gif",
        "avatar.png",
        "avatar.jpg",
        "avatar.jpeg",
        "avatar.webp",
    ):
        ruta = os.path.expanduser(f"~/yuna/{patron}")

        if os.path.exists(ruta):
            return ruta

    return None


# ============================================================
# YUNA
# ============================================================

class YunaAvatar:

    def __init__(self):

        self.app = ctk.CTk()

        self.app.title("Yuna")
        self.app.geometry("390x680+70+90")
        self.app.minsize(360, 600)

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

        self.current_status = "ready"

        self._drag_x = 0
        self._drag_y = 0

        self._build_topbar()
        self._build_identity()
        self._build_avatar(
            buscar_avatar()
        )
        self._build_status()
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
    # TOP BAR
    # ========================================================

    def _build_topbar(self):

        bar = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
            height=38,
        )

        bar.pack(
            fill="x",
            padx=18,
            pady=(12, 0),
        )

        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text="YUNA",
            font=("Helvetica", 11, "bold"),
            text_color=MUTED,
        ).pack(
            side="left",
            padx=5,
        )

        ctk.CTkButton(
            bar,
            text="×",
            width=30,
            height=30,
            corner_radius=15,
            fg_color="transparent",
            hover_color="#24171e",
            text_color=MUTED,
            font=("Helvetica", 18),
            command=self.cerrar_yuna,
        ).pack(
            side="right"
        )


    # ========================================================
    # IDENTITY
    # ========================================================

    def _build_identity(self):

        identity = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
        )

        identity.pack(
            fill="x",
            padx=28,
            pady=(8, 0),
        )

        ctk.CTkLabel(
            identity,
            text="Yuna",
            font=("Helvetica", 30, "bold"),
            text_color=TEXT,
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            identity,
            text="✦",
            font=("Helvetica", 19),
            text_color=ACCENT,
        ).pack(
            side="right",
            padx=4,
        )


    # ========================================================
    # AVATAR
    # ========================================================

    def _build_avatar(self, img_path):

        self.avatar_area = ctk.CTkFrame(
            self.app,
            fg_color=SURFACE,
            corner_radius=30,
            border_width=1,
            border_color=BORDER,
            height=310,
        )

        self.avatar_area.pack(
            fill="x",
            padx=24,
            pady=(22, 14),
        )

        self.avatar_area.pack_propagate(False)

        if not img_path:

            ctk.CTkLabel(
                self.avatar_area,
                text="Y",
                font=("Helvetica", 100, "bold"),
                text_color=ACCENT,
            ).pack(
                expand=True
            )

            return

        try:

            original = Image.open(img_path)

            max_size = 270

            ratio = min(
                max_size / original.width,
                max_size / original.height,
            )

            size = (
                max(1, int(original.width * ratio)),
                max(1, int(original.height * ratio)),
            )

            self.es_gif = img_path.lower().endswith(".gif")

            if self.es_gif:

                gif = Image.open(img_path)

                try:

                    while True:

                        frame = (
                            gif.copy()
                            .convert("RGBA")
                            .resize(
                                size,
                                Image.LANCZOS,
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
                        self.avatar_area,
                        image=self.frames[0],
                        text="",
                        fg_color="transparent",
                    )

                    self.label_img.pack(
                        expand=True
                    )

                    self.animar()

                    return

            image = (
                original
                .convert("RGBA")
                .resize(
                    size,
                    Image.LANCZOS,
                )
            )

            photo = ctk.CTkImage(
                image,
                image,
                size=size,
            )

            self.label_img = ctk.CTkLabel(
                self.avatar_area,
                image=photo,
                text="",
                fg_color="transparent",
            )

            self.label_img.pack(
                expand=True
            )

        except Exception:

            ctk.CTkLabel(
                self.avatar_area,
                text="Y",
                font=("Helvetica", 100, "bold"),
                text_color=ACCENT,
            ).pack(
                expand=True
            )


    def animar(self):

        if not self.frames:
            return

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
            height=28,
        )

        row.pack(
            fill="x",
            padx=30,
            pady=(0, 18),
        )

        row.pack_propagate(False)

        self.status_symbol = ctk.CTkLabel(
            row,
            text="●",
            font=("Helvetica", 9, "bold"),
            text_color=SUCCESS,
            width=12,
        )

        self.status_symbol.pack(
            side="left"
        )

        self.status_label = ctk.CTkLabel(
            row,
            text="Lista para ayudarte",
            font=("Helvetica", 11),
            text_color=TEXT_SECONDARY,
            anchor="w",
        )

        self.status_label.pack(
            side="left",
            padx=(5, 0),
        )

        ctk.CTkLabel(
            row,
            text="Qwen",
            font=("Helvetica", 9),
            text_color=MUTED,
        ).pack(
            side="right"
        )

        self.set_status("ready")


    def set_status(self, state):

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
                text=config["text"]
            )


    # ========================================================
    # ACTIONS
    # ========================================================

    def _build_actions(self):

        ctk.CTkLabel(
            self.app,
            text="ACCIONES",
            font=("Helvetica", 9, "bold"),
            text_color=MUTED,
            anchor="w",
        ).pack(
            fill="x",
            padx=30,
            pady=(0, 7),
        )

        actions = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
        )

        actions.pack(
            fill="x",
            padx=24,
        )

        self._button(
            actions,
            "◌",
            "Chat",
            "Hablar con Yuna",
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

        normal = (
            ACCENT_SOFT
            if accent
            else SURFACE
        )

        border = (
            "#33244d"
            if accent
            else BORDER
        )

        frame = ctk.CTkFrame(
            parent,
            fg_color=normal,
            corner_radius=18,
            border_width=1,
            border_color=border,
            height=62,
        )

        frame.pack(
            fill="x",
            pady=5,
        )

        frame.pack_propagate(False)

        icon_box = ctk.CTkFrame(
            frame,
            width=38,
            height=38,
            corner_radius=12,
            fg_color=(
                "#32204f"
                if accent
                else "#181820"
            ),
        )

        icon_box.pack(
            side="left",
            padx=(10, 11),
            pady=11,
        )

        icon_box.pack_propagate(False)

        ctk.CTkLabel(
            icon_box,
            text=icon,
            font=("Helvetica", 17, "bold"),
            text_color=(
                ACCENT
                if accent
                else TEXT_SECONDARY
            ),
        ).pack(
            expand=True
        )

        text_frame = ctk.CTkFrame(
            frame,
            fg_color="transparent",
        )

        text_frame.pack(
            side="left",
            fill="both",
            expand=True,
            pady=9,
        )

        ctk.CTkLabel(
            text_frame,
            text=title,
            font=("Helvetica", 11),
            text_color=TEXT,
            anchor="w",
        ).pack(
            fill="x"
        )

        ctk.CTkLabel(
            text_frame,
            text=subtitle,
            font=("Helvetica", 9),
            text_color=MUTED,
            anchor="w",
        ).pack(
            fill="x",
            pady=(2, 0),
        )

        ctk.CTkButton(
            frame,
            text="›",
            width=30,
            height=30,
            corner_radius=15,
            fg_color=(
                ACCENT
                if accent
                else "#1c1c26"
            ),
            hover_color=(
                ACCENT_HOVER
                if accent
                else "#292934"
            ),
            text_color=TEXT,
            font=("Helvetica", 18),
            command=command,
        ).pack(
            side="right",
            padx=10,
        )


    # ========================================================
    # FOOTER
    # ========================================================

    def _build_footer(self):

        footer = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
            height=32,
        )

        footer.pack(
            fill="x",
            padx=28,
            pady=(13, 10),
        )

        footer.pack_propagate(False)

        ctk.CTkLabel(
            footer,
            text="LOCAL  •  YUNA AI",
            font=("Helvetica", 8),
            text_color="#555160",
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            footer,
            text="●",
            font=("Helvetica", 7),
            text_color=SUCCESS,
        ).pack(
            side="right",
            padx=4,
        )


    # ========================================================
    # DRAG
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


# ============================================================
# ENTRY POINT
# ============================================================

def main():
    YunaAvatar()


if __name__ == "__main__":
    main()
