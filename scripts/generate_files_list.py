#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master.csv dan faqat haqiqiy gaplashilgan (operator bilan suhbat bo'lgan) qo'ng'iroqlarni
filtrlab, downloadRecords.py uchun data/files.txt ro'yxatini hosil qiladi.

Filtr mantiqi:
  - Disposition == "ANSWERED"
  - Talk Time > 0   (real gaplashish vaqti bo'lgan)
  - Answered by to'ldirilgan  (kimdir javob bergan)
  - Callee Number tizim raqami (IVR/Queue: 7000, 7001, 6500, ...) EMAS
    -> bular faqat menyu/navbat, real odam bilan suhbat emas

Fayl nomi formulasi (Grandstream UCM record fayl nomlash qoidasi):
  auto-<UnixTimestamp(Unique ID)>-<Caller Number>-<Callee Number>.wav
  papka: YYYY-MM  (Start Time asosida)

MERGE MANTIGI:
  Agar data/files.txt allaqachon mavjud bo'lsa, bu skript uni O'CHIRMAYDI —
  eski qatorlarni o'qib, yangi Master.csv'dan topilgan qatorlar bilan birlashtiradi
  (takrorlanuvchilar bir marta saqlanadi). Shunday qilib har safar yangi CDR
  eksportini qo'yganingizda, eski yozuvlar yo'qolmaydi va downloadRecords.py
  ham ularni qayta yuklab olishga urinmaydi (chunki diskda fayl borligini
  alohida tekshiradi).

Natija: data/files.txt ichida har bir qatorda
  2026-06/auto-1782100785-997023636-194.wav
ko'rinishidagi yo'l.
"""

import csv
import datetime
import os
import re

# ===== SOZLAMALAR =====
# Skript call24/scripts/ ichida turadi deb hisoblanadi; loyiha ildizi bir papka tepada.
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR    = os.path.join(PROJECT_DIR, "data")

INPUT_CSV   = os.path.join(DATA_DIR, "Master.csv")
OUTPUT_FILE = os.path.join(DATA_DIR, "files.txt")

# IVR / Queue / tizim raqamlari - bular real operator emas, shuning uchun
# bu raqamlarga "ulangan" qatorlar audio yozuv sifatida hisobga olinmaydi.
# Agar sizning tizimingizda boshqa IVR/Queue raqamlari bo'lsa, shu yerga qo'shing.
SYSTEM_NUMBERS = {"7000", "7001", "6500"}
# ======================


def load_rows(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def is_real_conversation(row):
    """Haqiqiy odam bilan gaplashilgan qatorni aniqlaydi."""
    if row["Disposition"] != "ANSWERED":
        return False
    try:
        talk = int(row["Talk Time"] or 0)
    except ValueError:
        talk = 0
    if talk <= 0:
        return False
    if not row["Answered by"].strip():
        return False
    if row["Callee Number"] in SYSTEM_NUMBERS:
        return False
    return True


QUEUE_RE = re.compile(r"QUEUE\[(\d+)\]")


def build_path(row):
    """Fayl nomini quradi. Ikki xil sxema mavjud (UCM'ning o'zi shunday saqlaydi):
      - Navbat (queue) orqali o'tgan qo'ng'iroqlar (Action Type == QUEUE[<n>]):
        q<queue>-<caller>-<YYYYMMDD>-<HHMMSS>-<unique_id>-<agent>.wav (type=queue_recording)
      - To'g'ridan-to'g'ri (DIAL) qo'ng'iroqlar:
        auto-<unix>-<caller>-<callee>.wav (type=voice_recording)
    Papka YYYY-MM/YYYY-MM-DD (Start Time asosida) — oylik papka ichida kunlik pastki papka.
    """
    start_time = row["Start Time"]
    dt = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    folder = dt.strftime("%Y-%m/%Y-%m-%d")
    unique_id = row["Unique ID"]
    caller = row["Caller Number"]

    m = QUEUE_RE.search(row["Action Type"])
    if m:
        queue = m.group(1)
        agent = row["Answered by"].strip() or row["Callee Number"]
        date_part = dt.strftime("%Y%m%d")
        time_part = dt.strftime("%H%M%S")
        filename = f"q{queue}-{caller}-{date_part}-{time_part}-{unique_id}-{agent}.wav"
    else:
        unix_ts = int(float(unique_id))  # "." dan oldingi qism
        callee = row["Callee Number"]
        filename = f"auto-{unix_ts}-{caller}-{callee}.wav"

    return f"{folder}/{filename}"


def load_existing(path):
    """Mavjud files.txt'ni o'qiydi (agar bo'lmasa, bo'sh ro'yxat qaytaradi)."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    rows = load_rows(INPUT_CSV)
    print(f"Jami qatorlar (Master.csv): {len(rows)}")

    talked = [r for r in rows if is_real_conversation(r)]
    print(f"Gaplashilgan (filtrlangan) qatorlar: {len(talked)}")

    new_paths = []
    seen_in_csv = set()
    skipped_dup = 0
    for r in talked:
        try:
            p = build_path(r)
        except Exception as e:
            print(f"OGOHLANTIRISH: qator o'tkazib yuborildi ({e}): {r.get('Unique ID')}")
            continue
        if p in seen_in_csv:
            skipped_dup += 1
            continue
        seen_in_csv.add(p)
        new_paths.append(p)

    # --- Eski files.txt bilan birlashtirish (merge) ---
    existing_paths = load_existing(OUTPUT_FILE)
    existing_set = set(existing_paths)

    added = [p for p in new_paths if p not in existing_set]
    merged = existing_paths + added  # eski tartib saqlanadi, yangilari oxiriga qo'shiladi

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for p in merged:
            f.write(p + "\n")

    print(f"Takroriy (CSV ichida) yozuvlar o'tkazib yuborildi: {skipped_dup}")
    print(f"Avvaldan files.txt'da bor edi: {len(existing_paths)}")
    print(f"Yangi qo'shildi: {len(added)}")
    print(f"Jami (yakuniy): {len(merged)} ta yo'l -> {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
