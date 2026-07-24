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
import time
from pathlib import Path

from PIL import Image, ImageDraw

from shorts_v2 import (
    GOLD, FONT_BOLD, FONT_REG, FONT_AR, UA,
    ar_text, pick_font, strip_accents, wrap_to_width,
    ffmpeg, probe_duration, elevenlabs_tts,
    commons_image_urls, download_head,
)

LW, LH = 1920, 1080
OUT_DIR = Path("build") / "long"
DARK = (8, 20, 15)
HEADER_H = 190


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
                        "по-арабски. Готов? Тогда начинаем первый урок курса!"),
            dict(theme="arabic calligraphy",
                 title="Мединский курс · Урок 1",
                 sub="Хаза и Хазихи — «это» по-арабски",
                 speech="Здравствуй! Сегодня — фундамент арабской "
                        "грамматики: указательные местоимения хаза и "
                        "хазихи. Оба значат «это», но используются по "
                        "разному — в зависимости от рода слова. Сейчас всё "
                        "станет понятно."),
            dict(theme="old books",
                 title="Хаза — для мужского рода",
                 ar_big="هذا",
                 sub="Хаза — «это» (про предметы мужского рода)",
                 speech="Слово хаза пишется هذا и переводится «это». Хаза "
                        "используется, когда предмет, о котором мы "
                        "говорим — мужского рода. Запомни одно это слово — "
                        "и ты уже можешь строить предложения!"),
            dict(theme="old city street",
                 title="Хаза + существительное",
                 lines=[("هذا بيت", "Хаза бейт — Это дом"),
                        ("هذا كتاب", "Хаза китаб — Это книга")],
                 speech="Хаза бейт — это дом. Хаза китаб — это книга. "
                        "Повтори вслух: хаза бейт. Хаза китаб."),
            dict(theme="arabic manuscript",
                 title="Хаза + существительное",
                 lines=[("هذا قلم", "Хаза калям — Это ручка"),
                        ("هذا باب", "Хаза баб — Это дверь")],
                 speech="Ещё два слова. Хаза калям — это ручка. Хаза баб — "
                        "это дверь. Повтори: хаза калям. Хаза баб."),
            dict(theme="souk market",
                 title="Спроси: «Что это?»",
                 ar_big="ما هذا؟",
                 sub="Ма хаза? — Что это? (про мужской род)",
                 speech="Хочешь спросить «что это»? Скажи: ма хаза? Ответ "
                        "строится так же: хаза бейт — это дом. Попробуй "
                        "сам, вслух: ма хаза?"),
            dict(theme="rose garden",
                 title="Хазихи — для женского рода",
                 ar_big="هذه",
                 sub="Хазихи — «это» (про предметы женского рода)",
                 speech="Теперь слово хазихи, пишется هذه. Оно тоже значит "
                        "«это», но для слов женского рода. Как понять, что "
                        "слово женского рода? Чаще всего на конце — округлая "
                        "буква та марбута. Сейчас увидишь на примерах."),
            dict(theme="desert road driving",
                 title="Хазихи + существительное",
                 lines=[("هذه سيارة", "Хазихи сайяра — Это машина"),
                        ("هذه مدرسة", "Хазихи мадраса — Это школа")],
                 speech="Хазихи сайяра — это машина. Хазихи мадраса — это "
                        "школа. Повтори: хазихи сайяра. Хазихи мадраса."),
            dict(theme="flower field",
                 title="Хазихи + существительное",
                 lines=[("هذه شجرة", "Хазихи шаджара — Это дерево"),
                        ("هذه وردة", "Хазихи варда — Это цветок")],
                 speech="И ещё два слова. Хазихи шаджара — это дерево. "
                        "Хазихи варда — это цветок. Повтори: хазихи "
                        "шаджара. Хазихи варда."),
            dict(theme="morocco market",
                 title="Спроси: «Что это?»",
                 ar_big="ما هذه؟",
                 sub="Ма хазихи? — Что это? (про женский род)",
                 speech="А для женского рода вопрос звучит так: ма "
                        "хазихи? Например: ма хазихи? Хазихи сайяра. "
                        "Попробуй сам: ма хазихи?"),
            dict(theme="medina morocco",
                 title="Живой диалог",
                 lines=[("ما هذا؟", "— Ма хаза?"),
                        ("هذا كتاب", "— Хаза китаб.")],
                 speech="Давай разыграем короткий диалог. Вопрос: ма хаза? "
                        "Ответ: хаза китаб. Ма хаза? Хаза китаб. Именно "
                        "так звучит живой разговор!"),
            dict(theme="camel desert",
                 title="Проверь себя!",
                 sub="Как сказать «это цветок»?",
                 lines=[("هذه وردة", "Хазихи варда")],
                 speech="Проверим, что запомнилось. Как сказать «это "
                        "цветок»? Поставь на паузу и попробуй ответить "
                        "сам… Готово? Правильный ответ: хазихи варда."),
            dict(theme="desert sunset",
                 title="Проверь себя!",
                 sub="Как сказать «это книга»?",
                 lines=[("هذا كتاب", "Хаза китаб")],
                 speech="Следующий вопрос. Как сказать «это книга»? "
                        "Пауза… Ответ: хаза китаб."),
            dict(theme="arabic coffee",
                 title="Проверь себя!",
                 sub="Хаза или Хазихи: مدرسة — школа?",
                 lines=[("هذه مدرسة", "Хазихи мадраса")],
                 speech="И последний вопрос, самый хитрый. Хаза или "
                        "хазихи — со словом мадраса, школа? Пауза… "
                        "Правильно — хазихи, потому что мадраса женского "
                        "рода: хазихи мадраса."),
            dict(theme="desert sunset",
                 title="Ты справился!",
                 bullets=[("هذا", "Хаза — это (муж. род)"),
                          ("هذه", "Хазихи — это (жен. род)"),
                          ("ما هذا؟ / ما هذه؟", "Что это?")],
                 speech="Отличная работа! Сегодня ты выучил два главных "
                        "слова арабского языка: хаза — для мужского рода, "
                        "и хазихи — для женского. И научился спрашивать: "
                        "ма хаза, ма хазихи. В следующей серии — "
                        "считаем предметы от одного до десяти. "
                        "Подписывайся, чтобы не пропустить! Увидимся в "
                        "следующем уроке."),
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

def build_scene_clip(scene: dict, idx: int, work: Path) -> Path:
    voice = work / f"voice_{idx:02d}.mp3"
    if not voice.exists():
        elevenlabs_tts(strip_accents(scene["speech"]), voice)
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
    ep = EPISODES[n]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    work = OUT_DIR / f"work_{n:02d}"
    work.mkdir(exist_ok=True)
    print(f"Эпизод {n}: {ep['title']}")

    clips = []
    for i, scene in enumerate(ep["scenes"]):
        print(f"  сцена {i + 1}/{len(ep['scenes'])}: "
              f"{scene.get('title') or scene.get('sub') or scene['theme']}")
        clips.append(build_scene_clip(scene, i, work))

    lst = work / "concat.txt"
    lst.write_text("\n".join(f"file '{c.resolve().as_posix()}'" for c in clips),
                   encoding="utf-8")
    out = OUT_DIR / f"episode_{n:02d}.mp4"
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
