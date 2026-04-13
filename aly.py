"""
aly.py — точка входа, главный цикл

Запуск: python aly.py
Экстренная остановка: двинуть мышь в левый верхний угол экрана.
"""

import asyncio
import logging
import logging.handlers
import queue
import sys
import threading
import time

import config
import actions
import listener as listener_module
import vision
import voice
import tray as tray_module

# ------------------------------------------------------------------
# Логирование
# ------------------------------------------------------------------
def _setup_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Консоль
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Файл с ротацией
    fh = logging.handlers.RotatingFileHandler(
        config.LOG_FILE,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)


logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Глобальные объекты
# ------------------------------------------------------------------
command_queue: queue.Queue = queue.Queue()
is_speaking = threading.Event()
_paused = threading.Event()
_shutdown = threading.Event()


# ------------------------------------------------------------------
async def main():
    _setup_logging()
    logger.info("=" * 60)
    logger.info("Аля стартует...")
    logger.info("=" * 60)

    # 1. VTube Studio
    live2d = None
    try:
        from live2d import VTubeStudio
        live2d = VTubeStudio()
        await live2d.connect()
    except Exception as exc:
        logger.warning("Live2D недоступен: %s", exc)

    # 2. Голос (RVC загружается здесь)
    voice.init(is_speaking, live2d)

    # 3. Listener (Whisper на CUDA)
    listener = listener_module.Listener(command_queue, is_speaking)
    listener.start()

    # 4. Трей
    def on_quit():
        _shutdown.set()

    def on_pause(paused: bool):
        if paused:
            _paused.set()
            logger.info("Пауза")
        else:
            _paused.clear()
            logger.info("Возобновление")

    tray = tray_module.TrayIcon(on_quit_callback=on_quit, on_pause_callback=on_pause)
    tray.start()

    tray.set_status("listening")
    logger.info("Готов! Скажи «Аля, ...»")

    # ------------------------------------------------------------------
    # Главный цикл
    # ------------------------------------------------------------------
    while not _shutdown.is_set():
        # Ждём команду (неблокирующе, чтобы проверять _shutdown)
        try:
            command = command_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        # Пауза
        if _paused.is_set():
            logger.debug("На паузе, команда проигнорирована: %r", command)
            continue

        ts = time.strftime("%H:%M:%S")
        logger.info("[%s] Команда: %s", ts, command)

        # Думаем
        tray.set_status("thinking")
        result = vision.ask_gemini(command)

        ts = time.strftime("%H:%M:%S")
        logger.info("[%s] Ответ Gemini: %s", ts, result)

        # Выполняем действие
        try:
            reply = actions.execute(result)
        except Exception as exc:
            logger.error("Ошибка actions.execute: %s", exc)
            reply = result.get("reply", "")
            tray.set_status("error")
            await asyncio.sleep(2)

        # Эмоция → Live2D
        emotion = result.get("emotion", "neutral")
        if live2d and emotion and emotion != "neutral":
            asyncio.create_task(live2d.set_expression(emotion))

        # Голос
        if reply and config.VOICE_RESPONSE:
            tray.set_status("speaking")
            await voice.speak(reply)

        tray.set_status("listening")

    # ------------------------------------------------------------------
    logger.info("Завершение...")
    listener.stop()
    tray.stop()
    if live2d:
        await live2d.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Прерван пользователем (Ctrl+C)")
    except Exception as exc:
        logger.exception("Критическая ошибка: %s", exc)
        sys.exit(1)
