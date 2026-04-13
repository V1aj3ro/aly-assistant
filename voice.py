"""
voice.py — Edge TTS + RVC pipeline

speak(text) — синтезирует речь, конвертирует через RVC (если включён),
воспроизводит и уведомляет Live2D о движении губ.
"""

import asyncio
import logging
import tempfile
import threading
import os

import edge_tts
import sounddevice as sd
import soundfile as sf
import numpy as np

import config

logger = logging.getLogger(__name__)

# Глобальный флаг «говорит» для listener.py
_is_speaking: threading.Event | None = None

# Live2D — устанавливается из aly.py
_live2d = None

# RVC модель — загружается один раз
_rvc = None


def init(is_speaking_flag: threading.Event, live2d_instance=None):
    """Вызвать один раз при старте."""
    global _is_speaking, _live2d, _rvc
    _is_speaking = is_speaking_flag
    _live2d = live2d_instance

    if config.RVC_ENABLED:
        _load_rvc()


def _load_rvc():
    global _rvc
    try:
        from rvc_python.infer import RVCInference
        _rvc = RVCInference(device="cuda:0")
        _rvc.load_model(config.RVC_MODEL_PATH, index_path=config.RVC_INDEX_PATH)
        logger.info("RVC модель загружена: %s", config.RVC_MODEL_PATH)
    except Exception as exc:
        logger.error("Не удалось загрузить RVC: %s. Используем Edge TTS напрямую.", exc)
        _rvc = None


# ------------------------------------------------------------------
async def speak(text: str):
    """Основная функция озвучки."""
    if not text:
        return

    if _is_speaking:
        _is_speaking.set()

    try:
        tts_path = await _edge_tts(text)

        if config.RVC_ENABLED and _rvc is not None:
            audio_path = _apply_rvc(tts_path)
        else:
            audio_path = tts_path

        duration = _get_duration(audio_path)

        # Уведомить Live2D — начало речи
        if _live2d is not None:
            asyncio.create_task(_live2d.start_talking())

        _play_audio(audio_path)

        # Уведомить Live2D — конец речи
        if _live2d is not None:
            asyncio.create_task(_live2d.stop_talking())

        # Cleanup
        for path in {tts_path, audio_path}:
            try:
                os.remove(path)
            except Exception:
                pass

    except Exception as exc:
        logger.error("Ошибка speak(): %s", exc)
    finally:
        if _is_speaking:
            _is_speaking.clear()


async def _edge_tts(text: str) -> str:
    """Синтез через Edge TTS → временный WAV файл."""
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()

    communicate = edge_tts.Communicate(text, config.EDGE_TTS_VOICE)
    await communicate.save(tmp.name)
    logger.debug("Edge TTS сохранён: %s", tmp.name)
    return tmp.name


def _apply_rvc(input_path: str) -> str:
    """Конвертация через RVC."""
    out = tempfile.NamedTemporaryFile(suffix="_rvc.wav", delete=False)
    out.close()
    try:
        _rvc.infer_file(
            input_path=input_path,
            output_path=out.name,
            f0_up_key=config.RVC_PITCH,
            f0_method=config.RVC_METHOD,
            index_rate=config.RVC_INDEX_RATE,
        )
        logger.debug("RVC конвертирован: %s", out.name)
        return out.name
    except Exception as exc:
        logger.error("RVC ошибка: %s. Используем оригинал.", exc)
        return input_path


def _get_duration(path: str) -> float:
    try:
        import librosa
        duration, _ = librosa.load(path, sr=None)
        return librosa.get_duration(y=duration)
    except Exception:
        return 3.0  # fallback


def _play_audio(path: str):
    """Воспроизведение через sounddevice."""
    try:
        data, samplerate = sf.read(path, dtype="float32")
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        sd.play(data, samplerate=samplerate)
        sd.wait()
    except Exception as exc:
        logger.error("Ошибка воспроизведения: %s", exc)


# Синхронная обёртка для вызова из не-async контекста
def speak_sync(text: str):
    asyncio.run(speak(text))
