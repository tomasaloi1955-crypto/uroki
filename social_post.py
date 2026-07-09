# -*- coding: utf-8 -*-
"""
Ежедневный автопостинг (запускается GitHub Actions, см. .github/workflows/daily.yml).

Что делает за один запуск:
  1. Читает state.json -> номер сегодняшнего урока N
  2. Собирает урок N (видео + шортсы) прямо на сервере GitHub
  3. Постит:
     - длинное видео -> YouTube + Telegram-канал
     - шортсы (до 3 шт.) -> YouTube Shorts + Telegram + Instagram Reels + TikTok
  4. Увеличивает счётчик в state.json (коммитится обратно воркфлоу)

Все ключи берутся из переменных окружения (секреты GitHub):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN  - YouTube (см. get_youtube_token.py)
  TG_BOT_TOKEN, TG_CHAT_ID                          - Telegram-канал
  IG_TOKEN, IG_USER_ID                              - Instagram (бизнес-аккаунт, опционально)
  TIKTOK_TOKEN                                      - TikTok (одобренное приложение, опционально)

Любую площадку можно не настраивать — скрипт просто пропустит её.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

STATE = Path("state.json")


def log(msg):
    print(f"[post] {msg}", flush=True)


# ---------------- YouTube ----------------

def yt_access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["YT_CLIENT_ID"],
        "client_secret": os.environ["YT_CLIENT_SECRET"],
        "refresh_token": os.environ["YT_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def yt_upload(video: Path, title: str, description: str, tags):
    token = yt_access_token()
    meta = {
        "snippet": {"title": title[:95], "description": description,
                    "tags": tags, "categoryId": "27"},  # 27 = Education
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    init = requests.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8"},
        json=meta, timeout=60)
    init.raise_for_status()
    upload_url = init.headers["Location"]
    with open(video, "rb") as f:
        up = requests.put(upload_url, data=f,
                          headers={"Authorization": f"Bearer {token}",
                                   "Content-Type": "video/mp4"}, timeout=1800)
    up.raise_for_status()
    vid = up.json()["id"]
    log(f"YouTube OK: https://youtu.be/{vid}")
    return vid


# ---------------- Telegram ----------------

def tg_send_video(video: Path, caption: str):
    token, chat = os.environ["TG_BOT_TOKEN"], os.environ["TG_CHAT_ID"]
    with open(video, "rb") as f:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendVideo",
            data={"chat_id": chat, "caption": caption[:1000],
                  "supports_streaming": "true"},
            files={"video": f}, timeout=600)
    r.raise_for_status()
    log(f"Telegram OK: {video.name}")
    return r.json()["result"]["video"]["file_id"]


def tg_public_url(file_id: str) -> str:
    """Публичная ссылка на файл в Telegram — используем для Instagram."""
    token = os.environ["TG_BOT_TOKEN"]
    r = requests.get(f"https://api.telegram.org/bot{token}/getFile",
                     params={"file_id": file_id}, timeout=30)
    r.raise_for_status()
    return f'https://api.telegram.org/file/bot{token}/{r.json()["result"]["file_path"]}'


# ---------------- Instagram Reels ----------------

def ig_post_reel(video_url: str, caption: str):
    token, user = os.environ["IG_TOKEN"], os.environ["IG_USER_ID"]
    r = requests.post(f"https://graph.facebook.com/v21.0/{user}/media",
                      data={"media_type": "REELS", "video_url": video_url,
                            "caption": caption, "access_token": token}, timeout=60)
    r.raise_for_status()
    creation_id = r.json()["id"]
    for _ in range(30):  # ждём обработку до ~5 минут
        s = requests.get(f"https://graph.facebook.com/v21.0/{creation_id}",
                         params={"fields": "status_code", "access_token": token},
                         timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        time.sleep(10)
    p = requests.post(f"https://graph.facebook.com/v21.0/{user}/media_publish",
                      data={"creation_id": creation_id, "access_token": token},
                      timeout=60)
    p.raise_for_status()
    log("Instagram OK")


# ---------------- TikTok (официальный API) ----------------

def tiktok_post(video: Path, title: str):
    token = os.environ["TIKTOK_TOKEN"]
    size = video.stat().st_size
    init = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        json={"post_info": {"title": title[:150],
                            "privacy_level": "SELF_ONLY"},
              "source_info": {"source": "FILE_UPLOAD", "video_size": size,
                              "chunk_size": size, "total_chunk_count": 1}},
        timeout=60)
    init.raise_for_status()
    upload_url = init.json()["data"]["upload_url"]
    with open(video, "rb") as f:
        up = requests.put(upload_url, data=f,
                          headers={"Content-Type": "video/mp4",
                                   "Content-Range": f"bytes 0-{size - 1}/{size}"},
                          timeout=1800)
    up.raise_for_status()
    log("TikTok OK (черновик, если приложение ещё не одобрено)")


# ---------------- Оркестрация ----------------

def has(*names):
    return all(os.environ.get(n) for n in names)


def try_post(fn, label, *args):
    try:
        fn(*args)
    except Exception as e:
        log(f"{label} ПРОПУЩЕН: {e}")


def main():
    # Ни одна площадка не настроена -> не тратим урок впустую
    if not (has("TG_BOT_TOKEN", "TG_CHAT_ID")
            or has("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
            or has("IG_TOKEN", "IG_USER_ID") or has("TIKTOK_TOKEN")):
        log("Секреты площадок не настроены — пропускаю день. "
            "См. GITHUB_SETUP.md, шаги 2-6.")
        return

    state = json.loads(STATE.read_text(encoding="utf-8"))
    n = state["next_lesson"]
    prefix = state.get("prefix", "arabic")
    lesson_json = Path(f"{prefix}_{n:03d}.json")
    if not lesson_json.exists():
        log(f"{lesson_json} нет — курс закончился, делать нечего.")
        return

    lesson = json.loads(lesson_json.read_text(encoding="utf-8"))
    log(f"Урок {n}: {lesson['topic']}")

    # Сборка на сервере: v2-уроки (с "items") собирает make_lesson2.py
    # (он делает и шортсы), классические — старая пара скриптов
    if "items" in lesson:
        subprocess.run([sys.executable, "make_lesson2.py", str(lesson_json)], check=True)
    else:
        subprocess.run([sys.executable, "make_lesson.py", str(lesson_json)], check=True)
        subprocess.run([sys.executable, "make_shorts.py", str(lesson_json)], check=True)

    bdir = Path("build") / lesson_json.stem
    long_video = bdir / "lesson.mp4"
    title = f'{lesson["course"]} — Урок {n}: {lesson["topic"]}'
    lang_tag = "английский" if lesson.get("target_lang") == "en" else "арабский"
    descr = (f'Урок {n} курса «{lesson["course"]}». Тема: {lesson["topic"]}.\n'
             f'Учитель: {lesson["teacher"]}. Новый урок — каждый день!\n'
             f'#{lang_tag} #урок{n}')
    tags = [lang_tag, f"{lang_tag} язык", f"уроки {lang_tag[:-2]}ого", lesson["topic"]]

    # Длинное видео
    if has("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        try_post(yt_upload, "YouTube", long_video, title, descr, tags)
    tg_file_ids = {}
    if has("TG_BOT_TOKEN", "TG_CHAT_ID"):
        try:
            tg_file_ids["long"] = tg_send_video(long_video, f"📚 {title}\n\n{descr}")
        except Exception as e:
            log(f"Telegram ПРОПУЩЕН: {e}")

    # Шортсы (до 3 за день)
    shorts = sorted((bdir / "shorts").glob("*.mp4"))[:3]
    for sv in shorts:
        cap_file = sv.with_suffix(".txt")
        cap = cap_file.read_text(encoding="utf-8") if cap_file.exists() else title
        s_title = cap.splitlines()[0][:90] + " #Shorts"

        if has("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
            try_post(yt_upload, "YouTube Shorts", sv, s_title, cap, tags)
        fid = None
        if has("TG_BOT_TOKEN", "TG_CHAT_ID"):
            try:
                fid = tg_send_video(sv, cap)
            except Exception as e:
                log(f"Telegram short ПРОПУЩЕН: {e}")
        if has("IG_TOKEN", "IG_USER_ID") and fid and sv.stat().st_size < 19_000_000:
            try_post(ig_post_reel, "Instagram", tg_public_url(fid), cap)
        if has("TIKTOK_TOKEN"):
            try_post(tiktok_post, "TikTok", sv, cap.splitlines()[0])

    # Сдвигаем счётчик
    state["next_lesson"] = n + 1
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                     encoding="utf-8")
    log(f"Готово. Завтра — урок {n + 1}.")


if __name__ == "__main__":
    main()
