import os
import customtkinter as ctk
from PIL import Image, ImageDraw
from interface.actions import (
    abrir_chat,
    abrir_agente,
    abrir_aprendizaje,
    cerrar_yuna,
)

ctk.set_appearance_mode("dark")

# ═══════════════════════════════════════════════════════════════
# PALETA: Dark Minimal + Lavender accents
# ═══════════════════════════════════════════════════════════════
BG        = "#0a0a0f"
SURFACE   = "#111118"
SURFACE_H = "#181822"
PANEL     = "#14141c"
BORDER    = "#1e1e2a"
BORDER_H  = "#2a2a3a"

ACCENT    = "#c8a8e0"
ACCENT_H  = "#dcc0f0"
ACCENT_G  = "#1a1520"
ACCENT_G2 = "#201a28"

TEXT      = "#f0eef5"
TEXT_SEC  = "#9b96a8"
TEXT_MUT  = "#5c5868"

STATE_OK  = "#7dd3c0"
STATE_WRN = "#e8c87a"
STATE_AC  = "#c8a8e0"

F_TITLE   = ("Helvetica Neue", 18, "bold")
F_SUB     = ("Helvetica Neue", 11)
F_BODY    = ("Helvetica Neue", 12)
F_CAP     = ("Helvetica Neue", 9)
F_ICON    = ("Helvetica Neue", 14)

STATES = {
    "ready":     {"sym": "●", "txt": "Yuna esta activa",      "col": STATE_OK},
    "thinking":  {"sym": "◐", "txt": "Yuna esta pensando...", "col": STATE_WRN},
    "executing": {"sym": "◉", "txt": "Ejecutando tarea...",   "col": STATE_AC},
    "done":      {"sym": "✓", "txt": "Tarea completada",      "col": STATE_OK},
    "offline":   {"sym": "○", "txt": "Desconectada",          "col": TEXT_MUT},
}

def buscar_avatar():
    for ext in ("avatar.gif", "avatar.png", "avatar.jpg", "avatar.jpeg", "avatar.webp"):
        p = os.path.expanduser(f"~/yuna/{ext}")
        if os.path.exists(p):
            return p
    return None

