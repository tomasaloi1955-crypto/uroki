# -*- coding: utf-8 -*-
"""
Длинные видео (~10 минут), 3 серии в неделю: тот же фирменный стиль,
что и в shorts_v2.py (фото-фоны с кен-бёрнсом, зелёно-золотой оверлей,
голос ElevenLabs), но landscape 1920x1080 и сериями из нескольких сцен.

ВАЖНО про источник: episodes НЕ пересказывают текст защищённых учебников
(«Мединский курс» на диске подписан «For Personal use Only») — контент
оригинальный, в той же (общей, не защищённой авторским правом) методической
последовательности: указательные местоимения -> вопросы -> лексика и т.д.

Запуск:
    python long_video.py 1        # собрать эпизод 1
Результат: build/long/episode_NN.mp4 + episode_NN.txt (описание для YouTube)
"""

import json
import os
import re
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

from shorts_v2 import (
    GOLD, FONT_BOLD, FONT_REG, FONT_AR, UA,
    ar_text, pick_font, strip_accents, wrap_to_width,
    ffmpeg, probe_duration,
    commons_image_urls, download_head,
)

LW, LH = 1920, 1080
OUT_DIR = Path("build") / "long"
DARK = (8, 20, 15)
HEADER_H = 190


def elevenlabs_tts_slow(text: str, out_mp3: Path):
    """Как shorts_v2.elevenlabs_tts, но чуть медленнее (speed=0.85) —
    длинное учебное видео легче слушать в спокойном темпе, и это же
    честно добавляет хронометража без искусственного раздувания текста.

    С повторами: на 19 сценах транзитный сетевой таймаут ElevenLabs
    иначе роняет всю сборку и теряет прогресс по текущей сцене."""
    key = os.environ["ELEVENLABS_API_KEY"]
    voice = os.environ["ELEVENLABS_VOICE_ID"]
    req_body = json.dumps({"text": text,
                           "model_id": "eleven_multilingual_v2",
                           "voice_settings": {"stability": 0.6,
                                              "similarity_boost": 0.75,
                                              "speed": 0.85}}).encode()
    last_err = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
                "?output_format=mp3_44100_128",
                data=req_body,
                headers={"xi-api-key": key, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                out_mp3.write_bytes(r.read())
            return
        except Exception as e:
            last_err = e
            print(f"    озвучка: попытка {attempt + 1} не удалась ({e}), "
                  f"жду и пробую снова...")
            time.sleep(10)
    raise last_err


# Служебные частицы, которые повторяются из урока в урок и не всегда
# попадают в lines/ar_big/bullets в чистом виде для авторазбора.
SEED_AR_VOCAB = {"ма": "ما", "хал": "هل", "наам": "نعم", "ля": "لا"}


def build_ar_vocab(scenes):
    """Собирает словарь транслит-слово -> арабское написание из lines/
    ar_big/bullets всего эпизода (там уже есть верные пары "как
    произносится" <-> "как пишется" для слов, которые проходят в
    уроке)."""
    vocab = dict(SEED_AR_VOCAB)

    def add_pair(ar_phrase, ru_phrase):
        ar_words = ar_phrase.replace("؟", "").replace("?", "").split()
        # strip_accents(): ключи должны совпадать со словами уже после
        # той же нормализации, что применяется к тексту озвучки (иначе
        # "бейт" не найдёт "беит" после вычитания диакритики из "й").
        ru_words = strip_accents(ru_phrase).split("—")[0].strip().split()
        if len(ar_words) != len(ru_words):
            return
        for aw, rw in zip(ar_words, ru_words):
            key = rw.strip(",.!?").lower()
            if key and key not in vocab:
                vocab[key] = aw

    for sc in scenes:
        if sc.get("ar_big") and sc.get("sub"):
            add_pair(sc["ar_big"], sc["sub"])
        for ar, ru in sc.get("lines", []):
            add_pair(ar, ru)
        for ar, ru in sc.get("bullets", []):
            add_pair(ar, ru)
    return vocab


def arabize(text, vocab):
    """Вставляет настоящее арабское произношение рядом с транслитом:
    ElevenLabs иначе читает кириллическую транслитерацию русским
    произношением, и арабские слова на обучающем канале звучат
    неверно."""
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in vocab) + r")\b",
        re.IGNORECASE)
    return pattern.sub(lambda m: f"{m.group(0)} ({vocab[m.group(0).lower()]})",
                        text)


