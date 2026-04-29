"""
Fuente única de verdad para rutas, constantes y parámetros de la aplicación.
Ningún otro módulo debe hardcodear valores que aquí estén definidos.
"""
from pathlib import Path
import os
import sys

APP_NAME    = "InnoTech VideoTutor"
APP_VERSION = "1.0.0"
APP_AUTHOR  = "InnoTech Solutions"

# Rutas base
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent

RESOURCES_DIR  = BASE_DIR / "resources"
ICONS_DIR      = RESOURCES_DIR / "icons"
FONTS_DIR      = RESOURCES_DIR / "fonts"
PROMPTS_DIR    = RESOURCES_DIR / "prompts"
STYLES_PATH    = BASE_DIR / "app" / "ui" / "styles.qss"

# Datos de usuario (persistentes entre sesiones)
DATA_DIR    = Path(os.environ.get("APPDATA", Path.home())) / "InnoTech" / "VideoTutor"
OUTPUTS_DIR = DATA_DIR / "proyectos"
LOGS_DIR    = DATA_DIR / "logs"
DB_PATH     = DATA_DIR / "historial.db"
CONFIG_PATH = DATA_DIR / "config.enc"

# Rutas de FFmpeg en orden de prioridad de búsqueda:
#   1. Junto al ejecutable (PyInstaller bundled)
#   2. En el directorio local del proyecto (descargado por setup_ffmpeg.py / auto-descarga)
#   3. En AppData (instalado por el instalador Inno Setup)
#   4. En PATH del sistema (fallback)
FFMPEG_BUNDLED_DIR = BASE_DIR / "ffmpeg" / "bin"          # junto al .exe
FFMPEG_LOCAL_DIR   = BASE_DIR / "tools" / "ffmpeg" / "bin" # para desarrollo local
FFMPEG_DIR         = DATA_DIR / "ffmpeg" / "bin"           # instalado por Inno Setup

# URL del build estático de FFmpeg para Windows x64 (gyan.dev — build oficial)
FFMPEG_DOWNLOAD_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-master-latest-win64-gpl.zip"
)

# Crear directorios de datos al importar
for _dir in (DATA_DIR, OUTPUTS_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# Inyectar el directorio de FFmpeg en PATH para que Whisper y otros subprocesos
# puedan llamar a "ffmpeg" directamente, sin importar dónde esté instalado.
for _ffmpeg_dir in (FFMPEG_BUNDLED_DIR, FFMPEG_LOCAL_DIR, FFMPEG_DIR):
    _ffmpeg_exe = _ffmpeg_dir / "ffmpeg.exe"
    if _ffmpeg_exe.exists():
        _current_path = os.environ.get("PATH", "")
        if str(_ffmpeg_dir) not in _current_path:
            os.environ["PATH"] = str(_ffmpeg_dir) + os.pathsep + _current_path
        break

# Configuración de Whisper
WHISPER_MODEL     = "medium"
WHISPER_LANGUAGE  = "es"
WHISPER_DEVICE    = "auto"
WHISPER_BEAM_SIZE = 5

# Parámetros de extracción de audio (óptimos para Whisper)
AUDIO_SAMPLE_RATE  = 16000
AUDIO_CHANNELS     = 1
AUDIO_FORMAT       = "wav"
AUDIO_CODEC        = "pcm_s16le"

# Formatos de video soportados
SUPPORTED_VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}

# Proveedores de IA
AI_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
        "default_model": "gemini-1.5-flash",
    },
    "groq": {
        "name": "Groq",
        "models": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"],
        "default_model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "name": "OpenRouter",
        "models": [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o-mini",
            "meta-llama/llama-3.3-70b-instruct",
        ],
        "default_model": "anthropic/claude-3.5-sonnet",
        "base_url": "https://openrouter.ai/api/v1",
    },
}
