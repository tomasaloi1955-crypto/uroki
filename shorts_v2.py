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
import re
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

# delete_harakat=True — огласовки (ташкиль) иногда мешают reshaper'у
# правильно соединять буквы (текст на экране распадался на отдельные
# изолированные буквы). На озвучку это не влияет: TTS получает текст с
# огласовками напрямую, в обход ar_text()/RESHAPER — только для показа
# на экране огласовки убираем, письмо остаётся слитным и читаемым.
RESHAPER = arabic_reshaper.ArabicReshaper({"delete_harakat": True})

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
    8:  dict(hook="Артикль Эль", ar="اَلْـ", translit="Аль-",
             teach="Артикль Аль- делает слово определённым. Книга — Китаб, эта книга — Аль-Китаб.",
             cta="Подпишись, чтобы не пропускать уроки!",
             themes=["arabic calligraphy", "mosque interior", "old books"]),
    9:  dict(hook="Верблюд и Красота", ar="جَمَل", translit="Джама́ль",
             teach="Джамаль означает верблюд и одновременно — красота.",
             cta="Подпишись: интересные факты об арабском!",
             themes=["camel desert", "desert dunes"]),
    10: dict(hook="Красивое спасибо", ar="شُكْراً", translit="Шу́кран — спасибо",
             teach="Шукран — спасибо. Ответ: Афуан — пожалуйста.",
             cta="Подпишись, завтра новые фразы!",
             themes=["sheikh zayed mosque", "sahara dunes", "arabic coffee"]),
    11: dict(hook="Слово дня: Вода", ar="مَاء", translit="Ма́ — вода",
             teach="Без воды нет жизни. Вода по-арабски — Ма. Запоминай: Ма.",
             cta="Ставь лайк, если пьёшь воду!",
             themes=["water drops", "ocean waves", "waterfall"]),
    12: dict(hook="Слово дня: Хлеб", ar="خُبْز", translit="Хубз — хлеб",
             teach="Хлеб — всему голова. Хлеб по-арабски — Хубз. Повтори: Хубз.",
             cta="Подпишись, чтобы не проголодаться!",
             themes=["bread baking", "wheat field"]),
    13: dict(hook="Слово дня: Дом", ar="بَيْت", translit="Бейт — дом",
             teach="Дом, милый дом. Дом по-арабски — Бейт. Запоминай: Бейт.",
             cta="Сохрани, чтобы не потерять дом!",
             themes=["old city street", "cozy house"]),
    14: dict(hook="Слово дня: Солнце", ar="شَمْس", translit="Шамс — солнце",
             teach="Солнце светит всем. Солнце по-арабски — Шамс. Запоминай: Шамс.",
             cta="Ставь лайк, если любишь солнце!",
             themes=["sunrise timelapse", "sun clouds"]),
    15: dict(hook="Слово дня: Луна", ar="قَمَر", translit="Ка́мар — луна",
             teach="Луна — символ красоты в арабском мире. Луна по-арабски — Камар. Повтори: Камар.",
             cta="Подпишись, завтра новые слова!",
             themes=["full moon", "night sky timelapse"]),
    16: dict(hook="Слово дня: Город", ar="مَدِينَة", translit="Мади́на — город",
             teach="Городской ритм. Город по-арабски — Мадина. Запоминай: Мадина.",
             cta="Подпишись на канал!",
             themes=["city skyline night", "old arab city"]),
    17: dict(hook="Слово дня: Улица", ar="شَارِع", translit="Ша́ри — улица",
             teach="Улица полна неожиданностей. Улица по-арабски — Шари. Повтори: Шари.",
             cta="Сохрани, чтобы не заблудиться!",
             themes=["market bazaar", "street walking"]),
    18: dict(hook="Слово дня: Машина", ar="سَيَّارَة", translit="Сайя́ра — машина",
             teach="Автомобиль — не роскошь. Машина по-арабски — Сайяра. Повтори: Сайяра.",
             cta="Ставь лайк, если любишь скорость!",
             themes=["desert road driving", "car road"]),
    19: dict(hook="Слово дня: Человек", ar="إِنْسَان", translit="Инса́н — человек",
             teach="Человек — это звучит гордо. Человек по-арабски — Инсан. Повтори: Инсан.",
             cta="Подпишись на канал!",
             themes=["footprints sand desert", "desert horizon sunrise"]),
    20: dict(hook="Слово дня: Друг", ar="صَدِيق", translit="Сади́к — друг",
             teach="Друг познаётся в беде. Друг по-арабски — Садик. Запоминай: Садик.",
             cta="Отправь другу!",
             themes=["arabic coffee", "tea pouring glass"]),
    21: dict(hook="Слово дня: Мама", ar="أُمّ", translit="Умм — мама",
             teach="Мама — самое важное слово. Мама по-арабски — Умм. Повтори: Умм.",
             cta="Ставь лайк, если любишь маму!",
             themes=["red rose garden", "cozy house interior"]),
    22: dict(hook="Слово дня: Папа", ar="أَب", translit="Аб — папа",
             teach="Отец — опора семьи. Папа по-арабски — Аб. Повтори: Аб.",
             cta="Подпишись на канал!",
             themes=["old wooden door morocco", "compass vintage"]),
    23: dict(hook="Слово дня: Брат", ar="أَخ", translit="Ах — брат",
             teach="Брат за брата. Брат по-арабски — Ах. Запоминай: Ах.",
             cta="Отправь брату!",
             themes=["two camels desert", "bridge stone arch"]),
    24: dict(hook="Слово дня: Сестра", ar="أُخْت", translit="Ухт — сестра",
             teach="Сестра — лучшая подруга. Сестра по-арабски — Ухт. Повтори: Ухт.",
             cta="Отправь сестре!",
             themes=["two roses garden", "butterflies pair"]),
    25: dict(hook="Слово дня: Яблоко", ar="تُفَّاح", translit="Туффа́х — яблоко",
             teach="Яблоко в день — и доктор не нужен. Яблоко по-арабски — Туффах. Запоминай: Туффах.",
             cta="Ставь лайк, если любишь яблоки!",
             themes=["red apples", "apple orchard"]),
    26: dict(hook="Слово дня: Чай", ar="شَاي", translit="Шай — чай",
             teach="Чайная церемония. Чай по-арабски — Шай. Повтори: Шай.",
             cta="Сохрани, пока не остыл!",
             themes=["tea pouring glass", "tea"]),
    27: dict(hook="Слово дня: Кофе", ar="قَهْوَة", translit="Ка́хва — кофе",
             teach="Утренний кофе. Кофе по-арабски — Кахва. Запоминай: Кахва.",
             cta="Ставь лайк, если любишь кофе!",
             themes=["coffee pouring", "arabic coffee"]),
    28: dict(hook="Слово дня: Небо", ar="سَمَاء", translit="Сама́ — небо",
             teach="Небо над головой. Небо по-арабски — Сама. Повтори: Сама.",
             cta="Подпишись на канал!",
             themes=["clouds timelapse", "blue sky"]),
    29: dict(hook="Слово дня: Земля", ar="أَرْض", translit="Ард — земля",
             teach="Родная земля. Земля по-арабски — Ард. Запоминай: Ард.",
             cta="Сохрани, чтобы не упасть!",
             themes=["green landscape aerial", "earth nature"]),
    30: dict(hook="Слово дня: Жизнь", ar="حَيَاة", translit="Хая́т — жизнь",
             teach="Жизнь прекрасна. Жизнь по-арабски — Хаят. Повтори: Хаят.",
             cta="Подпишись, впереди много нового!",
             themes=["flower blooming timelapse", "nature life"]),
    # --- Вторая серия (файл 30_Shorts_Arabic_Lessons_2.csv) ---
    31: dict(hook="Да и Нет по-арабски", ar="نَعَمْ / لَا",
             translit="На́ам — да, Ля — нет",
             teach="Два самых нужных слова: Наам — да. Ля — нет. Повтори: Наам. Ля.",
             cta="Подпишись, дальше — интереснее!",
             themes=["morocco desert", "desert sunset", "sheikh zayed mosque"]),
    32: dict(hook="Как спросить «Где?»", ar="أَيْنَ", translit="А́йна — где?",
             teach="Айна — где? Айна аль-фундук — где отель? Повтори: Айна.",
             cta="Сохрани, пригодится в путешествии!",
             themes=["medina morocco", "old map", "sahara dunes"]),
    33: dict(hook="Что это такое?", ar="مَا هَذَا؟", translit="Ма ха́за — что это?",
             teach="Показывай на что угодно и спрашивай: Ма хаза — что это? Повтори: Ма хаза.",
             cta="Подпишись, учим арабский легко!",
             themes=["souk market", "morocco market", "desert sunset"]),
    34: dict(hook="Сколько стоит?", ar="بِكَمْ؟", translit="Бика́м — почём?",
             teach="Главный вопрос на рынке: Бикам — сколько стоит? Повтори: Бикам.",
             cta="Сохрани для поездки на восток!",
             themes=["gold souk", "grand bazaar", "sheikh zayed mosque"]),
    35: dict(hook="Волшебное слово Тайиб", ar="طَيِّب", translit="Та́йиб — хорошо",
             teach="Тайиб — хорошо, ладно, договорились. Арабы говорят его постоянно. Повтори: Тайиб.",
             cta="Подпишись на канал!",
             themes=["oasis palm", "palm trees sunset", "sahara dunes"]),
    36: dict(hook="Слово дня: Сердце", ar="قَلْب", translit="Кальб — сердце",
             teach="Сердце по-арабски — Кальб. Говори от сердца. Повтори: Кальб.",
             cta="Ставь лайк от всего сердца!",
             themes=["red rose", "rose garden", "desert sunset"]),
    37: dict(hook="Слово дня: Свет", ar="نُور", translit="Нур — свет",
             teach="Нур — свет. Красивое имя и красивое слово. Повтори: Нур.",
             cta="Подпишись, впереди много света!",
             themes=["ramadan lantern", "mosque lamp", "sheikh zayed mosque"]),
    38: dict(hook="Цвет дня: Красный", ar="أَحْمَر", translit="А́хмар — красный",
             teach="Красный по-арабски — Ахмар. Повтори: Ахмар.",
             cta="Подпишись, соберём все цвета!",
             themes=["morocco spices", "red rose", "sahara dunes"]),
    39: dict(hook="Цвет дня: Зелёный", ar="أَخْضَر", translit="А́хдар — зелёный",
             teach="Зелёный — цвет оазиса. По-арабски — Ахдар. Повтори: Ахдар.",
             cta="Ставь лайк, если любишь природу!",
             themes=["green oasis", "palm grove", "oasis palm"]),
    40: dict(hook="Цвет дня: Белый", ar="أَبْيَض", translit="А́бъяд — белый",
             teach="Белый по-арабски — Абъяд. Как белые мечети. Повтори: Абъяд.",
             cta="Подпишись на канал!",
             themes=["white mosque", "sheikh zayed mosque", "white desert egypt"]),
    41: dict(hook="Слово дня: Море", ar="بَحْر", translit="Бахр — море",
             teach="Море по-арабски — Бахр. Красное море — Аль-Бахр аль-Ахмар. Повтори: Бахр.",
             cta="Ставь лайк, если любишь море!",
             themes=["red sea", "sea waves", "beach sunset"]),
    42: dict(hook="Слово дня: Звезда", ar="نَجْمَة", translit="На́джма — звезда",
             teach="Звезда по-арабски — Наджма. Повтори: Наджма.",
             cta="Подпишись, ты — звезда!",
             themes=["milky way desert", "starry night", "night sky"]),
    43: dict(hook="Слово дня: Цветок", ar="وَرْدَة", translit="Ва́рда — цветок",
             teach="Цветок, роза по-арабски — Варда. Повтори: Варда.",
             cta="Отправь этот цветок близкому!",
             themes=["rose garden", "jasmine flower", "flower field"]),
    44: dict(hook="Доброе утро!", ar="صَبَاح الْخَيْر", translit="Саба́х аль-хайр",
             teach="Доброе утро — Сабах аль-хайр. Ответ: Сабах ан-нур — утро света! Повтори: Сабах аль-хайр.",
             cta="Подпишись и начинай утро с арабского!",
             themes=["sunrise desert", "sunrise mosque", "sunrise"]),
    45: dict(hook="Добрый вечер!", ar="مَسَاء الْخَيْر", translit="Маса́ аль-хайр",
             teach="Добрый вечер — Маса аль-хайр. Ответ: Маса ан-нур. Повтори: Маса аль-хайр.",
             cta="Подпишись на канал!",
             themes=["sunset mosque", "city lights evening", "desert sunset"]),
    46: dict(hook="Спокойной ночи", ar="تُصْبِحْ عَلَى خَيْر",
             translit="Ту́сбих аля хайр",
             teach="Спокойной ночи — Тусбих аля хайр, буквально: проснись во благе. Повтори: Тусбих аля хайр.",
             cta="Сохрани и пожелай кому-то доброй ночи!",
             themes=["full moon", "night sky stars", "city night"]),
    47: dict(hook="Как тебя зовут?", ar="مَا اسْمُكَ؟",
             translit="Ма и́смук — как тебя зовут?",
             teach="Знакомимся: Ма исмук — как тебя зовут? Повтори: Ма исмук.",
             cta="Напиши своё имя в комментариях!",
             themes=["arabic calligraphy", "souk market", "sheikh zayed mosque"]),
    48: dict(hook="Меня зовут…", ar="اسْمِي", translit="И́сми — меня зовут",
             teach="Исми — меня зовут. Исми Марьям — меня зовут Марьям. Повтори: Исми.",
             cta="Представься по-арабски в комментариях!",
             themes=["arabic calligraphy", "medina morocco", "desert sunset"]),
    49: dict(hook="Я не понимаю", ar="لَا أَفْهَم", translit="Ля а́фхам — не понимаю",
             teach="Честная фраза новичка: Ля афхам — я не понимаю. Повтори: Ля афхам.",
             cta="Сохрани, выручит в разговоре!",
             themes=["old books", "arabic manuscript", "library"]),
    50: dict(hook="Я учу арабский!", ar="أَنَا أَتَعَلَّمُ الْعَرَبِيَّة",
             translit="А́на атаа́ллям аль-араби́йя",
             teach="Скажи с гордостью: Ана атааллям аль-арабийя — я учу арабский! Повтори медленно: Ана атааллям аль-арабийя.",
             cta="Подпишись, будем учить вместе!",
             themes=["arabic manuscript", "arabic calligraphy", "sahara dunes"]),
    51: dict(hook="Халва — это арабское слово!", ar="حَلْوَى",
             translit="Ха́льва — сладость",
             teach="Русское слово халва пришло из арабского: Хальва — сладость. Повтори: Хальва.",
             cta="Ставь лайк, если сладкоежка!",
             themes=["baklava", "turkish delight", "arabic sweets"]),
    52: dict(hook="Сундук — тоже арабский!", ar="صُنْدُوق",
             translit="Сунду́к — ящик",
             teach="Слово сундук пришло из арабского: Сундук — ящик, коробка. Повтори: Сундук.",
             cta="Подпишись, таких слов ещё много!",
             themes=["treasure chest", "old chest", "souk market"]),
    53: dict(hook="Слово дня: Жираф", ar="زَرَافَة", translit="Зара́фа — жираф",
             teach="И жираф — из арабского! Зарафа — жираф. Повтори: Зарафа.",
             cta="Подпишись, удивим ещё!",
             themes=["giraffe", "giraffe savanna", "africa savanna"]),
    54: dict(hook="Сахар — арабское слово", ar="سُكَّر", translit="Су́ккар — сахар",
             teach="Сахар по-арабски — Суккар. Оттуда и пришло к нам. Повтори: Суккар.",
             cta="Ставь лайк, если любишь сладкий чай!",
             themes=["sugar", "morocco spices", "arabic sweets"]),
    55: dict(hook="Слово дня: Кошка", ar="قِطَّة", translit="Ки́тта — кошка",
             teach="Кошка по-арабски — Китта. Повтори: Китта.",
             cta="Ставь лайк, если у тебя есть кот!",
             themes=["cat istanbul", "cat", "kitten"]),
    56: dict(hook="Слово дня: Птица", ar="طَائِر", translit="Та́ир — птица",
             teach="Птица по-арабски — Таир. Сокол — символ Эмиратов. Повтори: Таир.",
             cta="Подпишись на канал!",
             themes=["falcon", "bird flying", "falcon uae"]),
    57: dict(hook="Слово дня: Рыба", ar="سَمَك", translit="Са́мак — рыба",
             teach="Рыба по-арабски — Самак. Повтори: Самак.",
             cta="Сохрани, пригодится в ресторане!",
             themes=["red sea fish", "coral reef", "fish"]),
    58: dict(hook="Одну секунду!", ar="لَحْظَة", translit="Ля́хза — момент",
             teach="Ляхза — секундочку, момент! Очень ходовое слово. Повтори: Ляхза.",
             cta="Подпишись, не теряй ни секунды!",
             themes=["hourglass", "sand dunes wind", "sahara dunes"]),
    59: dict(hook="Добро пожаловать!", ar="أَهْلاً وَسَهْلاً",
             translit="А́хлян ва са́хлян",
             teach="Знаменитое гостеприимство: Ахлян ва сахлян — добро пожаловать! Повтори: Ахлян ва сахлян.",
             cta="Добро пожаловать на канал — подпишись!",
             themes=["moroccan door", "arabic door", "riad morocco"]),
    60: dict(hook="До свидания!", ar="مَعَ السَّلَامَة",
             translit="Ма́а с-саля́ма",
             teach="Прощаемся красиво: Маа с-саляма — до свидания, с миром. Повтори: Маа с-саляма.",
             cta="Подпишись, мы не прощаемся!",
             themes=["camel caravan", "desert sunset", "sunset"]),
    61: dict(hook="Слово дня: Лев", ar="أَسَد",
             translit="А́сад — лев",
             teach="Лев — царь зверей. Лев по-арабски — Асад. Повтори: Асад.",
             cta="Будь смелым как лев — подпишись!",
             themes=["lion", "lion portrait", "lion savanna"]),
    62: dict(hook="Слово дня: Сокол", ar="صَقْر",
             translit="Сакр — сокол",
             teach="Сокол — гордость Аравии. Сокол по-арабски — Сакр. Повтори: Сакр.",
             cta="Подпишись на канал!",
             themes=["falcon", "falconry", "saker falcon"]),
    63: dict(hook="Слово дня: Конь", ar="حِصَان",
             translit="Хиса́н — конь",
             teach="Арабский скакун — самый красивый конь. Конь по-арабски — Хисан. Повтори: Хисан.",
             cta="Подпишись, скачем дальше!",
             themes=["arabian horse", "horse running", "white horse"]),
    64: dict(hook="Газель — арабское слово", ar="غَزَال",
             translit="Газа́ль — газель",
             teach="Слово газель пришло из арабского: Газаль. Повтори: Газаль.",
             cta="Сохрани урок!",
             themes=["gazelle", "gazelle desert", "antelope"]),
    65: dict(hook="Слово дня: Меч", ar="سَيْف",
             translit="Сайф — меч",
             teach="Меч по-арабски — Сайф. Сайф — ещё и популярное имя. Повтори: Сайф.",
             cta="Подпишись на канал!",
             themes=["damascus sword", "scimitar", "sword"]),
    66: dict(hook="Слово дня: Гора", ar="جَبَل",
             translit="Джа́баль — гора",
             teach="Гора по-арабски — Джабаль. Гибралтар — это Джабаль Тарик, гора Тарика. Повтори: Джабаль.",
             cta="Подпишись, покоряем вершины!",
             themes=["gibraltar rock", "mountain", "atlas mountains"]),
    67: dict(hook="Слово дня: Река", ar="نَهْر",
             translit="Нахр — река",
             teach="Река по-арабски — Нахр. Нил — самая длинная река. Повтори: Нахр.",
             cta="Сохрани урок!",
             themes=["nile river", "river", "river valley"]),
    68: dict(hook="Слово дня: Дождь", ar="مَطَر",
             translit="Ма́тар — дождь",
             teach="В пустыне дождь — настоящий праздник. Дождь по-арабски — Матар. Повтори: Матар.",
             cta="Подпишись на канал!",
             themes=["rain", "rain drops", "rain window"]),
    69: dict(hook="Слово дня: Снег", ar="ثَلْج",
             translit="Сальдж — снег",
             teach="Снег по-арабски — Сальдж. А ещё так называют лёд. Повтори: Сальдж.",
             cta="Подпишись, учим дальше!",
             themes=["snow", "snowy mountains", "snowflakes"]),
    70: dict(hook="Слово дня: Ветер", ar="رِيح",
             translit="Рих — ветер",
             teach="Ветер по-арабски — Рих. Повтори: Рих.",
             cta="Сохрани урок!",
             themes=["sand dunes wind", "wind", "windmill"]),
    71: dict(hook="Слово дня: Рынок", ar="سُوق",
             translit="Сук — рынок",
             teach="Восточный базар — это Сук. Повтори: Сук.",
             cta="Сохрани, пригодится в поездке!",
             themes=["souk", "marrakech market", "spice market"]),
    72: dict(hook="Слово дня: Крепость", ar="قَلْعَة",
             translit="Ка́лъа — крепость",
             teach="Крепость по-арабски — Калъа. Повтори: Калъа.",
             cta="Подпишись на канал!",
             themes=["citadel", "fortress", "castle"]),
    73: dict(hook="Слово дня: Мост", ar="جِسْر",
             translit="Джиср — мост",
             teach="Мост по-арабски — Джиср. Повтори: Джиср.",
             cta="Подпишись — наведём мосты!",
             themes=["bridge", "stone bridge", "bridge river"]),
    74: dict(hook="Слово дня: Фонарь", ar="فَانُوس",
             translit="Фану́с — фонарь",
             teach="Фонарь по-арабски — Фанус. Такие фонари зажигают в Рамадан. Повтори: Фанус.",
             cta="Подпишись на канал!",
             themes=["ramadan lantern", "lanterns", "moroccan lamp"]),
    75: dict(hook="Слово дня: Кольцо", ar="خَاتَم",
             translit="Ха́там — кольцо",
             teach="Кольцо, перстень по-арабски — Хатам. Повтори: Хатам.",
             cta="Сохрани урок!",
             themes=["ring", "silver ring", "jewelry"]),
    76: dict(hook="Слово дня: Духи", ar="عِطْر",
             translit="Итр — духи",
             teach="Восточные ароматы. Духи по-арабски — Итр. Повтори: Итр.",
             cta="Подпишись на канал!",
             themes=["perfume bottle", "oud", "perfume"]),
    77: dict(hook="Слово дня: Мыло", ar="صَابُون",
             translit="Сабу́н — мыло",
             teach="Мыло по-арабски — Сабун. Алеппское мыло знают во всём мире. Повтори: Сабун.",
             cta="Подпишись, учим дальше!",
             themes=["aleppo soap", "soap", "handmade soap"]),
    78: dict(hook="Слово дня: Соль", ar="مِلْح",
             translit="Мильх — соль",
             teach="Соль по-арабски — Мильх. Повтори: Мильх.",
             cta="Сохрани, пригодится на кухне!",
             themes=["salt", "sea salt", "salt flats"]),
    79: dict(hook="Лимон — арабское слово", ar="لَيْمُون",
             translit="Ляйму́н — лимон",
             teach="Лимон по-арабски — Ляймун. Слышишь сходство? Повтори: Ляймун.",
             cta="Подпишись на канал!",
             themes=["lemon", "lemons", "lemon tree"]),
    80: dict(hook="Слово дня: Гранат", ar="رُمَّان",
             translit="Румма́н — гранат",
             teach="Гранат по-арабски — Румман. Повтори: Румман.",
             cta="Сохрани урок!",
             themes=["pomegranate", "pomegranates", "pomegranate tree"]),
    81: dict(hook="Слово дня: Оливки", ar="زَيْتُون",
             translit="Зайту́н — оливки",
             teach="Оливки, маслины по-арабски — Зайтун. Повтори: Зайтун.",
             cta="Подпишись на канал!",
             themes=["olive tree", "olives", "olive grove"]),
    82: dict(hook="Слово дня: Поезд", ar="قِطَار",
             translit="Кита́р — поезд",
             teach="Поезд по-арабски — Китар. Повтори: Китар.",
             cta="Подпишись, едем дальше!",
             themes=["train", "railway", "train station"]),
    83: dict(hook="Слово дня: Корабль", ar="سَفِينَة",
             translit="Сафи́на — корабль",
             teach="Корабль по-арабски — Сафина. Повтори: Сафина.",
             cta="Сохрани урок!",
             themes=["dhow", "sailing ship", "ship"]),
    84: dict(hook="Слово дня: Гость", ar="ضَيْف",
             translit="Дайф — гость",
             teach="Гость на Востоке — дар свыше. Гость по-арабски — Дайф. Повтори: Дайф.",
             cta="Будь нашим гостем — подпишись!",
             themes=["arabic coffee", "dallah", "majlis"]),
    85: dict(hook="Слово дня: Сосед", ar="جَار",
             translit="Джар — сосед",
             teach="Сосед по-арабски — Джар. Повтори: Джар.",
             cta="Подпишись на канал!",
             themes=["old city street", "neighborhood", "houses"]),
    86: dict(hook="Слово дня: Счастливый", ar="سَعِيد",
             translit="Саи́д — счастливый",
             teach="Счастливый по-арабски — Саид. Отсюда и имя Саид. Повтори: Саид.",
             cta="Подпишись — будь счастлив!",
             themes=["smile", "happy child", "sunflowers"]),
    87: dict(hook="Слово дня: Зима", ar="شِتَاء",
             translit="Шита́ — зима",
             teach="Зима по-арабски — Шита. Повтори: Шита.",
             cta="Сохрани урок!",
             themes=["winter", "snowy forest", "winter landscape"]),
    88: dict(hook="Слово дня: Бабочка", ar="فَرَاشَة",
             translit="Фара́ша — бабочка",
             teach="Бабочка по-арабски — Фараша. Повтори: Фараша.",
             cta="Подпишись на канал!",
             themes=["butterfly", "butterfly flower", "butterflies"]),
    89: dict(hook="Слово дня: Пчела", ar="نَحْلَة",
             translit="На́хля — пчела",
             teach="Пчела по-арабски — Нахля. Повтори: Нахля.",
             cta="Трудись как пчёлка — подпишись!",
             themes=["bee", "honey bee", "bee flower"]),
    90: dict(hook="Слово дня: Лиса", ar="ثَعْلَب",
             translit="Са́аляб — лиса",
             teach="Хитрая лиса по-арабски — Сааляб. Повтори: Сааляб.",
             cta="Подпишись на канал!",
             themes=["fox", "fennec fox", "red fox"]),
    # Уроки 91–150: новые слова — не повторяют ни шортсы 8–90,
    # ни 30-дневный курс (arabic_0XX.json), ни длинные эпизоды.
    91: dict(hook="Слово дня: Виноград", ar="عِنَب",
             translit="И́наб — виноград",
             teach="Виноград по-арабски — Инаб. Запомни: Инаб.",
             cta="Ставь лайк, если любишь виноград!",
             themes=["grapes", "vineyard", "grape bunch"]),
    92: dict(hook="Слово дня: Банан", ar="مَوْز",
             translit="Мауз — банан",
             teach="Банан по-арабски — Мауз. Повтори: Мауз.",
             cta="Подпишись, учим слова каждый день!",
             themes=["banana", "banana bunch", "banana tree"]),
    93: dict(hook="Слово дня: Арбуз", ar="بِطِّيخ",
             translit="Битти́х — арбуз",
             teach="Летний арбуз по-арабски — Биттих. Повтори: Биттих.",
             cta="Сохрани до лета!",
             themes=["watermelon", "watermelon slice", "watermelon field"]),
    94: dict(hook="Слово дня: Серебро", ar="فِضَّة",
             translit="Фи́дда — серебро",
             teach="Серебро по-арабски — Фидда. Повтори: Фидда.",
             cta="Подпишись на канал!",
             themes=["silver coins", "silver teapot", "silverware"]),
    95: dict(hook="Слово дня: Самолёт", ar="طَائِرَة",
             translit="Та́ира — самолёт",
             teach="Самолёт по-арабски — Таира, то есть «летающая». Повтори: Таира.",
             cta="Сохрани для путешествия!",
             themes=["airplane sky", "airplane", "jet airliner"]),
    96: dict(hook="Слово дня: Пустыня", ar="صَحْرَاء",
             translit="Сахра́ — пустыня",
             teach="Сахара — это просто «пустыня» по-арабски: Сахра. Повтори: Сахра.",
             cta="Ставь лайк, если не знал!",
             themes=["sahara dunes", "desert dunes", "sand dunes"]),
    97: dict(hook="Слово дня: Оазис", ar="وَاحَة",
             translit="Ва́ха — оазис",
             teach="Оазис посреди пустыни по-арабски — Ваха. Повтори: Ваха.",
             cta="Подпишись, отдохни с арабским!",
             themes=["oasis palm", "desert oasis", "oasis lake"]),
    98: dict(hook="Слово дня: Остров", ar="جَزِيرَة",
             translit="Джази́ра — остров",
             teach="Остров по-арабски — Джазира. Отсюда и название Алжира. Повтори: Джазира.",
             cta="Подпишись на канал!",
             themes=["tropical island", "island aerial", "island sea"]),
    99: dict(hook="Слово дня: Облако", ar="غَيْمَة",
             translit="Га́йма — облако",
             teach="Облако по-арабски — Гайма. Повтори: Гайма.",
             cta="Подпишись, учим слова каждый день!",
             themes=["clouds sky", "cumulus clouds", "clouds sunset"]),
    100: dict(hook="Слово дня: Весна", ar="رَبِيع",
             translit="Раби́ — весна",
             teach="Весна по-арабски — Раби. Запомни: Раби.",
             cta="Сохрани и повтори весной!",
             themes=["spring blossom", "cherry blossom", "spring flowers"]),
    101: dict(hook="Слово дня: Осень", ar="خَرِيف",
             translit="Хари́ф — осень",
             teach="Осень по-арабски — Хариф. Повтори: Хариф.",
             cta="Подпишись на канал!",
             themes=["autumn leaves", "autumn forest", "fall foliage"]),
    102: dict(hook="Слово дня: День", ar="يَوْم",
             translit="Яум — день",
             teach="День по-арабски — Яум. Каждый день новое слово: Яум.",
             cta="Подпишись, одно слово в день!",
             themes=["sunny day landscape", "blue sky", "sun clouds"]),
    103: dict(hook="Слово дня: Ночь", ar="لَيْل",
             translit="Ляйль — ночь",
             teach="Ночь по-арабски — Ляйль. Повтори: Ляйль.",
             cta="Сохрани перед сном!",
             themes=["night sky stars", "full moon", "milky way"]),
    104: dict(hook="Слово дня: Месяц", ar="شَهْر",
             translit="Шахр — месяц",
             teach="Месяц по-арабски — Шахр. Повтори: Шахр.",
             cta="Подпишись, занимайся весь месяц!",
             themes=["crescent moon", "calendar", "new moon"]),
    105: dict(hook="Слово дня: Год", ar="سَنَة",
             translit="Са́на — год",
             teach="Год по-арабски — Сана. Запомни: Сана.",
             cta="Подпишись на канал!",
             themes=["calendar", "hourglass", "clock"]),
    106: dict(hook="Слово дня: Медведь", ar="دُبّ",
             translit="Дубб — медведь",
             teach="Медведь по-арабски — Дубб. Повтори: Дубб.",
             cta="Подпишись на канал!",
             themes=["brown bear", "polar bear", "bear forest"]),
    107: dict(hook="Слово дня: Волк", ar="ذِئْب",
             translit="Зиъб — волк",
             teach="Волк по-арабски — Зиъб. Повтори: Зиъб.",
             cta="Подпишись, учим зверей по-арабски!",
             themes=["wolf", "grey wolf", "wolf snow"]),
    108: dict(hook="Слово дня: Муравей", ar="نَمْلَة",
             translit="На́мля — муравей",
             teach="Муравей по-арабски — Намля. Целая сура Корана так и называется: Намля.",
             cta="Ставь лайк, если не знал!",
             themes=["ant", "ant macro", "anthill"]),
    109: dict(hook="Слово дня: Сова", ar="بُومَة",
             translit="Бу́ма — сова",
             teach="Сова по-арабски — Бума. Повтори: Бума.",
             cta="Подпишись на канал!",
             themes=["owl", "snowy owl", "owl tree"]),
    110: dict(hook="Слово дня: Черепаха", ar="سُلَحْفَاة",
             translit="Сулахфа́ — черепаха",
             teach="Медленно, но верно. Черепаха по-арабски — Сулахфа. Повтори: Сулахфа.",
             cta="Учи медленно, но каждый день — подпишись!",
             themes=["tortoise", "sea turtle", "turtle"]),
    111: dict(hook="Слово дня: Голубь", ar="حَمَامَة",
             translit="Хама́ма — голубь",
             teach="Голубь по-арабски — Хамама. Повтори: Хамама.",
             cta="Подпишись на канал!",
             themes=["white dove", "pigeon", "doves flying"]),
    112: dict(hook="Магазин — арабское слово", ar="مَخْزَن",
             translit="Ма́хзан — склад",
             teach="Русское «магазин» пришло от арабского Махзан — склад. Повтори: Махзан.",
             cta="Ставь лайк, если не знал!",
             themes=["warehouse", "old storehouse", "shop shelves"]),
    113: dict(hook="Сироп — арабское слово", ar="شَرَاب",
             translit="Шара́б — напиток",
             teach="Сироп пришёл в русский от арабского Шараб — напиток. Повтори: Шараб.",
             cta="Подпишись, таких слов много!",
             themes=["fruit syrup", "lemonade", "juice glass"]),
    114: dict(hook="Цифра — арабское слово", ar="صِفْر",
             translit="Сифр — ноль",
             teach="Слово «цифра» пришло от арабского Сифр — ноль, пустота. Повтори: Сифр.",
             cta="Ставь лайк, если не знал!",
             themes=["arabic numerals", "astrolabe", "old manuscript"]),
    115: dict(hook="Алгебра — арабское слово", ar="الْجَبْر",
             translit="Аль-джа́бр — восполнение",
             teach="Алгебра названа по книге учёного из Багдада. В названии было слово Аль-джабр.",
             cta="Отметь того, кто любит алгебру!",
             themes=["arabic manuscript", "astrolabe", "old books"]),
    116: dict(hook="Карат — через арабский", ar="قِيرَاط",
             translit="Кира́т — карат",
             teach="Вес драгоценных камней считают в каратах. По-арабски — Кират. Повтори: Кират.",
             cta="Подпишись на канал!",
             themes=["diamond", "gemstones", "gold ring"]),
    117: dict(hook="Адмирал — арабское слово", ar="أَمِير",
             translit="Ами́р — правитель",
             teach="Адмирал — это искажённое арабское Амир, правитель моря. Повтори: Амир.",
             cta="Ставь лайк, если не знал!",
             themes=["old sailing ship", "ship sea", "lighthouse"]),
    118: dict(hook="Муссон — арабское слово", ar="مَوْسِم",
             translit="Ма́усим — сезон",
             teach="Муссон назван от арабского Маусим — сезон. Повтори: Маусим.",
             cta="Подпишись на канал!",
             themes=["monsoon rain", "storm clouds", "rain sea"]),
    119: dict(hook="Слово дня: Шафран", ar="زَعْفَرَان",
             translit="Заафара́н — шафран",
             teach="Шафран по-арабски — Заафаран. Повтори: Заафаран.",
             cta="Ставь лайк, если пробовал шафран!",
             themes=["saffron", "saffron flower", "spices"]),
    120: dict(hook="Хна — арабское слово", ar="حِنَّاء",
             translit="Хинна́ — хна",
             teach="Хна — это арабское Хинна. Повтори: Хинна.",
             cta="Подпишись на канал!",
             themes=["henna powder", "henna pattern", "henna plant"]),
    121: dict(hook="Сафари — из арабского", ar="سَفَر",
             translit="Са́фар — путешествие",
             teach="Сафари пришло от арабского Сафар — путешествие. Повтори: Сафар.",
             cta="Сохрани для путешествия!",
             themes=["savanna", "desert road", "travel map"]),
    122: dict(hook="Тариф — арабское слово", ar="تَعْرِيفَة",
             translit="Таари́фа — тариф",
             teach="Тариф — от арабского Таарифа, список цен. Повтори: Таарифа.",
             cta="Ставь лайк, если не знал!",
             themes=["old harbor", "price tags", "market scale"]),
    123: dict(hook="Слово дня: Сад", ar="حَدِيقَة",
             translit="Хади́ка — сад",
             teach="Сад по-арабски — Хадика. Повтори: Хадика.",
             cta="Подпишись на канал!",
             themes=["garden", "andalusian garden", "fountain garden"]),
    124: dict(hook="Слово дня: Телефон", ar="هَاتِف",
             translit="Ха́тиф — телефон",
             teach="Телефон по-арабски — Хатиф. Повтори: Хатиф.",
             cta="Сохрани на телефон!",
             themes=["old telephone", "smartphone", "phone booth"]),
    125: dict(hook="Слово дня: Быстрый", ar="سَرِيع",
             translit="Сари́ — быстрый",
             teach="Быстрый по-арабски — Сари. Скажи быстро: Сари.",
             cta="Подпишись, учим быстро!",
             themes=["race car", "cheetah", "high speed train"]),
    126: dict(hook="Слово дня: Апельсин", ar="بُرْتُقَال",
             translit="Буртука́ль — апельсин",
             teach="Апельсин по-арабски — Буртукаль. Почти как Португалия! Повтори: Буртукаль.",
             cta="Ставь лайк, если не знал!",
             themes=["orange fruit", "orange tree", "citrus fruit"]),
    127: dict(hook="Слово дня: Инжир", ar="تِين",
             translit="Тин — инжир",
             teach="Инжир по-арабски — Тин. Так называется и сура Корана: Тин.",
             cta="Подпишись на канал!",
             themes=["fig fruit", "fig tree", "dried figs"]),
    128: dict(hook="Слово дня: Миндаль", ar="لَوْز",
             translit="Ляуз — миндаль",
             teach="Миндаль по-арабски — Ляуз. Повтори: Ляуз.",
             cta="Подпишись на канал!",
             themes=["almonds", "almond blossom", "almond tree"]),
    129: dict(hook="Слово дня: Мята", ar="نَعْنَاع",
             translit="На́ана — мята",
             teach="Мятный чай по-арабски — шай би Наана. Мята — Наана.",
             cta="Ставь лайк, если любишь чай с мятой!",
             themes=["mint leaves", "mint tea", "fresh mint"]),
    130: dict(hook="Слово дня: Пещера", ar="كَهْف",
             translit="Кахф — пещера",
             teach="Пещера по-арабски — Кахф. Сура «Аль-Кахф» — о людях пещеры. Повтори: Кахф.",
             cta="Подпишись на канал!",
             themes=["cave", "cave entrance", "limestone cave"]),
    131: dict(hook="Слово дня: Вулкан", ar="بُرْكَان",
             translit="Бурка́н — вулкан",
             teach="Вулкан по-арабски — Буркан. Повтори: Буркан.",
             cta="Ставь лайк, если не знал!",
             themes=["volcano", "volcano eruption", "volcanic crater"]),
    132: dict(hook="Слово дня: Водопад", ar="شَلَّال",
             translit="Шалля́ль — водопад",
             teach="Водопад по-арабски — Шалляль. Повтори: Шалляль.",
             cta="Подпишись на канал!",
             themes=["waterfall", "waterfall forest", "big waterfall"]),
    133: dict(hook="Слово дня: Волна", ar="مَوْجَة",
             translit="Ма́уджа — волна",
             teach="Волна по-арабски — Мауджа. Повтори: Мауджа.",
             cta="Подпишись, лови волну!",
             themes=["ocean wave", "sea waves", "surf wave"]),
    134: dict(hook="Слово дня: Песок", ar="رَمْل",
             translit="Рамль — песок",
             teach="Песок по-арабски — Рамль. Повтори: Рамль.",
             cta="Подпишись на канал!",
             themes=["sand dunes", "sand texture", "desert sand"]),
    135: dict(hook="Слово дня: Лес", ar="غَابَة",
             translit="Га́ба — лес",
             teach="Лес по-арабски — Габа. Повтори: Габа.",
             cta="Подпишись на канал!",
             themes=["forest", "pine forest", "forest path"]),
    136: dict(hook="Слово дня: Озеро", ar="بُحَيْرَة",
             translit="Бухе́йра — озеро",
             teach="Озеро по-арабски — Бухейра, то есть «маленькое море». Повтори: Бухейра.",
             cta="Ставь лайк, если не знал!",
             themes=["lake", "mountain lake", "lake reflection"]),
    137: dict(hook="Слово дня: Орёл", ar="نَسْر",
             translit="Наср — орёл",
             teach="Орёл по-арабски — Наср. Повтори: Наср.",
             cta="Подпишись на канал!",
             themes=["eagle", "golden eagle", "eagle flying"]),
    138: dict(hook="Слово дня: Дельфин", ar="دُلْفِين",
             translit="Дульфи́н — дельфин",
             teach="Это легко! Дельфин по-арабски — Дульфин.",
             cta="Ставь лайк, если любишь дельфинов!",
             themes=["dolphin", "dolphins jumping", "dolphin sea"]),
    139: dict(hook="Слово дня: Кит", ar="حُوت",
             translit="Хут — кит",
             teach="Кит по-арабски — Хут. Пророка Юнуса проглотил Хут.",
             cta="Подпишись на канал!",
             themes=["whale", "humpback whale", "whale tail"]),
    140: dict(hook="Слово дня: Заяц", ar="أَرْنَب",
             translit="А́рнаб — заяц",
             teach="Заяц и кролик по-арабски — Арнаб. Повтори: Арнаб.",
             cta="Подпишись на канал!",
             themes=["hare", "rabbit", "wild rabbit"]),
    141: dict(hook="Слово дня: Тигр", ar="نَمِر",
             translit="На́мир — тигр",
             teach="Тигр по-арабски — Намир. Повтори: Намир.",
             cta="Ставь лайк, если любишь тигров!",
             themes=["tiger", "bengal tiger", "tiger stripes"]),
    142: dict(hook="Слово дня: Павлин", ar="طَاوُوس",
             translit="Таву́с — павлин",
             teach="Павлин по-арабски — Тавус. Повтори: Тавус.",
             cta="Подпишись на канал!",
             themes=["peacock", "peacock feathers", "peacock tail"]),
    143: dict(hook="Слово дня: Свеча", ar="شَمْعَة",
             translit="Ша́мъа — свеча",
             teach="Свеча по-арабски — Шамъа. Повтори: Шамъа.",
             cta="Подпишись на канал!",
             themes=["candle", "candle light", "candles"]),
    144: dict(hook="Слово дня: Ковёр", ar="سَجَّادَة",
             translit="Саджжа́да — ковёр",
             teach="Ковёр и молитвенный коврик по-арабски — Саджжада. Повтори: Саджжада.",
             cta="Подпишись на канал!",
             themes=["persian carpet", "prayer rug", "carpet pattern"]),
    145: dict(hook="Минарет — арабское слово", ar="مَنَارَة",
             translit="Мана́ра — маяк",
             teach="Минарет — от арабского Манара: маяк, место света. Повтори: Манара.",
             cta="Ставь лайк, если не знал!",
             themes=["minaret", "lighthouse", "mosque minaret"]),
    146: dict(hook="Альков — арабское слово", ar="قُبَّة",
             translit="Ку́бба — купол",
             teach="Купол по-арабски — Кубба. От него и русское «альков». Повтори: Кубба.",
             cta="Подпишись, таких слов много!",
             themes=["mosque dome", "dome interior", "islamic architecture dome"]),
    147: dict(hook="Матрас — арабское слово", ar="مَطْرَح",
             translit="Ма́трах — место",
             teach="Матрас — от арабского Матрах: место, куда что-то кладут. Повтори: Матрах.",
             cta="Ставь лайк, если не знал!",
             themes=["bed pillows", "bedroom interior", "cushions"]),
    148: dict(hook="Слово дня: Палатка", ar="خَيْمَة",
             translit="Ха́йма — палатка",
             teach="Шатёр и палатка по-арабски — Хайма. Повтори: Хайма.",
             cta="Подпишись на канал!",
             themes=["desert tent", "desert camp", "tent night"]),
    149: dict(hook="Слово дня: Колодец", ar="بِئْر",
             translit="Биър — колодец",
             teach="Колодец по-арабски — Биър. Повтори: Биър.",
             cta="Подпишись на канал!",
             themes=["old well", "stone well", "desert well"]),
    150: dict(hook="Слово дня: Фонтан", ar="نَافُورَة",
             translit="Нафу́ра — фонтан",
             teach="Фонтан по-арабски — Нафура. Повтори: Нафура.",
             cta="Подпишись на канал!",
             themes=["fountain", "alhambra fountain", "courtyard fountain"]),
}


