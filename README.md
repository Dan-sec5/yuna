# Yuna — Agente IA Local

Asistente personal con ejecución de herramientas, memoria persistente y voz.

## Estructura

```
yuna/
├── app.py                 # Entry point
├── config/
│   ├── config.json        # Configuración central
│   └── __init__.py
├── core/                  # Núcleo del agente
│   ├── agent.py           # Loop Plan→Execute→Evaluate
│   ├── llm.py             # Wrapper Ollama + tool calling
│   ├── planner.py         # System prompt & parsing
│   ├── executor.py        # Ejecuta tools con permisos
│   ├── evaluator.py       # Evalúa resultados
│   └── context.py         # Manejo de contexto + memoria
├── tools/                 # Herramientas registradas
│   ├── registry.py        # Dict {name: function}
│   ├── schemas.py         # JSON Schema para Ollama
│   ├── permisos.py        # SAFE / CONFIRM / DANGEROUS
│   ├── archivos.py        # FS: buscar, listar, organizar
│   ├── datos.py           # Data: Excel, CSV, PDF
│   ├── web.py             # Web: search, precios, noticias
│   ├── sistema.py         # Sistema: bash, notify, files
│   └── __init__.py
├── memory/                # Memoria SQLite
│   ├── manager.py         # CRUD preferencias, episodic, tareas
│   └── __init__.py
├── interface/             # Interfaces de usuario
│   ├── cli.py             # Chat conversacional
│   ├── agent_cli.py       # Agente autónomo
│   ├── avatar.py          # GUI flotante (CustomTkinter)
│   ├── voice.py           # TTS (edge-tts) + STT (Whisper)
│   └── __init__.py
├── automation/            # Automatizaciones
│   ├── scheduler.py       # Cron jobs (APScheduler)
│   ├── watchers.py        # File watchers (watchdog)
│   └── __init__.py
├── data/                  # Datos persistentes
│   └── yuna.db            # SQLite
├── logs/                  # Logs de app y auditoría
├── tests/                 # Tests unitarios
├── migrate_memoria.py     # Migración única memoria.txt → SQLite
├── install.sh             # Instalación automática
└── requirements.txt
```

## Instalación

```bash
cd ~/yuna
./install.sh
```

## Uso

```bash
# Chat conversacional
python app.py chat

# Agente autónomo (usa tools via Ollama tool calling)
python app.py agent

# GUI flotante
python app.py avatar

# Migrar memoria antigua
python app.py migrate
```

## Herramientas disponibles

| Tool | Descripción | Permiso |
|------|-------------|---------|
| buscar_archivos | Buscar por patrón glob | SAFE |
| listar_recientes | Archivos modificados últimos N días | SAFE |
| organizar_archivos | Mover a subcarpetas por tipo | CONFIRM |
| leer_excel / leer_csv / leer_pdf | Resumen de datos | SAFE |
| buscar_web | DuckDuckGo search | SAFE |
| precio_activo | Precio financiero (yfinance) | SAFE |
| noticias_financieras_mx | Noticias México | SAFE |
| info_sistema | Disco, memoria, fecha | SAFE |
| notificar | Notification macOS | SAFE |
| crear_archivo | Escribir archivo | CONFIRM |
| ejecutar_bash_seguro | Bash whitelist (ls, cat, grep...) | DANGEROUS |
| consultar_memoria / escribir_memoria | SQLite | SAFE / CONFIRM |

## Permisos

- **SAFE**: Solo lectura, sin efectos laterales → ejecuta directo
- **CONFIRM**: Modifica sistema/archivos → pide confirmación
- **DANGEROUS**: Bash arbitrario → bloqueado por defecto, whitelist estricta

## Configuración

Edita `config/config.json`:

```json
{
  "models": {
    "chat": "gemma2b",
    "agent": "qwen3:8b"
  },
  "permissions": {
    "confirmations": true
  }
}
```

## Tests

```bash
pytest tests/ -v
```

## Memoria

- `preferencias`: clave/valor persistente (nombre, preferencias...)
- `episodic`: historial de eventos con timestamp
- `tarea_actual`: estado de tareas en curso (JSON)

Migración automática desde `memoria.txt` y `bitacora.txt` al ejecutar `python app.py migrate`.

## Requisitos

- Python 3.10+
- Ollama corriendo (`ollama serve`)
- Modelo `qwen3:8b` (o compatible con tool calling)
- macOS (para `afplay`, `osascript`, `say`)
- edge-tts (`pip install edge-tts`)
- Opcional: Whisper (`pip install openai-whisper`) + sox/ffmpeg para STT
