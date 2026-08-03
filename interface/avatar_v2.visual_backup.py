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


BG = "#0b0b12"
PANEL = "#12121c"
PANEL_2 = "#181824"
ACCENT = "#8b5cf6"
ACCENT_HOVER = "#7c3aed"
TEXT = "#f5f3ff"
MUTED = "#9b98aa"
SUCCESS = "#34d399"


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
        self.app.geometry("390x620+70+120")
        self.app.minsize(350, 560)

        self.app.configure(
            fg_color=BG
        )

        self.app.attributes(
            "-topmost",
            True
        )

        self.app.attributes(
            "-alpha",
            0.98
        )

        self.app.overrideredirect(True)

        self.frames = []
        self.frame_idx = 0

        self._drag_x = 0
        self._drag_y = 0

        self._build_titlebar()
        self._build_header()
        self._build_avatar(img_path)
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
    # TITLE BAR
    # ========================================================

    def _build_titlebar(self):

        bar = ctk.CTkFrame(
            self.app,
            fg_color=BG,
            corner_radius=0,
            height=34,
        )

        bar.pack(
            fill="x",
            padx=10,
            pady=(8, 0),
        )

        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar,
            text="YUNA",
            font=("Helvetica", 11, "bold"),
            text_color=MUTED,
        ).pack(
            side="left",
            padx=8,
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
            padx=28,
            pady=(8, 0),
        )

        ctk.CTkLabel(
            header,
            text="Yuna",
            font=("Helvetica", 26, "bold"),
            text_color=TEXT,
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            header,
            text="✦",
            font=("Helvetica", 20),
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
            corner_radius=28,
            width=334,
            height=300,
        )

        self.avatar_card.pack(
            fill="x",
            padx=28,
            pady=(18, 14),
        )

        self.avatar_card.pack_propagate(False)

        if not img_path:

            ctk.CTkLabel(
                self.avatar_card,
                text="Y",
                font=("Helvetica", 92, "bold"),
                text_color=ACCENT,
            ).pack(
                expand=True
            )

            return

        img_original = Image.open(img_path)

        max_size = 250

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
            padx=32,
            pady=(0, 16),
        )

        ctk.CTkLabel(
            row,
            text="●",
            font=("Helvetica", 13),
            text_color=SUCCESS,
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            row,
            text="  Agente activo",
            font=("Helvetica", 13, "bold"),
            text_color=TEXT,
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            row,
            text="Qwen",
            font=("Helvetica", 11),
            text_color=MUTED,
        ).pack(
            side="right"
        )


    # ========================================================
    # ACTIONS
    # ========================================================

    def _build_actions(self):

        title = ctk.CTkLabel(
            self.app,
            text="ACCIONES RÁPIDAS",
            font=("Helvetica", 11, "bold"),
            text_color=MUTED,
            anchor="w",
        )

        title.pack(
            fill="x",
            padx=32,
            pady=(0, 8),
        )

        actions = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
        )

        actions.pack(
            fill="x",
            padx=28,
        )

        self._button(
            actions,
            "💬",
            "Chat",
            "Conversación normal",
            abrir_chat,
        )

        self._button(
            actions,
            "🤖",
            "Agente",
            "Herramientas y automatización",
            abrir_agente,
            accent=True,
        )

        self._button(
            actions,
            "🧠",
            "Aprender",
            "Entrenamiento y memoria",
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

        frame = ctk.CTkFrame(
            parent,
            fg_color=PANEL_2,
            corner_radius=16,
            height=58,
        )

        frame.pack(
            fill="x",
            pady=4,
        )

        frame.pack_propagate(False)

        ctk.CTkLabel(
            frame,
            text=icon,
            font=("Helvetica", 19),
            text_color=(
                ACCENT if accent
                else TEXT
            ),
            width=42,
        ).pack(
            side="left",
            padx=(8, 0),
        )

        text_frame = ctk.CTkFrame(
            frame,
            fg_color="transparent",
        )

        text_frame.pack(
            side="left",
            fill="both",
            expand=True,
        )

        ctk.CTkLabel(
            text_frame,
            text=title,
            font=("Helvetica", 12, "bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(
            fill="x",
            pady=(8, 0),
        )

        ctk.CTkLabel(
            text_frame,
            text=subtitle,
            font=("Helvetica", 10),
            text_color=MUTED,
            anchor="w",
        ).pack(
            fill="x"
        )

        ctk.CTkButton(
            frame,
            text="›",
            width=34,
            height=34,
            corner_radius=17,
            fg_color=(
                ACCENT
                if accent
                else "#252535"
            ),
            hover_color=ACCENT_HOVER,
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
        )

        footer.pack(
            fill="x",
            padx=28,
            pady=(12, 14),
        )

        ctk.CTkLabel(
            footer,
            text="Yuna AI  •  Local",
            font=("Helvetica", 10),
            text_color="#6f6b7d",
        ).pack(
            side="left"
        )

        ctk.CTkButton(
            footer,
            text="Cerrar",
            width=70,
            height=28,
            corner_radius=14,
            fg_color="transparent",
            hover_color="#25151a",
            text_color="#9f7b83",
            font=("Helvetica", 10),
            command=self.cerrar_yuna,
        ).pack(
            side="right"
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