def pick_font(candidates, size):
    for p in candidates:
        if Path(p).exists():
            # layout_engine=BASIC: мы уже сами разворачиваем арабский текст
            # через arabic_reshaper+get_display. Там, где Pillow собран с
            # raqm (Linux/GitHub Actions), движок RAQM сделал бы это ещё
            # раз поверх нашей раскладки — текст съезжал бы обратно
            # слева направо. BASIC просто рисует символы в заданном
            # порядке, без повторной bidi-обработки.
            return ImageFont.truetype(p, size,
                                      layout_engine=ImageFont.Layout.BASIC)
    return ImageFont.load_default()


def ar_text(s):
    return get_display(RESHAPER.reshape(s))


def strip_accents(s):
    """Убирает знак ударения (U+0301): TTS читает его с ошибками.
    Снимаем через NFD только сам акут и возвращаем NFC — если убирать
    ВСЕ комбинирующие знаки без разбора, "й" (= "и" + краткая) тоже
    разваливается и превращается в "и", ломая слово."""
    decomposed = unicodedata.normalize("NFD", s)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if ch != "́"))


def split_word_occurrences(text, word, ar_word):
    """Режет текст на чередующиеся сегменты [("ru", кусок), ("ar", слово)]
    по каждому вхождению транслитерированного word (границы слова, без
    учёта регистра), заменяя его на арабское произношение.

    Кусок из одних знаков препинания (когда арабское слово стоит сразу
    после запятой/точки) в TTS не отправляем — ElevenLabs озвучивает
    голый "." или "," каким-то посторонним звуком, отсюда были
    случайные огрехи в русской речи. Пауза между сегментами и так есть
    (тишина в synthesize_plan), отдельное озвучивание знака не нужно."""
    if not word:
        return [("ru", text)] if text.strip() else []
    parts = re.split(r"\b(" + re.escape(word) + r")\b", text, flags=re.IGNORECASE)
    segs = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            segs.append(("ar", ar_word))
        elif re.search(r"\w", part, re.UNICODE):
            segs.append(("ru", part))
    return segs


