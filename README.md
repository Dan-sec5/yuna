# Yuna — Agente IA Personal

Asistente y agente IA local para macOS, construido con Ollama + llama3.2:3b.
100% gratuito, privado y sin conexión a internet (excepto búsqueda web y voz).

## Stack
- **LLM**: Ollama + llama3.2:3b (local, sin internet)
- **Voz**: edge-tts DaliaNeural (español mexicano)
- **Interfaz**: CustomTkinter (avatar flotante)
- **Agente**: Sistema de herramientas modulares

## Archivos principales
| Archivo | Función |
|---|---|
| `chat.py` | Modo conversación con voz y memoria |
| `agente.py` | Modo agente con herramientas autónomas |
| `avatar.py` | Interfaz gráfica flotante |
| `aprender.py` | Análisis de bitácora y aprendizaje |
| `ejecutar.py` | Ejecutor de comandos bash |
| `limpiar_memoria.py` | Consolidación de memoria |
| `tools/` | Módulos de herramientas del agente |

## Herramientas del agente
- `tools/archivos.py` — Gestión de archivos del sistema
- `tools/datos.py` — Análisis de Excel, CSV y PDF
- `tools/web.py` — Búsqueda web y precios de activos
- `tools/sistema.py` — Acciones en macOS

## Instalación
```bash
# Requisitos
brew install ollama
ollama pull llama3.2:3b
pip install ollama customtkinter Pillow edge-tts pandas openpyxl pdfplumber yfinance ddgs

# Aliases en ~/.zshrc
alias yuna="python3 ~/yuna/avatar.py &"
alias yuna-chat="python3 ~/yuna/chat.py"
alias yuna-agente="python3 ~/yuna/agente.py"
alias yuna-ejecutar="python3 ~/yuna/ejecutar.py"
alias yuna-aprender="python3 ~/yuna/aprender.py"
alias yuna-limpiar="python3 ~/yuna/limpiar_memoria.py"
```

## Uso
```bash
yuna              # Abre panel de control con avatar
yuna-chat         # Modo conversación
yuna-agente       # Modo agente autónomo
```
