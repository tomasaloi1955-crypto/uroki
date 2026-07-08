# -*- coding: utf-8 -*-
"""
Яркий «мультяшный» шаблон урока (v2) — по принципам детских обучающих
каналов (Закария и подобные):

  * одно слово = одна яркая сцена (смена экрана каждые ~20 сек — динамика)
  * большая картинка-эмодзи — «герой» слова
  * сочные цвета, на каждом слове — новый
  * произношение МЕДЛЕННОЕ и чёткое (rate -25%), повторы 3 раза
  * призыв к действию на каждом слове: «Теперь ты! Скажи вслух!»
  * маскот-сова в углу и прогресс-точки — ребёнок видит, сколько осталось
  * в конце — игра-проверка (вспомни слово) и похвала

JSON-формат v2 (проще старого — слайды строятся сами):
{
  "course": ..., "lesson_number": ..., "topic": ..., "teacher": ...,
  "voice_ru": ..., "voice_ar": ..., "mascot": "🦉",
  "items": [ {"ar": "أَحْمَر", "tr": "ахмар", "ru": "красный", "emoji": "🔴"}, ... ]
}

Запуск:  python make_lesson2.py v2_colors.json
Результат: build/<имя>/lesson.mp4  +  build/<имя>/shorts/*.mp4 (вертикальные)
"""

import asyncio
import json
import random
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from make_lesson import prep_text, ffmpeg, audio_duration

W, H = 1280, 720
SW, SH = 1080, 1920
PAUSE_AFTER = 0.6
AR_RATE = "-25%"          # медленное чёткое произношение арабского

# Сочная палитра — каждый следующий экран нового цвета
ACCENTS = [
    (230, 57, 70),    # красно-коралловый
    (42, 157, 143),   # бирюзовый
    (155, 93, 229),   # фиолетовый
    (247, 127, 0),    # оранжевый
    (241, 91, 181),   # розовый
    (67, 97, 238),    # синий
    (56, 176, 0),     # зелёный
]
DARK = (45, 40, 60)
WHITE = (255, 255, 255)

F_BOLD = "C:/Windows/Fonts/arialbd.ttf"
F_REG = "C:/Windows/Fonts/arial.ttf"
F_EMOJI = "C:/Windows/Fonts/seguiemj.ttf"
# На Linux (GitHub Actions): ставится в workflow, пути ниже подхватятся сами
import platform
if platform.system() != "Windows":
    F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    F_REG = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
    F_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def tint(accent, k=0.88):
    """Светлый пастельный фон из акцентного цвета."""
    return tuple(int(c + (255 - c) * k) for c in accent)


def emoji_text(d, xy, s, size, anchor="mm"):
    f = font(F_EMOJI, size)
    try:
        d.text(xy, s, font=f, embedded_color=True, anchor=anchor)
    except TypeError:
        d.text(xy, s, font=f, anchor=anchor)


def progress_dots(d, cx, y, total, current, accent, r=12, gap=40):
    x0 = cx - (total - 1) * gap / 2
    for k in range(total):
        x = x0 + k * gap
        if k < current:
            d.ellipse([x - r, y - r, x + r, y + r], fill=accent)
        else:
            d.ellipse([x - r, y - r, x + r, y + r], outline=accent, width=3)