# Связующие фразы варьируются по уроку (см. _pick), чтобы 30 роликов
# подряд не звучали как один и тот же шаблон — меняется только текст,
# сама схема произношения арабского слова (split_word_occurrences +
# synthesize_plan) не зависит от того, какая фраза выбрана.
INTRO_PHRASES = [
    "Слушай, как это звучит по-арабски",
    "Вот как это произносится по-арабски",
    "А теперь — настоящее арабское произношение",
    "Слушай внимательно, как звучит это слово по-арабски",
]
REPEAT_PHRASES = [
    "Повторим ещё раз",
    "Ещё раз, внимательно",
    "И снова, чтобы запомнить",
    "Послушай ещё раз",
]
MEANING_LEADS = [
    "Запомни",
    "Не забудь",
    "Возьми на заметку",
    "Держи в памяти",
]
ASK_PHRASES = [
    "А теперь скажи вслух",
    "Твоя очередь — скажи вслух",
    "Попробуй произнести сам",
    "А теперь повтори за мной вслух",
]
OUTRO_PHRASES = [
    "Отлично, у тебя получается!",
    "Здорово, у тебя получилось!",
    "Супер, ты справляешься!",
    "Молодец, продолжай в том же духе!",
]


def _pick(options, n, salt):
    return options[(n * 7 + salt) % len(options)]


