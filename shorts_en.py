# -*- coding: utf-8 -*-
"""
Шортсы для англоязычного канала «арабский для всех»: тот же конвейер,
что и shorts_v2.py (фото-фоны Wikimedia + крупное арабское слово +
ElevenLabs), но вся речь, подписи и тексты — на английском.

Запуск:
    python shorts_en.py 1          # один урок
    python shorts_en.py 1 2 5      # несколько

Голоса: английская речь — бесплатный en-US-AvaNeural (или ElevenLabs при
EN_TTS=elevenlabs, голос из ELEVENLABS_VOICE_ID_EN), арабские слова —
носитель ar-SA-ZariyahNeural (edge-tts), чтобы не было ошибок произношения.
Результат: build/shorts_en/short_NN.mp4 + short_NN.txt (подпись для поста).
"""

import os
import re
import sys
from pathlib import Path

import shorts_v2 as v2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT_DIR = Path("build") / "shorts_en"
# Арабские слова — носитель языка (как в уроках русского канала)
AR_VOICE = "ar-SA-ZariyahNeural"
AR_RATE = "-25%"
# Английская речь — бесплатный голос edge-tts; кредиты ElevenLabs
# оставлены русскому каналу. EN_TTS=elevenlabs вернёт голос русского канала.
EN_TTS = os.environ.get("EN_TTS", "edge")
EN_VOICE = "en-US-AvaNeural"
EN_RATE = "-5%"

