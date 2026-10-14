# -*- coding: utf-8 -*-
"""
Озвучка длинных серий голосом преподавателя вместо синтеза.

Преподаватель записывает серию одним файлом (voice/seriya_9.m4a), сцены
по порядку. transcribe_voice.py (GitHub Actions) распознаёт запись в
voice/seriya_9.words.json — слова с таймингами. Здесь распознанный текст
сопоставляется с текстами сцен (EPISODES[n]["scenes"][i]["speech"]),
и запись режется на сцены в самой длинной паузе между последним словом
одной сцены и первым словом следующей. Паузы по 3 секунды не обязательны,
но помогают.

    python teacher_voice.py 9     # показать, где пройдут разрезы
"""

import difflib
import json
import re
import subprocess
from pathlib import Path

VOICE_DIR = Path("voice")
AUDIO = (".m4a", ".mp3", ".ogg", ".opus", ".wav", ".aac")


def recording(n: int):
    """Запись серии n или None."""
    for stem in (f"seriya_{n}", f"seriya_{n:02d}"):
        for ext in AUDIO:
            p = VOICE_DIR / f"{stem}{ext}"
            if p.exists():
                return p
    return None


def _norm(w: str) -> str:
    w = w.lower().replace("ё", "е")
    return re.sub(r"[^\w]", "", w)


def scene_spans(n: int, scenes):
    """[(начало, конец)] в секундах для каждой сцены, либо None, если
    записи или распознавания нет. Бросает ValueError, если сцену не
    удалось найти в записи (пропущена или прочитана не та)."""
    rec = recording(n)
    if not rec:
        return None
    wfile = rec.with_suffix(".words.json")
    if not wfile.exists():
        raise ValueError(f"{rec} ещё не распознана (нет {wfile.name}) — "
                         "запусти workflow «Распознать записи голоса»")
    hyp = [w for w in json.loads(wfile.read_text(encoding="utf-8"))
           if _norm(w["w"])]
    ref, ref_scene = [], []
    for i, s in enumerate(scenes):
        for w in s["speech"].split():
            if _norm(w):
                ref.append(_norm(w))
                ref_scene.append(i)

    sm = difflib.SequenceMatcher(None, ref, [_norm(w["w"]) for w in hyp],
                                 autojunk=False)
    # для каждой сцены — первое и последнее совпавшее слово в записи
    first, last = {}, {}
    for a, b, size in sm.get_matching_blocks():
        for k in range(size):
            sc, h = ref_scene[a + k], b + k
            first.setdefault(sc, h)
            last[sc] = h
    missing = [i + 1 for i in range(len(scenes)) if i not in first]
    if missing:
        raise ValueError(f"в записи серии {n} не нашлись сцены {missing}")
    for i in range(1, len(scenes)):
        if first[i] <= last[i - 1]:
            raise ValueError(f"сцены {i} и {i + 1} перепутаны в записи серии {n}")

    # разрез — середина самой длинной паузы между сценами
    cuts = []
    for i in range(1, len(scenes)):
        lo, hi = last[i - 1], first[i]
        k = max(range(lo, hi), key=lambda j: hyp[j + 1]["s"] - hyp[j]["e"])
        cuts.append((hyp[k]["e"] + hyp[k + 1]["s"]) / 2)
    starts = [max(0.0, hyp[0]["s"] - 0.3)] + cuts
    ends = cuts + [hyp[-1]["e"] + 0.6]
    return list(zip(starts, ends))


def cut_scene(src: Path, start: float, end: float, out: Path):
    """Вырезает сцену и чистит звук: срез гула, мягкое шумоподавление,
    обрезка тишины по краям, громкость как у YouTube (-16 LUFS)."""
    af = ("highpass=f=80,afftdn=nf=-25,"
          "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,"
          "areverse,"
          "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.4,"
          "areverse,"
          "loudnorm=I=-16:TP=-1.5:LRA=11")
    p = subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-ss", f"{start:.2f}", "-to", f"{end:.2f}", "-i", str(src),
                        "-af", af, "-ar", "44100", "-ac", "1",
                        "-c:a", "libmp3lame", "-b:a", "160k", str(out)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg: {p.stderr[-500:]}")


def scene_voices(n: int, scenes, work: Path):
    """Режет запись на voice_NN.mp3 в work. True — голос преподавателя
    есть и разрезан, False — записи нет (серия озвучивается синтезом)."""
    spans = scene_spans(n, scenes)
    if spans is None:
        return False
    src = recording(n)
    for i, (s, e) in enumerate(spans):
        out = work / f"voice_{i:02d}.mp3"
        if not out.exists():
            cut_scene(src, s, e, out)
    return True


if __name__ == "__main__":
    import sys
    from long_video import EPISODES
    n = int(sys.argv[1])
    scenes = EPISODES[n]["scenes"]
    for i, (s, e) in enumerate(scene_spans(n, scenes)):
        print(f"сцена {i + 1:2d}: {s:6.1f}–{e:6.1f} с  "
              f"({e - s:5.1f} с)  {scenes[i]['speech'][:50]}…")