def tts_plan(n, lesson):
    """Развёрнутый сценарий озвучки как список чередующихся сегментов
    ru/ar. Текст собирается как раньше, с транслитом на месте слова —
    но КАЖДОЕ его вхождение (в том числе внутри lesson["teach"]) потом
    заменяется на сегмент с настоящим арабским словом. Одно и то же
    арабское аудио синтезируется один раз и переиспользуется на всех
    повторах: если просить ElevenLabs повторить слово несколько раз
    внутри одной генерации, произношение после первого раза плывёт.

    Голосовое «подпишись» — через ролик (в каждом втором), чтобы не
    надоедало; на экране призыв есть всегда."""
    parts = [p.strip() for p in strip_accents(lesson["translit"]).split("—")]
    # rstrip("-") отдельно: у урока 8 ("Аль-") конечный дефис ломает
    # \b-границу регулярки всякий раз, когда после слова идёт знак
    # препинания или конец фразы (а не следующая буква) — совпадение
    # находилось только внутри "Аль-Китаб", а не в служебных фразах.
    word = parts[0].rstrip("!?.").rstrip("-")
    meaning = parts[1] if len(parts) > 1 else ""

    intro = _pick(INTRO_PHRASES, n, 0)
    repeat = _pick(REPEAT_PHRASES, n, 1)
    meaning_lead = _pick(MEANING_LEADS, n, 2)
    ask = _pick(ASK_PHRASES, n, 3)
    outro = _pick(OUTRO_PHRASES, n, 4)

    s = f'{lesson["hook"]}. {intro}: {word}.'
    s += f' {lesson["teach"]}'
    s += f' {repeat}: {word}.'
    if meaning:
        s += f' {meaning_lead}: {word} — значит «{meaning}».'
    s += f' {ask}: {word}. {outro}'
    if n % 2 == 0:
        s += f' {lesson["cta"]}'

    return split_word_occurrences(s, word, lesson["ar"])


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
                         # Повыше стабильность — меньше оговорок и глюков;
                         # speed<1 — не тараторит и не глотает окончания
                         "voice_settings": {"stability": 0.72,
                                            "similarity_boost": 0.75,
                                            "speed": 0.85}}).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out_mp3.write_bytes(r.read())


