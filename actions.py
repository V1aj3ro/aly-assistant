"""
actions.py — выполнение команд на ПК через pyautogui

Поддерживаемые action:
    click, key, type, scroll, open, speak, multi
"""

import os
import time
import logging
import subprocess

import pyautogui
import pyperclip

logger = logging.getLogger(__name__)

# Безопасность: failsafe — мышь в левый верхний угол останавливает программу
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def execute(action_json: dict) -> str:
    """Выполнить action и вернуть reply (строку для голоса)."""
    action = action_json.get("action", "speak")
    reply = action_json.get("reply", "")

    try:
        if action == "click":
            _do_click(action_json)
        elif action == "key":
            _do_key(action_json)
        elif action == "type":
            _do_type(action_json)
        elif action == "scroll":
            _do_scroll(action_json)
        elif action == "open":
            _do_open(action_json)
        elif action == "speak":
            pass  # только ответить
        elif action == "multi":
            _do_multi(action_json)
        else:
            logger.warning("Неизвестный action: %s", action)
    except pyautogui.FailSafeException:
        logger.warning("FailSafe сработал — мышь в углу экрана")
        raise
    except Exception as exc:
        logger.error("Ошибка выполнения action '%s': %s", action, exc)

    return reply


# ------------------------------------------------------------------
def _do_click(a: dict):
    x = int(a.get("x", 0))
    y = int(a.get("y", 0))
    logger.info("Click (%d, %d)", x, y)
    pyautogui.click(x, y, duration=0.2)


def _do_key(a: dict):
    key_str: str = a.get("key", "")
    logger.info("Key: %s", key_str)
    parts = [k.strip() for k in key_str.split("+")]
    if len(parts) > 1:
        pyautogui.hotkey(*parts)
    else:
        pyautogui.press(parts[0])


def _do_type(a: dict):
    text: str = a.get("text", "")
    logger.info("Type: %r", text)

    # Кириллица через буфер обмена
    has_cyrillic = any("\u0400" <= ch <= "\u04FF" for ch in text)
    if has_cyrillic:
        # Если в тексте есть \n — разбиваем и жмём Enter отдельно
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line:
                pyperclip.copy(line)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
            if i < len(lines) - 1:
                pyautogui.press("enter")
    else:
        pyautogui.write(text, interval=0.03)


def _do_scroll(a: dict):
    x = int(a.get("x", 0))
    y = int(a.get("y", 0))
    clicks = int(a.get("clicks", 3))
    logger.info("Scroll %d at (%d, %d)", clicks, x, y)
    pyautogui.scroll(clicks, x=x, y=y)


def _do_open(a: dict):
    program: str = a.get("program", "")
    logger.info("Open: %s", program)
    if os.path.exists(program):
        os.startfile(program)
    else:
        try:
            subprocess.Popen(program, shell=True)
        except Exception as exc:
            logger.error("Не удалось открыть '%s': %s", program, exc)


def _do_multi(a: dict):
    steps: list = a.get("steps", [])
    for step in steps:
        execute(step)
        time.sleep(0.3)
