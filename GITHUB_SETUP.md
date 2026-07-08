# Автопилот на GitHub: уроки постятся сами, бесплатно

Каждый день в 10:00 по Москве сервер GitHub сам:
1. собирает очередной урок (видео + шортсы) — твой компьютер может быть выключен;
2. заливает длинное видео на **YouTube** и в **Telegram**;
3. заливает до 3 шортсов на **YouTube Shorts**, в **Telegram**, **Instagram Reels** и **TikTok**;
4. запоминает, что урок опубликован, и завтра берёт следующий.

Все площадки необязательны: настроишь только Telegram — будет постить только туда.
Стоимость: 0 ₽ (лимитов GitHub хватает с большим запасом).

---

## Шаг 1. Выложить проект на GitHub (10 минут)

1. Зарегистрируйся на [github.com](https://github.com) (если нет аккаунта).
2. Справа вверху **+** → **New repository** → имя `uroki` → выбери **Private** → **Create**.
3. Установи [GitHub Desktop](https://desktop.github.com) → войди в аккаунт →
   **File → Add local repository** → выбери папку
   `C:\Users\lima2\Downloads\урок английский тест` → **Publish**.

> Папку `build/` заливать не нужно — она в `.gitignore`, видео собираются на сервере.

## Шаг 2. Telegram (5 минут — самое простое, начни с него)

1. В Telegram найди **@BotFather** → команда `/newbot` → придумай имя.
   Получишь **токен** вида `1234567:AAE...` — это `TG_BOT_TOKEN`.
2. Создай канал (например «Арабский с Хадиджой»), зайди в управление каналом →
   **Администраторы** → добавь своего бота с правом публиковать.
3. Узнай ID канала: перешли любой пост из канала боту **@userinfobot** —
   он покажет `Id: -100xxxxxxxxxx` — это `TG_CHAT_ID`.

## Шаг 3. YouTube (15 минут)

1. Зайди на [console.cloud.google.com](https://console.cloud.google.com) под Google-аккаунтом канала.
2. Создай проект → в поиске найди **YouTube Data API v3** → **Enable**.
3. **APIs & Services → OAuth consent screen**: тип External, заполни имя, добавь свой
   email в Test users.
4. **Credentials → Create Credentials → OAuth client ID** → тип **Desktop app** →
   скачай JSON → переименуй в `client_secret.json` → положи в папку проекта.
5. В PowerShell в папке проекта:
   ```
   pip install google-auth-oauthlib
   python get_youtube_token.py
   ```
   Откроется браузер → разреши доступ → скрипт напечатает три значения.

⚠️ Пока приложение не прошло проверку Google, YouTube может ставить видео
в «private» — публикуешь одной кнопкой в YouTube Studio. После проверки
(кнопка Publish App + аудит) всё становится полностью автоматическим.

## Шаг 4. Instagram Reels (по желанию, ~30 минут)

Нужен **профессиональный аккаунт** Instagram, привязанный к странице Facebook:
1. Instagram → Настройки → Тип аккаунта → **Бизнес/Автор**.
2. Привяжи к странице Facebook (создай пустую, если нет).
3. На [developers.facebook.com](https://developers.facebook.com) создай приложение →
   добавь продукт **Instagram Graph API**.
4. В **Graph API Explorer** выбери приложение, запроси права
   `instagram_basic, instagram_content_publish, pages_show_list` →
   сгенерируй токен → обменяй на долгоживущий (кнопка «Extend» в
   [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/)).
   Это `IG_TOKEN`.
5. ID аккаунта (`IG_USER_ID`) — в Graph Explorer запрос
   `me/accounts?fields=instagram_business_account`.

## Шаг 5. TikTok (по желанию)

У TikTok строгий порядок: полноценный автопостинг разрешён только одобренным
приложениям. Реалистично:
- зарегистрируй приложение на [developers.tiktok.com](https://developers.tiktok.com),
  добавь **Content Posting API**, пройди ревью (несколько дней);
- до одобрения видео будут падать в **черновики твоего аккаунта** — публикуешь
  их в приложении TikTok двумя тапами; после одобрения — полный автомат.
Токен положи в секрет `TIKTOK_TOKEN`.

## Шаг 6. Вставить ключи в GitHub (5 минут)

В репозитории: **Settings → Secrets and variables → Actions → New repository secret**.
Добавь те, что настроила:

| Секрет | Откуда |
|---|---|
| `TG_BOT_TOKEN`, `TG_CHAT_ID` | шаг 2 |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | шаг 3 |
| `IG_TOKEN`, `IG_USER_ID` | шаг 4 |
| `TIKTOK_TOKEN` | шаг 5 |

## Шаг 7. Проверка

Вкладка **Actions** → «Ежедневный урок на все площадки» → **Run workflow**.
Через ~10 минут проверь каналы: должен появиться урок 1. Дальше — само,
каждый день в 10:00 МСК. Остановить: Actions → три точки → Disable workflow.

## Как это устроено

- расписание и шаги сервера: `.github/workflows/daily.yml`
- логика постинга: `social_post.py`
- какой урок следующий: `state.json` (можно руками поменять номер)
- какой курс постится: `state.json` → `"prefix": "arabic"` (или `lesson` для английского)