# hook — крючок сверху, ar — арабское слово, translit — «слово — значение»
# (слово до тире озвучивается настоящим арабским аудио), teach — обучающая
# фраза, cta — призыв, themes — поиск фото на Wikimedia Commons.
# Слово из translit должно дословно встречаться в teach — тогда и там
# звучит арабское произношение, а не английское чтение транслита.
LESSONS = {
    1:  dict(hook="Say Hello in Arabic", ar="مَرْحَبًا", translit="Marhaba — hello",
             teach="The easiest way to say hello in Arabic is Marhaba. Say it with a smile: Marhaba!",
             cta="Subscribe and learn one word a day!",
             themes=["sheikh zayed mosque", "sahara dunes", "arabic calligraphy"]),
    2:  dict(hook="You already speak Arabic: Sugar", ar="سُكَّر", translit="Sukkar — sugar",
             teach="The English word sugar comes from Arabic: Sukkar. Sukkar, sugar. Sounds familiar, right?",
             cta="Subscribe, more hidden Arabic words coming!",
             themes=["sugar cane field", "sugar cubes", "baklava", "morocco spices"]),
    3:  dict(hook="How to say Thank you", ar="شُكْرًا", translit="Shukran — thank you",
             teach="Thank you in Arabic is Shukran. Use it everywhere: Shukran!",
             cta="Subscribe, new phrases tomorrow!",
             themes=["arabic coffee", "sahara dunes", "sheikh zayed mosque"]),
    4:  dict(hook="Coffee is an Arabic word", ar="قَهْوَة", translit="Qahwa — coffee",
             teach="Coffee travelled the world from Arabia, and so did its name: Qahwa. Qahwa became coffee.",
             cta="Like if you can't live without coffee!",
             themes=["arabic coffee", "coffee pouring"]),
    5:  dict(hook="The greeting of 2 billion people", ar="السَّلَامُ عَلَيْكُمْ",
             translit="As-salamu alaykum — peace be upon you",
             teach="From Morocco to Indonesia, people greet each other with As-salamu alaykum. It means peace be upon you.",
             cta="Subscribe and learn Arabic with us!",
             themes=["sheikh zayed mosque", "mosque interior", "arabic calligraphy"]),
    6:  dict(hook="Yes and No in Arabic", ar="نَعَمْ / لَا", translit="Na'am / La — yes / no",
             teach="The two most useful words you will ever learn. Yes and no in Arabic: Na'am / La.",
             cta="Subscribe, it only gets better!",
             themes=["morocco desert", "desert sunset", "sheikh zayed mosque"]),
    7:  dict(hook="Giraffe comes from Arabic!", ar="زَرَافَة", translit="Zarafa — giraffe",
             teach="Even the giraffe got its name from Arabic: Zarafa. Zarafa, giraffe.",
             cta="Subscribe for more surprises!",
             themes=["giraffe", "giraffe savanna", "africa savanna"]),
    8:  dict(hook="How to ask Where?", ar="أَيْنَ", translit="Ayna — where?",
             teach="Lost in the old city? Just ask Ayna. Ayna means where.",
             cta="Save this for your next trip!",
             themes=["medina morocco", "old map", "sahara dunes"]),
    9:  dict(hook="What is this?", ar="مَا هَذَا؟", translit="Ma hadha — what is this?",
             teach="Point at anything and ask: Ma hadha. It means what is this?",
             cta="Subscribe, Arabic made easy!",
             themes=["moroccan lanterns", "dates fruit", "ceramic tiles"]),
    10: dict(hook="Zero is an Arabic word", ar="صِفْر", translit="Sifr — zero",
             teach="The idea of zero reached Europe through Arabic. Sifr gave us both zero and cipher.",
             cta="Share with a math lover!",
             themes=["arabic manuscript", "old books", "astrolabe"]),
    11: dict(hook="How much is it?", ar="بِكَمْ؟", translit="Bikam — how much?",
             teach="The most important question at any market: Bikam. How much is it?",
             cta="Save this before you go shopping!",
             themes=["morocco spices", "gold jewellery", "brass teapot"]),
    12: dict(hook="The magic word Tayyib", ar="طَيِّب", translit="Tayyib — okay",
             teach="Tayyib means okay, good, deal. Arabs say it all the time: Tayyib.",
             cta="Subscribe for daily Arabic!",
             themes=["oasis palm", "palm trees sunset", "sahara dunes"]),
    13: dict(hook="Algebra is Arabic!", ar="الْجَبْر", translit="Al-jabr — algebra",
             teach="Algebra is named after an Arabic book from Baghdad. Its title had the word Al-jabr, which means restoring.",
             cta="Tag the friend who hated algebra!",
             themes=["arabic manuscript", "astrolabe", "old books"]),
    14: dict(hook="What's your name?", ar="مَا اسْمُكَ؟", translit="Ma ismuk — what's your name?",
             teach="Meeting someone new? Ask: Ma ismuk. What's your name?",
             cta="Write your name in the comments!",
             themes=["arabic calligraphy", "moroccan lanterns", "sheikh zayed mosque"]),
    15: dict(hook="My name is...", ar="اسْمِي", translit="Ismi — my name is",
             teach="To introduce yourself, say Ismi and then your name. Ismi Maryam: my name is Maryam.",
             cta="Introduce yourself in Arabic below!",
             themes=["arabic calligraphy", "medina morocco", "desert sunset"]),
    16: dict(hook="Lemon is Arabic too", ar="لَيْمُون", translit="Laymun — lemon",
             teach="Lemon came to English through Arabic: Laymun. Laymun, lemon.",
             cta="Like if you knew that!",
             themes=["lemon", "lemon tree", "citrus fruit"]),
    17: dict(hook="I don't understand", ar="لَا أَفْهَم", translit="La afham — I don't understand",
             teach="Every beginner needs this one: La afham. I don't understand.",
             cta="Save it, it will save you!",
             themes=["old books", "arabic manuscript", "library"]),
    18: dict(hook="Good morning in Arabic", ar="صَبَاحُ الْخَيْر", translit="Sabah al-khayr — good morning",
             teach="Good morning is Sabah al-khayr. The reply is even more beautiful: morning of light.",
             cta="Subscribe and start your day with Arabic!",
             themes=["sunrise desert", "sunrise mosque", "sunrise"]),
    19: dict(hook="Cotton comes from Arabic", ar="قُطْن", translit="Qutn — cotton",
             teach="Your cotton T-shirt speaks Arabic! Cotton comes from Qutn.",
             cta="Subscribe, more hidden Arabic words!",
             themes=["cotton field", "cotton plant", "cotton"]),
    20: dict(hook="Good evening in Arabic", ar="مَسَاءُ الْخَيْر", translit="Masa al-khayr — good evening",
             teach="When the sun goes down, say Masa al-khayr. Good evening.",
             cta="Subscribe for more greetings!",
             themes=["sunset mosque", "city lights evening", "desert sunset"]),
    21: dict(hook="Good night in Arabic", ar="تُصْبِحُ عَلَى خَيْر", translit="Tusbih ala khayr — good night",
             teach="Good night is Tusbih ala khayr. Literally: may you wake up well.",
             cta="Save it and wish someone good night!",
             themes=["full moon", "night sky stars", "city night"]),
    22: dict(hook="Safari is an Arabic word", ar="سَفَر", translit="Safar — journey",
             teach="Safari came from the Arabic word Safar, which means a journey.",
             cta="Like if you love to travel!",
             themes=["africa savanna", "camel caravan", "desert road"]),
    23: dict(hook="Welcome in Arabic", ar="أَهْلًا وَسَهْلًا", translit="Ahlan wa sahlan — welcome",
             teach="Famous Arab hospitality starts with Ahlan wa sahlan. Welcome!",
             cta="Welcome to the channel, subscribe!",
             themes=["moroccan door", "arabic door", "riad morocco"]),
    24: dict(hook="Goodbye in Arabic", ar="مَعَ السَّلَامَة", translit="Ma'a as-salama — goodbye",
             teach="Say goodbye beautifully: Ma'a as-salama. Go with peace.",
             cta="Subscribe, this is not goodbye!",
             themes=["camel caravan", "desert sunset", "sunset"]),
    25: dict(hook="Magazine comes from Arabic", ar="مَخْزَن", translit="Makhzan — storehouse",
             teach="A magazine was once a storehouse, from the Arabic Makhzan. A storehouse of stories!",
             cta="Subscribe for more word stories!",
             themes=["old books", "library", "arabic manuscript"]),
    26: dict(hook="Just a moment!", ar="لَحْظَة", translit="Lahza — one moment",
             teach="Lahza means just a moment! You will hear it everywhere: Lahza.",
             cta="Subscribe, don't waste a moment!",
             themes=["hourglass", "sand dunes wind", "sahara dunes"]),
    27: dict(hook="I'm learning Arabic!", ar="أَنَا أَتَعَلَّمُ الْعَرَبِيَّة",
             translit="Ana ata'allam al-arabiyya — I'm learning Arabic",
             teach="Say it with pride: Ana ata'allam al-arabiyya. I'm learning Arabic!",
             cta="Subscribe and let's learn together!",
             themes=["arabic manuscript", "arabic calligraphy", "sahara dunes"]),
    28: dict(hook="Word of the day: Water", ar="مَاء", translit="Maa — water",
             teach="No life without water. Water in Arabic is Maa.",
             cta="Like if you drank water today!",
             themes=["water drops", "ocean waves", "waterfall"]),
    29: dict(hook="Word of the day: Bread", ar="خُبْز", translit="Khubz — bread",
             teach="Fresh bread from the oven is Khubz. Say it: Khubz.",
             cta="Subscribe before you get hungry!",
             themes=["bread baking", "wheat field"]),
    30: dict(hook="Word of the day: House", ar="بَيْت", translit="Bayt — house",
             teach="Home sweet home. House in Arabic is Bayt.",
             cta="Save this word!",
             themes=["old city street", "cozy house"]),
    31: dict(hook="Word of the day: Sun", ar="شَمْس", translit="Shams — sun",
             teach="The sun shines for everyone. Sun in Arabic is Shams.",
             cta="Like if you love sunny days!",
             themes=["sunrise timelapse", "sun clouds"]),
    32: dict(hook="Word of the day: Moon", ar="قَمَر", translit="Qamar — moon",
             teach="In Arabic poetry the moon means beauty. Moon is Qamar.",
             cta="Subscribe, new words tomorrow!",
             themes=["full moon", "night sky timelapse"]),
    33: dict(hook="Word of the day: City", ar="مَدِينَة", translit="Madina — city",
             teach="City in Arabic is Madina. You may know the famous city of Madina!",
             cta="Subscribe to the channel!",
             themes=["city skyline night", "old arab city"]),
    34: dict(hook="Word of the day: Car", ar="سَيَّارَة", translit="Sayyara — car",
             teach="Car in Arabic is Sayyara. Literally: the one that travels.",
             cta="Like if you love road trips!",
             themes=["desert road driving", "car road"]),
    35: dict(hook="Word of the day: Friend", ar="صَدِيق", translit="Sadiq — friend",
             teach="A true friend is Sadiq. It comes from the word for truth.",
             cta="Send this to your friend!",
             themes=["arabic coffee", "tea pouring glass"]),
    36: dict(hook="Word of the day: Mother", ar="أُمّ", translit="Umm — mother",
             teach="The most important word of all. Mother in Arabic is Umm.",
             cta="Like if you love your mom!",
             themes=["red rose garden", "cozy house interior"]),
    37: dict(hook="Word of the day: Father", ar="أَب", translit="Ab — father",
             teach="Father, the pillar of the family. Father in Arabic is Ab.",
             cta="Subscribe to the channel!",
             themes=["old wooden door morocco", "compass vintage"]),
    38: dict(hook="Word of the day: Brother", ar="أَخ", translit="Akh — brother",
             teach="Brother in Arabic is Akh. Short and strong.",
             cta="Send this to your brother!",
             themes=["two camels desert", "bridge stone arch"]),
    39: dict(hook="Word of the day: Sister", ar="أُخْت", translit="Ukht — sister",
             teach="Sister in Arabic is Ukht. Your best friend for life.",
             cta="Send this to your sister!",
             themes=["two roses garden", "butterflies pair"]),
    40: dict(hook="Word of the day: Apple", ar="تُفَّاح", translit="Tuffah — apple",
             teach="An apple a day keeps the doctor away. Apple in Arabic is Tuffah.",
             cta="Like if you love apples!",
             themes=["red apples", "apple orchard"]),
    41: dict(hook="Word of the day: Tea", ar="شَاي", translit="Shay — tea",
             teach="Nothing says hospitality like a glass of tea. Tea in Arabic is Shay.",
             cta="Save it while it's hot!",
             themes=["tea pouring glass", "tea"]),
    42: dict(hook="Word of the day: Sky", ar="سَمَاء", translit="Samaa — sky",
             teach="Look up! Sky in Arabic is Samaa.",
             cta="Subscribe to the channel!",
             themes=["clouds timelapse", "blue sky"]),
    43: dict(hook="Word of the day: Earth", ar="أَرْض", translit="Ard — earth",
             teach="Earth, land, ground. In Arabic it is all Ard.",
             cta="Save this word!",
             themes=["green landscape aerial", "earth nature"]),
    44: dict(hook="Word of the day: Life", ar="حَيَاة", translit="Hayat — life",
             teach="Life is beautiful. Life in Arabic is Hayat.",
             cta="Subscribe, there is so much more to learn!",
             themes=["flower blooming timelapse", "nature life"]),
    45: dict(hook="Word of the day: Heart", ar="قَلْب", translit="Qalb — heart",
             teach="Speak from the heart. Heart in Arabic is Qalb.",
             cta="Like from the heart!",
             themes=["red rose", "rose garden", "desert sunset"]),
    46: dict(hook="Word of the day: Light", ar="نُور", translit="Nur — light",
             teach="A beautiful word and a beautiful name. Light in Arabic is Nur.",
             cta="Subscribe for more light!",
             themes=["ramadan lantern", "mosque lamp", "sheikh zayed mosque"]),
    47: dict(hook="Color of the day: Red", ar="أَحْمَر", translit="Ahmar — red",
             teach="Red in Arabic is Ahmar. Like the Red Sea!",
             cta="Subscribe and collect all the colors!",
             themes=["morocco spices", "red rose", "sahara dunes"]),
    48: dict(hook="Color of the day: Green", ar="أَخْضَر", translit="Akhdar — green",
             teach="Green is the color of the oasis. In Arabic it is Akhdar.",
             cta="Like if you love nature!",
             themes=["green oasis", "palm grove", "oasis palm"]),
    49: dict(hook="Color of the day: White", ar="أَبْيَض", translit="Abyad — white",
             teach="White like the marble of a mosque. White in Arabic is Abyad.",
             cta="Subscribe to the channel!",
             themes=["white mosque", "sheikh zayed mosque", "white desert egypt"]),
    50: dict(hook="Word of the day: Sea", ar="بَحْر", translit="Bahr — sea",
             teach="Close your eyes and hear the waves. Sea in Arabic is Bahr.",
             cta="Like if you love the sea!",
             themes=["red sea", "sea waves", "beach sunset"]),
    51: dict(hook="Word of the day: Star", ar="نَجْمَة", translit="Najma — star",
             teach="Many stars still carry Arabic names. Star in Arabic is Najma.",
             cta="Subscribe, you are a star!",
             themes=["milky way desert", "starry night", "night sky"]),
    52: dict(hook="Word of the day: Rose", ar="وَرْدَة", translit="Warda — rose",
             teach="A rose, a flower. In Arabic it is Warda.",
             cta="Send this flower to someone you love!",
             themes=["rose garden", "jasmine flower", "flower field"]),
    53: dict(hook="Word of the day: Cat", ar="قِطَّة", translit="Qitta — cat",
             teach="Cats are loved all over the Arab world. Cat in Arabic is Qitta.",
             cta="Like if you have a cat!",
             themes=["cat istanbul", "cat", "kitten"]),
    54: dict(hook="Word of the day: Bird", ar="طَائِر", translit="Tair — bird",
             teach="Bird in Arabic is Tair. The falcon is the bird of the desert.",
             cta="Subscribe to the channel!",
             themes=["falcon", "bird flying", "falcon uae"]),
    55: dict(hook="Word of the day: Fish", ar="سَمَك", translit="Samak — fish",
             teach="Fish in Arabic is Samak. Useful at any seaside restaurant!",
             cta="Save it for your next dinner out!",
             themes=["red sea fish", "coral reef", "fish"]),
    56: dict(hook="Word of the day: Camel", ar="جَمَل", translit="Jamal — camel",
             teach="The ship of the desert. Camel in Arabic is Jamal.",
             cta="Subscribe for more desert words!",
             themes=["camel desert", "desert dunes"]),
    57: dict(hook="Word of the day: Book", ar="كِتَاب", translit="Kitab — book",
             teach="The first step to any language is a book. Book in Arabic is Kitab.",
             cta="Subscribe and keep learning!",
             themes=["old books", "arabic manuscript", "library"]),
}

