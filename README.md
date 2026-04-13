# Аля — голосовой аниме ИИ-ассистент

Аля слушает тебя через микрофон, думает с помощью Gemini (видит твой экран), отвечает аниме-голосом и управляет ПК по команде. На рабочем столе живёт Live2D моделька, которая шевелит губами когда говорит.

```
Микрофон → Whisper → Gemini 2.0 Flash → Edge TTS → RVC → VTube Studio
                   ↓
              pyautogui (клики, клавиши, открытие программ)
```

---

## Требования

- **Windows 10 / 11**
- **Python 3.10** (не выше — rvc-python требует 3.10)
- **NVIDIA GPU** с CUDA 11.8+ (GTX 1080 и выше, ~4GB VRAM)
- Микрофон

---

## Установка

### 1. Python 3.10

Обязательно **Python 3.10**: https://www.python.org/downloads/release/python-3100/

При установке поставить галочку **Add Python to PATH**.

Проверка:
```cmd
python --version
```

### 2. CUDA Toolkit 11.8

Для GTX 1080 нужен CUDA 11.8:
https://developer.nvidia.com/cuda-11-8-0-download-archive

Проверка:
```cmd
nvcc --version
```

### 3. ffmpeg (нужен для pydub — конвертация MP3→WAV)

Скачать: https://www.gyan.dev/ffmpeg/builds/ → `ffmpeg-release-essentials.zip`

Распаковать, добавить папку `bin/` в системный PATH, или просто положить `ffmpeg.exe` в папку проекта.

Проверка:
```cmd
ffmpeg -version
```

### 4. PyTorch с CUDA

```cmd
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 5. Зависимости

```cmd
pip install -r requirements.txt
```

### 6. Gemini API ключ

1. Зайти на https://aistudio.google.com
2. **Get API Key** → **Create API Key**
3. Вставить в `config.py`:

```python
GEMINI_API_KEY = "AIza..."
```

Бесплатно, карта не нужна, лимит **1500 запросов в день**.

### 7. VTube Studio

1. Скачать бесплатно в **Steam** → VTube Studio
2. Загрузить Live2D модель. Рекомендуется **Hakui Koyori** (белые волосы):
   https://booth.pm/ja/items/3500430
3. Включить API: **Settings → Plugins → Enable Plugins** и **Start API (порт 8001)**
4. При первом запуске Али — подтвердить разрешение плагина во всплывающем окне VTS

Если VTube Studio не запущена — Аля работает без Live2D.

### 8. RVC модель голоса

1. Скачать аниме RVC модель:
   - https://huggingface.co/datasets/SayanoAI/RVC-Studio
   - Поиск: `anime voice RVC model huggingface`
2. Положить файлы в `models/rvc/`:
   ```
   models/rvc/voice.pth
   models/rvc/voice.index
   ```
3. Прописать пути в `config.py` если названия другие
4. Для аниме-голоса попробовать `RVC_PITCH = 6`

Если RVC не нужен — в `config.py` поставить `RVC_ENABLED = False`.
Edge TTS с `DariyaNeural` звучит хорошо и без RVC.

### 9. Запуск

```cmd
python aly.py
```

Сказать **«Аля, привет»** для проверки.

---

## Команды

| Что сказать | Что сделает |
|---|---|
| Аля, пауза | Нажмёт пробел |
| Аля, громче | Увеличит громкость (WinAPI) |
| Аля, тише | Уменьшит громкость |
| Аля, открой ютуб | Откроет YouTube |
| Аля, что на экране? | Опишет экран |
| Аля, закрой окно | Alt+F4 |
| Аля, следующая серия | Найдёт кнопку на экране |
| Аля, напечатай [текст] | Напечатает (поддерживает кириллицу) |

---

## Безопасность

- **Failsafe**: двинь мышь в **левый верхний угол** — Аля остановится
- Иконка в трее → правой кнопкой → **Выход**
- `Ctrl+C` в терминале

---

## Структура проекта

```
aly/
├── aly.py           # точка входа, главный цикл (asyncio)
├── config.py        # все настройки
├── listener.py      # микрофон + Whisper CUDA + wake-word
├── vision.py        # mss скриншот + Gemini 2.0 Flash
├── actions.py       # click/key/type/scroll/open + Windows volume keys
├── voice.py         # Edge TTS (MP3) + RVC + pygame воспроизведение
├── live2d.py        # VTube Studio WebSocket API
├── tray.py          # системный трей с цветовым статусом
├── models/
│   └── rvc/         # .pth и .index файлы RVC модели
└── requirements.txt
```

---

## Windows-специфика

| Проблема | Решение |
|---|---|
| `asyncio` на Windows | `WindowsSelectorEventLoopPolicy` (совместимость с edge-tts/websockets) |
| Edge TTS сохраняет MP3 | pydub конвертирует MP3→WAV для RVC, pygame играет MP3 напрямую |
| Кириллица в type | pyperclip + Ctrl+V вместо pyautogui.write() |
| Volume keys | ctypes + WinAPI keybd_event (VK_VOLUME_UP/DOWN/MUTE) |
| Subprocess без консоли | CREATE_NO_WINDOW флаг |
| Шрифт иконки трея | Ищет arial/segoeui/tahoma в C:\\Windows\\Fonts |

---

## Настройки (config.py)

| Параметр | По умолчанию | Описание |
|---|---|---|
| `GEMINI_API_KEY` | `""` | API ключ от Google AI Studio |
| `WHISPER_MODEL` | `"base"` | tiny / base / small / medium |
| `WHISPER_DEVICE` | `"cuda"` | "cuda" или "cpu" |
| `WAKE_WORD` | `"аля"` | Слово-триггер |
| `EDGE_TTS_VOICE` | `"ru-RU-DariyaNeural"` | Голос Edge TTS |
| `RVC_ENABLED` | `True` | Использовать RVC |
| `RVC_PITCH` | `0` | Сдвиг тона (+6 = аниме-голос) |
| `VAD_THRESHOLD` | `0.02` | Чувствительность микрофона |
| `SCREEN_W/H` | `2560/1440` | Разрешение экрана |
