#!/bin/bash
set -e

echo "🚀 Instalando Yuna..."

# Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 requerido"
    exit 1
fi

# Ollama
if ! command -v ollama &> /dev/null; then
    echo "📦 Instalando Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Modelo por defecto
echo "📥 Descargando modelo qwen3:8b..."
ollama pull qwen3:8b

# Dependencias Python
echo "📦 Instalando dependencias Python..."
pip install --upgrade pip
pip install -r requirements.txt

# edge-tts (voz)
pip install edge-tts

# Verificar sox para STT
if ! command -v sox &> /dev/null; then
    echo "⚠ sox no instalado (necesario para STT). En macOS: brew install sox"
fi

# Verificar ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠ ffmpeg no instalado (alternativa para STT). En macOS: brew install ffmpeg"
fi

# Crear directorios
mkdir -p ~/yuna/data ~/yuna/logs ~/yuna/historial

# Inicializar BD
python -c "from memory.manager import init_db; init_db(); print('✓ BD inicializada')"

# Verificar avatar
if [ ! -f ~/yuna/avatar.png ] && [ ! -f ~/yuna/avatar.gif ]; then
    echo "⚠ No hay avatar. Pon una imagen en ~/yuna/avatar.png o avatar.gif"
fi

echo ""
echo "✅ Instalación completa"
echo ""
echo "Uso:"
echo "  python app.py chat      # Chat conversacional"
echo "  python app.py agent     # Agente autónomo"
echo "  python app.py avatar    # GUI flotante"
echo "  python app.py migrate   # Migrar memoria antigua"
