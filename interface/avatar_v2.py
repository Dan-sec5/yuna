import os
import customtkinter as ctk
from PIL import Image
from interface.actions import (
    abrir_chat,
    abrir_agente,
    abrir_aprendizaje,
    cerrar_yuna,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── PALETA RETRO-GAME ────────────────────────────────────────
BG       = "#0d0d1a"
SURFACE  = "#13132b"
PANEL    = "#1a1a38"
PANEL2   = "#0f0f22"

BLUE     = "#4fc3f7"
BLUE_DIM = "#1a6a8a"
BLUE_BG  = "#0a1929"
BLUE_HVR = "#29b6f6"

GOLD     = "#ffd700"
GOLD_DIM = "#997a00"
GOLD_BG  = "#1a1500"

RED      = "#ff5252"
GREEN    = "#69ff47"
GREEN_DIM= "#256b12"

TEXT     = "#ffffff"
TEXT2    = "#b0bec5"
MUTED    = "#546e7a"
BORDER   = "#2a2a50"
BORDER_B = "#4fc3f7"

# fuente limpia tipo juego
F_TITLE  = ("Arial Rounded MT Bold", )
F_BODY   = ("Arial", )
F_MONO   = ("Courier", )

# ── ESTADOS ──────────────────────────────────────────────────
STATES = {
    "ready":     {"sym": "▶", "txt": "Lista",       "col": GREEN, "bar": GREEN},
    "thinking":  {"sym": "◆", "txt": "Pensando...", "col": GOLD,  "bar": GOLD},
    "executing": {"sym": "◆", "txt": "Ejecutando",  "col": BLUE,  "bar": BLUE},
    "done":      {"sym": "★", "txt": "Listo",        "col": GREEN, "bar": GREEN},
    "offline":   {"sym": "◯", "txt": "Desconectada","col": MUTED, "bar": MUTED},
}

def buscar_avatar():
    for ext in ("avatar.gif","avatar.png","avatar.jpg","avatar.jpeg","avatar.webp"):
        p = os.path.expanduser(f"~/yuna/{ext}")
        if os.path.exists(p):
            return p
    return None

# ── CLASE PRINCIPAL ──────────────────────────────────────────
class YunaAvatar:

    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("YUNA")
        self.app.geometry("300x660+70+90")
        self.app.minsize(280, 580)
        self.app.configure(fg_color=BG)
        self.app.attributes("-topmost", True)
        self.app.attributes("-alpha", 0.97)
        self.app.overrideredirect(True)

        self.frames    = []
        self.frame_idx = 0
        self.current_status = "ready"
        self._drag_x   = 0
        self._drag_y   = 0

        self._topbar()
        self._nametag()
        self._avatar_card(buscar_avatar())
        self._hp_bar()
        self._actions()
        self._footer()

        self.app.bind("<Button-1>", self._start_drag)
        self.app.bind("<B1-Motion>", self._drag)
        self.app.mainloop()

    # ── TOP BAR ──────────────────────────────────────────────
    def _topbar(self):
        bar = ctk.CTkFrame(self.app,
            fg_color=PANEL2, corner_radius=0,
            height=30, border_width=0,
        )
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # dots estilo game
        for col in (RED, GOLD, GREEN):
            ctk.CTkLabel(bar,
                text="●", font=(F_BODY[0], 9),
                text_color=col, width=16,
            ).pack(side="left", padx=(6,0), pady=8)

        ctk.CTkLabel(bar,
            text="YUNA  v3.0",
            font=(F_MONO[0], 9),
            text_color=MUTED,
        ).pack(side="left", padx=6)

        ctk.CTkButton(bar,
            text="✕",
            width=30, height=30,
            corner_radius=0,
            fg_color="transparent",
            hover_color="#2a0010",
            text_color=MUTED,
            font=(F_BODY[0], 12, "bold"),
            command=self.cerrar_yuna,
        ).pack(side="right")

    # ── NAME TAG ─────────────────────────────────────────────
    def _nametag(self):
        wrap = ctk.CTkFrame(self.app,
            fg_color=PANEL,
            corner_radius=0,
            border_width=2,
            border_color=BLUE,
            height=42,
        )
        wrap.pack(fill="x", padx=10, pady=(8, 0))
        wrap.pack_propagate(False)

        ctk.CTkLabel(wrap,
            text="✦  YUNA",
            font=(F_TITLE[0], 16, "bold"),
            text_color=TEXT,
        ).pack(side="left", padx=12)

        badge = ctk.CTkFrame(wrap,
            fg_color=GOLD_BG,
            corner_radius=4,
            border_width=1,
            border_color=GOLD,
        )
        badge.pack(side="right", padx=10, pady=8)

        ctk.CTkLabel(badge,
            text=" LOCAL ",
            font=(F_MONO[0], 9, "bold"),
            text_color=GOLD,
        ).pack(padx=4, pady=1)

    # ── AVATAR CARD ──────────────────────────────────────────
    def _avatar_card(self, img_path):
        # panel con borde grueso estilo game dialog
        outer = ctk.CTkFrame(self.app,
            fg_color=BLUE_DIM,
            corner_radius=8,
            height=276,
        )
        outer.pack(fill="x", padx=10, pady=(6, 0))
        outer.pack_propagate(False)

        inner = ctk.CTkFrame(outer,
            fg_color=PANEL2,
            corner_radius=6,
        )
        inner.pack(fill="both", expand=True, padx=3, pady=3)

        if not img_path:
            ctk.CTkLabel(inner,
                text="?",
                font=(F_TITLE[0], 80, "bold"),
                text_color=BLUE,
            ).pack(expand=True)
            return

        try:
            original = Image.open(img_path)
            max_s = 240
            ratio = min(max_s/original.width, max_s/original.height)
            size = (max(1,int(original.width*ratio)), max(1,int(original.height*ratio)))

            if img_path.lower().endswith(".gif"):
                gif = Image.open(img_path)
                try:
                    while True:
                        f = gif.copy().convert("RGBA").resize(size, Image.LANCZOS)
                        self.frames.append(ctk.CTkImage(f, f, size=size))
                        gif.seek(gif.tell()+1)
                except EOFError:
                    pass
                if self.frames:
                    self.label_img = ctk.CTkLabel(inner, image=self.frames[0], text="", fg_color="transparent")
                    self.label_img.pack(expand=True)
                    self.animar()
                    return

            img = original.convert("RGBA").resize(size, Image.LANCZOS)
            photo = ctk.CTkImage(img, img, size=size)
            self.label_img = ctk.CTkLabel(inner, image=photo, text="", fg_color="transparent")
            self.label_img.pack(expand=True)

        except Exception:
            ctk.CTkLabel(inner, text="?", font=(F_TITLE[0], 80, "bold"), text_color=BLUE).pack(expand=True)

    def animar(self):
        if not self.frames:
            return
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        self.label_img.configure(image=self.frames[self.frame_idx])
        self.app.after(80, self.animar)

    # ── HP BAR (status) ──────────────────────────────────────
    def _hp_bar(self):
        wrap = ctk.CTkFrame(self.app,
            fg_color=PANEL,
            corner_radius=0,
            border_width=1,
            border_color=BORDER,
            height=38,
        )
        wrap.pack(fill="x", padx=10, pady=(4,0))
        wrap.pack_propagate(False)

        # símbolo estado
        self.sym_lbl = ctk.CTkLabel(wrap,
            text="▶", font=(F_BODY[0], 10, "bold"),
            text_color=GREEN, width=18,
        )
        self.sym_lbl.pack(side="left", padx=(8,4))

        self.status_lbl = ctk.CTkLabel(wrap,
            text="Lista",
            font=(F_BODY[0], 10, "bold"),
            text_color=GREEN, anchor="w",
        )
        self.status_lbl.pack(side="left")

        # barra HP
        bar_bg = ctk.CTkFrame(wrap,
            fg_color="#0a0a18",
            corner_radius=3,
            width=80, height=10,
            border_width=1, border_color="#333355",
        )
        bar_bg.pack(side="right", padx=10)
        bar_bg.pack_propagate(False)

        self.hp_fill = ctk.CTkFrame(bar_bg,
            fg_color=GREEN,
            corner_radius=2,
            width=76, height=8,
        )
        self.hp_fill.place(x=2, y=1)

        self.set_status("ready")

    def set_status(self, state):
        if state not in STATES:
            state = "ready"
        self.current_status = state
        cfg = STATES[state]
        if hasattr(self, "sym_lbl"):
            self.sym_lbl.configure(text=cfg["sym"], text_color=cfg["col"])
        if hasattr(self, "status_lbl"):
            self.status_lbl.configure(text=cfg["txt"], text_color=cfg["col"])
        if hasattr(self, "hp_fill"):
            self.hp_fill.configure(fg_color=cfg["bar"])

    # ── ACTIONS ──────────────────────────────────────────────
    def _actions(self):
        # separador decorativo
        sep = ctk.CTkFrame(self.app, fg_color=BORDER, corner_radius=0, height=1)
        sep.pack(fill="x", padx=10, pady=(10,0))

        ctk.CTkLabel(self.app,
            text="▸ ACCIONES",
            font=(F_BODY[0], 9, "bold"),
            text_color=MUTED,
            anchor="w",
        ).pack(fill="x", padx=14, pady=(5,3))

        wrap = ctk.CTkFrame(self.app, fg_color="transparent")
        wrap.pack(fill="x", padx=10)

        BTNS = [
            ("◌", "CHAT",     "Conversación",              abrir_chat,       BLUE,  BLUE_BG,  BLUE_DIM),
            ("◈", "AGENTE",   "Herramientas",              abrir_agente,     GOLD,  GOLD_BG,  GOLD_DIM),
            ("✦", "APRENDER", "Memoria",                   abrir_aprendizaje,GREEN, "#0a1800", GREEN_DIM),
        ]

        for icon, label, sub, cmd, col, bg, bdr in BTNS:
            self._game_btn(wrap, icon, label, sub, cmd, col, bg, bdr)

    def _game_btn(self, parent, icon, label, sub, command, col, bg, bdr):
        # efecto neo-skeuo: borde bottom/right más oscuro, top/left del color
        outer = ctk.CTkFrame(parent,
            fg_color=bdr,
            corner_radius=6,
            height=52,
        )
        outer.pack(fill="x", pady=3)
        outer.pack_propagate(False)

        inner = ctk.CTkFrame(outer,
            fg_color=bg,
            corner_radius=5,
        )
        inner.pack(fill="both", expand=True, padx=(2,3), pady=(2,3))

        # icono
        icon_box = ctk.CTkFrame(inner,
            width=34, height=34,
            corner_radius=6,
            fg_color=BG,
            border_width=1,
            border_color=bdr,
        )
        icon_box.pack(side="left", padx=(8,8), pady=8)
        icon_box.pack_propagate(False)
        ctk.CTkLabel(icon_box,
            text=icon, font=(F_BODY[0], 14, "bold"),
            text_color=col,
        ).pack(expand=True)

        # texto
        txt = ctk.CTkFrame(inner, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True, pady=8)
        ctk.CTkLabel(txt,
            text=label, font=(F_BODY[0], 11, "bold"),
            text_color=TEXT, anchor="w",
        ).pack(fill="x")
        ctk.CTkLabel(txt,
            text=sub, font=(F_BODY[0], 9),
            text_color=MUTED, anchor="w",
        ).pack(fill="x")

        # botón ›
        ctk.CTkButton(inner,
            text="›",
            width=26, height=26,
            corner_radius=5,
            fg_color=BG,
            hover_color=bdr,
            border_width=1,
            border_color=bdr,
            text_color=col,
            font=(F_BODY[0], 14, "bold"),
            command=command,
        ).pack(side="right", padx=8)

    # ── FOOTER ───────────────────────────────────────────────
    def _footer(self):
        f = ctk.CTkFrame(self.app,
            fg_color=PANEL2,
            corner_radius=0,
            height=24,
            border_width=1,
            border_color=BORDER,
        )
        f.pack(fill="x", padx=10, pady=(8,10))
        f.pack_propagate(False)

        ctk.CTkLabel(f,
            text="◆ OLLAMA  ◆ LOCAL  ◆ YUNA AI",
            font=(F_MONO[0], 8),
            text_color=MUTED,
        ).pack(expand=True)

    # ── DRAG ─────────────────────────────────────────────────
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag(self, event):
        x = self.app.winfo_x() + event.x - self._drag_x
        y = self.app.winfo_y() + event.y - self._drag_y
        self.app.geometry(f"+{x}+{y}")

    # ── CLOSE ────────────────────────────────────────────────
    def cerrar_yuna(self):
        cerrar_yuna()
        self.app.destroy()

def main():
    YunaAvatar()

if __name__ == "__main__":
    main()