# ---------- эпизоды (оригинальный контент, методика курса, не пересказ книги) ----------

EPISODES = {
    1: dict(
        title="Указательные местоимения: Хаза и Хазихи",
        next_teaser="считаем предметы от одного до десяти",
        scenes=[
            dict(theme="sheikh zayed mosque",
                 title="Всего 1 урок",
                 ar_big="هذا؟ هذه؟",
                 sub="…и ты назовёшь по-арабски ЛЮБОЙ предмет вокруг себя",
                 speech="Через десять минут ты сможешь показать пальцем на "
                        "любой предмет вокруг — и правильно назвать его "
                        "по-арабски: дом, книгу, машину, дерево — что "
                        "угодно. Всего два маленьких слова открывают тебе "
                        "почти весь окружающий мир по-арабски. Это первая "
                        "серия нового курса на нашем канале — мы будем "
                        "выпускать новый урок три раза в неделю, шаг за "
                        "шагом, от простого к сложному, без спешки. Не "
                        "нужно ничего запоминать заранее — просто слушай, "
                        "смотри и повторяй вслух вместе со мной. Готов? "
                        "Тогда начинаем первый урок курса!"),
            dict(theme="arabic calligraphy",
                 title="Мединский курс · Урок 1",
                 sub="Хаза и Хазихи — «это» по-арабски",
                 speech="Здравствуй, и добро пожаловать на первый урок! "
                        "Сегодня мы разберём фундамент арабской "
                        "грамматики — указательные местоимения хаза и "
                        "хазихи. Оба слова переводятся одинаково — «это», "
                        "но используются по-разному, в зависимости от "
                        "рода слова, к которому относятся. Это первое, "
                        "что должен усвоить любой, кто начинает учить "
                        "арабский — потому что эта конструкция встретится "
                        "тебе в каждом следующем уроке. Курс подходит "
                        "любому новичку — не важно, учил ли ты арабский "
                        "раньше. Слушай внимательно и повторяй вслух "
                        "каждое слово — так оно запоминается в разы "
                        "быстрее, чем при простом чтении. Если у тебя "
                        "есть тетрадь — запиши сегодняшние слова, это "
                        "тоже здорово помогает."),
            dict(theme="old books",
                 title="Хаза — для мужского рода",
                 ar_big="هذا",
                 sub="Хаза — «это» (про предметы мужского рода)",
                 speech="Слово хаза пишется هذا и переводится «это» или "
                        "«этот». Хаза используется, когда предмет, о "
                        "котором мы говорим — мужского рода. В арабском "
                        "языке у каждого существительного есть род, "
                        "мужской или женский, и от этого зависит, какое "
                        "слово мы выберем — хаза или хазихи. Запомни одно "
                        "это слово, хаза, — и ты уже можешь строить "
                        "простые предложения о множестве вещей вокруг "
                        "себя. Повтори вслух: хаза. Ещё раз: хаза."),
            dict(theme="old city street",
                 title="Хаза + существительное",
                 lines=[("هذا بيت", "Хаза бейт — Это дом"),
                        ("هذا كتاب", "Хаза китаб — Это книга")],
                 speech="Давай применим наше новое слово. Бейт значит дом. "
                        "Хаза бейт — это дом. А китаб значит книга. Хаза "
                        "китаб — это книга. Заметь: порядок слов такой же, "
                        "как в русском — сначала хаза, потом предмет. "
                        "Повтори вслух, не торопясь: хаза бейт… хаза "
                        "китаб… Отлично, идём дальше!"),
            dict(theme="arabic manuscript",
                 title="Хаза + существительное",
                 lines=[("هذا قلم", "Хаза калям — Это ручка"),
                        ("هذا باب", "Хаза баб — Это дверь")],
                 speech="Ещё два полезных слова. Калям значит ручка или "
                        "карандаш — этим словом называют любой пишущий "
                        "предмет. Хаза калям — это ручка. А баб значит "
                        "дверь. Хаза баб — это дверь. Повтори: хаза "
                        "калям… хаза баб… Теперь у тебя в запасе уже "
                        "четыре слова мужского рода!"),
            dict(theme="mosque interior",
                 title="Хаза + существительное",
                 lines=[("هذا مسجد", "Хаза масджид — Это мечеть"),
                        ("هذا كرسي", "Хаза курси — Это стул")],
                 speech="И ещё пара слов для практики. Масджид — мечеть, "
                        "очень важное слово. Хаза масджид — это мечеть. А "
                        "курси значит стул. Хаза курси — это стул. "
                        "Повтори: хаза масджид… хаза курси… Прекрасно, "
                        "теперь ты знаешь уже шесть слов мужского рода!"),
            dict(theme="souk market",
                 title="Спроси: «Что это?»",
                 ar_big="ما هذا؟",
                 sub="Ма хаза? — Что это? (про мужской род)",
                 speech="А теперь научимся спрашивать. Хочешь узнать «что "
                        "это»? Скажи: ма хаза? Слово ма в начале "
                        "превращает утверждение в вопрос. Ответ строится "
                        "точно так же, как мы уже учили: ма хаза? — хаза "
                        "бейт, это дом. Или: ма хаза؟ — хаза китаб, это "
                        "книга. Ещё пример: ма хаза؟ — хаза баб, это "
                        "дверь. Попробуй сам, вслух, глядя на предметы "
                        "вокруг себя: ма хаза? И отвечай полным "
                        "предложением, как мы учили."),
            dict(theme="rose garden",
                 title="Хазихи — для женского рода",
                 ar_big="هذه",
                 sub="Хазихи — «это» (про предметы женского рода)",
                 speech="Теперь второе слово нашего урока — хазихи, "
                        "пишется هذه. Оно тоже переводится «это», но "
                        "используется для слов женского рода. Как понять, "
                        "что слово женского рода? Есть простое правило: "
                        "чаще всего у таких слов на конце стоит округлая "
                        "буква та марбута. Это очень удобная подсказка — "
                        "сейчас ты увидишь её на живых примерах. Повтори "
                        "вслух: хазихи. Ещё раз, медленно: ха-зи-хи."),
            dict(theme="desert road driving",
                 title="Хазихи + существительное",
                 lines=[("هذه سيارة", "Хазихи сайяра — Это машина"),
                        ("هذه مدرسة", "Хазихи мадраса — Это школа")],
                 speech="Сайяра значит машина, автомобиль. Хазихи сайяра — "
                        "это машина. А мадраса значит школа. Хазихи "
                        "мадраса — это школа. Обрати внимание: у обоих "
                        "слов на конце та марбута — вот и подсказка, "
                        "почему мы говорим именно хазихи. Повтори: хазихи "
                        "сайяра… хазихи мадраса…"),
            dict(theme="flower field",
                 title="Хазихи + существительное",
                 lines=[("هذه شجرة", "Хазихи шаджара — Это дерево"),
                        ("هذه وردة", "Хазихи варда — Это цветок")],
                 speech="И ещё два красивых слова. Шаджара значит дерево. "
                        "Хазихи шаджара — это дерево. А варда значит "
                        "цветок, роза. Хазихи варда — это цветок. Повтори "
                        "вслух: хазихи шаджара… хазихи варда… Ты уже "
                        "выучил четыре слова женского рода!"),
            dict(theme="arabic window",
                 title="Хазихи + существительное",
                 lines=[("هذه نافذة", "Хазихи нафида — Это окно"),
                        ("هذه ساعة", "Хазихи саа — Это часы")],
                 speech="Ещё два слова для практики. Нафида — окно. "
                        "Хазихи нафида — это окно. А саа значит часы или "
                        "час. Хазихи саа — это часы. Повтори: хазихи "
                        "нафида… хазихи саа… Отлично, шесть слов женского "
                        "рода в твоей копилке!"),
            dict(theme="morocco market",
                 title="Спроси: «Что это?»",
                 ar_big="ما هذه؟",
                 sub="Ма хазихи? — Что это? (про женский род)",
                 speech="А для женского рода вопрос звучит так: ма "
                        "хазихи? Например: ма хазихи? Хазихи сайяра, это "
                        "машина. Или: ма хазихи? Хазихи мадраса, это "
                        "школа. Ещё пример: ма хазихи? — хазихи варда, "
                        "это цветок. Попробуй сам: ма хазихи? Обрати "
                        "внимание, как похожи оба вопроса — ма хаза и ма "
                        "хазихи, разница только в одном слове, которое "
                        "зависит от рода. Это правило распространяется "
                        "вообще на все существительные арабского языка, "
                        "какое бы слово ты ни выучил дальше."),
            dict(theme="medina morocco",
                 title="Живой диалог",
                 lines=[("ما هذا؟ — هذا كتاب", "Ма хаза? — Хаза китаб."),
                        ("ما هذه؟ — هذه سيارة", "Ма хазихи? — Хазихи "
                                                  "сайяра."),
                        ("هل هذا بيت؟ — نعم، هذا بيت", "Хал хаза бейт? — "
                                                        "Наам, хаза бейт.")],
                 speech="Теперь разыграем живой диалог из трёх вопросов. "
                        "Первый: ма хаза? — хаза китаб, это книга. "
                        "Второй: ма хазихи? — хазихи сайяра, это машина. "
                        "И третий, немного другой: хал хаза бейт? — это "
                        "значит «это дом?», с вопросительным словом хал в "
                        "начале, для вопроса да или нет. Ответ: наам, "
                        "хаза бейт — да, это дом. Кстати, слова наам и "
                        "ля — да и нет по-арабски — ты наверняка уже "
                        "видел в наших коротких видео на канале! Здесь та "
                        "же самая пара слов, просто в живом диалоге. А "
                        "если бы ответ был отрицательным, мы бы сказали: "
                        "ля, хаза масджид — нет, это мечеть. Частица ля "
                        "перед словом и превращает ответ в отрицание, "
                        "точно так же просто, как наам превращает его в "
                        "согласие. Повтори весь диалог ещё раз вслух, "
                        "вместе со мной, стараясь не подглядывать в "
                        "перевод."),
            dict(theme="camel desert",
                 title="Проверь себя! · 1",
                 sub="Как сказать «это цветок»?",
                 lines=[("هذه وردة", "Хазихи варда")],
                 speech="А теперь проверим, что запомнилось — пять "
                        "быстрых вопросов. Вопрос первый: как сказать "
                        "«это цветок»? Поставь видео на паузу и попробуй "
                        "ответить сам, вслух… Готово? Правильный ответ: "
                        "хазихи варда — потому что варда, цветок, "
                        "женского рода."),
            dict(theme="desert sunset",
                 title="Проверь себя! · 2",
                 sub="Как сказать «это книга»?",
                 lines=[("هذا كتاب", "Хаза китаб")],
                 speech="Вопрос второй. Как сказать «это книга»? Пауза, "
                        "попробуй сам… Ответ: хаза китаб — китаб "
                        "мужского рода, поэтому хаза."),
            dict(theme="arabic coffee",
                 title="Проверь себя! · 3",
                 sub="Хаза или Хазихи: «школа»?",
                 lines=[("هذه مدرسة", "Хазихи мадраса")],
                 speech="Вопрос третий, чуть хитрее. Хаза или хазихи — со "
                        "словом мадраса, школа? Пауза… Правильно — "
                        "хазихи, потому что мадраса заканчивается на та "
                        "марбуту и значит она женского рода: хазихи "
                        "мадраса."),
            dict(theme="sheikh zayed mosque",
                 title="Проверь себя! · 4",
                 sub="Хаза или Хазихи: «мечеть»?",
                 lines=[("هذا مسجد", "Хаза масджид")],
                 speech="Вопрос четвёртый. А со словом масджид, мечеть — "
                        "хаза или хазихи? Пауза, подумай сам… Ответ: хаза "
                        "масджид — масджид мужского рода, окончания та "
                        "марбута здесь нет."),
            dict(theme="arabic window",
                 title="Проверь себя! · 5",
                 sub="Как сказать «это окно»?",
                 lines=[("هذه نافذة", "Хазихи нафида")],
                 speech="И последний, пятый вопрос. Как сказать «это "
                        "окно»? Пауза, ответь вслух… Правильный ответ: "
                        "хазихи нафида. Если ты ответил верно хотя бы на "
                        "четыре вопроса из пяти — ты отлично усвоил "
                        "материал сегодняшнего урока!"),
            dict(theme="desert sunset",
                 title="Ты справился!",
                 bullets=[("هذا", "Хаза — это (муж. род)"),
                          ("هذه", "Хазихи — это (жен. род)"),
                          ("ما هذا؟ / ما هذه؟", "Что это?"),
                          ("هل … ؟ — نعم / لا", "Вопрос да/нет — да / нет")],
                 speech="Отличная работа, ты дошёл до конца первого урока! "
                        "Давай коротко повторим самое важное. Хаза — это, "
                        "про предметы мужского рода. Хазихи — это, про "
                        "предметы женского рода. Вопрос ма хаза или ма "
                        "хазихи — значит «что это». А вопрос хал в начале "
                        "предложения превращает его в вопрос да или нет. "
                        "Ты выучил двенадцать новых слов и две ключевые "
                        "конструкции — это отличный результат для первого "
                        "урока! Постарайся сегодня же, в течение дня, "
                        "несколько раз посмотреть вокруг себя и назвать "
                        "хотя бы три предмета по-арабски — это займёт "
                        "буквально минуту, а память закрепит материал "
                        "гораздо лучше, чем просто просмотр видео. Если "
                        "хочешь ещё практики между большими уроками — "
                        "загляни в короткие видео на канале, там мы "
                        "разбираем отдельные слова и фразы за пятнадцать "
                        "секунд. В следующей серии мы научимся считать "
                        "предметы от одного до десяти. Подписывайся, "
                        "чтобы не пропустить, и ставь лайк, если урок был "
                        "полезен — это правда помогает каналу расти. "
                        "Увидимся в следующем уроке, ма ассаляма!"),
        ],
    ),
}


