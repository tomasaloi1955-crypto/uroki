# -*- coding: utf-8 -*-
"""
Вертикальные нарезки (9:16) для TikTok / YouTube Shorts / VK Клипов.

Из одного урока делает несколько коротких роликов: один содержательный
слайд = один ролик. Озвучка переиспользуется из build/<урок>/audio,
если урок уже собирался; иначе генерируется заново.

Запуск:
    python make_shorts.py lesson_001.json
    python make_shorts.py arabic_001.json

Результат: build/<урок>/shorts/*.mp4 + рядом .txt с подписью для поста.
"""

import asyncio
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from make_lesson import (
    BG, GOLD, HEADER, PAUSE_AFTER_SLIDE, TEXT,
    FONT_CANDIDATES, FONT_REG_CANDIDATES,
    audio_duration, ffmpeg, pick_font, prep_text, tts_segment,
)

SW, SH = 1080, 1920

# Слайды-обвязка в нарезки не идут: без контекста урока они не нужны
SKIP_SUFFIXES = ("title", "task", "end")


def fit_font(d, lines, candidates, start_size, max_w):
    """Подбирает размер шрифта, чтобы самая длинная строка влезла."""
    size = start_size
    while size > 28:
        f = pick_font(candidates, size)
        if all(d.textlength(prep_text(l), font=f) <= max_w for l in lines):
            return f, size
        size -= 4
    return pick_font(candidates, 28), 28


def draw_vertical(slide, lesson, out_path: Path):
    img = Image.new("RGB", (SW, SH), BG)
    d = ImageDraw.Draw(img)

    # Шапка
    d.rectangle([0, 0, SW, 240], fill=HEADER)
    f_head, _ = fit_font(d, [slide["title"]], FONT_CANDIDATES, 64, SW - 100)
    d.text((SW // 2, 120), prep_text(slide["title"]),
           font=f_head, fill=(255, 255, 255), anchor="mm")
    d.rectangle([0, 240, SW, 252], fill=GOLD)

    # Основной текст — по центру свободной зоны
    f_body, body_size = fit_font(d, slide["lines"], FONT_REG_CANDIDATES, 60, SW - 120)
    lh = int(body_size * 2.1)
    total_h = lh * len(slide["lines"])
    y = 320 + (1280 - total_h) // 2
    for line in slide["lines"]:
        d.text((SW // 2, y + lh // 2), prep_text(line),
               font=f_body, fill=TEXT, anchor="mm")
        y += lh

    # Призыв + подвал
    f_cta = pick_font(FONT_CANDIDATES, 40)
    d.text((SW // 2, 1680), "Полный урок — на канале",
           font=f_cta, fill=GOLD, anchor="mm")
    d.rectangle([0, SH - 160, SW, SH], fill=HEADER)
    f_foot = pick_font(FONT_REG_CANDIDATES, 34)
    footer = f'{lesson["course"]}  ·  Урок {lesson["lesson_number"]}  ·  {lesson["teacher"]}'
    d.text((SW // 2, SH - 80), footer, font=f_foot, fill=(230, 230, 230), anchor="mm")

    img.save(out_path)


async def ensure_audio(slide, lesson, audio_dir: Path) -> Path:
    """Берёт готовую озвучку слайда или генерирует её заново."""
    slide_mp3 = audio_dir / f'{slide["id"]}.mp3'
    if slide_mp3.exists():
        return slide_mp3

    audio_dir.mkdir(parents=True, exist_ok=True)
    seg_files = []
    for j, seg in enumerate(slide["speech"]):
        voice = lesson[f'voice_{seg["lang"]}']
        seg_mp3 = audio_dir / f'{slide["id"]}_{j:02d}.mp3'
        await tts_segment(seg["text"], voice, seg_mp3)
        seg_files.append(seg_mp3)

    concat_list = audio_dir / f'{slide["id"]}_list.txt'
    concat_list.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in seg_files),
        encoding="utf-8",
    )
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(concat_list),
           "-c:a", "libmp3lame", "-q:a", "3", str(slide_mp3))
    return slide_mp3


def caption_for(slide, lesson) -> str:
    """Текст подписи для поста: заголовок + хештеги."""
    if "voice_ar" in lesson:
        tags = "#арабский #арабскийязык #арабскийснуля #учимарабский #алфавит"
    else:
        tags = "#английский #английскийязык #английскийснуля #учиманглийский"
    return (f'{slide["title"]} · {lesson["course"]}, урок {lesson["lesson_number"]}.\n'
            f'Учитель: {lesson["teacher"]}. Полный урок — на канале.\n{tags}')


async def build_shorts(lesson_path: str):
    lesson = json.loads(Path(lesson_path).read_text(encoding="utf-8"))
    build_dir = Path("build") / Path(lesson_path).stem
    shorts_dir = build_dir / "shorts"
    shorts_dir.mkdir(parents=True, exist_ok=True)

    made = []
    for slide in lesson["slides"]:
        if slide["id"].endswith(SKIP_SUFFIXES):
            continue
        print(f'Ролик: {slide["id"]} ...')

        png = shorts_dir / f'{slide["id"]}.png'
        draw_vertical(slide, lesson, png)

        mp3 = await ensure_audio(slide, lesson, build_dir / "audio")

        dur = audio_duration(mp3) + PAUSE_AFTER_SLIDE
        clip = shorts_dir / f'{slide["id"]}.mp4'
        ffmpeg("-loop", "1", "-i", str(png), "-i", str(mp3),
               "-t", f"{dur:.2f}",
               "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k",
               str(clip))

        (shorts_dir / f'{slide["id"]}.txt').write_text(
            caption_for(slide, lesson), encoding="utf-8")
        made.append((clip, dur))

    print(f"\nГотово, роликов: {len(made)} — в папке {shorts_dir}")
    for clip, dur in made:
        print(f"  {clip.name}  ({dur:.0f} сек)")


if __name__ == "__main__":
    lesson_file = sys.argv[1] if len(sys.argv) > 1 else "lesson_001.json"
    asyncio.run(build_shorts(lesson_file))
