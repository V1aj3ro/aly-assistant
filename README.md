# Аля — голосовой аниме ИИ-ассистент

Аля слушает тебя через микрофон, думает с помощью Gemini (видит твой экран), отвечает аниме-голосом и управляет ПК по команде. На рабочем столе живёт Live2D моделька, которая шевелит губами когда говорит.

```
Микрофон → Whisper → Gemini 2.0 Flash → Edge TTS → RVC → VTube Studio
                   ↓
              pyautogui (клики, клавиши, открытие программ)
```

---

## Установка

### 1. Python 3.10

Обязательно **Python 3.10** — rvc-python требует именно эту версию.

Скачать: https://www.python.org/downloads/release/python-3100/

Проверить версию:
```bash
python --version
# Python 3.10.x
```

---

### 2. CUDA Toolkit 11.8

Для GTX 1080 нужен CUDA 11.8.

Скачать: https://developer.nvidia.com/cuda-11-8-0-download-archive

Проверить:
```bash
nvcc --version
# Cuda compilation tools, release 11.8
```

---

### 3. PyTorch с CUDA

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

### 4. Зависимости

```bash
pip install -r requirements.txt
```

---

### 5. Gemini API ключ

1. Зайти на https://aistudio.google.com
2. Нажать **Get API Key** → **Create API Key**
3. Вставить в `config.py`:

```python
GEMINI_API_KEY = "AIza..."
```

Бесплатно, карта не нужна, лимит **1500 запросов в день**.

---

### 6. VTube Studio

1. Скачать бесплатно в **Steam** → VTube Studio
2. Загрузить Live2D модель. Рекомендуется **Hakui Koyori** (белые волосы):
   https://booth.pm/ja/items/3500430
3. В настройках VTS включить API:
   **Settings → Plugins → Enable Plugins** и **Start API (порт 8001)**
4. При первом запуске Али — подтвердить разрешение плагина во всплывающем окне VTS

Если VTube Studio не запущена — Аля продолжает работать без Live2D.

---

### 7. RVC модель голоса

1. Скачать аниме RVC модель:
   - https://huggingface.co/datasets/SayanoAI/RVC-Studio
   - Поиск: `"anime voice RVC model huggingface"`
2. Положить файлы в папку `models/rvc/`:
   ```
   models/rvc/voice.pth
   models/rvc/voice.index
   ```
3. Прописать пути в `config.py`:
   ```python
   RVC_MODEL_PATH = "models/rvc/voice.pth"
   RVC_INDEX_PATH = "models/rvc/voice.index"
   ```
4. Для аниме-голоса попробовать `RVC_PITCH = 6`
5. Если хочется только хороший голос без аниме-конвертации:
   ```python
   RVC_ENABLED = False
   ```
   Edge TTS с голосом `DariyaNeural` звучит хорошо и без RVC.

---

### 8. Запуск

```bash
python aly.py
```

Скажи **«Аля, привет»** для проверки.

---

## Команды

| Что сказать | Что сделает |
|---|---|
| Аля, пауза | Нажмёт пробел |
| Аля, громче | Нажмёт кнопку громкости |
| Аля, открой ютуб | Откроет YouTube в браузере |
| Аля, что на экране? | Опишет что видит на экране |
| Аля, закрой окно | Alt+F4 |
| Аля, следующая серия | Найдёт и нажмёт кнопку |
| Аля, напечатай [текст] | Напечатает текст (работает с кириллицей) |

Аля сама решает что именно делать — Gemini видит твой экран и подбирает правильное действие.

---

## Безопасность

- **Failsafe**: двинь мышь в **левый верхний угол** экрана — Аля немедленно остановится
- Иконка в трее: правой кнопкой → **Выход**
- `Ctrl+C` в терминале

---

## Структура проекта

```
aly/
├── aly.py           # точка входа, главный цикл
├── config.py        # все настройки
├── listener.py      # микрофон + Whisper (faster-whisper, CUDA)
├── vision.py        # скриншот + Gemini 2.0 Flash API
├── actions.py       # действия на ПК (click, key, type, scroll, open)
├── voice.py         # Edge TTS + RVC pipeline
├── live2d.py        # VTube Studio WebSocket API
├── tray.py          # иконка в трее
├── models/
│   └── rvc/         # сюда кладутся .pth и .index файлы RVC модели
└── requirements.txt
```

---

## Настройки (config.py)

| Параметр | По умолчанию | Описание |
|---|---|---|
| `GEMINI_API_KEY` | `""` | API ключ от Google AI Studio |
| `WHISPER_MODEL` | `"base"` | Размер модели: tiny/base/small/medium |
| `WAKE_WORD` | `"аля"` | Слово-триггер |
| `EDGE_TTS_VOICE` | `"ru-RU-DariyaNeural"` | Голос Edge TTS |
| `RVC_ENABLED` | `True` | Использовать RVC конвертацию |
| `RVC_PITCH` | `0` | Сдвиг тона (+6 = выше, аниме-голос) |
| `SCREEN_W/H` | `2560/1440` | Разрешение экрана |
| `VAD_THRESHOLD` | `0.02` | Чувствительность микрофона |

---

## Требования

- Windows 10/11
- Python 3.10
- NVIDIA GPU с CUDA 11.8+ (GTX 1080 и выше)
- Микрофон
- ~4GB VRAM (Whisper base + RVC)