def draw_item(item, idx, total, lesson, out, vertical=False):
    """Сцена одного слова: эмодзи-герой, арабский крупно, транскрипция, перевод."""
    accent = ACCENTS[idx % len(ACCENTS)]
    w, h = (SW, SH) if vertical else (W, H)
    img = Image.new("RGB", (w, h), tint(accent))
    d = ImageDraw.Draw(img)

    if vertical:
        d.rounded_rectangle([40, 500, w - 40, 1500], 60, fill=WHITE)
        emoji_text(d, (w // 2, 340), item["emoji"], 260)
        d.text((w // 2, 760), prep_text(item_word(item)), font=font(F_BOLD, 150),
               fill=DARK, anchor="mm")
        d.text((w // 2, 1000), item["tr"], font=font(F_BOLD, 90),
               fill=accent, anchor="mm")
        d.text((w // 2, 1200), item["ru"], font=font(F_REG, 76),
               fill=DARK, anchor="mm")
        d.text((w // 2, 1390), "Скажи вслух!", font=font(F_BOLD, 56),
               fill=accent, anchor="mm")
        progress_dots(d, w // 2, 1580, total, idx + 1, accent, r=14, gap=56)
        emoji_text(d, (110, 1760), lesson.get("mascot", "🦉"), 120)
        d.text((w // 2 + 40, 1760), f'{lesson["course"]} · Урок {lesson["lesson_number"]}',
               font=font(F_REG, 40), fill=DARK, anchor="mm")
    else:
        # Белая карточка слева, эмодзи-герой справа
        d.rounded_rectangle([60, 120, 760, 600], 48, fill=WHITE)
        d.text((410, 230), prep_text(item_word(item)), font=font(F_BOLD, 120),
               fill=DARK, anchor="mm")
        d.text((410, 380), item["tr"], font=font(F_BOLD, 72),
               fill=accent, anchor="mm")
        d.text((410, 500), item["ru"], font=font(F_REG, 56),
               fill=DARK, anchor="mm")
        emoji_text(d, (1020, 330), item["emoji"], 300)
        d.text((1020, 580), "Скажи вслух!", font=font(F_BOLD, 44),
               fill=accent, anchor="mm")
        # Шапка: тема + счёт слов
        d.text((60, 50), lesson["topic"], font=font(F_BOLD, 44), fill=DARK, anchor="lm")
        d.text((w - 60, 50), f"{idx + 1} / {total}", font=font(F_BOLD, 44),
               fill=accent, anchor="rm")
        progress_dots(d, w // 2, 665, total, idx + 1, accent)
        emoji_text(d, (70, 660), lesson.get("mascot", "🦉"), 80)
    img.save(out)


def draw_cover(lesson, out, text_top, text_big, emoji, vertical=False, accent=None):
    """Титул / игра / финал — крупный текст + эмодзи."""
    accent = accent or ACCENTS[1]
    w, h = (SW, SH) if vertical else (W, H)
    img = Image.new("RGB", (w, h), tint(accent))
    d = ImageDraw.Draw(img)
    cy = h // 2
    emoji_text(d, (w // 2, cy - (300 if vertical else 170)), emoji, 300 if vertical else 220)
    d.text((w // 2, cy + (60 if vertical else 40)), text_top,
           font=font(F_BOLD, 64 if vertical else 52), fill=accent, anchor="mm")
    d.text((w // 2, cy + (220 if vertical else 140)), prep_text(text_big),
           font=font(F_BOLD, 88 if vertical else 72), fill=DARK, anchor="mm")
    d.text((w // 2, h - 100), f'{lesson["course"]} · Урок {lesson["lesson_number"]} · {lesson["teacher"]}',
           font=font(F_REG, 40 if vertical else 30), fill=DARK, anchor="mm")
    img.save(out)


def item_word(item):
    """Слово урока: ключ 'word' (любой язык) или 'ar' (старые файлы)."""
    return item.get("word") or item["ar"]


async def tts(text, voice, out_path, rate=None):
    import edge_tts
    kw = {"rate": rate} if rate else {}
    await edge_tts.Communicate(text.strip(), voice, **kw).save(str(out_path))


def make_silence(path, seconds=1.6):
    ffmpeg("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
           "-t", str(seconds), "-c:a", "libmp3lame", "-q:a", "9", str(path))


async def slide_audio(segments, adir, name, lesson, silence):
    """segments: список (lang, text, slow?) -> один mp3."""
    files = []
    for j, (lang, text, slow) in enumerate(segments):
        if lang == "pause":
            files.append(silence)
            continue
        p = adir / f"{name}_{j:02d}.mp3"
        await tts(text, lesson[f"voice_{lang}"],
                  p, rate=AR_RATE if slow else None)
        files.append(p)
    lst = adir / f"{name}_list.txt"
    lst.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in files),
                   encoding="utf-8")
    out = adir / f"{name}.mp3"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst),
           "-c:a", "libmp3lame", "-q:a", "3", str(out))
    return out


def clip(png, mp3, out):
    dur = audio_duration(mp3) + PAUSE_AFTER
    ffmpeg("-loop", "1", "-i", str(png), "-i", str(mp3),
           "-t", f"{dur:.2f}",
           "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", str(out))


async def build(lesson_path: str):
    lesson = json.loads(Path(lesson_path).read_text(encoding="utf-8"))
    items = lesson["items"]
    bdir = Path("build") / Path(lesson_path).stem
    if bdir.exists():
        shutil.rmtree(bdir)
    adir = bdir / "audio"
    sdir = bdir / "slides"
    cdir = bdir / "clips"
    shdir = bdir / "shorts"
    for p in (adir, sdir, cdir, shdir):
        p.mkdir(parents=True)

    silence = adir / "_pause.mp3"
    make_silence(silence)
    clips = []
    n = len(items)
    mascot = lesson.get("mascot", "🦉")
    tlang = lesson.get("target_lang", "ar")   # ar / en — язык изучения
    lang_label = {"ar": "по-арабски", "en": "по-английски"}.get(tlang, "")
    bye = {"ar": "مَعَ السَّلَامَة!", "en": "Goodbye, my friends!"}.get(tlang, "")
    hashtags = lesson.get("hashtags",
                          "#арабский #арабскийязык #учимарабский" if tlang == "ar"
                          else "#английский #английскийязык #учиманглийский")

    # --- Титул: коротко и бодро ---
    print("[титул]")
    draw_cover(lesson, sdir / "00_title.png", "Сегодня учим:", lesson["topic"], mascot)
    a = await slide_audio(
        [("ru", f'Ассаляму алейкум, друзья! С вами {lesson["teacher"]}. '
                f'Сегодня учим: {lesson["topic"]}! '
                f'Слушай внимательно и повторяй за мной вслух. Поехали!', False)],
        adir, "00_title", lesson, silence)
    clip(sdir / "00_title.png", a, cdir / "00.mp4")
    clips.append(cdir / "00.mp4")

    # --- Одно слово = одна яркая сцена ---
    for i, item in enumerate(items):
        print(f'[{i + 1}/{n}] {item["ru"]}')
        png = sdir / f"{i + 1:02d}.png"
        draw_item(item, i, n, lesson, png)
        word = item_word(item)
        segs = [
            ("ru", f'{item["ru"]}!', False),
            (tlang, word, True),
            ("ru", f'{item["tr"]}. Ещё раз, медленно:', False),
            (tlang, word, True),
            ("ru", "Теперь ты! Скажи вслух:", False),
            ("pause", "", False),
            (tlang, word, False),
            ("ru", "Молодец!", False),
        ]
        a = await slide_audio(segs, adir, f"item{i:02d}", lesson, silence)
        c = cdir / f"{i + 1:02d}.mp4"
        clip(png, a, c)
        clips.append(c)

        # Вертикальная версия той же сцены -> отдельный шортс
        vpng = shdir / f"{i + 1:02d}.png"
        draw_item(item, i, n, lesson, vpng, vertical=True)
        clip(vpng, a, shdir / f'{i + 1:02d}_{item["tr"]}.mp4')
        (shdir / f'{i + 1:02d}_{item["tr"]}.txt').write_text(
            f'{item["ru"].capitalize()} {lang_label} — {item["tr"]} {item["emoji"]}\n'
            f'{lesson["course"]}, урок {lesson["lesson_number"]}. Полный урок — на канале!\n'
            f'{hashtags}',
            encoding="utf-8")

    # --- Игра: вспомни слово (3 случайных) ---
    print("[игра]")
    quiz = random.sample(items, min(3, n))
    draw_cover(lesson, sdir / "90_quiz.png", "Игра!", "Что это значит?", "🎮",
               accent=ACCENTS[3])
    segs = [("ru", "А теперь — игра! Я говорю слово по-арабски, а ты вспоминай перевод. Готова?", False)]
    for q in quiz:
        segs += [(tlang, item_word(q), True), ("pause", "", False),
                 ("ru", f'Правильно: {q["ru"]}!', False)]
    segs.append(("ru", "Умница! Машаллах!", False))
    a = await slide_audio(segs, adir, "90_quiz", lesson, silence)
    clip(sdir / "90_quiz.png", a, cdir / "90.mp4")
    clips.append(cdir / "90.mp4")

    # --- Финал ---
    print("[финал]")
    draw_cover(lesson, sdir / "99_end.png", "Ты молодец!", "До завтра!", "⭐",
               accent=ACCENTS[6])
    a = await slide_audio(
        [("ru", f'На сегодня всё! Ты выучила {n} новых слов — это здорово! '
                f'Повтори их вечером ещё раз. Завтра будет новый урок. '
                f'Подпишись, чтобы не пропустить. С тобой была {lesson["teacher"]}.', False),
         (tlang, bye, False)],
        adir, "99_end", lesson, silence)
    clip(sdir / "99_end.png", a, cdir / "99.mp4")
    clips.append(cdir / "99.mp4")

    # --- Склейка ---
    lst = bdir / "clips_list.txt"
    lst.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in clips),
                   encoding="utf-8")
    final = bdir / "lesson.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(final))
    print(f"\nГотово: {final}")
    print(f"Шортсы: {shdir} ({n} шт.)")


if __name__ == "__main__":
    asyncio.run(build(sys.argv[1] if len(sys.argv) > 1 else "v2_colors.json"))
