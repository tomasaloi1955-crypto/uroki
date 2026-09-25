# -*- coding: utf-8 -*-
"""
Проверка готовых роликов: есть ли в кадре лица.

    python check_faces_en.py            # все готовые ролики
    python check_faces_en.py 9 11       # только эти

Берёт кадр каждые 2 секунды и ищет лица (shorts_en.has_face). Печатает
список роликов, которые нельзя публиковать без пересборки.
"""

import subprocess
import sys
from pathlib import Path

from shorts_en import OUT_DIR, has_face

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TMP = Path("build") / "facecheck"


def frames(video: Path, step=2):
    TMP.mkdir(parents=True, exist_ok=True)
    for old in TMP.glob("*.png"):
        old.unlink()
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(video), "-vf", f"fps=1/{step},scale=540:960",
                    str(TMP / "f_%03d.png")], check=False)
    return sorted(TMP.glob("*.png"))


def main():
    nums = [int(a) for a in sys.argv[1:]]
    videos = ([OUT_DIR / f"short_{n:02d}.mp4" for n in nums] if nums
              else sorted(OUT_DIR.glob("short_*.mp4")))
    bad = []
    for v in videos:
        if not v.exists():
            continue
        hits = [f.name for f in frames(v) if has_face(f)]
        print(f"{v.name}: {'ЛИЦО в кадре' if hits else 'чисто'}", flush=True)
        if hits:
            bad.append(int(v.stem.split("_")[1]))
    print("\nПересобрать:", bad or "нечего")


if __name__ == "__main__":
    main()
