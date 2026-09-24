# -*- coding: utf-8 -*-
"""
Облачный запуск: собрать N следующих уроков и поставить их в расписание
канала Easy_arabic. Компьютер для этого не нужен — работает на GitHub.

    python build_and_publish_en.py 3

Ролик, в фоне которого нашлось лицо, не соберётся с этим фото: проверка
лиц стоит внутри shorts_en. Загруженные файлы удаляются сразу.
"""

import sys

import publish_en
from shorts_en import LESSONS, build_short

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    st = publish_en.load_state()
    queue = [n for n in sorted(LESSONS) if str(n) not in st["scheduled"]][:count]
    if not queue:
        print("Очередь пуста: все уроки уже в расписании.")
        return
    print("В работе:", queue)
    for n in queue:
        build_short(n)
    publish_en.main_schedule(queue)


if __name__ == "__main__":
    main()
