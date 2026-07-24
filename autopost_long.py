# -*- coding: utf-8 -*-
"""
Автопостинг длинных видео (~10 мин), 3 серии в неделю (пн/ср/пт).

  python autopost_long.py        # следующая серия из очереди
  python autopost_long.py 1      # конкретная серия

Конвейер: long_video.py (фото-фоны + текст + ElevenLabs, тот же фирменный
стиль, что у shorts). Обложка — только для длинных видео (у shorts её нет).
Журнал — long_state.json.
"""

import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
STATE = HERE / "long_state.json"

from long_video import EPISODES, OUT_DIR, build_episode, make_thumbnail


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"posted": []}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2),
                     encoding="utf-8")


def main():
    st = load_state()
    if len(sys.argv) > 1:
        n = int(sys.argv[1])
    else:
        queue = [k for k in sorted(EPISODES) if k not in st["posted"]]
        if not queue:
            print("Очередь пуста: все серии опубликованы.")
            return
        n = queue[0]

    video = OUT_DIR / f"episode_{n:02d}.mp4"
    if not video.exists():
        build_episode(n)

    thumb = OUT_DIR / f"episode_{n:02d}_thumb.jpg"
    if not thumb.exists():
        make_thumbnail(n)

    ep = EPISODES[n]
    title = f'Мединский курс — Серия {n}: {ep["title"]}'[:100]
    desc = (HERE / "build" / "long" / f"episode_{n:02d}.txt").read_text(
        encoding="utf-8")
    tags = ["арабский", "арабский язык", "мединский курс", "с нуля", "урок арабского"]

    print(f"YouTube: серия {n} — «{title}»")
    if all(os.environ.get(k) for k in
           ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        from social_post import yt_upload, yt_set_thumbnail
        vid = yt_upload(video, title, desc, tags)
        yt_set_thumbnail(vid, thumb)
    else:
        from upload_youtube import upload_video, set_thumbnail
        vid = upload_video(video, title, desc, tags)
        set_thumbnail(vid, thumb)

    if n not in st["posted"]:
        st["posted"].append(n)
    save_state(st)
    print("Готово на сегодня.")


if __name__ == "__main__":
    main()
