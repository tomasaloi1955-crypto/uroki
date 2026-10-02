# -*- coding: utf-8 -*-
"""
Бесплатный тариф ElevenLabs (10 000 символов в месяц) — в первую
очередь русским шортсам: один ролик в день ≈ 250 символов, за месяц
≈ 7 500–8 500. Длинные серии берут ElevenLabs, только если после
резерва на шортсы до конца месяца остаётся на всю серию целиком;
иначе вся серия озвучивается бесплатным edge-tts (Светлана + носитель
Зарийя для арабских слов). Голос внутри одной серии не смешивается.

Если ElevenLabs отказал шортсу (кончился лимит, сбой), шортс тоже
собирается на edge-tts — канал не останавливается.
"""

import asyncio
import json
import math
import os
import time
import urllib.request
from pathlib import Path

# Шортс сейчас 200–280 символов; берём с запасом
SHORT_RESERVE = 300
# На повторные попытки и случайные пересборки
SAFETY = 500

FREE_RU_VOICE = "ru-RU-SvetlanaNeural"
FREE_AR_VOICE = "ar-SA-ZariyahNeural"
FREE_AR_RATE = "-25%"


def eleven_quota():
    """(израсходовано, лимит, unix-время сброса) или None, если узнать
    не удалось (нет ключа, нет сети, ключ без права user_read)."""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        return None
    try:
        req = urllib.request.Request(
            "https://api.elevenlabs.io/v1/user/subscription",
            headers={"xi-api-key": key})
        with urllib.request.urlopen(req, timeout=30) as r:
            sub = json.loads(r.read())
        return (sub["character_count"], sub["character_limit"],
                sub.get("next_character_count_reset_unix"))
    except Exception as e:
        print(f"  ElevenLabs: остаток не узнать ({e})")
        return None


def shorts_reserve(reset_unix, now=None):
    """Сколько символов держать для шортсов до сброса лимита."""
    now = now or time.time()
    days = math.ceil((reset_unix - now) / 86400) if reset_unix else 31
    return max(days, 1) * SHORT_RESERVE + SAFETY


def long_may_use_eleven(chars_needed):
    """Хватит ли ElevenLabs на серию так, чтобы шортсы не остались
    без голоса до конца месяца. Не знаем остаток — не рискуем."""
    q = eleven_quota()
    if q is None:
        print("  серия: бесплатная озвучка (остаток ElevenLabs неизвестен)")
        return False
    used, limit, reset = q
    left = limit - used
    reserve = shorts_reserve(reset)
    ok = left - reserve >= chars_needed
    print(f"  ElevenLabs: осталось {left}, резерв шортсам {reserve}, "
          f"серии нужно {chars_needed} → "
          f"{'ElevenLabs' if ok else 'бесплатная озвучка'}")
    return ok


def free_tts(kind, text, out_mp3: Path, ru_rate=None):
    """edge-tts, приведённый к 44.1 кГц моно — как клипы ElevenLabs,
    иначе concat в ffmpeg путает дорожки."""
    import edge_tts
    from shorts_v2 import ffmpeg

    raw = out_mp3.with_name(out_mp3.stem + "_raw.mp3")
    if kind == "ar":
        voice, rate = FREE_AR_VOICE, FREE_AR_RATE
    else:
        voice, rate = FREE_RU_VOICE, ru_rate
    kw = {"rate": rate} if rate else {}
    asyncio.run(edge_tts.Communicate(text.strip() or "…", voice, **kw)
                .save(str(raw)))
    ffmpeg("-i", str(raw), "-ar", "44100", "-ac", "1", "-q:a", "2",
           str(out_mp3))
    raw.unlink(missing_ok=True)
