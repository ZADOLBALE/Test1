"""Распознавание речи с микрофона (SpeechRecognition + Google Web Speech API).

Если микрофона нет или нет сети — запустите main.py с флагом --text
и печатайте команды руками.
"""

from __future__ import annotations

from typing import Iterator

import speech_recognition as sr


def make_listener(language: str = "ru-RU") -> tuple[sr.Recognizer, sr.Microphone | None]:
    """Создать распознаватель и микрофон. Микрофон может быть недоступен."""
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    try:
        mic = sr.Microphone()
    except OSError:
        mic = None
    return recognizer, mic


def listen_once(recognizer: sr.Recognizer, mic: sr.Microphone,
                language: str = "ru-RU", timeout: float = 8.0,
                phrase_time_limit: float = 6.0) -> str | None:
    """Одно ожидание речи -> текст (или None, если тишина/шум)."""
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        try:
            audio = recognizer.listen(source, timeout=timeout,
                                      phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError:
            return None
    try:
        # бесплатный онлайн-распознаватель Google
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        print(f"[!] Проблема с сервисом распознавания: {e}")
        return None


def speech_loop(language: str = "ru-RU") -> Iterator[str]:
    """Бесконечный генератор: слушает микрофон и выдаёт распознанные фразы."""
    recognizer, mic = make_listener(language)
    if mic is None:
        raise RuntimeError(
            "Микрофон не найден. Запустите с --text и печатайте команды вручную."
        )
    print("🎙  Слушаю... говорите команду (пауза = отправка).")
    while True:
        text = listen_once(recognizer, mic, language=language)
        if text:
            yield text