# ═══════════════════════════════════════════════════════════════
class YunaAvatar:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("Yuna")
        self.app.geometry("340x720+80+80")
        self.app.minsize(320, 600)
        self.app.configure(fg_color=BG)
        self.app.attributes("-topmost", True)
        self.app.attributes("-alpha", 0.0)
        self.app.overrideredirect(True)

        self.frames = []
        self.frame_idx = 0
        self.current_status = "ready"
        self._drag_x = 0
        self._drag_y = 0

        self._build_ui()
        self._fade_in()
        self.app.mainloop()

    def _build_ui(self):
        self.root = ctk.CTkFrame(self.app, fg_color=BG, corner_radius=0)
        self.root.pack(fill="both", expand=True, padx=16, pady=16)

        self._top_bar()
        self._avatar_section(buscar_avatar())
        self._status_pill()
        self._actions_section()
        self._bottom_bar()

        self.app.bind("<Button-1>", self._start_drag)
        self.app.bind("<B1-Motion>", self._drag)
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._drag)

    def _top_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color="transparent", height=28)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        dot = ctk.CTkFrame(bar, width=6, height=6, corner_radius=3, fg_color=ACCENT)
        dot.pack(side="left", pady=11)

        ctk.CTkLabel(bar, text="Yuna", font=F_SUB,
                     text_color=TEXT_SEC).pack(side="left", padx=6)

        close = ctk.CTkButton(bar, text="✕", width=24, height=24,
                              corner_radius=12, fg_color=SURFACE,
                              hover_color="#2a1a2a", text_color=TEXT_SEC,
                              font=F_ICON, command=self.cerrar_yuna)
        close.pack(side="right")

    def _avatar_section(self, img_path):
        container = ctk.CTkFrame(self.root, fg_color="transparent")
        container.pack(pady=(20, 12))

        glow1 = ctk.CTkFrame(container, width=224, height=224,
                             corner_radius=112, fg_color=ACCENT_G,
                             border_width=0)
        glow1.pack()
        glow1.pack_propagate(False)

        glow2 = ctk.CTkFrame(glow1, width=216, height=216,
                             corner_radius=108, fg_color=ACCENT_G2,
                             border_width=0)
        glow2.place(relx=0.5, rely=0.5, anchor="center")
        glow2.pack_propagate(False)

        card = ctk.CTkFrame(glow2, width=200, height=200,
                            corner_radius=100, fg_color=PANEL,
                            border_width=2, border_color=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        if not img_path:
            ctk.CTkLabel(card, text="Y", font=(F_TITLE[0], 64, "bold"),
                         text_color=ACCENT).pack(expand=True)
            return

        try:
            original = Image.open(img_path)
            size = (192, 192)

            if img_path.lower().endswith(".gif"):
                gif = Image.open(img_path)
                try:
                    while True:
                        f = gif.copy().convert("RGBA").resize(size, Image.LANCZOS)
                        mask = Image.new("L", size, 0)
                        draw = ImageDraw.Draw(mask)
                        draw.ellipse((0, 0, size[0], size[1]), fill=255)
                        f.putalpha(mask)
                        self.frames.append(ctk.CTkImage(f, f, size=size))
                        gif.seek(gif.tell()+1)
                except EOFError:
                    pass
                if self.frames:
                    self.label_img = ctk.CTkLabel(card, image=self.frames[0],
                                                   text="", fg_color="transparent")
                    self.label_img.pack(expand=True)
                    self.animar()
                return

            img = original.convert("RGBA").resize(size, Image.LANCZOS)
            mask = Image.new("L", size, 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size[0], size[1]), fill=255)
            img.putalpha(mask)

            photo = ctk.CTkImage(img, img, size=size)
            self.label_img = ctk.CTkLabel(card, image=photo,
                                           text="", fg_color="transparent")
            self.label_img.pack(expand=True)

        except Exception:
            ctk.CTkLabel(card, text="Y", font=(F_TITLE[0], 64, "bold"),
                         text_color=ACCENT).pack(expand=True)

    def animar(self):
        if not self.frames:
            return
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        self.label_img.configure(image=self.frames[self.frame_idx])
        self.app.after(80, self.animar)

    def _status_pill(self):
        self.pill = ctk.CTkFrame(self.root, fg_color=SURFACE,
                                  corner_radius=16, height=32,
                                  border_width=1, border_color=BORDER)
        self.pill.pack(fill="x", pady=(8, 20))
        self.pill.pack_propagate(False)

        self.sym_lbl = ctk.CTkLabel(self.pill, text="●", font=(F_BODY[0], 8),
                                     text_color=STATE_OK)
        self.sym_lbl.pack(side="left", padx=(12, 4))

        self.status_lbl = ctk.CTkLabel(self.pill, text="Yuna esta activa",
                                        font=F_CAP, text_color=TEXT_SEC)
        self.status_lbl.pack(side="left")

        badge = ctk.CTkFrame(self.pill, fg_color=ACCENT_G,
                              corner_radius=10, height=18)
        badge.pack(side="right", padx=10)
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="qwen3:8b", font=(F_CAP[0], 8),
                     text_color=ACCENT).pack(padx=8, pady=2)

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

    def _actions_section(self):
        ctk.CTkLabel(self.root, text="Acciones", font=(F_SUB[0], 10, "bold"),
                     text_color=TEXT_MUT, anchor="w").pack(fill="x", pady=(0, 8))

        actions = [
            ("💬", "Chat", "Conversacion con Yuna", abrir_chat),
            ("⚡", "Agente", "Herramientas y busqueda", abrir_agente),
            ("🧠", "Aprender", "Memoria y patrones", abrir_aprendizaje),
        ]

        for icon, title, desc, cmd in actions:
            self._action_card(icon, title, desc, cmd)

    def _action_card(self, icon, title, desc, command):
        card = ctk.CTkFrame(self.root, fg_color=SURFACE,
                            corner_radius=14, height=64,
                            border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=4)
        card.pack_propagate(False)

        card.bind("<Enter>", lambda e: card.configure(fg_color=SURFACE_H, border_color=BORDER_H))
        card.bind("<Leave>", lambda e: card.configure(fg_color=SURFACE, border_color=BORDER))
        card.bind("<Button-1>", lambda e: command())

        icon_box = ctk.CTkFrame(card, width=36, height=36,
                                corner_radius=18, fg_color=ACCENT_G,
                                border_width=0)
        icon_box.pack(side="left", padx=(12, 10))
        icon_box.pack_propagate(False)
        ctk.CTkLabel(icon_box, text=icon, font=(F_ICON[0], 16),
                     text_color=ACCENT).pack(expand=True)

        txt = ctk.CTkFrame(card, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True, pady=12)
        ctk.CTkLabel(txt, text=title, font=(F_BODY[0], 12, "bold"),
                     text_color=TEXT, anchor="w").pack(fill="x")
        ctk.CTkLabel(txt, text=desc, font=F_CAP,
                     text_color=TEXT_SEC, anchor="w").pack(fill="x")

        arrow = ctk.CTkLabel(card, text="›", font=(F_TITLE[0], 18),
                              text_color=TEXT_MUT)
        arrow.pack(side="right", padx=14)

    def _bottom_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color="transparent", height=20)
        bar.pack(fill="x", pady=(16, 0))
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="Yuna AI  •  Local  •  Ollama",
                     font=(F_CAP[0], 8), text_color=TEXT_MUT).pack(side="left")

        lbl = ctk.CTkLabel(bar, text="Cerrar",
                     font=(F_CAP[0], 8, "bold"), text_color=TEXT_MUT,
                     cursor="hand2")
        lbl.pack(side="right")
        lbl.bind("<Button-1>", lambda e: self.cerrar_yuna())

    def _fade_in(self, step=0):
        alpha = min(0.97, step * 0.06)
        self.app.attributes("-alpha", alpha)
        if alpha < 0.97:
            self.app.after(16, lambda: self._fade_in(step + 1))

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag(self, event):
        x = self.app.winfo_x() + event.x - self._drag_x
        y = self.app.winfo_y() + event.y - self._drag_y
        self.app.geometry(f"+{x}+{y}")

    def cerrar_yuna(self):
        cerrar_yuna()
        self.app.destroy()


def main():
    YunaAvatar()


if __name__ == "__main__":
    main()
