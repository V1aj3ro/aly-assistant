"""
voice.py — Edge TTS + RVC pipeline (Windows-совместимая версия)

Edge TTS сохраняет MP3, не WAV.
Воспроизведение через pygame.mixer (поддерживает MP3 и WAV на Windows).
RVC работает с WAV → конвертируем MP3→WAV через pydub.
"""

import asyncio
import logging
import os
import tempfile
import threading
import time

import edge_tts
import pygame

import config

logger = logging.getLogger(__name__)

# Глобальные объекты
_is_speaking: threading.Event | None = None
_live2d = None
_rvc = None

# Инициализация pygame.mixer один раз
pygame.mixer.pre_init(frequency=44100, size=-16, channels=1, buffer=512)
pygame.mixer.init()


def init(is_speaking_flag: threading.Event, live2d_instance=None):
    """Вызвать один раз при старте."""
    global _is_speaking, _live2d, _rvc
    _is_speaking = is_speaking_flag
    _live2d = live2d_instance

    if config.RVC_ENABLED:
        _load_rvc()


def _load_rvc():
    global _rvc
    if not os.path.exists(config.RVC_MODEL_PATH):
        logger.warning("RVC модель не найдена: %s. RVC отключён.", config.RVC_MODEL_PATH)
        return
    try:
        from rvc_python.infer import RVCInference
        _rvc = RVCInference(device="cuda:0")
        _rvc.load_model(config.RVC_MODEL_PATH, index_path=config.RVC_INDEX_PATH)
        logger.info("RVC модель загружена: %s", config.RVC_MODEL_PATH)
    except Exception as exc:
        logger.error("Не удалось загрузить RVC: %s. Edge TTS напрямую.", exc)
        _rvc = None


# ------------------------------------------------------------------
async def speak(text: str):
    """Синтез, конвертация, воспроизведение."""
    if not text:
        return

    if _is_speaking:
        _is_speaking.set()

    mp3_path = None
    wav_path = None

    try:
        # 1. Edge TTS → MP3
        mp3_path = await _edge_tts_mp3(text)

        # 2. RVC требует WAV → конвертируем
        if config.RVC_ENABLED and _rvc is not None:
            wav_path = _mp3_to_wav(mp3_path)
            audio_path = _apply_rvc(wav_path)
        else:
            audio_path = mp3_path

        # 3. Длительность для Live2D
        duration = _get_duration(audio_path)

        # 4. Live2D — начало речи
        if _live2d is not None:
            asyncio.create_task(_live2d.start_talking())

        # 5. Воспроизведение (блокирующее, но мы уже в async)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _play_audio, audio_path)

        # 6. Live2D — конец речи
        if _live2d is not None:
            asyncio.create_task(_live2d.stop_talking())

    except Exception as exc:
        logger.error("speak() ошибка: %s", exc)
    finally:
        if _is_speaking:
            _is_speaking.clear()
        # Cleanup временных файлов
        for path in filter(None, [mp3_path, wav_path]):
            try:
                os.remove(path)
            except Exception:
                pass


async def _edge_tts_mp3(text: str) -> str:
    """Edge TTS → временный MP3."""
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp.close()
    communicate = edge_tts.Communicate(text, config.EDGE_TTS_VOICE)
    await communicate.save(tmp.name)
    logger.debug("Edge TTS: %s", tmp.name)
    return tmp.name


def _mp3_to_wav(mp3_path: str) -> str:
    """Конвертация MP3 → WAV через pydub (нужен ffmpeg)."""
    from pydub import AudioSegment
    wav_path = mp3_path.replace(".mp3", "_src.wav")
    AudioSegment.from_mp3(mp3_path).export(wav_path, format="wav")
    return wav_path


def _apply_rvc(input_path: str) -> str:
    """RVC конвертация голоса."""
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
        logger.debug("RVC: %s", out.name)
        return out.name
    except Exception as exc:
        logger.error("RVC ошибка: %s. Используем оригинал.", exc)
        try:
            os.remove(out.name)
        except Exception:
            pass
        return input_path


def _get_duration(path: str) -> float:
    """Длительность аудио в секундах."""
    try:
        # pygame может определить длину без librosa
        snd = pygame.mixer.Sound(path)
        return snd.get_length()
    except Exception:
        try:
            import soundfile as sf
            info = sf.info(path)
            return info.duration
        except Exception:
            return 3.0


def _play_audio(path: str):
    """Воспроизведение через pygame.mixer (поддерживает MP3 и WAV)."""
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        # Ждём окончания
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    except Exception as exc:
        logger.error("Ошибка воспроизведения: %s", exc)
    finally:
        try:
            pygame.mixer.music.unload()
        except Exception:
            pass
