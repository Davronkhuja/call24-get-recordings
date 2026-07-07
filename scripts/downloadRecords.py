#!/usr/bin/env python3
# Grandstream UCM recording yuklab oluvchi — ISHLAYDIGAN versiya
import os, re, sys, time
import requests
from grandstream_client import build_session, BASE, PROJECT_DIR

OUT     = os.getenv("OUTPUT_DIR", os.path.join(PROJECT_DIR, "recordings"))
FILES   = os.getenv("FILES_LIST", os.path.join(PROJECT_DIR, "data", "files.txt"))
LOGFILE = os.getenv("DOWNLOAD_LOG", os.path.join(PROJECT_DIR, "downloaded.log"))
PAUSE   = float(os.getenv("PAUSE_SECONDS", "0.15"))


QUEUE_FILENAME_RE = re.compile(r"^q\d+-")


def recording_type(path):
    """Fayl nomidan UCM API 'type' parametrini aniqlaydi:
    q<queue>-... -> queue_recording, auto-... -> voice_recording."""
    fn = path.rsplit("/", 1)[-1]
    return "queue_recording" if QUEUE_FILENAME_RE.match(fn) else "voice_recording"


def reverse_order(path):
    # Faqat "auto-<unix>-<caller>-<callee>.wav" (voice_recording) formatiga tegishli.
    if recording_type(path) != "voice_recording":
        return path
    d, fn = path.rsplit("/", 1) if "/" in path else ("", path)
    base = fn[:-4] if fn.endswith(".wav") else fn
    p = base.split("-")
    if len(p) >= 4:
        p[-1], p[-2] = p[-2], p[-1]
    return (f"{d}/" if d else "") + "-".join(p) + ".wav"


class NetworkError(Exception):
    """Tarmoq/ulanish xatosi — bu 'fayl topilmadi' emas, urinishni davom
    ettirish ma'nosiz (server umuman javob bermayapti)."""


def try_download(session, path):
    try:
        r = session.get(BASE, params={"action": "downloadFile", "type": recording_type(path),
                                       "data": path, "_": int(time.time() * 1000)}, timeout=60)
    except requests.exceptions.RequestException as e:
        raise NetworkError(str(e)) from e
    if r.status_code == 200 and len(r.content) > 1000 and r.content[:4] == b"RIFF":
        return r.content
    return None


def log_download(path, size_kb):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOGFILE, "a", encoding="utf-8") as f:
        f.write(f"{ts}\t{path}\t{size_kb}KB\n")


def server_path(path):
    """Lokal yo'ldan (YYYY-MM/YYYY-MM-DD/fayl.wav) server yo'lini (YYYY-MM/fayl.wav) chiqaradi.
    Server fayllarni kun papkasisiz, faqat oy papkasida saqlaydi."""
    parts = path.split("/")
    if len(parts) == 3:
        return f"{parts[0]}/{parts[2]}"
    return path


def handle(session, path):
    # path masalan: "2026-06/2026-06-29/auto-1782100785-997023636-194.wav"
    # Lokal saqlash uchun to'liq yo'l (kun papkasi bilan), API uchun oy/fayl formatida.
    if "/" in path:
        date_folder, fn = path.rsplit("/", 1)
    else:
        date_folder, fn = "boshqa", path

    dest_dir = os.path.join(OUT, date_folder)
    os.makedirs(dest_dir, exist_ok=True)
    out_name = os.path.join(dest_dir, fn)

    if os.path.exists(out_name) and os.path.getsize(out_name) > 1000:
        return "skip"
    spath = server_path(path)
    data = try_download(session, spath)
    if data is None:
        rp = reverse_order(spath)
        if rp != spath:
            data = try_download(session, rp)
    if data is None:
        return "yo'q"
    with open(out_name, "wb") as f:
        f.write(data)
    size_kb = len(data) // 1024
    log_download(path, size_kb)
    return f"OK {size_kb}KB"


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def path_date(path):
    """Path'dan YYYY-MM-DD ni chiqarib oladi (YYYY-MM/YYYY-MM-DD/fayl.wav yoki YYYY-MM-DD/fayl.wav)."""
    for part in path.split("/"):
        if DATE_RE.match(part):
            return part
    return None


def download_all(session, since_date=None):
    os.makedirs(OUT, exist_ok=True)
    paths = [l.strip() for l in open(FILES, encoding="utf-8") if l.strip()]
    if since_date:
        before = len(paths)
        paths = [p for p in paths if (path_date(p) or "9999-99-99") >= since_date]
        print(f"Incremental: {since_date} dan boshlab — {before} tadan {len(paths)} tasi tanlandi.")
    ok = miss = skip = 0
    i = 0
    while i < len(paths):
        p = paths[i]
        try:
            res = handle(session, p)
        except NetworkError as e:
            for attempt in range(3):
                print(f"OGOHLANTIRISH: tarmoq xatosi ({e}), {attempt+1}/3 qayta urinish, 5s kutilmoqda...")
                time.sleep(5)
                try:
                    res = handle(session, p)
                    break
                except NetworkError as e2:
                    e = e2
            else:
                print(
                    f"\nXATO: tarmoq bilan aloqa uzildi, {i}/{len(paths)} yozuv tekshirildi. "
                    "Internet/VPN ulanishini tekshirib, keyin qayta ishga tushiring "
                    "(allaqachon yuklangan fayllar qayta yuklanmaydi)."
                )
                print(f"\n=== To'xtatildi === Yuklandi: {ok} | Avval bor: {skip} | Yozuv yo'q: {miss}")
                return
        if   res.startswith("OK"): ok += 1
        elif res == "skip":        skip += 1
        else:                      miss += 1
        print(f"[{i+1}/{len(paths)}] {res:9} {p}")
        time.sleep(PAUSE)
        i += 1
    print(f"\n=== Tugadi === Yuklandi: {ok} | Avval bor: {skip} | Yozuv yo'q: {miss}")
    print(f"Papka: {OUT}/")


if __name__ == "__main__":
    download_all(build_session())
