# -*- coding: utf-8 -*-
"""
Распознаёт записи преподавателя из voice/ (faster-whisper) и сохраняет
слова с таймингами рядом: voice/seriya_9.m4a -> voice/seriya_9.words.json.
По ним long_video режет запись на сцены. Уже распознанные файлы пропускает.

    python transcribe_voice.py            # все новые записи
    python transcribe_voice.py voice/x.m4a
"""
import json
import sys
from pathlib import Path

from faster_whisper import WhisperModel

AUDIO = {".m4a", ".mp3", ".ogg", ".opus", ".wav", ".aac"}


def main():
    files = [Path(a) for a in sys.argv[1:]] or sorted(
        p for p in Path("voice").iterdir() if p.suffix.lower() in AUDIO)
    todo = [f for f in files if not f.with_suffix(".words.json").exists()]
    if not todo:
        print("Нечего распознавать.")
        return
    model = WhisperModel("medium", device="cpu", compute_type="int8")
    for f in todo:
        print(f"Распознаю {f} ...", flush=True)
        segs, _ = model.transcribe(str(f), language="ru", word_timestamps=True,
                                   vad_filter=False, beam_size=5)
        words = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)}
                 for s in segs for w in (s.words or [])]
        f.with_suffix(".words.json").write_text(
            json.dumps(words, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"  слов: {len(words)}")


if __name__ == "__main__":
    main()
