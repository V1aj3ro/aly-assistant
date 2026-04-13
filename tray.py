"""
tray.py — системный трей (Windows)

Иконка — круг с буквой А:
  listening → зелёный
  thinking  → жёлтый
  speaking  → оранжевый
  error     → красный
  paused    → серый
"""

import logging
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import pystray

logger = logging.getLogger(__name__)

STATUS_COLORS = {
    "listening": (76,  175, 80),
    "thinking":  (255, 193,  7),
    "speaking":  (255, 152,  0),
    "error":     (244,  67, 54),
    "paused":    (120, 120, 120),
}

# Шрифты Windows (по убыванию предпочтительности)
_WINDOWS_FONTS = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
    r"C:\Windows\Fonts\verdana.ttf",
]


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _WINDOWS_FONTS:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _make_icon(status: str) -> Image.Image:
    size = 64
    color = STATUS_COLORS.get(status, STATUS_COLORS["paused"])

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color)

    font = _get_font(28)
    text = "А"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), text, fill=(255, 255, 255), font=font)

    return img


class TrayIcon:
    def __init__(self, on_quit_callback=None, on_pause_callback=None):
        self._status = "paused"
        self._paused = False
        self._on_quit = on_quit_callback
        self._on_pause = on_pause_callback
        self._icon: pystray.Icon | None = None

    def start(self):
        t = threading.Thread(target=self._run, daemon=True, name="Tray")
        t.start()

    def _run(self):
        menu = pystray.Menu(
            pystray.MenuItem("Пауза / Продолжить", self._toggle_pause),
            pystray.MenuItem(
                "Статус",
                lambda icon, item: logger.info("Статус: %s", self._status),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._quit),
        )

        self._icon = pystray.Icon(
            name="Аля",
            icon=_make_icon("paused"),
            title="Аля — голосовой ассистент",
            menu=menu,
        )
        self._icon.run()

    def set_status(self, status: str):
        self._status = status
        if self._icon:
            self._icon.icon = _make_icon(status)
            self._icon.title = f"Аля — {status}"

    def _toggle_pause(self, icon, item):
        self._paused = not self._paused
        self.set_status("paused" if self._paused else "listening")
        if self._on_pause:
            self._on_pause(self._paused)

    def _quit(self, icon, item):
        logger.info("Завершение через трей...")
        icon.stop()
        if self._on_quit:
            self._on_quit()

    def stop(self):
        if self._icon:
            self._icon.stop()
