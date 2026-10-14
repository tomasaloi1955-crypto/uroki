# -*- coding: utf-8 -*-
"""
Видео-презентация курса «Алфавит + таджвид» голосом преподавателя
(voice/prezentaciya.*). Тот же стиль, что у длинных серий (long_video.py).
В описании длинного видео ссылки кликаются — поэтому его ставят
«Похожим видео» под шортсами (вручную в YouTube Studio).

    python promo_video.py           # собрать build/long/promo.mp4
    python promo_video.py upload    # собрать и загрузить на YouTube
"""

import os
import sys
from pathlib import Path

import long_video as lv
from promo import check_url, course_url, tariffs
from teacher_voice import scene_voices

TITLE = "Научись читать Коран с нуля: курс «Алфавит + таджвид»"

SCENES = [
    dict(theme="arabic calligraphy", title="Arabic for Everyone",
         ar_big="السَّلَامُ عَلَيْكُمْ", sub="Ассаляму алейкум!",
         speech="Ассаляму алейкум! Меня зовут, и на этом канале мы вместе учим арабский."),
    dict(theme="quran", title="Хочешь читать Коран?",
         sub="Буквы непонятные, а ошибки без таджвида меняют смысл",
         speech="Многие мечтают читать Коран, но не знают, с чего начать: буквы "
                "непонятные, а читать без таджвида — значит делать ошибки, "
                "которые меняют смысл."),
    dict(theme="open book", title="Курс «Алфавит + таджвид»",
         ar_big="الْمُعَلِّمُ الثَّانِي", sub="По книге «Муаллим сани» — для тех, кто не знает ни одной буквы",
         speech="Поэтому я сделала курс «Алфавит плюс таджвид» по книге «Муаллим "
                "сани». Он для тех, кто не знает ни одной буквы."),
    dict(theme="arabic letters", title="Что внутри",
         ar_big="أ ب ت ث", sub="Алфавит, огласовки, соединение букв → таджвид шаг за шагом",
         speech="Сначала мы учим арабский алфавит: каждую букву, огласовки и как "
                "буквы соединяются. Потом переходим к таджвиду и шаг за шагом "
                "учимся читать правильно."),
    dict(theme="student studying", title="Два тарифа",
         sub="1) Самостоятельно — все видеоуроки и материалы, в своём темпе.  "
             "2) С проверкой ДЗ — присылаешь чтение, я исправляю каждую ошибку",
         speech="Есть два варианта. Первый — самостоятельно: вы получаете все "
                "видеоуроки и материалы и занимаетесь в своём темпе. Второй — с "
                "проверкой домашних заданий: вы присылаете мне запись своего "
                "чтения, я слушаю и исправляю каждую ошибку. Так прогресс идёт "
                "гораздо быстрее."),
    dict(theme="mosque sunrise", title="Ссылки — в описании и в шапке канала",
         sub=f"Самостоятельно: {course_url().split('://')[-1]}   "
             f"С проверкой ДЗ: {(check_url() or course_url()).split('://')[-1]}",
         speech="Ссылки на оба тарифа — в описании под этим видео и в шапке "
                "канала. Выбирайте свой вариант, и давайте начнём читать Коран "
                "правильно уже сегодня!"),
]


def build() -> Path:
    work = lv.OUT_DIR / "work_promo"
    work.mkdir(parents=True, exist_ok=True)
    if not scene_voices("prezentaciya", SCENES, work):
        raise SystemExit("Нет записи voice/prezentaciya.*")
    clips = [lv.build_scene_clip(s, i, work, {}) for i, s in enumerate(SCENES)]
    lst = work / "concat.txt"
    lst.write_text("\n".join(f"file '{c.resolve().as_posix()}'" for c in clips),
                   encoding="utf-8")
    out = lv.OUT_DIR / "promo.mp4"
    lv.ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst),
              "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "160k", str(out))
    print(f"Готово: {out} ({lv.probe_duration(out):.0f} сек)")
    return out


def description() -> str:
    return ("📖 Курс «Алфавит + таджвид» по книге «Муаллим сани» — "
            "научись читать Коран с нуля.\n\n" + tariffs() +
            "\nСначала алфавит: буквы, огласовки, соединение. Потом таджвид — "
            "шаг за шагом, до правильного чтения.\n\n"
            "#арабский #таджвид #коран #арабскийснуля #муаллимсани")


if __name__ == "__main__":
    video = build()
    if sys.argv[1:] == ["upload"]:
        from social_post import yt_upload
        yt_upload(video, TITLE, description(),
                  ["таджвид", "арабский алфавит", "курс таджвида",
                   "муаллим сани", "чтение корана"],
                  os.environ.get("PROMO_PUBLISH_AT") or None)
