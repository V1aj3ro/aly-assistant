"""
listener.py — микрофон + Whisper (Windows-версия)

- faster-whisper на CUDA (GTX 1080: float16)
- sounddevice для захвата аудио (WASAPI на Windows)
- VAD по RMS энергии
- Wake-word регуляркой с учётом транслитерации
- Пока Аля говорит (is_speaking) — не слушаем
"""

import logging
import queue
import re
import threading

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

import config

logger = logging.getLogger(__name__)


class Listener:
    def __init__(self, command_queue: queue.Queue, is_speaking_flag: threading.Event):
        self.command_queue = command_queue
        self.is_speaking = is_speaking_flag
        self._stop_event = threading.Event()
        self._wake_re = re.compile(config.WAKE_WORD_PATTERN, re.IGNORECASE)

        logger.info(
            "Загрузка Whisper '%s' на %s (%s)...",
            config.WHISPER_MODEL,
            config.WHISPER_DEVICE,
            config.WHISPER_COMPUTE_TYPE,
        )
        self.model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper загружен.")

    def start(self) -> threading.Thread:
        t = threading.Thread(target=self._listen_loop, daemon=True, name="Listener")
        t.start()
        return t

    def stop(self):
        self._stop_event.set()

    # ------------------------------------------------------------------
    def _listen_loop(self):
        chunk_samples = int(config.SAMPLE_RATE * config.CHUNK_DURATION)
        silence_chunks = int(config.VAD_SILENCE_DURATION / config.CHUNK_DURATION)

        logger.info("Слушаю микрофон (VAD порог=%.3f)...", config.VAD_THRESHOLD)

        recording = False
        silent_count = 0
        buffer: list[np.ndarray] = []

        # Windows: sounddevice автоматически использует WASAPI
        try:
            with sd.InputStream(
                samplerate=config.SAMPLE_RATE,
                channels=config.CHANNELS,
                dtype="float32",
                blocksize=chunk_samples,
            ) as stream:
                logger.info("Устройство: %s", sd.query_devices(kind="input")["name"])

                while not self._stop_event.is_set():
                    # Пока Аля говорит — сбрасываем буфер
                    if self.is_speaking.is_set():
                        try:
                            stream.read(chunk_samples)
                        except Exception:
                            pass
                        recording = False
                        buffer.clear()
                        silent_count = 0
                        continue

                    try:
                        chunk, _ = stream.read(chunk_samples)
                    except Exception as exc:
                        logger.error("sounddevice ошибка: %s", exc)
                        continue

                    chunk = chunk[:, 0]  # stereo → mono
                    rms = float(np.sqrt(np.mean(chunk ** 2)))

                    if rms > config.VAD_THRESHOLD:
                        if not recording:
                            logger.debug("VAD: начало речи (RMS=%.4f)", rms)
                            recording = True
                        silent_count = 0
                        buffer.append(chunk.copy())
                    else:
                        if recording:
                            silent_count += 1
                            buffer.append(chunk.copy())
                            if silent_count >= silence_chunks:
                                audio = np.concatenate(buffer)
                                buffer.clear()
                                recording = False
                                silent_count = 0
                                self._process_audio(audio)

        except Exception as exc:
            logger.error("Listener: критическая ошибка sounddevice: %s", exc)
            logger.info("Попробуй проверить устройство ввода в настройках Windows")

    # ------------------------------------------------------------------
    def _process_audio(self, audio: np.ndarray):
        if len(audio) < config.SAMPLE_RATE * 0.3:
            return  # слишком короткий звук

        try:
            segments, _ = self.model.transcribe(
                audio,
                language="ru",
                beam_size=5,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(s.text for s in segments).strip()
        except Exception as exc:
            logger.error("Whisper ошибка: %s", exc)
            return

        if not text:
            return

        logger.debug("Whisper: «%s»", text)

        match = self._wake_re.search(text)
        if not match:
            return

        command = text[match.end():].strip(" ,!?.")
        if not command:
            command = "привет"

        logger.info("Команда: «%s»", command)
        self.command_queue.put(command)