# Связующие фразы варьируются по уроку, как в shorts_v2 — чтобы ролики
# подряд не звучали одним шаблоном.
INTRO_PHRASES = [
    "Here's how it sounds in Arabic",
    "Listen to the real Arabic pronunciation",
    "This is how you say it in Arabic",
    "Listen closely to how it sounds in Arabic",
]
REPEAT_PHRASES = [
    "One more time",
    "Again, slowly",
    "Once more, so it sticks",
    "Listen again",
]
MEANING_LEADS = [
    "Remember",
    "Don't forget",
    "Keep this in mind",
    "Lock it in",
]
ASK_PHRASES = [
    "Now say it out loud",
    "Your turn, say it out loud",
    "Try it yourself",
    "Repeat after me",
]
OUTRO_PHRASES = [
    "Great job!",
    "Perfect, you've got it!",
    "Awesome, you're doing great!",
    "Well done, keep going!",
]

CTA_TEXT = "Learn Arabic one word a day. Subscribe!"

# Теги и хэштеги — по смыслу ролика, а не одни и те же на всех:
# YouTube по ним понимает, кому показывать, а зритель ищет именно это.
GROUPS = {
    "loanwords": ([2, 4, 7, 10, 13, 16, 19, 22, 25],
                  ["english words from arabic", "word origins", "etymology",
                   "arabic loanwords", "language facts"],
                  "#etymology #wordorigins #languagefacts"),
    "greetings": ([1, 5, 18, 20, 21, 23, 24],
                  ["arabic greetings", "how to say hello in arabic",
                   "arabic phrases", "speak arabic"],
                  "#arabicgreetings #arabicphrases #speakarabic"),
    "phrases": ([6, 8, 9, 11, 12, 14, 15, 17, 26, 27],
                ["arabic phrases", "travel arabic", "arabic conversation",
                 "useful arabic", "speak arabic"],
                "#arabicphrases #travelarabic #speakarabic"),
    "colors": ([47, 48, 49],
               ["arabic colors", "colors in arabic", "arabic vocabulary"],
               "#arabiccolors #arabicvocabulary"),
    "family": ([36, 37, 38, 39],
               ["family in arabic", "arabic family words", "arabic vocabulary"],
               "#arabicfamily #arabicvocabulary"),
}
BASE_TAGS = ["learn arabic", "arabic", "arabic for beginners",
             "arabic words", "arabic lesson", "shorts"]
