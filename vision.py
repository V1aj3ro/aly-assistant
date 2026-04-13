"""
vision.py — скриншот + Ollama (локальная LLM, без API ключей)

ask_ollama(command, with_screenshot) → dict с action/reply/emotion
Модель: llava:7b (vision) или moondream (быстрее, легче)
"""

import re
import time
import json
import base64
import logging
from io import BytesIO

import mss
import requests
from PIL import Image

import config

logger = logging.getLogger(__name__)

_SYSTEM = f"""Ты — Аля, голосовой ассистент. Тебе дают скриншот экрана {config.SCREEN_W}x{config.SCREEN_H} (сжат до {config.SCREENSHOT_W}x{config.SCREENSHOT_H}) и команду пользователя.
{config.ALY_PERSONALITY}
Верни ТОЛЬКО валидный JSON без markdown, без пояснений.

Форматы action:
- click: {{"action":"click","x":INT,"y":INT,"reply":"текст"}}
- key:   {{"action":"key","key":"комбинация","reply":"текст"}}
- type:  {{"action":"type","text":"что напечатать","reply":"текст"}}
- scroll:{{"action":"scroll","x":INT,"y":INT,"clicks":INT,"reply":"текст"}}
- open:  {{"action":"open","program":"название","reply":"текст"}}
- speak: {{"action":"speak","reply":"текст"}}
- multi: {{"action":"multi","steps":[...],"reply":"текст"}}

Необязательное поле "emotion": "happy|sad|surprised|neutral"
ВАЖНО: координаты на скриншоте {config.SCREENSHOT_W}x{config.SCREENSHOT_H}, умножай на 2 для реального экрана."""

_last_request_time: float = 0.0


def _take_screenshot() -> str:
    """Скриншот → base64 JPEG."""
    with mss.mss() as sct:
        monitor = {"top": 0, "left": 0, "width": config.SCREEN_W, "height": config.SCREEN_H}
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    img = img.resize((config.SCREENSHOT_W, config.SCREENSHOT_H), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.b64encode(buf.getvalue()).decode()


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
    # Попробовать вырезать первый {...}
    m = re.search(r"\{[\s\S]+\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    logger.error("Не удалось распарсить JSON: %s", text[:300])
    return {"action": "speak", "reply": "Прости, не смогла понять ответ модели."}


def ask_ollama(command: str, with_screenshot: bool = True) -> dict:
    global _last_request_time

    elapsed = time.time() - _last_request_time
    if elapsed < config.OLLAMA_MIN_INTERVAL:
        time.sleep(config.OLLAMA_MIN_INTERVAL - elapsed)

    prompt = f"{_SYSTEM}\n\nКоманда: {command}"

    payload: dict = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",       # Ollama принудительно возвращает JSON
        "options": {
            "temperature": 0.1,
            "num_predict": 256,
        },
    }

    if with_screenshot:
        payload["images"] = [_take_screenshot()]

    try:
        resp = requests.post(
            f"{config.OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=config.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        _last_request_time = time.time()
        text = resp.json().get("response", "")
        result = _parse_json(text)
        logger.debug("Ollama: %s", result)
        return result
    except requests.exceptions.ConnectionError:
        logger.error("Ollama не запущен. Запусти: ollama serve")
        return {"action": "speak", "reply": "Ollama не запущен."}
    except Exception as exc:
        _last_request_time = time.time()
        logger.error("Ollama ошибка: %s", exc)
        return {"action": "speak", "reply": "Ошибка обращения к модели."}


# Алиас для совместимости с aly.py
def ask_gemini(command: str, with_screenshot: bool = True) -> dict:
    return ask_ollama(command, with_screenshot)
