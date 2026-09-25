# -*- coding: utf-8 -*-
"""
Оформление канала: баннер, значок и описание — в фирменных цветах роликов
(тёмно-зелёный фон, золото, арабская вязь), без людей и без ИИ-картинок.

    python make_brand.py es      # испанский канал
    python make_brand.py en      # английский

Размеры по требованиям YouTube:
  баннер 2560x1440, безопасная зона 1546x423 по центру — она видна на
  телефоне, всё важное только в ней;
  значок 800x800 (показывается кругом, поэтому запас по краям).
Результат: build/brand_<код>/banner.png, avatar.png, descripcion.txt
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from shorts_v2 import ar_text, pick_font, FONT_AR, FONT_BOLD, FONT_REG, GOLD

DARK = (8, 30, 22)
DARK2 = (5, 20, 15)
CREAM = (243, 233, 210)

BRAND = {
    "es": dict(
        channel="Árabe Fácil",
        arabic="الْعَرَبِيَّة",
        tagline="Una palabra árabe al día",
        bullets=["Palabras · Frases · Cultura", "Nuevos vídeos cada día"],
        description="""¡Bienvenido a Árabe Fácil!

Aquí aprendes árabe con vídeos cortos de menos de un minuto: una palabra
o una frase al día, con su escritura, su pronunciación real por una voz
nativa y su significado en español.

Qué vas a encontrar:
• Palabras del día: casa, agua, luna, corazón, café.
• Frases para viajar: ¿dónde?, ¿cuánto cuesta?, no entiendo, gracias.
• Saludos y cortesía: marhaba, shukran, as-salamu alaykum.
• Ya hablas árabe: azúcar, aceite, ojalá, naranja, almohada, álgebra,
  arroz, azafrán... el español tiene miles de palabras de origen árabe
  y aquí descubrirás de dónde vienen.

No hace falta saber nada de antemano. Empieza por cualquier vídeo,
repite en voz alta y en un mes tendrás tus primeras cien palabras.

Nuevos vídeos todos los días. Suscríbete y aprende árabe sin esfuerzo.""",
    ),
    "en": dict(
        channel="Easy_arabic",
        arabic="الْعَرَبِيَّة",
        tagline="One Arabic word a day",
        bullets=["Words · Phrases · Culture", "New videos every day"],
        description="""Welcome to Easy Arabic!

Learn Arabic in under a minute a day: one word or phrase at a time, with
the Arabic script, real pronunciation by a native voice, and the meaning
in plain English.

What you get:
• Word of the day: house, water, moon, heart, coffee.
• Travel phrases: where?, how much?, I don't understand, thank you.
• Greetings: marhaba, shukran, as-salamu alaykum.
• You already speak Arabic: sugar, coffee, giraffe, algebra, zero,
  cotton, lemon — English borrowed them all from Arabic.

No prior knowledge needed. Start anywhere, repeat out loud, and in a
month you will have your first hundred words.

New videos every day. Subscribe and learn Arabic the easy way.""",
    ),
}


def girih(draw, w, h, step=150):
    """Восьмиконечные звёзды — геометрический исламский орнамент.
    Рисуем кодом, никаких ИИ-картинок и никаких людей."""
    r = step * 0.46
    for cy in range(-step, h + step, step):
        for cx in range(-step, w + step, step):
            pts = []
            for i in range(16):
                a = math.pi * i / 8 - math.pi / 16
                rad = r if i % 2 == 0 else r * 0.42
                pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
            draw.polygon(pts, outline=GOLD + (34,))
            draw.line(pts + [pts[0]], fill=GOLD + (30,), width=2)


def backdrop(w, h):
    """Тёмно-зелёный фон с мягким золотым свечением по центру."""
    img = Image.new("RGBA", (w, h), DARK2)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse([w * 0.18, -h * 0.35, w * 0.82, h * 1.35],
              fill=(30, 74, 56, 255))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(w // 12)))
    pattern = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    girih(ImageDraw.Draw(pattern), w, h, step=max(110, w // 16))
    img.alpha_composite(pattern)
    return img


def banner(code):
    b = BRAND[code]
    W, H = 2560, 1440
    img = backdrop(W, H)
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2          # безопасная зона 1546x423 по центру

    # арабская вязь крупно — главный образ канала
    f_ar = pick_font(FONT_AR, 170)
    d.text((cx, cy - 110), ar_text(b["arabic"]), font=f_ar, fill=GOLD,
           anchor="mm", stroke_width=4, stroke_fill=DARK)

    f_name = pick_font(FONT_BOLD, 118)
    d.text((cx, cy + 20), b["channel"].upper(), font=f_name, fill=CREAM,
           anchor="mm", stroke_width=3, stroke_fill=DARK)

    # две короткие черты по бокам подписи — линия во всю ширину
    # перечёркивала текст
    for sign in (-1, 1):
        d.line([(cx + sign * 290, cy + 112), (cx + sign * 430, cy + 112)],
               fill=GOLD + (220,), width=4)

    f_tag = pick_font(FONT_REG, 56)
    d.text((cx, cy + 112), b["tagline"], font=f_tag, fill=GOLD, anchor="mm")

    f_small = pick_font(FONT_REG, 40)
    d.text((cx, cy + 178), "   ".join(b["bullets"]), font=f_small,
           fill=(214, 214, 205), anchor="mm")
    return img


def avatar(code):
    b = BRAND[code]
    S = 800
    img = backdrop(S, S)
    d = ImageDraw.Draw(img)
    # значок показывается кругом — держим отступ от краёв
    d.ellipse([28, 28, S - 28, S - 28], outline=GOLD + (230,), width=10)
    f_ar = pick_font(FONT_AR, 430)
    d.text((S // 2, S // 2 - 40), ar_text("ع"), font=f_ar, fill=GOLD,
           anchor="mm", stroke_width=6, stroke_fill=DARK)
    f = pick_font(FONT_BOLD, 74)
    word = "ÁRABE" if code == "es" else "ARABIC"
    d.text((S // 2, S - 150), word, font=f, fill=CREAM, anchor="mm",
           stroke_width=3, stroke_fill=DARK)
    return img


def main():
    code = sys.argv[1] if len(sys.argv) > 1 else "es"
    out = Path("build") / f"brand_{code}"
    out.mkdir(parents=True, exist_ok=True)
    banner(code).convert("RGB").save(out / "banner.png")
    avatar(code).convert("RGB").save(out / "avatar.png")
    (out / "descripcion.txt").write_text(BRAND[code]["description"],
                                         encoding="utf-8")
    print("готово:", out.resolve())


if __name__ == "__main__":
    main()