def synthesize_plan(plan, out_mp3: Path, work: Path):
    """Синтезирует план [("ru"|"ar", текст)] по сегментам и склеивает
    их через ffmpeg. Одинаковые сегменты (в первую очередь — арабское
    слово, которое повторяется несколько раз) синтезируются только
    один раз и переиспользуются, чтобы произношение было одинаково
    чистым на каждом повторе."""
    cache = {}
    clips = []
    silence = work / "_silence.mp3"
    if not silence.exists():
        ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
               "-t", "0.35", "-q:a", "9", str(silence))

    for i, (kind, text) in enumerate(plan):
        if text not in cache:
            clip = work / f"_seg_{kind}_{len(cache):02d}.mp3"
            if not clip.exists():
                elevenlabs_tts(text, clip)
            cache[text] = clip
        clips.append(cache[text])
        clips.append(silence)

    cmd = []
    for c in clips:
        cmd += ["-i", str(c)]
    n = len(clips)
    filt = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"
    ffmpeg(*cmd, "-filter_complex", filt, "-map", "[out]", str(out_mp3))


# ---------- фоновые ролики ----------

# Недопустимые сюжеты: новости о трагедиях, политика, конфликты и т.п.
BAD_WORDS = ("bombing", "bomb", "attack", "war", "riot", "protest",
             "funeral", "crash", "accident", "shooting", "destruction",
             "damage", "rubble", "demolit", "flood", "earthquake", "strike",
             "arson", "vandal", "clash", "president", "potus", "minister")

