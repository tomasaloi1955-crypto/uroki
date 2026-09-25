# -*- coding: utf-8 -*-
"""
Облачный запуск: собрать N следующих уроков нужного языка и поставить
их в расписание канала. Компьютер не нужен — работает на GitHub.

    python build_and_publish.py en 3
    python build_and_publish.py es 3

Фото с лицами отклоняются при сборке, загруженные файлы удаляются.
"""

import sys

import publish
import shorts_core as core

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "en"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    lang = publish.lang_by_code(code)
    st = publish.load_state(lang)
    queue = [n for n in sorted(lang.lessons)
             if str(n) not in st["scheduled"]][:count]
    if not queue:
        print("Очередь пуста: все уроки уже в расписании.")
        return
    print(f"[{code}] в работе:", queue)
    for n in queue:
        core.build_short(lang, n)
    publish.schedule(lang, queue)


if __name__ == "__main__":
    main()