BASE_HASHTAGS = "#learnarabic #arabic #arabicforbeginners"


def _group(n):
    for name, (nums, tags, hashtags) in GROUPS.items():
        if n in nums:
            return tags, hashtags
    return (["arabic vocabulary", "word of the day", "arabic words for beginners"],
            "#arabicvocabulary #wordoftheday")


def tags_for(n):
    word, meaning = split_translit(LESSONS[n])
    extra, _ = _group(n)
    meaning = meaning.rstrip("?!.")
    own = [f"{meaning} in arabic", f"arabic word {word.lower()}"] if meaning else []
    # YouTube принимает до 500 символов тегов — с запасом укладываемся
    return BASE_TAGS + extra + own


def hashtags_for(n):
    _, meaning = split_translit(LESSONS[n])
    _, extra = _group(n)
    own = "#" + re.sub(r"[^a-z]", "", meaning.lower()) if meaning else ""
    return " ".join(x for x in (BASE_HASHTAGS, extra, own, "#shorts") if x)


# Фильтр shorts_v2 пропускал людей и неуместное: проводник-бербер в
# пустыне, картина «Придворные в розовом саду», могила с розой.
EXTRA_BAD = re.compile(
    r"(?:guide|courtier|lad(?:y|ies)|gentlem[ae]n|grave|tomb|cemetery|"
    r"berber|tuareg|nomad|bedouin|merchant|vendor|seller|tourist|"
    r"market|souk|bazaar|shop|stall|crowd|workers?|"
    r"portrait|painting)", re.IGNORECASE)
