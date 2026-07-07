#!/usr/bin/env python3
# To'liq avtomatik oqim:
#   1) UCM'da CDR faylini yangilaydi (reloadCDRRecordFile)
#   2) Yangi CDR CSV'ni yuklab oladi va data/Master.csv'ni yangilaydi (eskisi .bak'ga saqlanadi)
#   3) files.txt'ni yangi Master.csv bilan birlashtiradi (eski yozuvlar saqlanadi)
#   4) Faqat oxirgi marta sinxronlangan sanadan hozirgacha bo'lgan recording'larni
#      yuklab oladi (eski sanalar har safar qayta urinilmaydi — data/last_synced.txt'da saqlanadi)
#
# Ishga tushirish: python3 scripts/sync.py
import datetime, os, sys, shutil, time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from grandstream_client import build_session, BASE, PROJECT_DIR
import generate_files_list as gfl
import downloadRecords as dr

DATA_DIR = os.path.join(PROJECT_DIR, "data")
MASTER_CSV = os.path.join(DATA_DIR, "Master.csv")
LAST_SYNCED_FILE = os.path.join(DATA_DIR, "last_synced.txt")
LOOKBACK_DAYS = 2  # kunlar kech to'ldirilishi mumkinligi uchun ortga qarab tekshirish


def read_last_synced():
    if os.path.exists(LAST_SYNCED_FILE):
        v = open(LAST_SYNCED_FILE, encoding="utf-8").read().strip()
        return v or None
    return None


def write_last_synced(date_str):
    with open(LAST_SYNCED_FILE, "w", encoding="utf-8") as f:
        f.write(date_str + "\n")


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

    last_synced = read_last_synced()
    if last_synced:
        lookback_dt = datetime.datetime.strptime(last_synced, "%Y-%m-%d") - datetime.timedelta(days=LOOKBACK_DAYS)
        since_date = lookback_dt.strftime("%Y-%m-%d")
        print(f"4) Yangi recordinglar yuklab olinmoqda (oxirgi sinxron: {last_synced}, {since_date} dan tekshiriladi)...")
    else:
        since_date = None
        print("4) Birinchi ishga tushirish — barcha recordinglar tekshiriladi...")
    dr.download_all(session, since_date=since_date)

    write_last_synced(time.strftime("%Y-%m-%d"))


if __name__ == "__main__":
    main()
