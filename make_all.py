# -*- coding: utf-8 -*-
"""
Пакетная сборка: все уроки (arabic_*.json, lesson_*.json) -> видео + нарезки.

Уже собранные уроки пропускаются, поэтому скрипт можно запускать сколько
угодно раз — дособерёт только новое. Полная сборка 30 уроков занимает
несколько часов (озвучка через интернет) — удобно запустить на ночь:

    python make_all.py            # собрать всё, чего не хватает
    python make_all.py --force    # пересобрать вообще всё заново
"""

import asyncio
import sys
from pathlib import Path

from make_lesson import build as build_lesson
from make_shorts import build_shorts


def main():
    force = "--force" in sys.argv
    jsons = sorted(Path(".").glob("arabic_*.json")) + sorted(Path(".").glob("lesson_*.json"))
    print(f"Найдено уроков: {len(jsons)}\n")

    done, skipped, failed = 0, 0, []
    for j in jsons:
        final = Path("build") / j.stem / "lesson.mp4"
        if final.exists() and not force:
            print(f"— {j.name}: уже собран, пропускаю")
            skipped += 1
        else:
            print(f"=== Собираю {j.name} ===")
            try:
                asyncio.run(build_lesson(str(j)))
                done += 1
            except Exception as e:
                print(f"!!! Ошибка на {j.name}: {e}")
                failed.append(j.name)
                continue

        shorts_dir = Path("build") / j.stem / "shorts"
        if not shorts_dir.exists() or force or not any(shorts_dir.glob("*.mp4")):
            try:
                asyncio.run(build_shorts(str(j)))
            except Exception as e:
                print(f"!!! Ошибка нарезки {j.name}: {e}")
                failed.append(j.name + " (shorts)")

    print(f"\nИтог: собрано {done}, пропущено {skipped}, ошибок {len(failed)}")
    for f in failed:
        print(f"  ошибка: {f}")


if __name__ == "__main__":
    main()