_commons_image_urls = v2.commons_image_urls


def commons_image_urls(term, limit=8):
    return [u for u in _commons_image_urls(term, limit)
            if not EXTRA_BAD.search(u)]


# build_background в shorts_v2 ищет фото через эту функцию модуля
v2.commons_image_urls = commons_image_urls

_kenburns_clip = v2.kenburns_clip


CASCADES = Path("build") / "cascades"
CASCADE_URL = ("https://raw.githubusercontent.com/opencv/opencv/4.x/data/"
               "haarcascades/")


def _cascade_file(name):
    """OpenCV 5 больше не кладёт каскады в пакет — качаем один раз."""
    CASCADES.mkdir(parents=True, exist_ok=True)
    path = CASCADES / name
    if not path.exists():
        import urllib.request
        urllib.request.urlretrieve(CASCADE_URL + name, path)
    return str(path)


def has_face(img: Path) -> bool:
    """Ищет лица на фото. Фильтр по названию файла ловит не всё: на
    рынках и в пустыне люди попадали в кадр. Не распознаётся — считаем,
    что лица нет (отказ проверки не должен останавливать сборку)."""
    try:
        import cv2
        data = cv2.imread(str(img))
        if data is None:
            return False
        gray = cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
        for name in ("haarcascade_frontalface_default.xml",
                     "haarcascade_profileface.xml"):
            cascade = cv2.CascadeClassifier(_cascade_file(name))
            if len(cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))):
                return True
    except Exception as e:
        print(f"  проверка на лица не сработала: {e}")
    return False


