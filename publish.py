# -*- coding: utf-8 -*-
"""
Публикация шортсов на YouTube-канал нужного языка.

    python publish.py en schedule           # все готовые английские
    python publish.py es schedule 1 2 3     # эти испанские
    python publish.py es whoami             # в какой канал смотрит токен
    python publish.py en schedule --hours 13,17,23

Ролики уходят скрытыми с датой (privacyStatus=private + publishAt) —
YouTube публикует их сам, по три в день. Загруженный файл сразу
удаляется с компьютера. Доступ к каналу — youtube_accounts.py, грузим
строго в канал с названием LANG.channel.
Что уже в расписании — помнит shorts_<код>_state.json.
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import shorts_core as core

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
# Три выхода в день: утро и вечер в США, день и вечер в Европе.
DEFAULT_HOURS_UTC = [13, 17, 23]


def lang_by_code(code):
    import importlib
    return importlib.import_module(f"shorts_{code}").LANG


def state_file(lang):
    return HERE / f"shorts_{lang.code}_state.json"


def get_service(lang):
    from youtube_accounts import get_service as channel_service
    return channel_service(lang.channel)


def load_state(lang):
    path = state_file(lang)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"scheduled": {}}


def save_state(lang, st):
    state_file(lang).write_text(json.dumps(st, ensure_ascii=False, indent=2),
                                encoding="utf-8")


def meta(lang, n):
    lesson = lang.lessons[n]
    word, _ = core.split_translit(lesson)
    title = f'{lesson["hook"]} | {lesson["ar"]} ({word}) #shorts'
    desc = (f'{lesson["teach"]}\n{lesson["cta"]}\n\n'
            f'{core.hashtags_for(lang, n)}')
    return title[:100], desc


def whoami(yt):
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    for ch in items:
        print(f'Канал: {ch["snippet"]["title"]}  (id {ch["id"]})')
    if not items:
        print("У этого аккаунта нет YouTube-канала.")


def next_slot(st, hours):
    """Следующее свободное окно выхода: заполняем день за днём."""
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


def upload(yt, lang, n, publish_at):
    from googleapiclient.http import MediaFileUpload

    title, desc = meta(lang, n)
    body = {
        "snippet": {"title": title, "description": desc,
                    "tags": core.tags_for(lang, n),
                    "categoryId": "27",  # Education
                    "defaultLanguage": lang.code,
                    "defaultAudioLanguage": lang.code},
        "status": {"privacyStatus": "private",
                   "publishAt": publish_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "selfDeclaredMadeForKids": False},
    }
    # кусками по 4 МБ: при обрыве связи догружается остаток, а не файл целиком
    media = MediaFileUpload(str(lang.out_dir / f"short_{n:02d}.mp4"),
                            chunksize=4 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, tries = None, 0
    while resp is None:
        try:
            _, resp = req.next_chunk()
        except Exception as e:
            if "uploadLimitExceeded" in str(e):
                # суточный лимит канала на загрузки: повторы бесполезны
                raise RuntimeError("Достигнут суточный лимит загрузок YouTube "
                                   "— продолжим завтра") from e
            tries += 1
            if tries > 6:
                raise
            print(f"  связь оборвалась ({type(e).__name__}), "
                  f"повтор {tries} через {5 * tries} сек...", flush=True)
            time.sleep(5 * tries)
    return resp["id"]


def free_disk(lang, n):
    """Удаляет с компьютера всё, что связано с загруженным роликом."""
    import shutil
    shutil.rmtree(lang.out_dir / f"work_{n:02d}", ignore_errors=True)
    for p in lang.out_dir.glob(f"short_{n:02d}.*"):
        p.unlink(missing_ok=True)


def schedule(lang, nums=None, hours=None):
    """Загружает готовые ролики с отложенной публикацией."""
    hours = hours or DEFAULT_HOURS_UTC
    nums = nums or sorted(lang.lessons)
    yt = get_service(lang)
    st = load_state(lang)
    for n in nums:
        if str(n) in st["scheduled"]:
            print(f"Урок {n} уже в расписании — пропускаю.")
            continue
        if not (lang.out_dir / f"short_{n:02d}.mp4").exists():
            print(f"Урок {n}: нет готового ролика "
                  f"(python shorts_{lang.code}.py {n})")
            continue
        when = next_slot(st, hours)
        try:
            vid = upload(yt, lang, n, when)
        except RuntimeError as e:      # лимит канала — дальше грузить нечем
            print(e)
            return
        except Exception as e:         # один упавший ролик не рушит очередь
            print(f"Урок {n}: загрузка не удалась ({e}); продолжаю дальше.")
            continue
        st["scheduled"][str(n)] = {"youtube_id": vid,
                                   "publish_at": when.isoformat()}
        save_state(lang, st)
        free_disk(lang, n)             # ролик уже на YouTube
        print(f"Урок {n}: https://youtu.be/{vid}  выйдет {when:%d.%m %H:%M} UTC")


def main():
    args = sys.argv[1:]
    if len(args) < 2 or args[1] not in ("whoami", "schedule"):
        print(__doc__)
        return
    lang = lang_by_code(args[0])
    if args[1] == "whoami":
        whoami(get_service(lang))
        return
    args = args[2:]
    hours = DEFAULT_HOURS_UTC
    if "--hours" in args:
        i = args.index("--hours")
        hours = [int(h) for h in args[i + 1].split(",")]
        del args[i:i + 2]
    schedule(lang, [int(a) for a in args] or None, hours)


if __name__ == "__main__":
    main()
