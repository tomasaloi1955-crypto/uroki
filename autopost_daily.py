# -*- coding: utf-8 -*-
"""
Дневной автопостинг. Один запуск = один день контента:

  1. YouTube: следующий по очереди ПОЛНЫЙ урок (arabic_001 -> 002 -> ... -> 030,
     потом lesson_001...)
  2. TikTok: следующая по очереди КОРОТКАЯ нарезка (из shorts всех уроков)

Что уже запощено — помнит в post_log.json, поэтому запускать можно хоть
каждый день по расписанию, хоть вручную. Видео должны быть заранее
собраны (python make_all.py).

Расписание на каждый день настраивается один раз командой (см. README):
  schtasks /Create /SC DAILY /ST 10:00 /TN "UrokiAutopost" /TR "<путь>\autopost_daily.bat"
"""

import json
import sys
from pathlib import Path

# Консоль Windows (cp1251) не умеет печатать арабские буквы — не падаем на этом
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
LOG_FILE = HERE / "post_log.json"


def load_log():
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return {"youtube_posted": [], "tiktok_posted": []}


def save_log(log):
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2),
                        encoding="utf-8")


def lesson_meta(stem):
    """Название и описание для полного урока по его JSON."""
    j = json.loads((HERE / f"{stem}.json").read_text(encoding="utf-8"))
    title = f'{j["course"]} — Урок {j["lesson_number"]}: {j["topic"]}'
    desc = (f'Урок {j["lesson_number"]} курса «{j["course"]}». Тема: {j["topic"]}.\n'
            f'Учитель: {j["teacher"]}.\n\n'
            "Задание урока — в конце видео. Пишите ответы в комментариях!\n\n"
            "#арабский #английский #урок #обучение")
    return title, desc


def next_full_lesson(log):
    stems = sorted(p.stem for p in HERE.glob("arabic_*.json"))
    stems += sorted(p.stem for p in HERE.glob("lesson_*.json"))
    for stem in stems:
        video = HERE / "build" / stem / "lesson.mp4"
        if stem not in log["youtube_posted"] and video.exists():
            return stem, video
    return None, None


def next_short(log):
    shorts = sorted(HERE.glob("build/*/shorts/*.mp4"))
    for s in shorts:
        key = f"{s.parent.parent.name}/{s.name}"
        if key not in log["tiktok_posted"]:
            return key, s
    return None, None


def main():
    log = load_log()
    dry = "--dry-run" in sys.argv

    # --- 1. Полный урок -> YouTube ---
    stem, video = next_full_lesson(log)
    if stem:
        title, desc = lesson_meta(stem)
        print(f"YouTube: {stem} — «{title}»")
        if not dry:
            from upload_youtube import upload_video
            upload_video(video, title, desc,
                         tags=["арабский", "английский", "урок", "с нуля"])
            log["youtube_posted"].append(stem)
            save_log(log)
    else:
        print("YouTube: очередь пуста (все уроки запощены или не собраны — make_all.py)")

    # --- 2. Нарезка -> TikTok ---
    key, short = next_short(log)
    if short:
        cap_file = short.with_suffix(".txt")
        caption = cap_file.read_text(encoding="utf-8") if cap_file.exists() else short.stem
        print(f"TikTok: {key}")
        if not dry:
            from upload_tiktok import upload_tiktok
            upload_tiktok(short, caption)
            # считаем запощенным и в полуручном режиме — файл уже в TIKTOK_TODAY
            log["tiktok_posted"].append(key)
            save_log(log)
    else:
        print("TikTok: очередь нарезок пуста")

    print("Готово на сегодня.")


if __name__ == "__main__":
    main()