def kenburns_clip(img, seg_dur, out, zoom_in=True):
    if has_face(img):
        print("  фото отклонено: в кадре лицо")
        return False
    return _kenburns_clip(img, seg_dur, out, zoom_in)


v2.kenburns_clip = kenburns_clip


def split_translit(lesson):
    word, _, meaning = lesson["translit"].partition("—")
    return word.strip().rstrip("!?."), meaning.strip()


def tts_plan(n, lesson):
    """Сценарий озвучки: английская речь, а каждое вхождение транслита
    заменяется на сегмент с настоящим арабским словом (см.
    shorts_v2.split_word_occurrences)."""
    word, meaning = split_translit(lesson)
    s = f'{lesson["hook"]}. {v2._pick(INTRO_PHRASES, n, 0)}: {word}.'
    s += f' {lesson["teach"]}'
    s += f' {v2._pick(REPEAT_PHRASES, n, 1)}: {word}.'
    if meaning:
        s += f' {v2._pick(MEANING_LEADS, n, 2)}: {word} means {meaning}.'
    s += f' {v2._pick(ASK_PHRASES, n, 3)}: {word}. {v2._pick(OUTRO_PHRASES, n, 4)}'
    if n % 2 == 0:
        s += f' {lesson["cta"]}'
    return v2.split_word_occurrences(s, word, lesson["ar"])


