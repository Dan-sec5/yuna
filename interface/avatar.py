import customtkinter as ctk
from PIL import Image
import subprocess
import threading
import os
import glob
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def buscar_avatar():
    for patron in ['avatar.gif', 'avatar.png', 'avatar.jpg', 'avatar.jpeg', 'avatar.webp']:
        ruta = os.path.expanduser(f'~/yuna/{patron}')
        if os.path.exists(ruta):
            return ruta
    return None

def abrir_terminal(comando):
    script = f'tell app "Terminal" to do script "{comando}"'
    threading.Thread(target=lambda: os.system(f"osascript -e '{script}'")).start()

class YunaAvatar:
    def __init__(self):
        img_path = buscar_avatar()
        if not img_path:
            print("No encontré imagen. Guarda una como ~/yuna/avatar.png o avatar.gif")
            return

        img_original = Image.open(img_path)
        ancho_orig, alto_orig = img_original.size
        max_ancho = 200
        proporcion = max_ancho / ancho_orig
        self.ancho = max_ancho
        self.alto = int(alto_orig * proporcion)

        self.app = ctk.CTk()
        self.app.title("Yuna")
        self.app.geometry(f"{self.ancho+20}x{self.alto+190}+50+350")
        self.app.attributes("-topmost", True)
        self.app.attributes("-alpha", 0.97)
        self.app.overrideredirect(True)
        self.app.configure(fg_color="#1a1a2e")

        self.es_gif = img_path.lower().endswith('.gif')
        self.frames = []

        if self.es_gif:
            try:
                img_temp = Image.open(img_path)
                while True:
                    frame = img_temp.copy().convert("RGBA").resize((self.ancho, self.alto), Image.LANCZOS)
                    self.frames.append(ctk.CTkImage(light_image=frame, dark_image=frame, size=(self.ancho, self.alto)))
                    img_temp.seek(img_temp.tell() + 1)
            except EOFError:
                pass
            self.label_img = ctk.CTkLabel(self.app, image=self.frames[0], text="", fg_color="#1a1a2e")
            self.label_img.pack(pady=(8, 4))
            self.frame_idx = [0]
            self.animar()
        else:
            img = img_original.convert("RGBA").resize((self.ancho, self.alto), Image.LANCZOS)
            foto = ctk.CTkImage(light_image=img, dark_image=img, size=(self.ancho, self.alto))
            self.label_img = ctk.CTkLabel(self.app, image=foto, text="", fg_color="#1a1a2e")
            self.label_img.pack(pady=(8, 4))

        ctk.CTkLabel(self.app, text="✦ Yuna", font=("Helvetica", 13, "bold"), text_color="#a78bfa").pack(pady=(0, 6))

        # FIX: Usar python3 en vez de python, y rutas correctas
        ctk.CTkButton(self.app, text="💬 Hablar", width=self.ancho,
            fg_color="#534AB7", hover_color="#3d368a",
            command=lambda: abrir_terminal("cd ~/yuna && python3 app.py chat")).pack(pady=3)

        ctk.CTkButton(self.app, text="⚡ Ejecutar", width=self.ancho,
            fg_color="#185FA5", hover_color="#0f4578",
            command=lambda: abrir_terminal("cd ~/yuna && python3 app.py agent")).pack(pady=3)

        ctk.CTkButton(self.app, text="🤖 Modo Agente", width=self.ancho,
            fg_color="#7C3AED", hover_color="#5B21B6",
            command=lambda: abrir_terminal("cd ~/yuna && python3 app.py agent")).pack(pady=3)

        # FIX: aprender.py existe, no yuna_aprender
        ctk.CTkButton(self.app, text="🧠 Aprender", width=self.ancho,
            fg_color="#0F6E56", hover_color="#094d3c",
            command=lambda: abrir_terminal("cd ~/yuna && python3 aprender.py")).pack(pady=3)

        ctk.CTkButton(self.app, text="❌ Cerrar Yuna", width=self.ancho,
            fg_color="#7f1d1d", hover_color="#5c1414",
            command=self.cerrar_yuna).pack(pady=(3, 8))

        self.label_img.bind("<Button-1>", self.mover)
        ctk.CTkLabel(self.app, text="").bind("<Button-1>", self.mover)

        self.app.mainloop()

    def animar(self):
        if self.frames:
            self.frame_idx[0] = (self.frame_idx[0] + 1) % len(self.frames)
            self.label_img.configure(image=self.frames[self.frame_idx[0]])
            self.app.after(80, self.animar)

    def mover(self, e):
        self.app.geometry(f"+{e.x_root - (self.ancho//2 + 10)}+{e.y_root - self.alto//2}")

    def cerrar_yuna(self):
        os.system("""osascript -e '
        tell application "Terminal"
            set windowList to every window
            repeat with w in windowList
                set tabList to every tab of w
                repeat with t in tabList
                    set cmd to custom title of t
                    if cmd contains "yuna" then close t
                end repeat
            end repeat
        end tell'""")

        bitacora = os.path.expanduser("~/yuna/bitacora.txt")
        historial_dir = os.path.expanduser("~/yuna/historial/")
        os.makedirs(historial_dir, exist_ok=True)

        if os.path.exists(bitacora) and os.path.getsize(bitacora) > 0:
            fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")
            destino = f"{historial_dir}sesion_{fecha}.txt"
            with open(bitacora, "r") as src, open(destino, "w") as dst:
                dst.write(src.read())
            open(bitacora, "w").close()

        subprocess.run(["ollama", "stop", "qwen3:8b"], capture_output=True)
        self.app.destroy()

def main():
    YunaAvatar()

if __name__ == "__main__":
    main()
