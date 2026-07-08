# -*- coding: utf-8 -*-
"""
Пилотный пайплайн видеоурока: JSON -> слайды -> озвучка -> видео.

Запуск:
    pip install edge-tts pillow
    python make_lesson.py lesson_001.json

Требуется установленный FFmpeg (ffmpeg.org, или: winget install ffmpeg).
Результат: папка build/<номер урока>/lesson.mp4
"""

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Поддержка арабской вязи: буквы соединяются и пишутся справа-налево.
# pip install arabic-reshaper python-bidi
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    # delete_harakat=False: сохраняем огласовки (фатха, кясра, дамма) —
    # для обучающего курса они обязательны
    RESHAPER = arabic_reshaper.ArabicReshaper({"delete_harakat": False})
    HAS_ARABIC = True
except ImportError:
    HAS_ARABIC = False


def prep_text(s: str) -> str:
    """Готовит строку к отрисовке в PIL: арабские куски — вязь + RTL."""
    if HAS_ARABIC and any("؀" <= ch <= "ۿ" for ch in s):
        # base_dir='L': строка идёт слева-направо (наши подписи на русском),
        # а арабские куски внутри неё корректно собираются в вязь RTL
        return get_display(RESHAPER.reshape(s), base_dir="L")
    return s

# ---------- НАСТРОЙКИ ОФОРМЛЕНИЯ ----------
W, H = 1280, 720
BG = (250, 247, 240)        # тёплый кремовый фон
HEADER = (14, 87, 62)       # тёмно-зелёный
GOLD = (191, 149, 63)       # золотой акцент
TEXT = (40, 40, 40)
PAUSE_AFTER_SLIDE = 1.0     # пауза (сек) в конце каждого слайда

# Шрифты: подставь свои пути, если эти не найдутся
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
FONT_REG_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def pick_font(candidates, size):
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def draw_slide(slide, lesson, out_path: Path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # Шапка
    d.rectangle([0, 0, W, 110], fill=HEADER)
    f_head = pick_font(FONT_CANDIDATES, 42)
    d.text((50, 30), prep_text(slide["title"]), font=f_head, fill=(255, 255, 255))

    # Золотая полоса под шапкой
    d.rectangle([0, 110, W, 118], fill=GOLD)

    # Основной текст (размер: у слайда приоритет, потом у урока)
    body_size = slide.get("body_size", lesson.get("body_size", 40))
    f_body = pick_font(FONT_REG_CANDIDATES, body_size)
    y = 190
    for line in slide["lines"]:
        d.text((80, y), prep_text(line), font=f_body, fill=TEXT)
        y += int(body_size * 1.95)

    # Подвал: курс + учитель + номер урока
    f_foot = pick_font(FONT_REG_CANDIDATES, 26)
    footer = f'{lesson["course"]}  ·  Урок {lesson["lesson_number"]}  ·  {lesson["teacher"]}'
    d.rectangle([0, H - 70, W, H], fill=HEADER)
    d.text((50, H - 52), footer, font=f_foot, fill=(230, 230, 230))

    img.save(out_path)


async def tts_segment(text: str, voice: str, out_path: Path):
    import edge_tts
    communicate = edge_tts.Communicate(text.strip(), voice)
    await communicate.save(str(out_path))


def ffmpeg(*args):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *args]
    subprocess.run(cmd, check=True)


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


async def build(lesson_path: str):
    lesson = json.loads(Path(lesson_path).read_text(encoding="utf-8"))
    build_dir = Path("build") / Path(lesson_path).stem
    if build_dir.exists():
        shutil.rmtree(build_dir)
    (build_dir / "audio").mkdir(parents=True)
    (build_dir / "slides").mkdir()
    (build_dir / "clips").mkdir()

    slide_videos = []

    for i, slide in enumerate(lesson["slides"], 1):
        print(f'[{i}/{len(lesson["slides"])}] Слайд {slide["id"]} ...')

        # 1) Картинка слайда
        slide_png = build_dir / "slides" / f'{slide["id"]}.png'
        draw_slide(slide, lesson, slide_png)

        # 2) Озвучка: каждый сегмент своим голосом (ru/en), потом склейка
        seg_files = []
        for j, seg in enumerate(slide["speech"]):
            # Голос по языку сегмента: voice_ru / voice_en / voice_ar из JSON
            voice = lesson[f'voice_{seg["lang"]}']
            seg_mp3 = build_dir / "audio" / f'{slide["id"]}_{j:02d}.mp3'
            await tts_segment(seg["text"], voice, seg_mp3)
            seg_files.append(seg_mp3)

        concat_list = build_dir / "audio" / f'{slide["id"]}_list.txt'
        concat_list.write_text(
            "\n".join(f"file '{p.resolve().as_posix()}'" for p in seg_files),
            encoding="utf-8",
        )
        slide_mp3 = build_dir / "audio" / f'{slide["id"]}.mp3'
        ffmpeg("-f", "concat", "-safe", "0", "-i", str(concat_list),
               "-c:a", "libmp3lame", "-q:a", "3", str(slide_mp3))

        # 3) Слайд + звук -> видеоклип (плюс пауза в конце)
        dur = audio_duration(slide_mp3) + PAUSE_AFTER_SLIDE
        clip = build_dir / "clips" / f'{slide["id"]}.mp4'
        ffmpeg("-loop", "1", "-i", str(slide_png), "-i", str(slide_mp3),
               "-t", f"{dur:.2f}",
               "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k",
               str(clip))
        slide_videos.append(clip)

    # 4) Склейка всех клипов в финальный урок
    final_list = build_dir / "clips_list.txt"
    final_list.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in slide_videos),
        encoding="utf-8",
    )
    final = build_dir / "lesson.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", str(final_list),
           "-c", "copy", str(final))

    print(f"\nГотово: {final}")
    print("Дальше: залить на VK Видео / Rutube / YouTube, в ТГ — пост со ссылкой.")


if __name__ == "__main__":
    lesson_file = sys.argv[1] if len(sys.argv) > 1 else "lesson_001.json"
    asyncio.run(build(lesson_file))
