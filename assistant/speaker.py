"""Озвучка ответов помощника.

Порождающий выбор движка:
  1. pyttsx3 (офлайн, SAPI/eSpeak)
  2. say (macOS)
  3. espeak / espeak-ng (Linux)
  Если ничего нет — просто печатаем текст.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

_engine = None


def _init_pyttsx3():
    global _engine
    try:
        import pyttsx3
        _engine = pyttsx3.init()
        # попробуем русский голос, если он есть
        for vid in _engine.getProperty("voices"):
            lang = getattr(getattr(vid, "languages", ""), "value", "") or ""
            if "ru" in lang.lower() or "ru" in (vid.id or "").lower():
                _engine.setProperty("voice", vid.id)
                break
    except Exception:
        _engine = None


def speak(text: str) -> None:
    """Произнести текст доступным способом."""
    print(f"🔊 {text}")

    if sys.platform.startswith("win"):
        if _engine is None:
            _init_pyttsx3()
        if _engine is not None:
            try:
                _engine.say(text)
                _engine.runAndWait()
                return
            except Exception:
                pass

    if sys.platform == "darwin" and shutil.which("say"):
        subprocess.Popen(["say", "-v", "Milena", text])
        return

    for cmd in ("espeak-ng", "espeak"):
        if shutil.which(cmd):
            subprocess.Popen([cmd, "-v", "ru", text])
            return

    # озвучки нет — текст уже напечатан выше


if __name__ == "__main__":
    speak("Привет! Я твой голосовой помощник.")
