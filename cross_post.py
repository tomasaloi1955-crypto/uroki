# -*- coding: utf-8 -*-
"""
Шортс дня -> Instagram Reels и TikTok (вызывается из autopost_shorts2.py).

Площадка без ключей просто пропускается; ошибка одной площадки не мешает
другим и не роняет публикацию на YouTube.

Секреты GitHub (Settings -> Secrets and variables -> Actions):
  Instagram (профессиональный аккаунт, см. GITHUB_SETUP.md, шаг 4):
    IG_TOKEN, IG_USER_ID
    IG_API_HOST — только если токен получен через «Instagram Login»:
                  graph.instagram.com (по умолчанию graph.facebook.com)
  TikTok (приложение на developers.tiktok.com, scope video.upload):
    TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN
      — access token живёт сутки, поэтому берём свежий по refresh token
        (тот живёт год);
    или TIKTOK_TOKEN — готовый access token (на сутки, для проверки).
    TIKTOK_DIRECT=1 — публиковать сразу (только после аудита приложения
    TikTok). Без него ролик падает в «Входящие» TikTok: открыть
    уведомление в приложении и нажать «Опубликовать».
"""

import os
import time
from pathlib import Path

import requests

IG_VERSION = "v21.0"
TT_API = "https://open.tiktokapis.com"


def log(msg):
    print(f"[cross] {msg}", flush=True)


def has(*names):
    return all(os.environ.get(n) for n in names)


# ---------------- Instagram Reels ----------------

def ig_post_reel(video: Path, caption: str):
    """Загружает файл напрямую (resumable upload) — публичная ссылка
    на видео не нужна."""
    token, user = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    host = os.environ.get("IG_API_HOST") or "graph.facebook.com"
    base = f"https://{host}/{IG_VERSION}"

    r = requests.post(f"{base}/{user}/media",
                      data={"media_type": "REELS", "upload_type": "resumable",
                            "caption": caption[:2200], "share_to_feed": "true",
                            "access_token": token}, timeout=60)
    if not r.ok:
        raise RuntimeError(f"создание контейнера: {r.text[:300]}")
    creation_id = r.json()["id"]
    upload_uri = (r.json().get("uri") or
                  f"https://rupload.facebook.com/ig-api-upload/{IG_VERSION}/{creation_id}")

    data = video.read_bytes()
    up = requests.post(upload_uri, data=data, timeout=600,
                       headers={"Authorization": f"OAuth {token}",
                                "offset": "0", "file_size": str(len(data))})
    if not up.ok:
        raise RuntimeError(f"загрузка видео: {up.text[:300]}")

    for _ in range(60):  # обработка обычно 30-90 сек, ждём до 10 минут
        s = requests.get(f"{base}/{creation_id}",
                         params={"fields": "status_code,status",
                                 "access_token": token}, timeout=30).json()
        code = s.get("status_code")
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Instagram не принял видео: {s.get('status')}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram не обработал видео за 10 минут")

    p = requests.post(f"{base}/{user}/media_publish",
                      data={"creation_id": creation_id, "access_token": token},
                      timeout=60)
    if not p.ok:
        raise RuntimeError(f"публикация: {p.text[:300]}")
    log(f"Instagram OK: {p.json().get('id')}")


# ---------------- TikTok ----------------

def tiktok_access_token():
    if has("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN"):
        r = requests.post(f"{TT_API}/v2/oauth/token/", timeout=60, data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"],
        })
        d = r.json()
        if "access_token" not in d:
            raise RuntimeError(f"обновление токена: {d}")
        return d["access_token"]
    return os.environ["TIKTOK_TOKEN"]


def tiktok_post(video: Path, caption: str):
    token = tiktok_access_token()
    size = video.stat().st_size
    source = {"source": "FILE_UPLOAD", "video_size": size,
              "chunk_size": size, "total_chunk_count": 1}
    direct = os.environ.get("TIKTOK_DIRECT") == "1"
    if direct:
        url = f"{TT_API}/v2/post/publish/video/init/"
        body = {"post_info": {"title": caption[:2200],
                              "privacy_level": "PUBLIC_TO_EVERYONE"},
                "source_info": source}
    else:
        url = f"{TT_API}/v2/post/publish/inbox/video/init/"
        body = {"source_info": source}
    init = requests.post(url, json=body, timeout=60,
                         headers={"Authorization": f"Bearer {token}",
                                  "Content-Type": "application/json"})
    upload_url = init.json().get("data", {}).get("upload_url")
    if not upload_url:
        raise RuntimeError(f"init: {init.text[:300]}")
    with open(video, "rb") as f:
        up = requests.put(upload_url, data=f, timeout=600,
                          headers={"Content-Type": "video/mp4",
                                   "Content-Range": f"bytes 0-{size - 1}/{size}"})
    if not up.ok:
        raise RuntimeError(f"загрузка видео: {up.status_code} {up.text[:300]}")
    log("TikTok OK: опубликовано" if direct else
        "TikTok OK: ролик во «Входящих» TikTok — нажми «Опубликовать»")


# ---------------- всё сразу ----------------

def post_everywhere(video: Path, caption: str):
    """Постит на все настроенные площадки; ошибки только пишет в лог."""
    targets = []
    if has("IG_TOKEN", "IG_USER_ID"):
        targets.append(("Instagram", ig_post_reel))
    else:
        log("Instagram не настроен (нет IG_TOKEN / IG_USER_ID) — пропускаю")
    if (has("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN")
            or has("TIKTOK_TOKEN")):
        targets.append(("TikTok", tiktok_post))
    else:
        log("TikTok не настроен (нет TIKTOK_* секретов) — пропускаю")
    for label, fn in targets:
        try:
            fn(video, caption)
        except Exception as e:
            log(f"{label} ПРОПУЩЕН: {e}")
