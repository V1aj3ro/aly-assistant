"""
vision.py — скриншот + Gemini API (google-genai SDK)

ask_gemini(command, with_screenshot) → dict с action/reply/emotion
"""

import re
import time
import json
import logging
from io import BytesIO

import mss
from PIL import Image
from google import genai
from google.genai import types

import config

logger = logging.getLogger(__name__)

# Системный промпт
_SYSTEM = f"""
Ты — Аля, голосовой ассистент. Тебе дают скриншот экрана {config.SCREEN_W}x{config.SCREEN_H}
(сжат до {config.SCREENSHOT_W}x{config.SCREENSHOT_H}) и команду пользователя.
Верни ТОЛЬКО валидный JSON без markdown, без пояснений.

{config.ALY_PERSONALITY}

Доступные форматы action:
- click: {{"action":"click","x":INT,"y":INT,"reply":"текст"}}
- key:   {{"action":"key","key":"комбинация","reply":"текст"}}
- type:  {{"action":"type","text":"что напечатать","reply":"текст"}}
- scroll:{{"action":"scroll","x":INT,"y":INT,"clicks":INT,"reply":"текст"}}
- open:  {{"action":"open","program":"название или путь","reply":"текст"}}
- speak: {{"action":"speak","reply":"текст"}}
- multi: {{"action":"multi","steps":[...список действий...],"reply":"текст"}}

Необязательное поле "emotion": "happy|sad|surprised|neutral"

ВАЖНО: координаты на скриншоте {config.SCREENSHOT_W}x{config.SCREENSHOT_H},
умножай на 2 для реального экрана {config.SCREEN_W}x{config.SCREEN_H}.

Примеры:
"пропусти опенинг" → {{"action":"click","x":РЕАЛЬНЫЙ_X,"y":РЕАЛЬНЫЙ_Y,"reply":"Пропускаю!"}}
"пауза" → {{"action":"key","key":"space","reply":"Пауза"}}
"открой ютуб" → {{"action":"multi","steps":[{{"action":"key","key":"ctrl+t"}},{{"action":"type","text":"youtube.com\\n"}}],"reply":"Открываю"}}
"громче" → {{"action":"key","key":"volumeup","reply":"Громче!"}}
"что на экране" → {{"action":"speak","reply":"подробное описание"}}
"""

_client = genai.Client(api_key=config.GEMINI_API_KEY)
_last_request_time: float = 0.0


def _take_screenshot() -> bytes:
    """Скриншот через mss, сжатый до SCREENSHOT_W x SCREENSHOT_H, JPEG bytes."""
    with mss.mss() as sct:
        monitor = {"top": 0, "left": 0, "width": config.SCREEN_W, "height": config.SCREEN_H}
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    img = img.resize((config.SCREENSHOT_W, config.SCREENSHOT_H), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _parse_json(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    logger.error("Не удалось распарсить JSON: %s", text[:200])
    return {"action": "speak", "reply": "Прости, что-то пошло не так."}


def ask_gemini(command: str, with_screenshot: bool = True) -> dict:
    global _last_request_time

    elapsed = time.time() - _last_request_time
    if elapsed < config.GEMINI_MIN_INTERVAL:
        time.sleep(config.GEMINI_MIN_INTERVAL - elapsed)

    contents = []

    if with_screenshot:
        jpeg_bytes = _take_screenshot()
        contents.append(types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"))

    contents.append(types.Part.from_text(text=f"Команда: {command}"))

    try:
        response = _client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM,
                temperature=0.3,
            ),
        )
        _last_request_time = time.time()
        result = _parse_json(response.text)
        logger.debug("Gemini: %s", result)
        return result
    except Exception as exc:
        _last_request_time = time.time()
        logger.error("Gemini ошибка: %s", exc)
        return {"action": "speak", "reply": "Ошибка обращения к Gemini."}
