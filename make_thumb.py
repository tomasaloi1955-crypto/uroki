# -*- coding: utf-8 -*-
"""
Обложки для YouTube на основе фирменной обложки канала
(«обложка арабск алфавит ютуб.png»): ведущая и стиль сохраняются,
меняются цвета фона и текст под каждый урок.

Запуск:  python make_thumb.py arabic_002.json
Результат: build/<урок>/thumb.jpg (подхватывается автопостингом)
"""

import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from make_lesson import prep_text

W, H = 1280, 720
BASE = Path(__file__).parent / "обложка арабск алфавит ютуб.png"

F_BOLD = "C:/Windows/Fonts/arialbd.ttf"
import platform
if platform.system() != "Windows":
    F_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_ARABIC = F_BOLD if platform.system() == "Windows" else \
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"

YELLOW = (255, 214, 0)
DARKLINE = (12, 10, 22)
# Пары цветов фона (клин + основа) — на каждом уроке своя
COLOR_PAIRS = [
    ((255, 122, 0), (18, 79, 168)),    # оранжевый / синий (как оригинал)
    ((155, 93, 229), (24, 20, 80)),    # фиолетовый / тёмно-синий
    ((0, 176, 155), (10, 60, 70)),     # бирюзовый / морской
    ((235, 40, 90), (60, 10, 60)),     # малиновый / сливовый
    ((250, 160, 0), (120, 30, 10)),    # золотой / кирпичный
    ((60, 170, 60), (10, 70, 50)),     # зелёный / хвойный
]
LETTER_COLORS = [(255, 214, 0), (0, 220, 130), (80, 190, 255),
                 (255, 105, 180), (255, 140, 60), (200, 120, 255)]
AR_LETTERS = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def fit_size(d, text, path, max_w, start=120, floor=44):
    size = start
    while size > floor and d.textlength(text, font=font(path, size)) > max_w:
        size -= 4
    return size


def title_lines(lesson):
    topic = lesson["topic"].split(" / ")[0].split(" — ")[0].upper()
    words = topic.split()
    if len(words) <= 2:
        # короткая тема -> добавляем ударную вторую строку
        second = "ПО-АНГЛИЙСКИ!" if lesson.get("target_lang") == "en" else "ПО-АРАБСКИ!"
        return [topic, second]
    mid = (len(words) + 1) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]


def scatter_letters(img, rng, x_max):
    for _ in range(8):
        size = rng.randint(45, 90)
        f = font(F_ARABIC, size)
        ch = rng.choice(AR_LETTERS)
        x = rng.randint(20, x_max - 80)
        y = rng.choice([rng.randint(8, 70), rng.randint(H - 150, H - 80)])
        tile = Image.new("RGBA", (size * 2, size * 2), (0, 0, 0, 0))
        td = ImageDraw.Draw(tile)
        td.text((size, size), prep_text(ch), font=f,
                fill=rng.choice(LETTER_COLORS) + (255,),
                stroke_width=max(4, size // 12), stroke_fill=DARKLINE + (255,),
                anchor="mm")
        tile = tile.rotate(rng.randint(-25, 25), resample=Image.BICUBIC)
        img.paste(tile, (x - size, y - size), tile)


def make_thumb(lesson_path: str, out: Path | None = None):
    lesson = json.loads(Path(lesson_path).read_text(encoding="utf-8"))
    n = lesson["lesson_number"]
    rng = random.Random(n)
    wedge, base_c = COLOR_PAIRS[(n - 1) % len(COLOR_PAIRS)]

    img = Image.new("RGB", (W, H), base_c)
    d = ImageDraw.Draw(img)
    # левый цветной клин, как на фирменной обложке
    d.polygon([(0, 0), (620, 0), (360, H), (0, H)], fill=wedge)

    # Ведущая: правая часть фирменной обложки, без зоны старого текста
    if BASE.exists():
        base = Image.open(BASE).convert("RGB")
        bw, bh = base.size
        crop = base.crop((int(bw * 0.60), 0, bw, bh))   # ведущая + алиф, без старого текста
        scale = H / crop.height
        crop = crop.resize((int(crop.width * scale), H))
        img.paste(crop, (W - crop.width, 0))
        d = ImageDraw.Draw(img)

    scatter_letters(img, rng, x_max=520)
    d = ImageDraw.Draw(img)

    # Заголовок (1-2 строки): белая + жёлтая, чёрная обводка — как на образце
    lines = title_lines(lesson)
    y = 130
    for i, line in enumerate(lines):
        size = fit_size(d, line, F_BOLD, 600, start=132)
        d.text((60, y), line, font=font(F_BOLD, size),
               fill=(255, 255, 255) if i == 0 else YELLOW,
               stroke_width=max(8, size // 9), stroke_fill=DARKLINE)
        y += size + 30

    # Подзаголовок «ЗА N МИНУТ!» в духе оригинала — по длительности незачем врать,
    # ставим номер урока крупным бейджем
    badge = f"УРОК {n}"
    bsize = 62
    bw_ = int(d.textlength(badge, font=font(F_BOLD, bsize))) + 76
    d.rounded_rectangle([60, H - 180, 60 + bw_, H - 72], 30,
                        fill=(225, 30, 45), outline=DARKLINE, width=7)
    d.text((60 + bw_ // 2, H - 126), badge, font=font(F_BOLD, bsize),
           fill=(255, 255, 255), anchor="mm")

    # жёлтая рамка по краю — фирменный элемент
    d.rectangle([0, 0, W - 1, H - 1], outline=YELLOW, width=12)

    out = out or Path("build") / Path(lesson_path).stem / "thumb.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=90)
    print(f"Обложка: {out}")
    return out


if __name__ == "__main__":
    make_thumb(sys.argv[1] if len(sys.argv) > 1 else "arabic_002.json")
