import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from interface.actions import abrir_chat, abrir_agente, abrir_aprendizaje, cerrar_yuna

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

BG        = "#f0f0ee"
PAPER     = "#ffffff"
INK       = "#111111"
INK_MED   = "#555555"
INK_LIGHT = "#999999"
BORDER    = "#111111"
BORDER_H  = "#333333"
GRAY_BG   = "#e8e8e6"

F_M       = ("SF Mono", 10)
F_MB      = ("SF Mono", 10, "bold")
F_MS      = ("SF Mono", 8)
F_ML      = ("SF Mono", 12, "bold")
F_MXL     = ("SF Mono", 20, "bold")

def buscar_avatar():
    for ext in ("avatar.gif","avatar.png","avatar.jpg","avatar.jpeg","avatar.webp"):
        p = os.path.expanduser(f"~/yuna/{ext}")
        if os.path.exists(p): return p
    return None

def fit_inside(img, max_w, max_h):
    """Redimensiona la imagen proporcionalmente para que quepa COMPLETA dentro de max_w x max_h."""
    w, h = img.size
    ratio = min(max_w / w, max_h / h, 1.0)
    new_w, new_h = int(w * ratio), int(h * ratio)
    return img.resize((new_w, new_h), Image.LANCZOS)

class YunaAvatar:
    def __init__(self):
        self.app = ctk.CTk()
        self.app.title("YUNA")
        self.app.geometry("360x680+80+80")
        self.app.minsize(340, 520)
        self.app.configure(fg_color=BG)
        self.app.attributes("-topmost", True)
        self.app.attributes("-alpha", 0.0)
        self.app.overrideredirect(True)

        self.frames = []
        self.frame_idx = 0
        self._drag_x = self._drag_y = 0
        self._img_path = buscar_avatar()

        self._build()
        self._fade_in()
        self.app.mainloop()

    def _build(self):
        root = ctk.CTkFrame(self.app, fg_color=BG, corner_radius=0)
        root.pack(fill="both", expand=True)

        # TOP BAR
        bar = ctk.CTkFrame(root, fg_color=PAPER, corner_radius=0, height=36,
                           border_width=2, border_color=BORDER)
        bar.pack(fill="x", padx=12, pady=(12,0))
        bar.pack_propagate(False)
        ctk.CTkLabel(bar, text="●", font=F_M, text_color=INK, width=20).pack(side="left", padx=(8,4))
        ctk.CTkLabel(bar, text="YUNA v3.0", font=F_MS, text_color=INK_MED).pack(side="left")
        ctk.CTkButton(bar, text="✕", width=28, height=28, corner_radius=0,
                      fg_color=PAPER, hover_color=GRAY_BG, text_color=INK,
                      font=F_M, command=self._close,
                      border_width=1, border_color=BORDER).pack(side="right", padx=4)

        # HEADER
        hdr = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
        hdr.pack(fill="x", padx=12, pady=(16,0))
        ctk.CTkLabel(hdr, text="YUNA", font=F_MXL, text_color=INK, anchor="w").pack(anchor="w")
        ctk.CTkFrame(hdr, fg_color=BORDER, corner_radius=0, height=2).pack(fill="x", pady=(4,0))

        # AVATAR CONTAINER (expande verticalmente)
        av_container = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
        av_container.pack(fill="both", expand=True, padx=12, pady=(12,12))

        av_box = ctk.CTkFrame(av_container, fg_color=PAPER, corner_radius=0,
                              border_width=3, border_color=BORDER)
        av_box.pack(expand=True, fill="both")

        # Grid dinámico
        self.grid_cvs = tk.Canvas(av_box, bg="white", highlightthickness=0)
        self.grid_cvs.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Avatar interior: tamaño inicial explícito, sin propagación
        self.av_card = ctk.CTkFrame(av_box, width=240, height=280,
                                    corner_radius=6, fg_color=PAPER,
                                    border_width=2, border_color=BORDER)
        self.av_card.place(relx=0.5, rely=0.5, anchor="center")
        self.av_card.pack_propagate(False)

        self._draw_grid()
        self._load_avatar()

        # Redibujar al cambiar tamaño
        av_box.bind("<Configure>", self._on_av_resize)

        # STATUS BAR
        st = ctk.CTkFrame(root, fg_color=PAPER, corner_radius=0, height=32,
                          border_width=2, border_color=BORDER)
        st.pack(fill="x", padx=12, pady=(0,12))
        st.pack_propagate(False)
        ctk.CTkLabel(st, text="●", font=F_MS, text_color=INK).pack(side="left", padx=(10,4))
        ctk.CTkLabel(st, text="ONLINE", font=F_MS, text_color=INK_MED).pack(side="left")
        ctk.CTkLabel(st, text="qwen3:8b", font=F_MS, text_color=INK_LIGHT).pack(side="right", padx=10)

        # ACCIONES
        ctk.CTkLabel(root, text="ACCIONES", font=F_MB, text_color=INK_MED,
                     anchor="w").pack(fill="x", padx=12, pady=(0,6))

        for num, ttl, dsc, cmd in [
            ("01","CHAT","Conversacion con Yuna", abrir_chat),
            ("02","AGENTE","Herramientas y busqueda", abrir_agente),
            ("03","APRENDER","Memoria y patrones", abrir_aprendizaje),
        ]:
            self._btn(root, num, ttl, dsc, cmd)

        # FOOTER
        foot = ctk.CTkFrame(root, fg_color=BG, corner_radius=0)
        foot.pack(fill="x", padx=12, pady=(12,12))
        ctk.CTkFrame(foot, fg_color=BORDER, corner_radius=0, height=2).pack(fill="x", pady=(0,6))
        row = ctk.CTkFrame(foot, fg_color=BG, corner_radius=0)
        row.pack(fill="x")
        ctk.CTkLabel(row, text="YUNA AI / LOCAL / OLLAMA", font=F_MS, text_color=INK_LIGHT).pack(side="left")
        c = ctk.CTkLabel(row, text="CERRAR →", font=F_MS, text_color=INK, cursor="hand2")
        c.pack(side="right")
        c.bind("<Button-1>", lambda e: self._close())

        self.app.bind("<Button-1>", self._sd)
        self.app.bind("<B1-Motion>", self._dg)
        root.bind("<Button-1>", self._sd)
        root.bind("<B1-Motion>", self._dg)

    def _draw_grid(self):
        self.grid_cvs.delete("all")
        w = self.grid_cvs.winfo_width() or 240
        h = self.grid_cvs.winfo_height() or 280
        for i in range(0, w, 10):
            for j in range(0, h, 10):
                self.grid_cvs.create_oval(i, j, i+1, j+1, fill="#cccccc", outline="")

    def _on_av_resize(self, event):
        self._draw_grid()
        # Ajustar card proporcionalmente al contenedor
        new_w = max(min(event.width - 20, 300), 160)
        new_h = max(min(event.height - 20, 380), 200)
        self.av_card.configure(width=new_w, height=new_h)
        # Recargar avatar con nuevo tamaño
        self._load_avatar()

    def _load_avatar(self):
        # Limpiar card anterior
        for w in self.av_card.winfo_children():
            w.destroy()
        self.frames = []

        if not self._img_path:
            ctk.CTkLabel(self.av_card, text="Y", font=F_MXL, text_color=INK).pack(expand=True)
            return

        try:
            # Tamaño disponible dentro del card (dejando margen para bordes)
            cw = max(self.av_card.winfo_width() - 12, 100)
            ch = max(self.av_card.winfo_height() - 12, 100)

            orig = Image.open(self._img_path)

            if self._img_path.lower().endswith(".gif"):
                gif = Image.open(self._img_path)
                try:
                    while True:
                        f = gif.copy().convert("RGBA")
                        f = fit_inside(f, cw, ch)
                        self.frames.append(ctk.CTkImage(f, f, size=f.size))
                        gif.seek(gif.tell()+1)
                except EOFError:
                    pass
                if self.frames:
                    self.lbl = ctk.CTkLabel(self.av_card, image=self.frames[0],
                                            text="", fg_color="transparent")
                    self.lbl.place(relx=0.5, rely=0.5, anchor="center")
                    self._anim()
            else:
                img = orig.convert("RGBA")
                img = fit_inside(img, cw, ch)
                ph = ctk.CTkImage(img, img, size=img.size)
                ctk.CTkLabel(self.av_card, image=ph, text="",
                             fg_color="transparent").place(relx=0.5, rely=0.5, anchor="center")
        except Exception:
            ctk.CTkLabel(self.av_card, text="Y", font=F_MXL, text_color=INK).pack(expand=True)

    def _btn(self, parent, num, ttl, dsc, cmd):
        card = ctk.CTkFrame(parent, fg_color=PAPER, corner_radius=0, height=64,
                            border_width=2, border_color=BORDER)
        card.pack(fill="x", padx=12, pady=3)
        card.pack_propagate(False)
        card.bind("<Enter>", lambda e: card.configure(fg_color=GRAY_BG, border_color=BORDER_H))
        card.bind("<Leave>", lambda e: card.configure(fg_color=PAPER, border_color=BORDER))
        card.bind("<Button-1>", lambda e: cmd())

        idx = ctk.CTkFrame(card, width=36, height=36, corner_radius=0,
                           fg_color=GRAY_BG, border_width=1, border_color=BORDER)
        idx.pack(side="left", padx=(10,8))
        idx.pack_propagate(False)
        ctk.CTkLabel(idx, text=num, font=F_MB, text_color=INK).pack(expand=True)

        t = ctk.CTkFrame(card, fg_color="transparent")
        t.pack(side="left", fill="both", expand=True, pady=10)
        ctk.CTkLabel(t, text=ttl, font=F_ML, text_color=INK, anchor="w").pack(fill="x")
        ctk.CTkLabel(t, text=dsc, font=F_MS, text_color=INK_MED, anchor="w").pack(fill="x")

        ctk.CTkLabel(card, text="→", font=F_ML, text_color=INK_LIGHT).pack(side="right", padx=12)

    def _anim(self):
        if not self.frames: return
        self.frame_idx = (self.frame_idx+1) % len(self.frames)
        self.lbl.configure(image=self.frames[self.frame_idx])
        self.app.after(80, self._anim)

    def _fade_in(self, s=0):
        a = min(0.97, s*0.06)
        self.app.attributes("-alpha", a)
        if a < 0.97: self.app.after(16, lambda: self._fade_in(s+1))

    def _sd(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _dg(self, e):
        x = self.app.winfo_x() + e.x - self._drag_x
        y = self.app.winfo_y() + e.y - self._drag_y
        self.app.geometry(f"+{x}+{y}")

    def _close(self):
        cerrar_yuna()
        self.app.destroy()

def main():
    YunaAvatar()

if __name__ == "__main__":
    main()
