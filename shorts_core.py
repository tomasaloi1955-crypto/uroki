# -*- coding: utf-8 -*-
"""
Общая механика роликов «арабский для иностранцев»: фото-фон Wikimedia,
крупное арабское слово, озвучка. Содержание уроков и язык подачи живут
в отдельных модулях (shorts_en.py — английский, shorts_es.py — испанский),
а всё, что чинится один раз для всех каналов, здесь.

Главные уроки, уже учтённые в коде:
  * арабское слово всегда читает носитель (edge-tts Zariyah, -25%),
    а не голос ведущего — иначе бывают ошибки произношения;
  * надписи накладываются с -loop 1, иначе они пропадают на стыке фото;
  * фото с людьми отсекаются дважды: по названию файла и нейросетью
    YuNet по кадру (каскады Хаара ошибались на листве и каллиграфии);
  * промежуточные файлы удаляются сразу — компьютер у владелицы старый.
"""

import re
import unicodedata
import sys
from dataclasses import dataclass, field
from pathlib import Path

import shorts_v2 as v2

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Арабские слова во всех языках читает носитель
AR_VOICE = "ar-SA-ZariyahNeural"
AR_RATE = "-25%"

MODELS = Path("build") / "models"
YUNET = "face_detection_yunet_2023mar.onnx"
YUNET_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
             "face_detection_yunet/" + YUNET)

# Фильтр shorts_v2 пропускал людей и неуместное: проводника-бербера,
# картину «Придворные в розовом саду», могилу с розой, рынки с людьми.
EXTRA_BAD = re.compile(
    r"(?:guide|courtier|lad(?:y|ies)|gentlem[ae]n|grave|tomb|cemetery|"
    r"berber|tuareg|nomad|bedouin|merchant|vendor|seller|tourist|"
    r"market|souk|bazaar|shop|stall|crowd|workers?|"
    r"portrait|painting)", re.IGNORECASE)


@dataclass
class Lang:
    """Язык подачи: содержание уроков и всё, что звучит и пишется."""
    code: str                 # "en", "es"
    channel: str              # название YouTube-канала
    voice: str                # голос ведущего (edge-tts)
    rate: str                 # темп речи
    lessons: dict
    intro: list               # «вот как это звучит по-арабски»
    repeat: list              # «ещё раз»
    meaning_lead: list        # «запомни»
    means: str                # «{слово} означает {перевод}» — шаблон
    ask: list                 # «скажи вслух»
    outro: list               # «молодец!»
    cta_text: str             # плашка внизу кадра
    base_tags: list
    base_hashtags: str
    groups: dict              # тема → (номера уроков, теги, хэштеги)
    default_group: tuple      # теги и хэштеги для остальных уроков
    meaning_tag: str          # шаблон тега «{перевод} по-арабски»
    word_tag: str             # шаблон тега «арабское слово {слово}»
    out_dir: Path = field(init=False)

    def __post_init__(self):
        self.out_dir = Path("build") / f"shorts_{self.code}"


# ---------- фото без людей ----------

_commons_image_urls = v2.commons_image_urls
_kenburns_clip = v2.kenburns_clip


def commons_image_urls(term, limit=8):
    return [u for u in _commons_image_urls(term, limit)
            if not EXTRA_BAD.search(u)]


def _yunet_file():
    MODELS.mkdir(parents=True, exist_ok=True)
    path = MODELS / YUNET
    if not path.exists():
        import urllib.request
        urllib.request.urlretrieve(YUNET_URL, path)
    return str(path)


def has_face(img) -> bool:
    """Ищет лица нейросетью YuNet. Не удалось проверить — считаем, что
    лица нет: отказ проверки не должен останавливать сборку."""
    try:
        import cv2
        data = cv2.imread(str(img))
        if data is None:
            return False
        h, w = data.shape[:2]
        det = cv2.FaceDetectorYN.create(_yunet_file(), "", (w, h),
                                        score_threshold=0.8)
        _, faces = det.detect(data)
        return faces is not None and len(faces) > 0
    except Exception as e:
        print(f"  проверка на лица не сработала: {e}")
    return False


def kenburns_clip(img, seg_dur, out, zoom_in=True):
    if has_face(img):
        print("  фото отклонено: в кадре лицо")
        return False
    return _kenburns_clip(img, seg_dur, out, zoom_in)


v2.commons_image_urls = commons_image_urls
v2.kenburns_clip = kenburns_clip


# ---------- тексты ----------

def split_translit(lesson):
    word, _, meaning = lesson["translit"].partition("—")
    return word.strip().rstrip("!?."), meaning.strip()


def _group(lang, n):
    for nums, tags, hashtags in lang.groups.values():
        if n in nums:
            return tags, hashtags
    return lang.default_group


