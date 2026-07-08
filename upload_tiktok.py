# -*- coding: utf-8 -*-
"""
Загрузка видео в TikTok через официальный Content Posting API.

ВАЖНО, честно: TikTok жёстче YouTube.
1. Нужно зарегистрировать приложение на developers.tiktok.com (бесплатно)
   и получить client_key / client_secret, включить Content Posting API.
2. Пока приложение не прошло проверку TikTok (audit), видео публикуются
   ТОЛЬКО как приватные (SELF_ONLY) — их надо открыть вручную в приложении.
   После проверки — публикуются сразу публично.
3. Неофициальные боты (без API) — риск бана канала, их не используем.

Если файла tiktok_token.json нет, скрипт работает в ПОЛУРУЧНОМ режиме:
кладёт видео + подпись в папку TIKTOK_TODAY и открывает её — остаётся
перетащить видео в приложение TikTok (30 секунд руками).

Формат tiktok_token.json: {"access_token": "act.xxx..."}
    pip install requests
"""

import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
TOKEN_FILE = HERE / "tiktok_token.json"
MANUAL_DIR = HERE / "TIKTOK_TODAY"

API_INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"


def upload_tiktok(path, caption):
    """Пробует официальный API; без токена — полуручной режим. True = загружено API."""
    path = Path(path)
    if not TOKEN_FILE.exists():
        return _manual_fallback(path, caption)

    import requests
    token = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))["access_token"]
    size = path.stat().st_size

    r = requests.post(
        API_INIT,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=UTF-8"},
        json={
            "post_info": {
                "title": caption[:2200],
                # SELF_ONLY — обязательный уровень до прохождения проверки TikTok;
                # после audit можно поменять на PUBLIC_TO_EVERYONE
                "privacy_level": "SELF_ONLY",
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": size,
                "total_chunk_count": 1,
            },
        },
        timeout=60,
    )
    data = r.json()
    if r.status_code != 200 or "data" not in data or not data["data"].get("upload_url"):
        print(f"  TikTok API ошибка: {data}. Перехожу в полуручной режим.")
        return _manual_fallback(path, caption)

    upload_url = data["data"]["upload_url"]
    with open(path, "rb") as f:
        r2 = requests.put(
            upload_url,
            headers={"Content-Type": "video/mp4",
                     "Content-Range": f"bytes 0-{size - 1}/{size}"},
            data=f, timeout=600,
        )
    if r2.status_code in (200, 201):
        print("  TikTok OK: видео загружено (проверь в приложении: Профиль -> видео)")
        return True
    print(f"  TikTok: ошибка загрузки {r2.status_code}. Полуручной режим.")
    return _manual_fallback(path, caption)


def _manual_fallback(path, caption):
    """Кладёт видео и подпись в TIKTOK_TODAY и открывает папку."""
    MANUAL_DIR.mkdir(exist_ok=True)
    # чистим вчерашнее
    for old in MANUAL_DIR.iterdir():
        old.unlink()
    shutil.copy2(path, MANUAL_DIR / path.name)
    (MANUAL_DIR / "подпись.txt").write_text(caption, encoding="utf-8")
    try:
        subprocess.Popen(["explorer", str(MANUAL_DIR)])
    except OSError:
        pass
    print(f"  TikTok (вручную): видео и подпись в папке {MANUAL_DIR}")
    print("  Открой tiktok.com/upload или приложение и перетащи видео.")
    return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Использование: python upload_tiktok.py видео.mp4 [\"Подпись\"]")
        raise SystemExit(1)
    upload_tiktok(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
