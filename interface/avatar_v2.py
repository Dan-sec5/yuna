import os
import customtkinter as ctk
from PIL import Image, ImageDraw
from interface.actions import (
    abrir_chat,
    abrir_agente,
    abrir_aprendizaje,
    cerrar_yuna,
)

ctk.set_appearance_mode("light")

BG        = "#f2f2f0"
PAPER     = "#ffffff"
GRID      = "#e0e0de"
INK       = "#111111"
INK_MED   = "#444444"
INK_LIGHT = "#888888"
BORDER    = "#111111"
BORDER_H  = "#333333"
ACCENT_BG = "#eeeeee"

F_MONO    = ("SF Mono", 11)
F_MONO_B  = ("SF Mono", 11, "bold")
F_MONO_S  = ("SF Mono", 9)
F_MONO_L  = ("SF Mono", 13, "bold")
F_MONO_XL = ("SF Mono", 18, "bold")

import tkinter.font as tkfont
if "SF Mono" not in tkfont.families():
    F_MONO    = ("Courier New", 11)
    F_MONO_B  = ("Courier New", 11, "bold")
    F_MONO_S  = ("Courier New", 9)
    F_MONO_L  = ("Courier New", 13, "bold")
    F_MONO_XL = ("Courier New", 18, "bold")

STATES = {
    "ready":     {"sym": "●", "txt": "ONLINE",    "col": INK},
    "thinking":  {"sym": "◐", "txt": "THINKING",  "col": INK_MED},
    "executing": {"sym": "◉", "txt": "EXEC",      "col": INK_MED},
    "done":      {"sym": "✓", "txt": "DONE",      "col": INK},
    "offline":   {"sym": "○", "txt": "OFFLINE",   "col": INK_LIGHT},
}

def buscar_avatar():
    for ext in ("avatar.gif", "avatar.png", "avatar.jpg", "avatar.jpeg", "avatar.webp"):
        p = os.path.expanduser(f"~/yuna/{ext}")
        if os.path.exists(p):
            return p
    return None

def _crop_center_cover(img, size):
    w, h = img.size
    ratio = max(size[0] / w, size[1] / h)
    new_w, new_h = int(w * ratio), int(h * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (img.width - size[0]) // 2
    top = (img.height - size[1]) // 2
    return img.crop((left, top, left + size[0], top + size[1]))

def _apply_circle_mask(img, size):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0]-1, size[1]-1), fill=255)
    img.putalpha(mask)
    return img

