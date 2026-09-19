# -*- coding: utf-8 -*-
"""
Публикация английских шортсов (shorts_en.py) на отдельный YouTube-канал.

Каждый ролик сначала смотрит владелица, поэтому в облаке ничего не
собирается: одобренные ролики загружаются отсюда с отложенной публикацией
(privacyStatus=private + publishAt), дальше YouTube выкладывает их сам,
по одному в день. Компьютер после загрузки можно выключать.

    python publish_en.py whoami              # в какой канал смотрит токен
    python publish_en.py schedule 1 2 3      # в расписание, по одному в день
    python publish_en.py schedule 4 --hour 15

Токен нового канала хранится в youtube_token_en.json (не в git). При
первом запуске откроется браузер — выбрать именно англоязычный канал.
Что уже в расписании — помнит shorts_en_state.json.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shorts_en import HASHTAGS, LESSONS, OUT_DIR, split_translit

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
CLIENT_SECRET = HERE / "client_secret.json"
TOKEN_FILE = HERE / "youtube_token_en.json"
STATE = HERE / "shorts_en_state.json"
# readonly — чтобы проверить название канала до первой загрузки
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
# 14:00 UTC — утро в США, вечер в Европе и на Ближнем Востоке
DEFAULT_HOUR_UTC = 14


def get_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline",
                                          prompt="consent select_account")
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


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
    desc = f'{l["teach"]}\n{l["cta"]}\n\n{HASHTAGS}'
    return title[:100], desc


def whoami(yt):
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    for ch in items:
        print(f'Канал: {ch["snippet"]["title"]}  (id {ch["id"]})')
    if not items:
        print("У этого аккаунта нет YouTube-канала.")


def next_slot(st, hour):
    """Следующий свободный день: после последнего запланированного, но
    не раньше завтрашнего."""
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=hour, minute=0, second=0, microsecond=0)
    taken = [datetime.fromisoformat(v["publish_at"]) for v in st["scheduled"].values()]
    if taken:
        return max(tomorrow, (max(taken) + timedelta(days=1)).replace(hour=hour))
    return tomorrow


def upload(yt, n, publish_at):
    from googleapiclient.http import MediaFileUpload

    title, desc = meta(n)
    body = {
        "snippet": {"title": title, "description": desc,
                    "tags": ["learn arabic", "arabic", "arabic for beginners",
                             "arabic words", "shorts"],
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


def main():
    args = sys.argv[1:]
    if not args or args[0] not in ("whoami", "schedule"):
        print(__doc__)
        return
    yt = get_service()
    if args[0] == "whoami":
        whoami(yt)
        return

    hour = DEFAULT_HOUR_UTC
    if "--hour" in args:
        i = args.index("--hour")
        hour = int(args[i + 1])
        del args[i:i + 2]
    st = load_state()
    for n in (int(a) for a in args[1:]):
        if str(n) in st["scheduled"]:
            print(f"Урок {n} уже в расписании — пропускаю.")
            continue
        if not (OUT_DIR / f"short_{n:02d}.mp4").exists():
            print(f"Урок {n}: нет готового ролика, сначала python shorts_en.py {n}")
            continue
        when = next_slot(st, hour)
        vid = upload(yt, n, when)
        st["scheduled"][str(n)] = {"youtube_id": vid,
                                   "publish_at": when.isoformat()}
        save_state(st)
        print(f"Урок {n}: https://youtu.be/{vid}  выйдет {when:%d.%m %H:%M} UTC")


if __name__ == "__main__":
    main()
