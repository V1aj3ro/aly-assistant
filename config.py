# =============================================================================
# Аля — конфигурация
# =============================================================================

# Gemini
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-2.0-flash"

# Whisper
WHISPER_MODEL = "base"          # base оптимален для GTX 1080
WHISPER_DEVICE = "cuda"
WHISPER_COMPUTE_TYPE = "float16"

# Wake word
WAKE_WORD = "аля"
WAKE_WORD_PATTERN = r"[аa][лl][яei]"  # учитывает транслитерацию Whisper

# Запись звука
SAMPLE_RATE = 16000
CHANNELS = 1
VAD_THRESHOLD = 0.02            # RMS порог начала записи
VAD_SILENCE_DURATION = 1.5     # секунд тишины до остановки записи
CHUNK_DURATION = 0.1            # длина одного чанка (сек)

# Экран
SCREEN_W = 2560
SCREEN_H = 1440
SCREENSHOT_W = 1280
SCREENSHOT_H = 720

# Голос — Edge TTS
EDGE_TTS_VOICE = "ru-RU-DariyaNeural"   # базовый русский голос

# RVC
RVC_ENABLED = True
RVC_MODEL_PATH = "models/rvc/voice.pth"      # путь к .pth файлу модели
RVC_INDEX_PATH = "models/rvc/voice.index"    # путь к .index файлу
RVC_PITCH = 0           # сдвиг тона: 0 = без изменений, +6 = выше (аниме-голос)
RVC_METHOD = "rmvpe"    # алгоритм pitch extraction, rmvpe самый качественный
RVC_INDEX_RATE = 0.75

# VTube Studio
VTS_HOST = "ws://localhost:8001"
VTS_PLUGIN_NAME = "Аля Ассистент"
VTS_PLUGIN_DEV = "user"
VTS_TOKEN_FILE = ".vts_token"   # кэш токена аутентификации

# Live2D модель (для справки в README)
# Рекомендуемая: Hakui Koyori (белые волосы)
# https://booth.pm/ja/items/3500430

# Персональность
VOICE_RESPONSE = True
ALY_PERSONALITY = """
Ты — Аля, аниме-ассистент с белыми волосами.
Отвечаешь коротко, по делу, иногда с лёгким аниме-флёром.
Обращаешься к пользователю на "ты".
Ответы максимум 2 предложения — ты голосовой ассистент, не чат-бот.
"""

# Логирование
LOG_FILE = "aly.log"
LOG_MAX_BYTES = 5 * 1024 * 1024    # 5 MB
LOG_BACKUP_COUNT = 3

# Gemini rate limit защита
GEMINI_MIN_INTERVAL = 4.0   # минимум секунд между запросами
