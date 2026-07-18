# -*- coding: utf-8 -*-
"""
Ежедневный автопостинг шортсов v2: один запуск = один ролик на YouTube.

  python autopost_shorts2.py        # следующий урок из очереди (11, 12, ...)
  python autopost_shorts2.py 10     # конкретный урок

Ролик собирается конвейером shorts_v2.py (фото-фоны + текст + ElevenLabs),
если ещё не собран. Что уже опубликовано — помнит shorts2_state.json.

Расписание (один раз):
  schtasks /Create /SC DAILY /ST 11:00 /TN "ArabicShorts2Daily" ^
           /TR "<путь>\autopost_shorts2.bat"
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
STATE = HERE / "shorts2_state.json"

from shorts_v2 import LESSONS, OUT_DIR, build_short, strip_accents


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"posted": []}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2),
                     encoding="utf-8")


def meta(n):
    l = LESSONS[n]
    word = strip_accents(l["translit"]).split("—")[0].strip().rstrip("!?.")
    title = f'{l["hook"]} по-арабски: {l["ar"]} ({word}) #shorts'
    desc = (f'{l["teach"]}\n{l["cta"]}\n\n'
            "#арабский #арабскийязык #арабскийснуля #учимарабский #shorts")
    return title[:100], desc


def main():
    st = load_state()
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    else:
        queue = [k for k in sorted(LESSONS) if k not in st["posted"]]
        if not queue:
            print("Очередь пуста: все уроки опубликованы.")
            return
        n = queue[0]

    video = OUT_DIR / f"short_{n:02d}.mp4"
    if not video.exists():
        build_short(n)

    title, desc = meta(n)
    print(f"YouTube: урок {n} — «{title}»")
    from upload_youtube import upload_video
    upload_video(video, title, desc,
                 tags=["арабский", "арабский язык", "с нуля", "shorts"])
    if n not in st["posted"]:
        st["posted"].append(n)
    save_state(st)
    print("Готово на сегодня.")


if __name__ == "__main__":
    main()