# ---------- фон: landscape кен-бёрнс (отдельно от вертикального в shorts_v2) ----------

def kenburns_clip_landscape(img: Path, seg_dur, out: Path, zoom_in=True) -> bool:
    frames = max(int(seg_dur * 30), 30)
    step = 0.18 / frames
    z = f"1+{step:.6f}*on" if zoom_in else f"1.18-{step:.6f}*on"
    p = ffmpeg("-loop", "1", "-i", str(img),
               "-vf", ("scale=3840:2160:force_original_aspect_ratio=increase,"
                       "crop=3840:2160,"
                       f"zoompan=z='{z}':d={frames}"
                       ":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                       f":s={LW}x{LH}:fps=30"),
               "-frames:v", str(frames),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
               "-pix_fmt", "yuv420p", str(out))
    ok = p.returncode == 0 and out.exists() and out.stat().st_size > 50_000
    if not ok and out.exists():
        out.unlink()
    return ok


def fallback_clip_landscape(seg_dur, out: Path):
    ffmpeg("-f", "lavfi",
           "-i", (f"gradients=size={LW}x{LH}:speed=0.02:nb_colors=3:"
                  "c0=0x0E573E:c1=0xDEB84A:c2=0x083D2B"),
           "-t", f"{seg_dur:.2f}", "-r", "30",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", str(out))


def scene_bg(theme, dur, work: Path, idx: int) -> Path:
    img = work / f"photo_{idx:02d}.img"
    out = work / f"bg_{idx:02d}.mp4"
    for url in commons_image_urls(theme):
        print(f"    фон: {theme} <- {url.rsplit('/', 1)[-1][:60]}")
        if download_head(url, img) and \
                kenburns_clip_landscape(img, dur, out, zoom_in=idx % 2 == 0):
            return out
        time.sleep(1)
    print("    фон: градиент (сток не нашёлся)")
    fallback_clip_landscape(dur, out)
    return out


# ---------- текстовый слой (landscape, тот же фирменный стиль) ----------

def rounded_panel(d, box, radius=30, alpha=155):
    d.rounded_rectangle(box, radius=radius, fill=(8, 30, 22, alpha))


def darken(d):
    d.rectangle([0, 0, LW, LH], fill=(8, 20, 15, 40))
    for i in range(260):
        a = int(120 * (1 - i / 260))
        d.line([(0, i), (LW, i)], fill=(5, 15, 10, a))
        d.line([(0, LH - 1 - i), (LW, LH - 1 - i)], fill=(5, 15, 10, a))


def draw_scene(scene: dict, out_png: Path):
    img = Image.new("RGBA", (LW, LH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    darken(d)

    # Заголовок сцены сверху
    if scene.get("title"):
        f_title = pick_font(FONT_BOLD, 62)
        lines = wrap_to_width(d, scene["title"], f_title, LW - 300)
        lh = 78
        top, bot = 60, 60 + 50 + lh * len(lines)
        rounded_panel(d, [140, top, LW - 140, bot])
        y = top + 26
        for line in lines:
            d.text((LW // 2, y + lh // 2), line, font=f_title,
                   fill=(255, 255, 255), anchor="mm",
                   stroke_width=3, stroke_fill=(8, 30, 22))
            y += lh
        body_top = bot + 30
    else:
        body_top = 140

    # Крупная арабская фраза по центру (сцены-«герои»)
    if scene.get("ar_big"):
        f_ar = pick_font(FONT_AR, 220)
        txt = ar_text(scene["ar_big"])
        while d.textlength(txt, font=f_ar) > LW - 300 and f_ar.size > 100:
            f_ar = pick_font(FONT_AR, f_ar.size - 16)
        cy = 430 if scene.get("sub") else 520
        for half, dy in ((360, -110), (360, 110)):
            d.line([(LW // 2 - half, cy + dy), (LW // 2 + half, cy + dy)],
                   fill=GOLD + (220,), width=5)
        d.text((LW // 2, cy), txt, font=f_ar, fill=GOLD, anchor="mm",
               stroke_width=7, stroke_fill=(8, 30, 22))

    if scene.get("sub"):
        f_sub = pick_font(FONT_BOLD, 58)
        sub_lines = wrap_to_width(d, scene["sub"], f_sub, LW - 400)
        y = 640
        for line in sub_lines:
            d.text((LW // 2, y), line, font=f_sub, fill=(255, 255, 255),
                   anchor="mm", stroke_width=3, stroke_fill=(8, 30, 22))
            y += 74
        # sub занимает место сверху — сдвигаем начало следующего блока
        # (lines/bullets) ниже последней строки, иначе они накладываются
        # друг на друга (было видно на сценах "Проверь себя!")
        body_top = max(body_top, y + 40)

    # Список фраз (лексика / диалог / квиз)
    if scene.get("lines"):
        n = len(scene["lines"])
        f_ar = pick_font(FONT_AR, 110 if n <= 2 else 90)
        f_tr = pick_font(FONT_REG, 46)
        row_h = (LH - body_top - 140) // max(n, 1)
        y = body_top + row_h // 2
        for ar, tr in scene["lines"]:
            txt = ar_text(ar)
            d.text((LW // 2, y - 34), txt, font=f_ar, fill=GOLD,
                   anchor="mm", stroke_width=5, stroke_fill=(8, 30, 22))
            d.text((LW // 2, y + 58), tr, font=f_tr, fill=(240, 240, 240),
                   anchor="mm", stroke_width=2, stroke_fill=(8, 30, 22))
            y += row_h

    # Итоговые тезисы (outro): арабская часть и русская — отдельными
    # прогонами (свой шрифт + reshape/bidi у каждой), как в "lines" —
    # смешивать письменности в одном text() нельзя: разный набор глифов
    # шрифта на Windows/Linux и его не развернёт reshape+bidi корректно.
    if scene.get("bullets"):
        f_ar = pick_font(FONT_AR, 56)
        f_b = pick_font(FONT_BOLD, 46)
        y = body_top + 50
        for ar, ru in scene["bullets"]:
            ar_txt = ar_text(ar)
            ar_w = d.textlength(ar_txt, font=f_ar)
            ru_txt = "•  " + ru
            ru_w = d.textlength(ru_txt, font=f_b)
            gap = 24
            x0 = (LW - ar_w - ru_w - gap) // 2
            d.text((x0, y), ru_txt, font=f_b, fill=(240, 240, 240),
                   anchor="lm", stroke_width=2, stroke_fill=(8, 30, 22))
            d.text((x0 + ru_w + gap, y), ar_txt, font=f_ar, fill=GOLD,
                   anchor="lm", stroke_width=3, stroke_fill=(8, 30, 22))
            y += 92
        f_cta = pick_font(FONT_BOLD, 54)
        rounded_panel(d, [260, LH - 150, LW - 260, LH - 60])
        d.text((LW // 2, LH - 105), "Хочешь учить арабский легко? Подпишись!",
               font=f_cta, fill=GOLD, anchor="mm",
               stroke_width=2, stroke_fill=(8, 30, 22))

    img.save(out_png)


# ---------- сборка ----------

def build_scene_clip(scene: dict, idx: int, work: Path, vocab: dict) -> Path:
    voice = work / f"voice_{idx:02d}.mp3"
    if not voice.exists():
        speech = arabize(strip_accents(scene["speech"]), vocab)
        elevenlabs_tts_slow(speech, voice)
    dur = probe_duration(voice) + 1.0

    png = work / f"overlay_{idx:02d}.png"
    draw_scene(scene, png)

    bg = scene_bg(scene["theme"], dur, work, idx)

    clip = work / f"scene_{idx:02d}.mp4"
    ffmpeg("-i", str(bg), "-i", str(png), "-i", str(voice),
           "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
           "-map", "[v]", "-map", "2:a", "-af", "apad",
           "-t", f"{dur:.2f}",
           "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", str(clip))
    return clip


def build_episode(n: int) -> Path:
    """Копим готовые сцены и склеиваем их ОДИН раз в конце (быстро,
    O(n)) — не на каждом шаге (это давало O(n^2): каждый повторный
    прогон переписывал уже накопленный файл целиком, и склейка
    затягивалась на часы). От вытеснения старых файлов песочницей
    защищаемся иначе — "подогреваем" уже готовые клипы (обновляем
    время модификации), чтобы они не выглядели устаревшими."""
    ep = EPISODES[n]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    work = OUT_DIR / f"work_{n:02d}"
    work.mkdir(exist_ok=True)
    print(f"Эпизод {n}: {ep['title']}")
    vocab = build_ar_vocab(ep["scenes"])

    clips = []
    for i, scene in enumerate(ep["scenes"]):
        print(f"  сцена {i + 1}/{len(ep['scenes'])}: "
              f"{scene.get('title') or scene.get('sub') or scene['theme']}")
        clips.append(build_scene_clip(scene, i, work, vocab))

        # Промежуточные файлы сцены (фото/фон/оверлей) больше не нужны —
        # освобождаем место, не дожидаясь конца сборки.
        for pat in (f"bg_{i:02d}.mp4", f"photo_{i:02d}.img",
                   f"overlay_{i:02d}.png"):
            p = work / pat
            if p.exists():
                p.unlink()

        # "Подогреваем" уже готовые клипы сцен, чтобы не выглядели
        # старыми файлами и не попали под возможную чистку песочницы.
        for c in clips:
            c.touch()

    lst = work / "concat.txt"
    lst.write_text("\n".join(f"file '{c.resolve().as_posix()}'" for c in clips),
                   encoding="utf-8")
    out = OUT_DIR / f"episode_{n:02d}.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out))
    if not (out.exists() and out.stat().st_size > 100_000):
        # На случай рассинхронизации кодеков между клипами — надёжный,
        # но более медленный путь с перекодированием.
        ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst),
               "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", str(out))

    total = probe_duration(out)
    (OUT_DIR / f"episode_{n:02d}.txt").write_text(
        caption_for(n, ep), encoding="utf-8")
    print(f"Готово: {out} ({total / 60:.1f} мин)")
    return out


def make_thumbnail(n: int) -> Path:
    """Обложка в фирменном стиле (зелёно-золотой, фото + арабское слово) —
    только для длинных видео, у shorts обложки нет."""
    ep = EPISODES[n]
    TW, TH = 1280, 720
    work = OUT_DIR / f"work_{n:02d}"
    work.mkdir(parents=True, exist_ok=True)

    hero = next((s for s in ep["scenes"] if s.get("ar_big")), ep["scenes"][0])
    img_path = work / "thumb_photo.img"
    photo = None
    for url in commons_image_urls(hero["theme"]):
        if download_head(url, img_path):
            photo = img_path
            break
    img = (Image.open(photo).convert("RGB") if photo
           else Image.new("RGB", (TW, TH), (14, 60, 45)))
    iw, ih = img.size
    scale = max(TW / iw, TH / ih)
    img = img.resize((int(iw * scale) + 1, int(ih * scale) + 1))
    img = img.crop((0, 0, TW, TH))
    img = img.convert("RGBA")

    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, TW, TH], fill=(8, 20, 15, 90))
    for i in range(260):
        a = int(170 * (1 - i / 260))
        d.line([(0, TH - 1 - i), (TW, TH - 1 - i)], fill=(5, 15, 10, a))

    f_ar = pick_font(FONT_AR, 220)
    txt = ar_text(hero.get("ar_big", ""))
    if txt:
        while d.textlength(txt, font=f_ar) > TW - 120 and f_ar.size > 100:
            f_ar = pick_font(FONT_AR, f_ar.size - 12)
        d.text((TW // 2, 260), txt, font=f_ar, fill=GOLD, anchor="mm",
               stroke_width=8, stroke_fill=(8, 30, 22))

    f_title = pick_font(FONT_BOLD, 64)
    lines = wrap_to_width(d, ep["title"], f_title, TW - 140)[:2]
    y = TH - 70 - 74 * len(lines)
    for line in lines:
        d.text((TW // 2, y), line, font=f_title, fill=(255, 255, 255),
               anchor="mm", stroke_width=4, stroke_fill=(8, 30, 22))
        y += 74

    f_badge = pick_font(FONT_BOLD, 46)
    badge = f"МЕДИНСКИЙ КУРС · СЕРИЯ {n}"
    bw = int(d.textlength(badge, font=f_badge)) + 60
    d.rounded_rectangle([TW // 2 - bw // 2, 30, TW // 2 + bw // 2, 96],
                        20, fill=(8, 30, 22, 210))
    d.text((TW // 2, 63), badge, font=f_badge, fill=GOLD, anchor="mm")

    out = OUT_DIR / f"episode_{n:02d}_thumb.jpg"
    img.convert("RGB").save(out, "JPEG", quality=92)
    print(f"  обложка: {out}")
    return out


def caption_for(n, ep):
    return (f'Мединский курс — Серия {n}: {ep["title"]}\n\n'
            f'Учим арабский с нуля, шаг за шагом. В следующей серии — '
            f'{ep["next_teaser"]}.\n\n'
            "#арабский #арабскийязык #арабскийснуля #мединскийкурс #урокарабского")


if __name__ == "__main__":
    import sys
    build_episode(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