def edge_tts(text, voice, out_mp3: Path, rate=None):
    import asyncio
    import edge_tts as et
    kw = {"rate": rate} if rate else {}
    asyncio.run(et.Communicate(text.strip(), voice, **kw).save(str(out_mp3)))


def synthesize_plan(plan, out_mp3: Path, work: Path):
    """Как shorts_v2.synthesize_plan, но арабское слово читает носитель
    (edge-tts Zariyah, медленно — как в уроках русского канала), а не
    ElevenLabs: у ElevenLabs-голоса бывали ошибки в арабском."""
    cache, clips = {}, []
    silence = work / "_silence.mp3"
    if not silence.exists():
        v2.ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                  "-t", "0.35", "-q:a", "9", str(silence))
    for kind, text in plan:
        if text not in cache:
            # единый формат (44.1 кГц моно) — иначе concat путает дорожки
            clip = work / f"_seg_{kind}_{len(cache):02d}.mp3"
            if not clip.exists():
                raw = work / f"_raw_{len(cache):02d}.mp3"
                if kind == "ar":
                    edge_tts(text, AR_VOICE, raw, rate=AR_RATE)
                elif EN_TTS == "elevenlabs":
                    v2.elevenlabs_tts(text, raw)
                else:
                    edge_tts(text, EN_VOICE, raw, rate=EN_RATE)
                v2.ffmpeg("-i", str(raw), "-ar", "44100", "-ac", "1",
                          "-q:a", "2", str(clip))
            cache[text] = clip
        clips += [cache[text], silence]

    cmd = []
    for c in clips:
        cmd += ["-i", str(c)]
    filt = "".join(f"[{i}:a]" for i in range(len(clips)))
    filt += f"concat=n={len(clips)}:v=0:a=1[out]"
    v2.ffmpeg(*cmd, "-filter_complex", filt, "-map", "[out]", str(out_mp3))


def caption_for(n, lesson):
    return (f'{lesson["hook"]} · {lesson["ar"]} · {lesson["translit"]}\n'
            f'{lesson["teach"]}\n{lesson["cta"]}\n\n{hashtags_for(n)}')


def build_short(n: int):
    lesson = LESSONS[n]
    # shorts_v2 берёт голос и нижнюю плашку из глобальных настроек —
    # подменяем их на английские
    if os.environ.get("ELEVENLABS_VOICE_ID_EN"):
        os.environ["ELEVENLABS_VOICE_ID"] = os.environ["ELEVENLABS_VOICE_ID_EN"]
    v2.CTA_TEXT = CTA_TEXT

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    work = OUT_DIR / f"work_{n:02d}"
    work.mkdir(exist_ok=True)
    print(f"Lesson {n}: {lesson['hook']}")

    voice = work / "voice.mp3"
    if not voice.exists():
        print("  ElevenLabs voice-over...")
        synthesize_plan(tts_plan(n, lesson), voice, work)
    total = v2.probe_duration(voice) + 1.5

    overlay = work / "overlay.png"
    v2.draw_overlay(lesson, overlay)

    bg = work / "bg.mp4"
    if not bg.exists():
        bg = v2.build_background(lesson, total, work)

    out = OUT_DIR / f"short_{n:02d}.mp4"
    # -loop 1: без него надписи пропадали на стыке фоновых фото — склейка
    # фона сбивает метки времени, и одиночный кадр оверлея «заканчивался»
    p = v2.ffmpeg("-i", str(bg), "-loop", "1", "-i", str(overlay), "-i", str(voice),
                  "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
                  "-map", "[v]", "-map", "2:a", "-af", "apad",
                  "-t", f"{total:.2f}",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                  "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-b:a", "160k", str(out))
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg: {p.stderr[-800:]}")

    (OUT_DIR / f"short_{n:02d}.txt").write_text(caption_for(n, lesson),
                                                  encoding="utf-8")
    # компьютер старый: промежуточные фото и куски фона больше не нужны
    for junk in list(work.glob("photo_*")) + list(work.glob("clip_*")):
        junk.unlink(missing_ok=True)
    print(f"  done: {out}  ({total:.0f} s)")
    return out


if __name__ == "__main__":
    nums = [int(a) for a in sys.argv[1:]] or [1]
    for n in nums:
        build_short(n)
