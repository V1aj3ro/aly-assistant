"""
listener.py — микрофон + Whisper (faster-whisper, CUDA)

Алгоритм:
1. Читаем чанки с микрофона через sounddevice
2. VAD по энергетическому порогу (RMS)
3. Когда VAD срабатывает — накапливаем аудио
4. После 1.5 сек тишины — отправляем в Whisper
5. Ищем wake-word регуляркой
6. Кладём чистую команду в command_queue
"""

import re
import queue
import logging
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

        logger.info("Загрузка Whisper модели '%s' на %s...", config.WHISPER_MODEL, config.WHISPER_DEVICE)
        self.model = WhisperModel(
            config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Whisper загружен.")

        self._wake_re = re.compile(config.WAKE_WORD_PATTERN, re.IGNORECASE)

    # ------------------------------------------------------------------
    def start(self):
        t = threading.Thread(target=self._listen_loop, daemon=True, name="Listener")
        t.start()
        return t

    def stop(self):
        self._stop_event.set()

    # ------------------------------------------------------------------
    def _listen_loop(self):
        chunk_samples = int(config.SAMPLE_RATE * config.CHUNK_DURATION)
        silence_chunks = int(config.VAD_SILENCE_DURATION / config.CHUNK_DURATION)

        logger.info("Слушаю микрофон (порог VAD=%.3f)...", config.VAD_THRESHOLD)

        recording = False
        silent_count = 0
        buffer: list[np.ndarray] = []

        with sd.InputStream(
            samplerate=config.SAMPLE_RATE,
            channels=config.CHANNELS,
            dtype="float32",
            blocksize=chunk_samples,
        ) as stream:
            while not self._stop_event.is_set():
                # Пока Аля говорит — не слушаем
                if self.is_speaking.is_set():
                    stream.read(chunk_samples)  # сбросить буфер
                    recording = False
                    buffer.clear()
                    silent_count = 0
                    continue

                chunk, _ = stream.read(chunk_samples)
                chunk = chunk[:, 0]  # mono
                rms = float(np.sqrt(np.mean(chunk ** 2)))

                if rms > config.VAD_THRESHOLD:
                    if not recording:
                        logger.debug("VAD: начало речи (RMS=%.4f)", rms)
                        recording = True
                    silent_count = 0
                    buffer.append(chunk)
                else:
                    if recording:
                        silent_count += 1
                        buffer.append(chunk)
                        if silent_count >= silence_chunks:
                            # Достаточно тишины — транскрибируем
                            audio = np.concatenate(buffer)
                            buffer.clear()
                            recording = False
                            silent_count = 0
                            self._process_audio(audio)

    # ------------------------------------------------------------------
    def _process_audio(self, audio: np.ndarray):
        try:
            segments, _ = self.model.transcribe(
                audio,
                language="ru",
                beam_size=5,
                vad_filter=True,
            )
            text = " ".join(s.text for s in segments).strip()
        except Exception as exc:
            logger.error("Whisper ошибка: %s", exc)
            return

        if not text:
            return

        logger.debug("Whisper: «%s»", text)

        # Ищем wake-word
        match = self._wake_re.search(text)
        if not match:
            return

        # Вырезаем wake-word и всё до него
        command = text[match.end():].strip(" ,!?.")
        if not command:
            command = "привет"

        logger.info("Команда: «%s»", command)
        self.command_queue.put(command)
