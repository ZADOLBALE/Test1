"""Разбор распознанной речи в команды и их выполнение.

Поддерживаемые команды (пока без голоса можно тестировать текстом):
  - "открой youtube" / "отключи ютуб"        -> открыть сайт по имени
  - "открой github.com/x"                     -> открыть произвольный URL
  - "найди котиков" / "загугли погоду"        -> поиск в Google
  - "открой файл readme"                      -> открыть файл из папки files/
  - "стоп" / "выход" / "пока"                 -> завершение работы
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser

# ---- словари соответствий: сказанное слово -> действие -------------------

SITES = {
    "ютуб": "https://www.youtube.com",
    "youtube": "https://www.youtube.com",
    "гугл": "https://www.google.com",
    "google": "https://www.google.com",
    "вконтакте": "https://vk.com",
    "ватсап": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "телеграм": "https://web.telegram.org",
    "github": "https://github.com",
    "гитхаб": "https://github.com",
    "habr": "https://habr.com",
    "хабр": "https://habr.com",
    "вики": "https://ru.wikipedia.org",
    "wikipedia": "https://ru.wikipedia.org",
    "авито": "https://www.avito.ru",
    "ozon": "https://www.ozon.ru",
    "netflix": "https://www.netflix.com",
    "нетфликс": "https://www.netflix.com",
    "почта": "https://mail.yandex.ru",
    "yandex": "https://yandex.ru",
    "яндекс": "https://yandex.ru",
}

EXIT_WORDS = {"стоп", "выход", "пока", "закройся", "stop", "exit"}

# короткие слова-команды выхода допускаются только как отдельное слово,
# чтобы "найди сайты с выходом в сеть" не выключало помощника

# папка, из которой помощник умеет открывать файлы
FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "files")


def _norm(text: str) -> str:
    """Привести фразу к нижнему регистру, убрать лишние пробелы/знаки."""
    text = text.lower().strip()
    text = re.sub(r"[?!.,;:]+", " ", text)
    return re.sub(r"\s+", " ", text)


def _open(url: str) -> tuple[str, bool]:
    """Открыть URL: сначала через браузер системы, иначе — subprocess.

    Возвращает (текст ответа, success). Если открыть нечем (например, запуск
    в контейнере без X11), возвращает ссылку — на машине с браузером всё
    откроется, а в логе будет видно, что именно помощник хотел открыть.
    """
    try:
        opened = webbrowser.open(url)
    except Exception:
        opened = False
    if not opened:
        opener = None
        if sys.platform.startswith("win"):
            opener = ["cmd", "/c", "start", "", url]
        elif sys.platform == "darwin":
            opener = ["open", url]
        else:
            browser = (shutil.which("xdg-open") or shutil.which("firefox")
                       or shutil.which("chromium") or shutil.which("google-chrome"))
            if browser is None:
                return f"Браузер не найден. Ссылка: {url}", False
            opener = [browser, url]
        try:
            subprocess.Popen(opener)
        except OSError:
            return f"Не удалось запустить браузер. Ссылка: {url}", False
    return f"Открываю {url}", True


def _find_file(name: str) -> str | None:
    """Найти файл в files/ по подстроке имени (без учёта регистра)."""
    name = _norm(name)
    files_dir = os.path.abspath(FILES_DIR)
    if not os.path.isdir(files_dir):
        return None
    candidates = [f for f in os.listdir(files_dir) if name in f.lower()]
    if not candidates:
        # попробуем по словам: "открой файл мой рецепт.txt" -> совпадение по любому слову
        words = [w for w in name.split() if len(w) > 3]
        candidates = [f for f in os.listdir(files_dir)
                      if any(w in f.lower() for w in words)]
    if not candidates:
        return None
    return os.path.join(files_dir, sorted(candidates)[0])


def is_exit(text: str) -> bool:
    """True, если фраза — команда выхода (сказана отдельными словами)."""
    words = _norm(text).split()
    return bool(words) and all(w in EXIT_WORDS for w in words[:2])


def execute(text: str) -> tuple[str, bool]:
    """Выполнить команду.

    Возвращает (ответ для озвучки, success). Завершение программы main.py
    определяет отдельно через is_exit() — здесь success означает, что
    действие удалось.
    """
    t = _norm(text)
    if not t:
        return "Я не расслышала.", False

    # "открой файл X"
    m = re.search(r"(?:открой|найди мне)?\s*файл\s+(.+)", t)
    if m:
        path = _find_file(m.group(1))
        if path is None:
            return f"Файл «{m.group(1)}» не найден в папке files.", False
        opened = False
        if sys.platform.startswith("win"):
            try:
                os.startfile(path)  # type: ignore[attr-defined]
                opened = True
            except OSError:
                opened = False
        else:
            opener = shutil.which("xdg-open") or shutil.which("open")
            if opener:
                try:
                    subprocess.Popen([opener, path])
                    opened = True
                except OSError:
                    opened = False
        if not opened:
            return f"Файл найден, но нечем открыть: {path}", False
        return f"Открываю файл {os.path.basename(path)}.", True

    # "найди X" / "загугли X" / "поищи X" -> google
    m = re.search(r"(?:найди|загугли|поищи|ищи|search)\s+(.+)", t)
    if m and "файл" not in t:
        query = urllib.parse.quote_plus(m.group(1).strip())
        msg, ok = _open(f"https://www.google.com/search?q={query}")
        return f"{msg}.", ok

    # "открой сайт/страницу X" — слово «сайт» не входит в словарь, ищем дальше
    m = re.search(r"(?:открой|запусти|отвори|открыть)\s+(?:\S+\s+)?(.+)", t)
    if m:
        target = m.group(1).strip()
        if re.match(r"^[\w-]+(\.[\w-]+)+(/.*)?$", target):
            url = target if target.startswith("http") else "https://" + target
            msg, ok = _open(url)
            return f"{msg}.", ok
        for word, url in SITES.items():
            if word in target.split():
                msg, ok = _open(url)
                return f"{msg}.", ok
        # не сайт и не файл — просто поищем в гугле
        msg, ok = _open(f"https://www.google.com/search?q={urllib.parse.quote_plus(target)}")
        return f"{msg}.", ok

    return (f"Команда не распознана: «{t}». Скажите, например: открой ютуб, "
            "найди погоду, открой файл readme."), False


if __name__ == "__main__":
    # ручной тест без микрофона: python -m assistant.commands
    from assistant.commands import is_exit  # noqa: E402 (для наглядности)
    print("Тест командного модуля ('стоп' или пустая строка — выход):")
    while True:
        line = input("> ")
        if not line or is_exit(line):
            print("Выход.")
            break
        answer, ok = execute(line)
        print(answer)
