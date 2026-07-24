# -*- coding: utf-8 -*-
"""
Загрузка видео на YouTube через официальный API.

Настройка (один раз, ~15 минут, бесплатно) — см. README, раздел «Автопостинг».
Нужен файл client_secret.json из Google Cloud Console рядом с этим скриптом.
При первом запуске откроется браузер — войди в аккаунт канала и разреши доступ.

    pip install google-api-python-client google-auth-oauthlib

Использование из кода:
    from upload_youtube import upload_video
    upload_video("build/arabic_001/lesson.mp4", "Заголовок", "Описание", ["тег1"])
"""

from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
HERE = Path(__file__).parent
CLIENT_SECRET = HERE / "client_secret.json"
TOKEN_FILE = HERE / "youtube_token.json"


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
            if not CLIENT_SECRET.exists():
                raise SystemExit(
                    "Нет client_secret.json! Следуй инструкции в README, "
                    "раздел «Автопостинг: настройка YouTube».")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload_video(path, title, description="", tags=None, privacy="public"):
    """Заливает видео, возвращает его id. privacy: public/unlisted/private."""
    from googleapiclient.http import MediaFileUpload

    yt = get_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags or [],
            "categoryId": "27",  # Education
            "defaultLanguage": "ru",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(path), chunksize=-1, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  YouTube: {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"  YouTube OK: https://youtu.be/{vid}")
    return vid


def set_thumbnail(video_id: str, thumb_path):
    """Ставит кастомную обложку — только для длинных видео (не для shorts)."""
    from googleapiclient.http import MediaFileUpload

    yt = get_service()
    yt.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(thumb_path), mimetype="image/jpeg"),
    ).execute()
    print(f"  Обложка установлена для {video_id}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Использование: python upload_youtube.py видео.mp4 \"Заголовок\" [\"Описание\"]")
        raise SystemExit(1)
    upload_video(sys.argv[1], sys.argv[2],
                 sys.argv[3] if len(sys.argv) > 3 else "")
