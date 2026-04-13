"""
actions.py — выполнение команд на ПК (Windows-версия)

Особенности Windows:
- subprocess с CREATE_NO_WINDOW (без мигающей консоли)
- volume keys через ctypes (WinAPI), pyautogui их не поддерживает
- кириллица через pyperclip + Ctrl+V
- os.startfile() для открытия файлов/программ
"""

import ctypes
import logging
import os
import subprocess
import time

import pyautogui
import pyperclip

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

# Windows VK коды для медиа-клавиш
_VK_MEDIA = {
    "volumeup":   0xAF,
    "volumedown": 0xAE,
    "volumemute": 0xAD,
    "playpause":  0xB3,
    "nexttrack":  0xB0,
    "prevtrack":  0xB1,
    "stop":       0xB2,
}

# Псевдонимы клавиш
_KEY_ALIASES = {
    "пробел":   "space",
    "enter":    "enter",
    "ввод":     "enter",
    "escape":   "escape",
    "esc":      "escape",
    "backspace": "backspace",
    "delete":   "delete",
    "tab":      "tab",
    "home":     "home",
    "end":      "end",
    "pgup":     "pageup",
    "pgdown":   "pagedown",
}


def execute(action_json: dict) -> str:
    """Выполнить action и вернуть reply."""
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
            pass
        elif action == "multi":
            _do_multi(action_json)
        else:
            logger.warning("Неизвестный action: %s", action)
    except pyautogui.FailSafeException:
        logger.warning("FailSafe: мышь в углу экрана")
        raise
    except Exception as exc:
        logger.error("Ошибка action '%s': %s", action, exc)

    return reply


# ------------------------------------------------------------------
def _do_click(a: dict):
    x, y = int(a.get("x", 0)), int(a.get("y", 0))
    logger.info("Click (%d, %d)", x, y)
    pyautogui.click(x, y, duration=0.15)


def _do_key(a: dict):
    key_str: str = a.get("key", "").strip().lower()
    logger.info("Key: %s", key_str)

    # Медиа-клавиши через WinAPI
    if key_str in _VK_MEDIA:
        _send_media_key(_VK_MEDIA[key_str])
        return

    # Псевдонимы
    key_str = _KEY_ALIASES.get(key_str, key_str)

    parts = [k.strip() for k in key_str.split("+")]
    if len(parts) > 1:
        pyautogui.hotkey(*parts)
    else:
        pyautogui.press(parts[0])


def _send_media_key(vk_code: int):
    """Нажать медиа-клавишу через WinAPI (keybd_event)."""
    KEYEVENTF_KEYDOWN = 0x0000
    KEYEVENTF_KEYUP   = 0x0002
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYDOWN, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _do_type(a: dict):
    text: str = a.get("text", "")
    logger.info("Type: %r", text)

    has_cyrillic = any("\u0400" <= ch <= "\u04FF" for ch in text)

    if has_cyrillic:
        # Кириллица только через буфер обмена
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if line:
                old_clip = _safe_get_clipboard()
                pyperclip.copy(line)
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
                # Восстанавливать буфер не будем — пользователь ожидает печати
            if i < len(lines) - 1:
                pyautogui.press("enter")
                time.sleep(0.05)
    else:
        # Латиница + цифры — напрямую
        # Если есть \n — разбиваем
        parts = text.split("\n")
        for i, part in enumerate(parts):
            if part:
                pyautogui.write(part, interval=0.02)
            if i < len(parts) - 1:
                pyautogui.press("enter")


def _safe_get_clipboard() -> str:
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _do_scroll(a: dict):
    x = int(a.get("x", 0))
    y = int(a.get("y", 0))
    clicks = int(a.get("clicks", 3))
    logger.info("Scroll %d at (%d, %d)", clicks, x, y)
    pyautogui.scroll(clicks, x=x, y=y)


def _do_open(a: dict):
    program: str = a.get("program", "").strip()
    logger.info("Open: %s", program)

    if not program:
        return

    # Если это существующий файл/папка — os.startfile
    if os.path.exists(program):
        os.startfile(program)
        return

    # Иначе — запуск через shell (работает для notepad, chrome, etc.)
    try:
        subprocess.Popen(
            program,
            shell=True,
            creationflags=subprocess.CREATE_NO_WINDOW,  # без мигающей консоли
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        logger.error("Не удалось открыть '%s': %s", program, exc)


def _do_multi(a: dict):
    steps: list = a.get("steps", [])
    for step in steps:
        execute(step)
        time.sleep(0.3)
