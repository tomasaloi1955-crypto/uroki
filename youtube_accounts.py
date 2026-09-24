# -*- coding: utf-8 -*-
"""
Один вход — один сохранённый YouTube-канал, для всех проектов.

    python youtube_accounts.py login     # войти; канал определится сам
    python youtube_accounts.py list      # какие каналы уже подключены

Какой канал выбрали в окне Google — такой и сохранится, под своим
названием, в %USERPROFILE%\\.youtube_tokens\\<id канала>.json. «Не тот»
канал не ошибка: его доступ тоже пригодится. Скрипты публикации берут
токен по названию канала (get_service("…")), а не «какой попался».

Вход через 127.0.0.1, а не localhost: Edge отправлял ответ Google на
IPv6-адрес ::1, который сервер не слушал, — страница висела и падала.
"""

import json
import os
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).parent
CLIENT_SECRET = HERE / "client_secret.json"
STORE = Path.home() / ".youtube_tokens"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
PORT = 8765


def _browser_login():
    from google_auth_oauthlib.flow import InstalledAppFlow

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"   # redirect на http://127.0.0.1
    os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"    # галочки проверяем сами
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    flow.redirect_uri = f"http://127.0.0.1:{PORT}/"
    url, _ = flow.authorization_url(access_type="offline",
                                    prompt="consent select_account")
    got = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # браузер делает пустые предзапросы — ждём именно ответ Google
            if "code=" in self.path or "error=" in self.path:
                got["path"] = self.path
                msg = "Done! You can close this tab. / Готово, вкладку можно закрыть."
            else:
                msg = "..."
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print("Открой в браузере:", url, flush=True)
    webbrowser.open(url)
    while "path" not in got:
        server.handle_request()
    server.server_close()
    if "error=" in got["path"]:
        raise SystemExit(f"Google отказал: {got['path']}")
    flow.fetch_token(authorization_response=f"http://127.0.0.1:{PORT}{got['path']}")
    granted = set(flow.oauth2session.token.get("scope") or [])
    if not set(SCOPES) <= granted:
        raise SystemExit("Выданы не все права — войдите ещё раз и отметьте ВСЕ галочки.")
    return flow.credentials


def _build(creds):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds)


def _channel(yt):
    items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    return items[0] if items else None


def login():
    creds = _browser_login()
    ch = _channel(_build(creds))
    if not ch:
        raise SystemExit("У выбранного аккаунта нет YouTube-канала.")
    STORE.mkdir(exist_ok=True)
    data = json.loads(creds.to_json())
    data["channel_title"] = ch["snippet"]["title"]
    (STORE / f'{ch["id"]}.json').write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f'Подключён канал: {ch["snippet"]["title"]}  (id {ch["id"]})')


def channels():
    """{название канала: путь к токену}"""
    out = {}
    for p in sorted(STORE.glob("*.json")) if STORE.exists() else []:
        out[json.loads(p.read_text(encoding="utf-8"))["channel_title"]] = p
    return out


def get_service(title):
    """YouTube-клиент строго для канала с этим названием."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    known = channels()
    if title not in known:
        raise SystemExit(f"Канал «{title}» не подключён. Подключены: "
                         f"{', '.join(known) or 'ни одного'}. "
                         "Запусти: python youtube_accounts.py login")
    path = known[title]
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        data = json.loads(creds.to_json())
        data["channel_title"] = title
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    yt = _build(creds)
    ch = _channel(yt)
    if not ch or ch["snippet"]["title"] != title:   # защита от «не того» канала
        raise SystemExit(f"Токен {path.name} смотрит не в «{title}».")
    return yt


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "login":
        login()
    else:
        for t, p in channels().items():
            print(f"{t}  ({p.stem})")
        if not channels():
            print("Пока ни одного канала. python youtube_accounts.py login")
