# -*- coding: utf-8 -*-
"""
Одноразовый помощник: получает YouTube refresh-token для автопостинга.

Перед запуском положи рядом файл client_secret.json
(как его скачать — см. GITHUB_SETUP.md, раздел YouTube).

    pip install google-auth-oauthlib
    python get_youtube_token.py

Откроется браузер -> войди в Google-аккаунт канала -> разреши доступ.
Скрипт напечатает три значения для секретов GitHub.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

print("\n=== Скопируй эти три значения в секреты GitHub ===")
print(f"YT_CLIENT_ID:     {creds.client_id}")
print(f"YT_CLIENT_SECRET: {creds.client_secret}")
print(f"YT_REFRESH_TOKEN: {creds.refresh_token}")
