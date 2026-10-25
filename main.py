"""Точка входа голосового помощника.

Запуск:
    python main.py            # голосовой режим (нужен микрофон)
    python main.py --text     # текстовый режим — печатаем команды руками
    python main.py --lang en-US
"""

from __future__ import annotations

import argparse
import sys

from assistant.commands import execute, is_exit
from assistant.speaker import speak


def run_text_mode() -> None:
    speak("Привет! Текстовый режим. Пиши команды, 'стоп' — выйти.")
    while True:
        try:
            line = input("🗣  > ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if is_exit(line):
            speak("Пока! Выключаюсь.")
            break
        answer, ok = execute(line)
        speak(answer)


def run_voice_mode(lang: str) -> None:
    from assistant.listener import speech_loop  # импорт здесь: без PyAudio не падаем в --text
    speak("Привет! Я на связи. Говори команды.")
    try:
        for phrase in speech_loop(language=lang):
            print(f"👂 {phrase}")
            if is_exit(phrase):
                speak("Пока! Выключаюсь.")
                return
            answer, ok = execute(phrase)
            speak(answer)
    except RuntimeError as e:
        print(f"[!] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print()
    speak("До встречи!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Голосовой помощник")
    parser.add_argument("--text", action="store_true",
                        help="текстовый режим вместо микрофона")
    parser.add_argument("--lang", default="ru-RU",
                        help="язык распознавания (по умолчанию ru-RU)")
    args = parser.parse_args()

    if args.text:
        run_text_mode()
    else:
        run_voice_mode(args.lang)


if __name__ == "__main__":
    main()