# Канал об исламе и арабском языке — символика и атрибутика любой другой
# религии (иконы, храмы, распятия, синагоги, будда-статуи и т.п.) на фоне
# звучит неуместно, исключаем всегда.
NON_ISLAMIC_RELIGIOUS_WORDS = (
    # христианство
    "church", "cathedral", "chapel", "basilica", "monastery",
    "convent", "crucifix", "crucifixion", "christ", "jesus",
    "bible", "biblical", "gospel", "christian", "christma",
    "nativity", "madonna", "nun", "priest", "pope", "vatican",
    "saint", "icon", "orthodox", "catholic", "cross", "angel",
    # иудаизм
    "synagogue", "torah", "rabbi", "menorah", "kippah", "judaism",
    "jewish", "hanukkah", "kosher",
    # прочие религии
    "buddhist", "buddha", "hindu", "hinduism", "pagoda", "shrine",
    "deity", "idol", "temple", "shiva", "vishnu", "krishna",
    "sikh", "gurdwara", "zoroastrian",
)

# Фото живых людей (лица, портреты и т.п.) на фоне тоже не используем —
# только пейзажи, архитектура, предметы, животные, каллиграфия.
PEOPLE_WORDS = (
    "portrait", "person", "people", "human", "man", "woman", "men",
    "women", "boy", "girl", "child", "children", "kid", "kids",
    "baby", "infant", "family", "couple", "bride", "groom",
    "wedding", "face", "faces", "selfie", "crowd", "worker",
    "farmer", "student", "teacher", "athlete", "player", "soldier",
    "king", "queen", "actor", "actress", "elderly",
)
BAD_WORDS = BAD_WORDS + NON_ISLAMIC_RELIGIOUS_WORDS + PEOPLE_WORDS
# Слово целиком, а не подстрока — иначе "icon" ловит "iconic", а "kid"
# ловит "skidmark" и т.п. ложные срабатывания.
BAD_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(w) for w in BAD_WORDS) + r")\b",
    re.IGNORECASE)


def commons_image_urls(term, limit=8):
    """Ищет фотографии на Wikimedia Commons, отдаёт URL уменьшенных копий.

    Видео на Commons — в основном хроника и новости, а фото мечетей и
    пустынь много профессиональных. Из фото делаем кен-бёрнс.
    Берём thumb-версии (iiurlheight) — так просят сами Wikimedia.
    Религиозную символику других религий и фото людей исключаем прямо в
    запросе (канал об исламе, без живых лиц на фоне), чтобы такие фото
    вообще не попадали в выдачу."""
    exclude = " ".join(f"-intitle:{w}"
                       for w in NON_ISLAMIC_RELIGIOUS_WORDS + PEOPLE_WORDS)
    search = (" ".join(f"intitle:{w}" for w in term.split())
              + " filetype:bitmap " + exclude)
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
            if not BAD_PATTERN.search(u)]


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
                  "c0=0xE8D9B5:c1=0xC9A876:c2=0xF3E9D2"),
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
        synthesize_plan(tts_plan(n, lesson), voice, work)
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
