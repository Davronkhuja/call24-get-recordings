#!/usr/bin/env python3
"""call24 recording statistics — total + per-day breakdown"""

import wave, glob, os
from collections import defaultdict

RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), "../recordings")


def fmt_dur(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def wav_duration(path):
    try:
        with wave.open(path) as w:
            return w.getnframes() / w.getframerate()
    except Exception:
        return 0.0


def main():
    files = glob.glob(os.path.join(RECORDINGS_DIR, "**/*.wav"), recursive=True)
    if not files:
        print("Hech qanday yozuv topilmadi.")
        return

    day_count = defaultdict(int)
    day_secs  = defaultdict(float)
    day_bytes = defaultdict(int)
    total_secs  = 0.0
    total_bytes = 0

    for f in files:
        dur  = wav_duration(f)
        size = os.path.getsize(f)
        total_secs  += dur
        total_bytes += size

        # Path: recordings/2026-07/2026-07-07/file.wav  → kun: 2026-07-07
        parts = f.replace("\\", "/").split("/")
        day = next((p for p in reversed(parts[:-1]) if len(p) == 10 and p.count("-") == 2), "nomalum")

        day_count[day] += 1
        day_secs[day]  += dur
        day_bytes[day] += size

    total_gb = total_bytes / 1_073_741_824

    # ── Header ────────────────────────────────────────────────────────────────
    print("=" * 62)
    print(f"  Jami yozuvlar : {len(files):,} ta")
    print(f"  Jami vaqt     : {fmt_dur(total_secs)}")
    print(f"  Jami hajm     : {total_gb:.2f} GB  ({total_bytes:,} bayt)")
    print("=" * 62)

    # ── Per-day table ─────────────────────────────────────────────────────────
    print(f"  {'Kun':<12}  {'Soni':>6}  {'Vaqt':>14}  {'Hajm':>8}")
    print("  " + "-" * 48)

    for day in sorted(day_count):
        cnt  = day_count[day]
        dur  = fmt_dur(day_secs[day])
        gb   = day_bytes[day] / 1_073_741_824
        print(f"  {day:<12}  {cnt:>6} ta  {dur:>14}  {gb:>6.2f} GB")

    print("=" * 62)


if __name__ == "__main__":
    main()
