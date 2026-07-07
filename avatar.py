from aprender import consolidar_memoria
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
    extensiones_validas = ['.gif', '.png', '.jpg', '.jpeg', '.webp']
    for ext in extensiones_validas:
        archivos = glob.glob(os.path.expanduser(f'~/yuna/avatar{ext}'))
        if archivos:
            return archivos[0]
    return None

img_path = buscar_avatar()
if not img_path:
    print("No encontré imagen. Guarda una como ~/yuna/avatar.png o avatar.gif")
    exit()

img_original = Image.open(img_path)
ancho_orig, alto_orig = img_original.size
max_ancho = 200
proporcion = max_ancho / ancho_orig
ancho = max_ancho
alto = int(alto_orig * proporcion)

app = ctk.CTk()
app.title("Yuna")
app.geometry(f"{ancho+20}x{alto+180}+50+350")
app.attributes("-topmost", True)
app.attributes("-alpha", 0.94)
app.overrideredirect(True)
app.configure(fg_color="#1a1a2e")

es_gif = img_path.lower().endswith('.gif')

if es_gif:
    frames = []
    try:
        img_temp = Image.open(img_path)
        while True:
            frame = img_temp.copy().convert("RGBA").resize((ancho, alto), Image.LANCZOS)
            frames.append(ctk.CTkImage(light_image=frame, dark_image=frame, size=(ancho, alto)))
            img_temp.seek(img_temp.tell() + 1)
    except EOFError:
        pass
    label_img = ctk.CTkLabel(app, image=frames[0], text="", fg_color="#1a1a2e")
    label_img.pack(pady=(8, 4))
    frame_idx = [0]
    def animar():
        frame_idx[0] = (frame_idx[0] + 1) % len(frames)
        label_img.configure(image=frames[frame_idx[0]])
        app.after(80, animar)
    app.after(80, animar)
else:
    img = img_original.convert("RGBA").resize((ancho, alto), Image.LANCZOS)
    foto = ctk.CTkImage(light_image=img, dark_image=img, size=(ancho, alto))
    label_img = ctk.CTkLabel(app, image=foto, text="", fg_color="#1a1a2e")
    label_img.pack(pady=(8, 4))

nombre = ctk.CTkLabel(app, text="✦ Yuna", font=("Helvetica", 13, "bold"), text_color="#a78bfa")
nombre.pack(pady=(0, 6))

def abrir_terminal(comando):
    script = f'tell app "Terminal" to do script "{comando}"'
    threading.Thread(target=lambda: os.system(f"osascript -e '{script}'")).start()

btn_hablar = ctk.CTkButton(
    app, text="💬  Hablar", width=ancho,
    fg_color="#534AB7", hover_color="#3d368a",
    command=lambda: abrir_terminal("yuna-chat")
)
btn_hablar.pack(pady=3)

btn_ejecutar = ctk.CTkButton(
    app, text="⚡  Ejecutar tarea", width=ancho,
    fg_color="#185FA5", hover_color="#0f4578",
    command=lambda: abrir_terminal("yuna-ejecutar")
)
btn_ejecutar.pack(pady=3)

btn_aprender = ctk.CTkButton(
    app, text="🧠  Aprender", width=ancho,
    fg_color="#0F6E56", hover_color="#094d3c",
    command=lambda: abrir_terminal("yuna-aprender")
)
btn_aprender.pack(pady=3)

def cerrar_yuna():
    # 1. Ejecutar el proceso de aprendizaje/resumen
    print("Yuna está procesando lo aprendido hoy...")
    consolidar_memoria()
    
    # 2. Archivar bitácora
    bitacora = os.path.expanduser("~/yuna/bitacora.txt")
    historial_dir = os.path.expanduser("~/yuna/historial/")
    os.makedirs(historial_dir, exist_ok=True)
    
    if os.path.exists(bitacora):
        fecha = datetime.now().strftime("%Y-%m-%d_%H-%M")
        destino = f"{historial_dir}sesion_{fecha}.txt"
        os.rename(bitacora, destino)
        open(bitacora, 'w').close()
    
    # 3. Liberar recursos
    subprocess.run(["ollama", "stop", "qwen3:4b"], capture_output=True)
    app.destroy()
    
btn_cerrar = ctk.CTkButton(
    app, text="❌  Cerrar Yuna", width=ancho,
    fg_color="#7f1d1d", hover_color="#5c1414",
    command=cerrar_yuna
)
btn_cerrar.pack(pady=(3, 8))
def mover(e):
    app.geometry(f"+{e.x_root - (ancho//2 + 10)}+{e.y_root - alto//2}")
label_img.bind("<B1-Motion>", mover)
nombre.bind("<B1-Motion>", mover)

app.mainloop()
