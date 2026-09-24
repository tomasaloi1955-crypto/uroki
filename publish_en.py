# -*- coding: utf-8 -*-
"""
Публикация английских шортсов (shorts_en.py) на отдельный YouTube-канал.

Каждый ролик сначала смотрит владелица, поэтому в облаке ничего не
собирается: одобренные ролики загружаются отсюда с отложенной публикацией
(privacyStatus=private + publishAt), дальше YouTube выкладывает их сам,
по одному в день. Компьютер после загрузки можно выключать.

    python publish_en.py whoami              # в какой канал смотрит токен
    python publish_en.py schedule            # все готовые — в расписание
    python publish_en.py schedule 4 --hours 13,17,23   # свои часы (UTC)

Доступ к каналу — через youtube_accounts.py (один раз: login), загрузка
идёт только в канал с названием EN_CHANNEL.
Что уже в расписании — помнит shorts_en_state.json.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shorts_en import (LESSONS, OUT_DIR, hashtags_for, split_translit,
                       tags_for)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
STATE = HERE / "shorts_en_state.json"
# Токен берётся строго для канала с этим названием (youtube_accounts.py)
EN_CHANNEL = "Easy_arabic"
# Три выхода в день: утро и вечер в США, день и вечер в Европе.
# 13:00 UTC — утро в Нью-Йорке, 17:00 — вечер в Европе, 23:00 — вечер в США.
DEFAULT_HOURS_UTC = [13, 17, 23]


def get_service():
    from youtube_accounts import get_service as channel_service
    return channel_service(EN_CHANNEL)


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"scheduled": {}}


def save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2),
                     encoding="utf-8")


def meta(n):
    l = LESSONS[n]
    word, _ = split_translit(l)
    title = f'{l["hook"]} | Arabic: {l["ar"]} ({word}) #shorts'
    desc = f'{l["teach"]}\n{l["cta"]}\n\n{hashtags_for(n)}'
    return title[:100], desc


def whoami(yt):
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    for ch in items:
        print(f'Канал: {ch["snippet"]["title"]}  (id {ch["id"]})')
    if not items:
        print("У этого аккаунта нет YouTube-канала.")


def next_slot(st, hours):
    """Следующее свободное окно выхода. hours — часы UTC в течение дня
    (три ролика в день — три часа): заполняем день за днём."""
    now = datetime.now(timezone.utc)
    taken = {datetime.fromisoformat(v["publish_at"])
             for v in st["scheduled"].values()}
    day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0,
                                            microsecond=0)
    for _ in range(400):
        for h in sorted(hours):
            slot = day.replace(hour=h)
            if slot > now and slot not in taken:
                return slot
        day += timedelta(days=1)
    raise RuntimeError("не нашлось свободной даты")


def upload(yt, n, publish_at):
    from googleapiclient.http import MediaFileUpload

    title, desc = meta(n)
    body = {
        "snippet": {"title": title, "description": desc,
                    "tags": tags_for(n),
                    "categoryId": "27",  # Education
                    "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "private",
                   "publishAt": publish_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(OUT_DIR / f"short_{n:02d}.mp4"),
                            chunksize=-1, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]


def free_disk(n):
    """Удаляет с компьютера всё, что связано с уже загруженным роликом."""
    import shutil
    shutil.rmtree(OUT_DIR / f"work_{n:02d}", ignore_errors=True)
    for p in OUT_DIR.glob(f"short_{n:02d}.*"):
        p.unlink(missing_ok=True)


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("whoami", "schedule"):
        print(__doc__)
        return
    if args[0] == "whoami":
        whoami(get_service())
        return

    hours = DEFAULT_HOURS_UTC
    if "--hours" in args:
        i = args.index("--hours")
        hours = [int(h) for h in args[i + 1].split(",")]
        del args[i:i + 2]
    main_schedule([int(a) for a in args[1:]] or sorted(LESSONS), hours)


def main_schedule(nums, hours=None):
    """Загружает готовые ролики с отложенной публикацией."""
    hours = hours or DEFAULT_HOURS_UTC
    yt = get_service()
    st = load_state()
    for n in nums:
        if str(n) in st["scheduled"]:
            print(f"Урок {n} уже в расписании — пропускаю.")
            continue
        if not (OUT_DIR / f"short_{n:02d}.mp4").exists():
            print(f"Урок {n}: нет готового ролика, сначала python shorts_en.py {n}")
            continue
        when = next_slot(st, hours)
        vid = upload(yt, n, when)
        st["scheduled"][str(n)] = {"youtube_id": vid,
                                   "publish_at": when.isoformat()}
        save_state(st)
        # ролик уже на YouTube — на старом компьютере место не занимаем
        free_disk(n)
        print(f"Урок {n}: https://youtu.be/{vid}  выйдет {when:%d.%m %H:%M} UTC")


if __name__ == "__main__":
    main()
