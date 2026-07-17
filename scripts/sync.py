#!/usr/bin/env python3
# To'liq avtomatik oqim:
#   1) UCM'da CDR faylini yangilaydi (reloadCDRRecordFile)
#   2) Yangi CDR CSV'ni yuklab oladi va data/Master.csv'ni yangilaydi (eskisi .bak'ga saqlanadi)
#   3) files.txt'ni yangi Master.csv bilan birlashtiradi (eski yozuvlar saqlanadi)
#   4) Recordings papkasidagi oxirgi mavjud sanadan boshlab yangi fayllarni yuklab oladi
#
# Ishga tushirish: python3 scripts/sync.py
import datetime, glob, os, sys, shutil, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from grandstream_client import build_session, BASE, PROJECT_DIR
import generate_files_list as gfl
import downloadRecords as dr

DATA_DIR        = os.path.join(PROJECT_DIR, "data")
RECORDINGS_DIR  = os.path.join(PROJECT_DIR, "recordings")
MASTER_CSV      = os.path.join(DATA_DIR, "Master.csv")


def last_recorded_date():
    """recordings/ papkasidagi eng oxirgi YYYY-MM-DD papkasini qaytaradi."""
    pattern = os.path.join(RECORDINGS_DIR, "????-??", "????-??-??")
    day_dirs = [d for d in glob.glob(pattern) if os.path.isdir(d)]
    if not day_dirs:
        return None
    return max(os.path.basename(d) for d in day_dirs)


def refresh_cdr(session):
    session.get(BASE, params={
        "action": "reloadCDRRecordFile",
        "reflush_Record": "all",
        "locale": "en-US",
        "_": int(time.time() * 1000),
    }, timeout=60)


def fetch_csv(session):
    r = session.get(BASE, params={
        "action": "downloadFile",
        "type": "cdr_recording",
        "data": "Master.csv",
        "_location": "cdr",
        "_": int(time.time() * 1000),
    }, timeout=180)
    r.raise_for_status()
    if not r.content or len(r.content) < 50:
        sys.exit(
            "XATO: CSV bo'sh yoki juda kichik keldi — GRANDSTREAM_BASIC/GRANDSTREAM_COOKIE "
            "muddati tugagan yoki noto'g'ri bo'lishi mumkin. .env'ni tekshiring."
        )
    return r.content


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    session = build_session()

    print("1) CDR UCM'da yangilanmoqda...")
    refresh_cdr(session)
    time.sleep(1)

    print("2) CSV yuklab olinmoqda...")
    csv_bytes = fetch_csv(session)
    if os.path.exists(MASTER_CSV):
        shutil.copy2(MASTER_CSV, MASTER_CSV + ".bak")
    with open(MASTER_CSV, "wb") as f:
        f.write(csv_bytes)
    print(f"   -> {MASTER_CSV} yangilandi ({len(csv_bytes)} bayt)")

    print("3) files.txt eski ma'lumotlar bilan solishtirilib yangilanmoqda...")
    gfl.main()

    since_date = last_recorded_date()
    if since_date:
        print(f"4) Yangi recordinglar yuklab olinmoqda (oxirgi mavjud sana: {since_date})...")
    else:
        print("4) Birinchi ishga tushirish — barcha recordinglar tekshiriladi...")
    dr.download_all(session, since_date=since_date)


if __name__ == "__main__":
    main()
