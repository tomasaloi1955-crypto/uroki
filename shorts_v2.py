# -*- coding: utf-8 -*-
"""
Шортсы v2: тематические стоковые видео (Wikimedia Commons) + крупный текст
в стиле канала + озвучка ElevenLabs (голос из ELEVENLABS_VOICE_ID).

Запуск:
    python shorts_v2.py 10          # один урок
    python shorts_v2.py 10 12 15    # несколько

Ключи берутся из переменных окружения ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID.
Результат: build/shorts_v2/short_NN.mp4 + short_NN.txt (подпись для поста).
"""

import json
import os
import subprocess
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

RESHAPER = arabic_reshaper.ArabicReshaper({"delete_harakat": False})

W, H = 1080, 1920
GOLD = (222, 184, 74)
UA = "ArabicShortsPipeline/1.0 (educational channel)"
OUT_DIR = Path("build") / "shorts_v2"

# Пути и для Windows, и для Linux (GitHub Actions: fonts-noto-core + dejavu)
FONT_BOLD = ["C:/Windows/Fonts/arialbd.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONT_REG = ["C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
# Для крупной арабской вязи Traditional Arabic красивее, Arial — запасной
FONT_AR = ["C:/Windows/Fonts/tradbdo.ttf", "C:/Windows/Fonts/arialbd.ttf",
           "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
           "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
           "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

# hook — крючок сверху, ar — арабское слово, translit — строка под ним,
# teach — обучающая фраза для озвучки, cta — призыв, themes — поиск фонов
LESSONS = {
    8:  dict(hook="Артикль Эль", ar="الـ", translit="Аль-",
             teach="Артикль Аль- делает слово определённым. Книга — Китаб, эта книга — Аль-Китаб.",
             cta="Подпишись, чтобы не пропускать уроки!",
             themes=["arabic calligraphy", "mosque interior", "old books"]),
    9:  dict(hook="Верблюд и Красота", ar="جمل", translit="Джама́ль",
             teach="Джамаль означает верблюд и одновременно — красота.",
             cta="Подпишись: интересные факты об арабском!",
             themes=["camel desert", "desert dunes"]),
    10: dict(hook="Красивое спасибо", ar="شكراً", translit="Шу́кран — спасибо",
             teach="Шукран — спасибо. Ответ: Афуан — пожалуйста.",
             cta="Подпишись, завтра новые фразы!",
             themes=["sheikh zayed mosque", "sahara dunes", "arabic coffee"]),
    11: dict(hook="Слово дня: Вода", ar="ماء", translit="Ма́ — вода",
             teach="Без воды нет жизни. Вода по-арабски — Ма. Запоминай: Ма.",
             cta="Ставь лайк, если пьёшь воду!",
             themes=["water drops", "ocean waves", "waterfall"]),
    12: dict(hook="Слово дня: Хлеб", ar="خبز", translit="Хубз — хлеб",
             teach="Хлеб — всему голова. Хлеб по-арабски — Хубз. Повтори: Хубз.",
             cta="Подпишись, чтобы не проголодаться!",
             themes=["bread baking", "wheat field"]),
    13: dict(hook="Слово дня: Дом", ar="بيت", translit="Бейт — дом",
             teach="Дом, милый дом. Дом по-арабски — Бейт. Запоминай: Бейт.",
             cta="Сохрани, чтобы не потерять дом!",
             themes=["old city street", "cozy house"]),
    14: dict(hook="Слово дня: Солнце", ar="شمس", translit="Шамс — солнце",
             teach="Солнце светит всем. Солнце по-арабски — Шамс. Запоминай: Шамс.",
             cta="Ставь лайк, если любишь солнце!",
             themes=["sunrise timelapse", "sun clouds"]),
    15: dict(hook="Слово дня: Луна", ar="قمر", translit="Ка́мар — луна",
             teach="Луна — символ красоты в арабском мире. Луна по-арабски — Камар. Повтори: Камар.",
             cta="Подпишись, завтра новые слова!",
             themes=["full moon", "night sky timelapse"]),
    16: dict(hook="Слово дня: Город", ar="مدينة", translit="Мади́на — город",
             teach="Городской ритм. Город по-арабски — Мадина. Запоминай: Мадина.",
             cta="Подпишись на канал!",
             themes=["city skyline night", "old arab city"]),
    17: dict(hook="Слово дня: Улица", ar="شارع", translit="Ша́ри — улица",
             teach="Улица полна неожиданностей. Улица по-арабски — Шари. Повтори: Шари.",
             cta="Сохрани, чтобы не заблудиться!",
             themes=["market bazaar", "street walking"]),
    18: dict(hook="Слово дня: Машина", ar="سيارة", translit="Сайя́ра — машина",
             teach="Автомобиль — не роскошь. Машина по-арабски — Сайяра. Повтори: Сайяра.",
             cta="Ставь лайк, если любишь скорость!",
             themes=["desert road driving", "car road"]),
    19: dict(hook="Слово дня: Человек", ar="إنسان", translit="Инса́н — человек",
             teach="Человек — это звучит гордо. Человек по-арабски — Инсан. Повтори: Инсан.",
             cta="Подпишись на канал!",
             themes=["silhouette person sunset", "people walking"]),
    20: dict(hook="Слово дня: Друг", ar="صديق", translit="Сади́к — друг",
             teach="Друг познаётся в беде. Друг по-арабски — Садик. Запоминай: Садик.",
             cta="Отправь другу!",
             themes=["friends laughing", "handshake"]),
    21: dict(hook="Слово дня: Мама", ar="أم", translit="Умм — мама",
             teach="Мама — самое важное слово. Мама по-арабски — Умм. Повтори: Умм.",
             cta="Ставь лайк, если любишь маму!",
             themes=["mother child", "family walking"]),
    22: dict(hook="Слово дня: Папа", ar="أب", translit="Аб — папа",
             teach="Отец — опора семьи. Папа по-арабски — Аб. Повтори: Аб.",
             cta="Подпишись на канал!",
             themes=["father child", "family"]),
    23: dict(hook="Слово дня: Брат", ar="أخ", translit="Ах — брат",
             teach="Брат за брата. Брат по-арабски — Ах. Запоминай: Ах.",
             cta="Отправь брату!",
             themes=["brothers", "children playing"]),
    24: dict(hook="Слово дня: Сестра", ar="أخت", translit="Ухт — сестра",
             teach="Сестра — лучшая подруга. Сестра по-арабски — Ухт. Повтори: Ухт.",
             cta="Отправь сестре!",
             themes=["sisters", "children smiling"]),
    25: dict(hook="Слово дня: Яблоко", ar="تفاح", translit="Туффа́х — яблоко",
             teach="Яблоко в день — и доктор не нужен. Яблоко по-арабски — Туффах. Запоминай: Туффах.",
             cta="Ставь лайк, если любишь яблоки!",
             themes=["red apples", "apple orchard"]),
    26: dict(hook="Слово дня: Чай", ar="شاي", translit="Шай — чай",
             teach="Чайная церемония. Чай по-арабски — Шай. Повтори: Шай.",
             cta="Сохрани, пока не остыл!",
             themes=["tea pouring glass", "tea"]),
    27: dict(hook="Слово дня: Кофе", ar="قهوة", translit="Ка́хва — кофе",
             teach="Утренний кофе. Кофе по-арабски — Кахва. Запоминай: Кахва.",
             cta="Ставь лайк, если любишь кофе!",
             themes=["coffee pouring", "arabic coffee"]),
    28: dict(hook="Слово дня: Небо", ar="سماء", translit="Сама́ — небо",
             teach="Небо над головой. Небо по-арабски — Сама. Повтори: Сама.",
             cta="Подпишись на канал!",
             themes=["clouds timelapse", "blue sky"]),
    29: dict(hook="Слово дня: Земля", ar="أرض", translit="Ард — земля",
             teach="Родная земля. Земля по-арабски — Ард. Запоминай: Ард.",
             cta="Сохрани, чтобы не упасть!",
             themes=["green landscape aerial", "earth nature"]),
    30: dict(hook="Слово дня: Жизнь", ar="حياة", translit="Хая́т — жизнь",
             teach="Жизнь прекрасна. Жизнь по-арабски — Хаят. Повтори: Хаят.",
             cta="Подпишись, впереди много нового!",
             themes=["flower blooming timelapse", "nature life"]),
    # --- Вторая серия (файл 30_Shorts_Arabic_Lessons_2.csv) ---
    31: dict(hook="Да и Нет по-арабски", ar="نعم / لا",
             translit="На́ам — да, Ля — нет",
             teach="Два самых нужных слова: Наам — да. Ля — нет. Повтори: Наам. Ля.",
             cta="Подпишись, дальше — интереснее!",
             themes=["morocco desert", "desert sunset", "sheikh zayed mosque"]),
    32: dict(hook="Как спросить «Где?»", ar="أين", translit="А́йна — где?",
             teach="Айна — где? Айна аль-фундук — где отель? Повтори: Айна.",
             cta="Сохрани, пригодится в путешествии!",
             themes=["medina morocco", "old map", "sahara dunes"]),
    33: dict(hook="Что это такое?", ar="ما هذا؟", translit="Ма ха́за — что это?",
             teach="Показывай на что угодно и спрашивай: Ма хаза — что это? Повтори: Ма хаза.",
             cta="Подпишись, учим арабский легко!",
             themes=["souk market", "morocco market", "desert sunset"]),
    34: dict(hook="Сколько стоит?", ar="بكم؟", translit="Бика́м — почём?",
             teach="Главный вопрос на рынке: Бикам — сколько стоит? Повтори: Бикам.",
             cta="Сохрани для поездки на восток!",
             themes=["gold souk", "grand bazaar", "sheikh zayed mosque"]),
    35: dict(hook="Волшебное слово Тайиб", ar="طيب", translit="Та́йиб — хорошо",
             teach="Тайиб — хорошо, ладно, договорились. Арабы говорят его постоянно. Повтори: Тайиб.",
             cta="Подпишись на канал!",
             themes=["oasis palm", "palm trees sunset", "sahara dunes"]),
    36: dict(hook="Слово дня: Сердце", ar="قلب", translit="Кальб — сердце",
             teach="Сердце по-арабски — Кальб. Говори от сердца. Повтори: Кальб.",
             cta="Ставь лайк от всего сердца!",
             themes=["red rose", "rose garden", "desert sunset"]),
    37: dict(hook="Слово дня: Свет", ar="نور", translit="Нур — свет",
             teach="Нур — свет. Красивое имя и красивое слово. Повтори: Нур.",
             cta="Подпишись, впереди много света!",
             themes=["ramadan lantern", "mosque lamp", "sheikh zayed mosque"]),
    38: dict(hook="Цвет дня: Красный", ar="أحمر", translit="А́хмар — красный",
             teach="Красный по-арабски — Ахмар. Повтори: Ахмар.",
             cta="Подпишись, соберём все цвета!",
             themes=["morocco spices", "red rose", "sahara dunes"]),
    39: dict(hook="Цвет дня: Зелёный", ar="أخضر", translit="А́хдар — зелёный",
             teach="Зелёный — цвет оазиса. По-арабски — Ахдар. Повтори: Ахдар.",
             cta="Ставь лайк, если любишь природу!",
             themes=["green oasis", "palm grove", "oasis palm"]),
    40: dict(hook="Цвет дня: Белый", ar="أبيض", translit="А́бъяд — белый",
             teach="Белый по-арабски — Абъяд. Как белые мечети. Повтори: Абъяд.",
             cta="Подпишись на канал!",
             themes=["white mosque", "sheikh zayed mosque", "white desert egypt"]),
    41: dict(hook="Слово дня: Море", ar="بحر", translit="Бахр — море",
             teach="Море по-арабски — Бахр. Красное море — Аль-Бахр аль-Ахмар. Повтори: Бахр.",
             cta="Ставь лайк, если любишь море!",
             themes=["red sea", "sea waves", "beach sunset"]),
    42: dict(hook="Слово дня: Звезда", ar="نجمة", translit="На́джма — звезда",
             teach="Звезда по-арабски — Наджма. Повтори: Наджма.",
             cta="Подпишись, ты — звезда!",
             themes=["milky way desert", "starry night", "night sky"]),
    43: dict(hook="Слово дня: Цветок", ar="وردة", translit="Ва́рда — цветок",
             teach="Цветок, роза по-арабски — Варда. Повтори: Варда.",
             cta="Отправь этот цветок близкому!",
             themes=["rose garden", "jasmine flower", "flower field"]),
    44: dict(hook="Доброе утро!", ar="صباح الخير", translit="Саба́х аль-хайр",
             teach="Доброе утро — Сабах аль-хайр. Ответ: Сабах ан-нур — утро света! Повтори: Сабах аль-хайр.",
             cta="Подпишись и начинай утро с арабского!",
             themes=["sunrise desert", "sunrise mosque", "sunrise"]),
    45: dict(hook="Добрый вечер!", ar="مساء الخير", translit="Маса́ аль-хайр",
             teach="Добрый вечер — Маса аль-хайр. Ответ: Маса ан-нур. Повтори: Маса аль-хайр.",
             cta="Подпишись на канал!",
             themes=["sunset mosque", "city lights evening", "desert sunset"]),
    46: dict(hook="Спокойной ночи", ar="تصبح على خير",
             translit="Ту́сбих аля хайр",
             teach="Спокойной ночи — Тусбих аля хайр, буквально: проснись во благе. Повтори: Тусбих аля хайр.",
             cta="Сохрани и пожелай кому-то доброй ночи!",
             themes=["full moon", "night sky stars", "city night"]),
    47: dict(hook="Как тебя зовут?", ar="ما اسمك؟",
             translit="Ма и́смук — как тебя зовут?",
             teach="Знакомимся: Ма исмук — как тебя зовут? Повтори: Ма исмук.",
             cta="Напиши своё имя в комментариях!",
             themes=["arabic calligraphy", "souk market", "sheikh zayed mosque"]),
    48: dict(hook="Меня зовут…", ar="اسمي", translit="И́сми — меня зовут",
             teach="Исми — меня зовут. Исми Марьям — меня зовут Марьям. Повтори: Исми.",
             cta="Представься по-арабски в комментариях!",
             themes=["arabic calligraphy", "medina morocco", "desert sunset"]),
    49: dict(hook="Я не понимаю", ar="لا أفهم", translit="Ля а́фхам — не понимаю",
             teach="Честная фраза новичка: Ля афхам — я не понимаю. Повтори: Ля афхам.",
             cta="Сохрани, выручит в разговоре!",
             themes=["old books", "arabic manuscript", "library"]),
    50: dict(hook="Я учу арабский!", ar="أنا أتعلم العربية",
             translit="А́на атаа́ллям аль-араби́йя",
             teach="Скажи с гордостью: Ана атааллям аль-арабийя — я учу арабский! Повтори медленно: Ана атааллям аль-арабийя.",
             cta="Подпишись, будем учить вместе!",
             themes=["arabic manuscript", "arabic calligraphy", "sahara dunes"]),
    51: dict(hook="Халва — это арабское слово!", ar="حلوى",
             translit="Ха́льва — сладость",
             teach="Русское слово халва пришло из арабского: Хальва — сладость. Повтори: Хальва.",
             cta="Ставь лайк, если сладкоежка!",
             themes=["baklava", "turkish delight", "arabic sweets"]),
    52: dict(hook="Сундук — тоже арабский!", ar="صندوق",
             translit="Сунду́к — ящик",
             teach="Слово сундук пришло из арабского: Сундук — ящик, коробка. Повтори: Сундук.",
             cta="Подпишись, таких слов ещё много!",
             themes=["treasure chest", "old chest", "souk market"]),
    53: dict(hook="Слово дня: Жираф", ar="زرافة", translit="Зара́фа — жираф",
             teach="И жираф — из арабского! Зарафа — жираф. Повтори: Зарафа.",
             cta="Подпишись, удивим ещё!",
             themes=["giraffe", "giraffe savanna", "africa savanna"]),
    54: dict(hook="Сахар — арабское слово", ar="سكر", translit="Су́ккар — сахар",
             teach="Сахар по-арабски — Суккар. Оттуда и пришло к нам. Повтори: Суккар.",
             cta="Ставь лайк, если любишь сладкий чай!",
             themes=["sugar", "morocco spices", "arabic sweets"]),
    55: dict(hook="Слово дня: Кошка", ar="قطة", translit="Ки́тта — кошка",
             teach="Кошка по-арабски — Китта. Повтори: Китта.",
             cta="Ставь лайк, если у тебя есть кот!",
             themes=["cat istanbul", "cat", "kitten"]),
    56: dict(hook="Слово дня: Птица", ar="طائر", translit="Та́ир — птица",
             teach="Птица по-арабски — Таир. Сокол — символ Эмиратов. Повтори: Таир.",
             cta="Подпишись на канал!",
             themes=["falcon", "bird flying", "falcon uae"]),
    57: dict(hook="Слово дня: Рыба", ar="سمك", translit="Са́мак — рыба",
             teach="Рыба по-арабски — Самак. Повтори: Самак.",
             cta="Сохрани, пригодится в ресторане!",
             themes=["red sea fish", "coral reef", "fish"]),
    58: dict(hook="Одну секунду!", ar="لحظة", translit="Ля́хза — момент",
             teach="Ляхза — секундочку, момент! Очень ходовое слово. Повтори: Ляхза.",
             cta="Подпишись, не теряй ни секунды!",
             themes=["hourglass", "sand dunes wind", "sahara dunes"]),
    59: dict(hook="Добро пожаловать!", ar="أهلاً وسهلاً",
             translit="А́хлян ва са́хлян",
             teach="Знаменитое гостеприимство: Ахлян ва сахлян — добро пожаловать! Повтори: Ахлян ва сахлян.",
             cta="Добро пожаловать на канал — подпишись!",
             themes=["moroccan door", "arabic door", "riad morocco"]),
    60: dict(hook="До свидания!", ar="مع السلامة",
             translit="Ма́а с-саля́ма",
             teach="Прощаемся красиво: Маа с-саляма — до свидания, с миром. Повтори: Маа с-саляма.",
             cta="Подпишись, мы не прощаемся!",
             themes=["camel caravan", "desert sunset", "sunset"]),
}


def pick_font(candidates, size):
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def ar_text(s):
    return get_display(RESHAPER.reshape(s))


def strip_accents(s):
    """Убирает ударения-диакритики: TTS читает их с ошибками."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(ch))


def tts_text(n, lesson):
    """Развёрнутый сценарий озвучки: повторы слова, паузы, ровный темп.

    Голосовое «подпишись» — через ролик (в каждом втором), чтобы не
    надоедало; на экране призыв есть всегда."""
    parts = [p.strip() for p in strip_accents(lesson["translit"]).split("—")]
    word = parts[0].rstrip("!?.")
    meaning = parts[1] if len(parts) > 1 else ""

    s = f'{lesson["hook"]}. {lesson["teach"]}'
    s += f' Повторим ещё раз: {word}.'
    if meaning:
        s += f' Запомни: {word} — значит «{meaning}».'
    s += f' А теперь скажи вслух: {word}. Отлично, у тебя получается!'
    if n % 2 == 0:
        s += f' {lesson["cta"]}'
    return s


def run(*cmd):
    p = subprocess.run(list(cmd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p


def ffmpeg(*args):
    return run("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args)


def probe_duration(path):
    p = run("ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=nw=1:nk=1", str(path))
    return float(p.stdout.strip())


# ---------- озвучка ----------

def elevenlabs_tts(text, out_mp3: Path):
    key = os.environ["ELEVENLABS_API_KEY"]
    voice = os.environ["ELEVENLABS_VOICE_ID"]
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
        "?output_format=mp3_44100_128",
        data=json.dumps({"text": text,
                         "model_id": "eleven_multilingual_v2",
                         # Повыше стабильность — меньше оговорок и глюков
                         "voice_settings": {"stability": 0.6,
                                            "similarity_boost": 0.75}}).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out_mp3.write_bytes(r.read())


# ---------- фоновые ролики ----------

# Недопустимые сюжеты: новости о трагедиях, политика, конфликты и т.п.
BAD_WORDS = ("bombing", "bomb", "attack", "war", "riot", "protest",
             "funeral", "crash", "accident", "shooting", "destruction",
             "damage", "rubble", "demolit", "flood", "earthquake", "strike",
             "arson", "vandal", "clash", "president", "potus", "minister")


def commons_image_urls(term, limit=8):
    """Ищет фотографии на Wikimedia Commons, отдаёт URL уменьшенных копий.

    Видео на Commons — в основном хроника и новости, а фото мечетей и
    пустынь много профессиональных. Из фото делаем кен-бёрнс.
    Берём thumb-версии (iiurlheight) — так просят сами Wikimedia."""
    search = " ".join(f"intitle:{w}" for w in term.split()) + " filetype:bitmap"
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search",
        "gsrnamespace": "6", "gsrsearch": search, "gsrlimit": limit,
        "prop": "imageinfo", "iiprop": "url|mime|size",
        "iiurlheight": "2100",
    })
    req = urllib.request.Request(
        "https://commons.wikimedia.org/w/api.php?" + q,
        headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except Exception as e:
        print(f"  поиск «{term}» не удался: {e}")
        return []
    urls = []
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        for ii in page.get("imageinfo", []):
            if ii.get("mime") in ("image/jpeg", "image/png"):
                urls.append((ii.get("size", 0),
                             ii.get("thumburl") or ii["url"]))
    # Крупные оригиналы первыми: обычно это самые качественные снимки
    return [u for _, u in sorted(urls, reverse=True)
            if not any(b in u.lower() for b in BAD_WORDS)]


def download_head(url, out: Path, max_bytes=40_000_000) -> bool:
    """Качает файл (ffmpeg в песочнице сам в сеть не ходит)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, out.open("wb") as f:
            got = 0
            while got < max_bytes:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
        return out.stat().st_size > 30_000
    except Exception as e:
        print(f"  скачивание не удалось: {e}")
        if out.exists():
            out.unlink()
        return False


def kenburns_clip(img: Path, seg_dur, out: Path, zoom_in=True) -> bool:
    """Оживляет фото плавным наездом/отъездом камеры (кен-бёрнс)."""
    frames = max(int(seg_dur * 30), 30)
    step = 0.22 / frames
    z = f"1+{step:.6f}*on" if zoom_in else f"1.22-{step:.6f}*on"
    p = ffmpeg("-loop", "1", "-i", str(img),
               "-vf", ("scale=2160:3840:force_original_aspect_ratio=increase,"
                       "crop=2160:3840,"
                       f"zoompan=z='{z}':d={frames}"
                       ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                       ":s=1080x1920:fps=30"),
               "-frames:v", str(frames),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
               "-pix_fmt", "yuv420p", str(out))
    ok = p.returncode == 0 and out.exists() and out.stat().st_size > 50_000
    if not ok and out.exists():
        out.unlink()
    return ok


def fallback_clip(seg_dur, out: Path):
    """Если сток не нашёлся — фирменный анимированный градиент."""
    ffmpeg("-f", "lavfi",
           "-i", ("gradients=size=1080x1920:speed=0.02:nb_colors=3:"
                  "c0=0x0E573E:c1=0xDEB84A:c2=0x083D2B"),
           "-t", f"{seg_dur:.2f}", "-r", "30",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
           "-pix_fmt", "yuv420p", str(out))


def build_background(lesson, total_dur, work: Path) -> Path:
    """2–3 тематических фото-сцены, склеенных в один фон нужной длины."""
    want = 3
    seg_dur = total_dur / want
    clips = []
    for term in lesson["themes"]:
        if len(clips) >= want:
            break
        for url in commons_image_urls(term):
            img = work / f"photo_{len(clips):02d}.img"
            print(f"  фон: {term} <- {url.rsplit('/', 1)[-1][:60]}")
            if not download_head(url, img):
                time.sleep(2)
                continue
            out = work / f"clip_{len(clips):02d}.mp4"
            if kenburns_clip(img, seg_dur, out, zoom_in=len(clips) % 2 == 0):
                clips.append(out)
                break
            time.sleep(2)
    while len(clips) < want:
        out = work / f"clip_{len(clips):02d}.mp4"
        print("  фон: градиент (сток не нашёлся)")
        fallback_clip(seg_dur, out)
        clips.append(out)

    lst = work / "concat.txt"
    lst.write_text("\n".join(f"file '{c.resolve().as_posix()}'"
                             for c in clips), encoding="utf-8")
    bg = work / "bg.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(bg))
    return bg


# ---------- текстовый слой ----------

def rounded_panel(d, box, radius=36, alpha=150):
    d.rounded_rectangle(box, radius=radius, fill=(8, 30, 22, alpha))


def wrap_to_width(d, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


CTA_TEXT = "Хочешь учить арабский легко? Подпишись!"


def draw_overlay(lesson, out_png: Path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Лёгкое затемнение всего кадра + виньетки сверху и снизу,
    # чтобы текст читался на любом видео (как на роликах пользователя)
    d.rectangle([0, 0, W, H], fill=(8, 20, 15, 50))
    for i in range(420):
        a = int(130 * (1 - i / 420))
        d.line([(0, i), (W, i)], fill=(5, 15, 10, a))
        d.line([(0, H - 1 - i), (W, H - 1 - i)], fill=(5, 15, 10, a))

    # Золотые линии-акценты вокруг арабского слова
    for half, y in ((300, 620), (190, 648), (300, 1300), (190, 1272)):
        d.line([(W // 2 - half, y), (W // 2 + half, y)],
               fill=GOLD + (220,), width=5)

    # Крючок сверху на полупрозрачной плашке
    f_hook = pick_font(FONT_BOLD, 84)
    lines = wrap_to_width(d, lesson["hook"], f_hook, W - 180)
    lh = 104
    top, bot = 190, 190 + 70 + lh * len(lines)
    rounded_panel(d, [60, top, W - 60, bot])
    y = top + 42
    for line in lines:
        d.text((W // 2, y + lh // 2), line, font=f_hook,
               fill=(255, 255, 255), anchor="mm",
               stroke_width=3, stroke_fill=(8, 30, 22))
        y += lh

    # Арабское слово — крупно, золотом, по центру
    f_ar = pick_font(FONT_AR, 300)
    txt = ar_text(lesson["ar"])
    while d.textlength(txt, font=f_ar) > W - 140 and f_ar.size > 120:
        f_ar = pick_font(FONT_AR, f_ar.size - 20)
    d.text((W // 2, 870), txt, font=f_ar, fill=GOLD, anchor="mm",
           stroke_width=6, stroke_fill=(8, 30, 22))

    # Транслитерация и перевод
    f_tr = pick_font(FONT_BOLD, 76)
    while d.textlength(lesson["translit"], font=f_tr) > W - 160 and f_tr.size > 40:
        f_tr = pick_font(FONT_BOLD, f_tr.size - 4)
    d.text((W // 2, 1150), lesson["translit"], font=f_tr,
           fill=(255, 255, 255), anchor="mm",
           stroke_width=3, stroke_fill=(8, 30, 22))

    # Фирменный призыв внизу на плашке (единый, как в ручных роликах)
    f_cta = pick_font(FONT_BOLD, 56)
    lines = wrap_to_width(d, CTA_TEXT, f_cta, W - 220)
    lh = 74
    bot, top = 1730, 1730 - 56 - lh * len(lines)
    rounded_panel(d, [80, top, W - 80, bot])
    y = top + 32
    for line in lines:
        d.text((W // 2, y + lh // 2), line, font=f_cta,
               fill=GOLD, anchor="mm",
               stroke_width=2, stroke_fill=(8, 30, 22))
        y += lh

    img.save(out_png)


# ---------- сборка ----------

def caption_for(n, lesson):
    return (f'{lesson["hook"]} · {lesson["ar"]} · {lesson["translit"]}\n'
            f'{lesson["teach"]}\n{lesson["cta"]}\n'
            "#арабский #арабскийязык #арабскийснуля #учимарабский #шортс")


def build_short(n: int):
    lesson = LESSONS[n]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    work = OUT_DIR / f"work_{n:02d}"
    work.mkdir(exist_ok=True)
    print(f"Урок {n}: {lesson['hook']}")

    voice = work / "voice.mp3"
    if not voice.exists():
        print("  озвучка ElevenLabs...")
        elevenlabs_tts(tts_text(n, lesson), voice)
    total = probe_duration(voice) + 1.5

    overlay = work / "overlay.png"
    draw_overlay(lesson, overlay)

    bg = build_background(lesson, total, work)

    out = OUT_DIR / f"short_{n:02d}.mp4"
    p = ffmpeg("-i", str(bg), "-i", str(overlay), "-i", str(voice),
               "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
               "-map", "[v]", "-map", "2:a", "-af", "apad",
               "-t", f"{total:.2f}",
               "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", str(out))
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg: {p.stderr[-800:]}")

    (OUT_DIR / f"short_{n:02d}.txt").write_text(
        caption_for(n, lesson), encoding="utf-8")
    print(f"  готово: {out}  ({total:.0f} сек)")
    return out


if __name__ == "__main__":
    nums = [int(a) for a in sys.argv[1:]] or [10]
    for n in nums:
        build_short(n)