def tags_for(lang, n):
    word, meaning = split_translit(lang.lessons[n])
    extra, _ = _group(lang, n)
    meaning = meaning.rstrip("?!.")
    own = ([lang.meaning_tag.format(meaning=meaning),
            lang.word_tag.format(word=word.lower())] if meaning else [])
    return lang.base_tags + extra + own


def hashtags_for(lang, n):
    _, meaning = split_translit(lang.lessons[n])
    _, extra = _group(lang, n)
    # свой хэштег — только если перевод это слово или короткая пара слов:
    # из «sí / no» получалось бессмысленное #síno.
    # Диакритику убираем: в поиске чаще пишут без неё (#azucar).
    plain = unicodedata.normalize("NFKD", meaning.lower())
    plain = re.sub(r"[^a-z ]", "", plain).strip()
    # артикль в хэштеге не нужен: было #laalmohada, стало #almohada
    plain = re.sub(r"^(el|la|los|las|un|una|the|a) ", "", plain)
    own = "#" + plain.replace(" ", "") if 0 < len(plain.split()) <= 2 \
        and "/" not in meaning else ""
    return " ".join(x for x in (lang.base_hashtags, extra, own, "#shorts") if x)


def caption_for(lang, n):
    lesson = lang.lessons[n]
    return (f'{lesson["hook"]} · {lesson["ar"]} · {lesson["translit"]}\n'
            f'{lesson["teach"]}\n{lesson["cta"]}\n\n{hashtags_for(lang, n)}')


def tts_plan(lang, n):
    """Сценарий озвучки: речь ведущего, а каждое вхождение транслита
    заменяется на сегмент с настоящим арабским словом."""
    lesson = lang.lessons[n]
    word, meaning = split_translit(lesson)
    s = f'{lesson["hook"]}. {v2._pick(lang.intro, n, 0)}: {word}.'
    s += f' {lesson["teach"]}'
    s += f' {v2._pick(lang.repeat, n, 1)}: {word}.'
    if meaning:
        s += (f' {v2._pick(lang.meaning_lead, n, 2)}: '
              + lang.means.format(word=word, meaning=meaning))
    s += f' {v2._pick(lang.ask, n, 3)}: {word}. {v2._pick(lang.outro, n, 4)}'
    if n % 2 == 0:
        s += f' {lesson["cta"]}'
    return v2.split_word_occurrences(s, word, lesson["ar"])


# ---------- звук ----------

def edge_tts(text, voice, out_mp3: Path, rate=None):
    import asyncio
    import edge_tts as et
    kw = {"rate": rate} if rate else {}
    asyncio.run(et.Communicate(text.strip(), voice, **kw).save(str(out_mp3)))


def synthesize_plan(lang, plan, out_mp3: Path, work: Path):
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
                else:
                    edge_tts(text, lang.voice, raw, rate=lang.rate)
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


# ---------- сборка ----------

def build_short(lang, n: int):
    lesson = lang.lessons[n]
    v2.CTA_TEXT = lang.cta_text        # нижняя плашка берётся отсюда
    out_dir = lang.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / f"work_{n:02d}"
    work.mkdir(exist_ok=True)
    print(f"[{lang.code}] урок {n}: {lesson['hook']}")

    voice = work / "voice.mp3"
    if not voice.exists():
        print("  озвучка...")
        synthesize_plan(lang, tts_plan(lang, n), voice, work)
    total = v2.probe_duration(voice) + 1.5

    overlay = work / "overlay.png"
    v2.draw_overlay(lesson, overlay)

    bg = work / "bg.mp4"
    if not bg.exists():
        bg = v2.build_background(lesson, total, work)

    out = out_dir / f"short_{n:02d}.mp4"
    # -loop 1: без него надписи пропадали на стыке фоновых фото
    p = v2.ffmpeg("-i", str(bg), "-loop", "1", "-i", str(overlay),
                  "-i", str(voice),
                  "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
                  "-map", "[v]", "-map", "2:a", "-af", "apad",
                  "-t", f"{total:.2f}",
                  "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                  "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-b:a", "160k", str(out))
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg: {p.stderr[-800:]}")

    (out_dir / f"short_{n:02d}.txt").write_text(caption_for(lang, n),
                                                encoding="utf-8")
    # компьютер старый: промежуточные фото и куски фона больше не нужны
    for junk in list(work.glob("photo_*")) + list(work.glob("clip_*")):
        junk.unlink(missing_ok=True)
    print(f"  готово: {out}  ({total:.0f} сек)")
    return out


def cli(lang):
    """python shorts_xx.py 1 2 3 — собрать эти уроки."""
    for n in [int(a) for a in sys.argv[1:]] or [1]:
        build_short(lang, n)