class YunaAvatar:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("YUNA")
        self.app.geometry("400x820+80+60")
        self.app.minsize(380, 700)
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
        self.root.pack(fill="both", expand=True, padx=0, pady=0)

        self._top_bar()
        self._header()
        self._avatar_section(buscar_avatar())
        self._status_bar()
        self._actions_section()
        self._footer()

        self.app.bind("<Button-1>", self._start_drag)
        self.app.bind("<B1-Motion>", self._drag)
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._drag)

    def _top_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color=PAPER,
                            corner_radius=0, height=36,
                            border_width=2, border_color=BORDER)
        bar.pack(fill="x", padx=16, pady=(16, 0))
        bar.pack_propagate(False)

        ctk.CTkLabel(bar, text="●", font=F_MONO,
                     text_color=INK, width=20).pack(side="left", padx=(10, 4))
        ctk.CTkLabel(bar, text="YUNA v3.0", font=F_MONO_S,
                     text_color=INK_MED).pack(side="left")
        ctk.CTkButton(bar, text="✕", width=28, height=28,
                      corner_radius=0, fg_color=PAPER,
                      hover_color=GRID, text_color=INK,
                      font=F_MONO, command=self.cerrar_yuna,
                      border_width=1, border_color=BORDER).pack(side="right", padx=4)

    def _header(self):
        hdr = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        hdr.pack(fill="x", padx=16, pady=(20, 8))
        ctk.CTkLabel(hdr, text="YUNA", font=F_MONO_XL,
                     text_color=INK).pack(anchor="w")
        line = ctk.CTkFrame(hdr, fg_color=BORDER, corner_radius=0, height=2)
        line.pack(fill="x", pady=(4, 0))

    def _avatar_section(self, img_path):
        container = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        container.pack(pady=(16, 16))

        outer = ctk.CTkFrame(container, width=300, height=300,
                             corner_radius=0, fg_color=PAPER,
                             border_width=3, border_color=BORDER)
        outer.pack()
        outer.pack_propagate(False)

        grid_canvas = ctk.CTkCanvas(outer, bg="white", highlightthickness=0)
        grid_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        for i in range(0, 300, 12):
            for j in range(0, 300, 12):
                grid_canvas.create_oval(i, j, i+1, j+1, fill="#dddddd", outline="")

        AVATAR_SIZE = 260
        IMG_SIZE = 248

        card = ctk.CTkFrame(outer, width=AVATAR_SIZE, height=AVATAR_SIZE,
                            corner_radius=AVATAR_SIZE//2,
                            fg_color=PAPER,
                            border_width=4,
                            border_color=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        if not img_path:
            ctk.CTkLabel(card, text="Y", font=F_MONO_XL,
                         text_color=INK).pack(expand=True)
            return

        try:
            original = Image.open(img_path)
            if img_path.lower().endswith(".gif"):
                gif = Image.open(img_path)
                try:
                    while True:
                        f = gif.copy().convert("RGBA")
                        f = _crop_center_cover(f, (IMG_SIZE, IMG_SIZE))
                        f = _apply_circle_mask(f, (IMG_SIZE, IMG_SIZE))
                        self.frames.append(ctk.CTkImage(f, f, size=(IMG_SIZE, IMG_SIZE)))
                        gif.seek(gif.tell()+1)
                except EOFError:
                    pass
                if self.frames:
                    self.label_img = ctk.CTkLabel(card, image=self.frames[0],
                                                   text="", fg_color="transparent")
                    self.label_img.place(relx=0.5, rely=0.5, anchor="center")
                    self.animar()
                return

            img = original.convert("RGBA")
            img = _crop_center_cover(img, (IMG_SIZE, IMG_SIZE))
            img = _apply_circle_mask(img, (IMG_SIZE, IMG_SIZE))
            photo = ctk.CTkImage(img, img, size=(IMG_SIZE, IMG_SIZE))
            self.label_img = ctk.CTkLabel(card, image=photo,
                                           text="", fg_color="transparent")
            self.label_img.place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(card, text="Y", font=F_MONO_XL,
                         text_color=INK).pack(expand=True)

    def animar(self):
        if not self.frames:
            return
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        self.label_img.configure(image=self.frames[self.frame_idx])
        self.app.after(80, self.animar)

    def _status_bar(self):
        bar = ctk.CTkFrame(self.root, fg_color=PAPER,
                            corner_radius=0, height=32,
                            border_width=2, border_color=BORDER)
        bar.pack(fill="x", padx=16, pady=(0, 20))
        bar.pack_propagate(False)

        self.sym_lbl = ctk.CTkLabel(bar, text="●", font=F_MONO_S,
                                     text_color=INK)
        self.sym_lbl.pack(side="left", padx=(10, 4))
        self.status_lbl = ctk.CTkLabel(bar, text="ONLINE",
                                        font=F_MONO_S, text_color=INK_MED)
        self.status_lbl.pack(side="left")
        ctk.CTkLabel(bar, text="qwen3:8b", font=F_MONO_S,
                     text_color=INK_LIGHT).pack(side="right", padx=10)
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
        hdr = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        hdr.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(hdr, text="ACCIONES", font=F_MONO_B,
                     text_color=INK_MED, anchor="w").pack(anchor="w")

        actions = [
            ("01", "CHAT",        "Conversacion con Yuna", abrir_chat),
            ("02", "AGENTE",      "Herramientas y busqueda", abrir_agente),
            ("03", "APRENDER",    "Memoria y patrones", abrir_aprendizaje),
        ]
        for num, title, desc, cmd in actions:
            self._action_card(num, title, desc, cmd)

    def _action_card(self, num, title, desc, command):
        card = ctk.CTkFrame(self.root, fg_color=PAPER,
                            corner_radius=0, height=72,
                            border_width=2, border_color=BORDER)
        card.pack(fill="x", padx=16, pady=4)
        card.pack_propagate(False)

        card.bind("<Enter>", lambda e: card.configure(fg_color=GRID, border_color=BORDER_H))
        card.bind("<Leave>", lambda e: card.configure(fg_color=PAPER, border_color=BORDER))
        card.bind("<Button-1>", lambda e: command())

        idx = ctk.CTkFrame(card, width=40, height=40,
                           corner_radius=0, fg_color=ACCENT_BG,
                           border_width=1, border_color=BORDER)
        idx.pack(side="left", padx=(12, 10))
        idx.pack_propagate(False)
        ctk.CTkLabel(idx, text=num, font=F_MONO_B,
                     text_color=INK).pack(expand=True)

        txt = ctk.CTkFrame(card, fg_color="transparent")
        txt.pack(side="left", fill="both", expand=True, pady=12)
        ctk.CTkLabel(txt, text=title, font=F_MONO_L,
                     text_color=INK, anchor="w").pack(fill="x")
        ctk.CTkLabel(txt, text=desc, font=F_MONO_S,
                     text_color=INK_MED, anchor="w").pack(fill="x")

        arrow = ctk.CTkLabel(card, text="→", font=F_MONO_L,
                              text_color=INK_LIGHT)
        arrow.pack(side="right", padx=14)

    def _footer(self):
        f = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        f.pack(fill="x", padx=16, pady=(16, 16))
        line = ctk.CTkFrame(f, fg_color=BORDER, corner_radius=0, height=2)
        line.pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(f, fg_color=BG, corner_radius=0)
        row.pack(fill="x")
        ctk.CTkLabel(row, text="YUNA AI / LOCAL / OLLAMA",
                     font=F_MONO_S, text_color=INK_LIGHT).pack(side="left")
        close_lbl = ctk.CTkLabel(row, text="CERRAR →",
                     font=F_MONO_S, text_color=INK,
                     cursor="hand2")
        close_lbl.pack(side="right")
        close_lbl.bind("<Button-1>", lambda e: self.cerrar_yuna())

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
