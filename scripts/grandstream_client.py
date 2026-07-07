#!/usr/bin/env python3
# Grandstream UCM uchun umumiy autentifikatsiya qilingan HTTP session.
# downloadRecords.py va sync.py shu yerdan session oladi.
import hashlib, os, ssl
import requests, urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
load_dotenv(os.path.join(PROJECT_DIR, ".env"))

BASE = os.getenv("GRANDSTREAM_BASE", "https://grandstream.realsoft.uz/cgi")


class WeakDHAdapter(HTTPAdapter):
    def init_poolmanager(self, *a, **kw):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        kw["ssl_context"] = ctx
        return super().init_poolmanager(*a, **kw)


def _apply_cookie_string(session, cookie_str):
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        session.cookies.set(k.strip(), v.strip())


def _login(session, user, password):
    """UCM challenge-response login (UCM web UI'ning login.js kodiga mos):
    token = MD5(challenge + parol)."""
    r = session.post(BASE, data={"action": "challenge", "user": user}, timeout=30)
    r.raise_for_status()
    body = r.json()
    if body.get("status") != 0:
        raise SystemExit(f"XATO: challenge so'rovi muvaffaqiyatsiz: {body}")
    challenge = body["response"]["challenge"]

    token = hashlib.md5((challenge + password).encode()).hexdigest()

    r2 = session.post(BASE, data={"action": "login", "user": user, "token": token}, timeout=30)
    r2.raise_for_status()
    body2 = r2.json()
    if body2.get("status") != 0:
        raise SystemExit(
            f"XATO: login muvaffaqiyatsiz ({body2}). "
            "GRANDSTREAM_USER / GRANDSTREAM_PASSWORD to'g'riligini tekshiring."
        )

    # Web UI login.js muvaffaqiyatli login'dan keyin "username" va "user_id"
    # cookie'larini alohida (JS orqali, Set-Cookie emas) qo'shadi — ba'zi API
    # action'lari (masalan voice_recording download) shularsiz ishlamaydi.
    user_id = body2.get("response", {}).get("user", {}).get("user_id")
    session.cookies.set("username", user)
    if user_id is not None:
        session.cookies.set("user_id", str(user_id))


def build_session():
    """Autentifikatsiya qilingan requests.Session yaratadi.

    Ustuvorlik:
    1) GRANDSTREAM_USER + GRANDSTREAM_PASSWORD berilgan bo'lsa — challenge/login
       oqimi orqali avtomatik sessiya olinadi (parol hech qachon tarmoqqa ochiq
       yuborilmaydi, faqat MD5 hash'i). Eng ishonchli va o'zini yangilaydigan usul.
    2) GRANDSTREAM_COOKIE (ixtiyoriy/zaxira) berilgan bo'lsa, session cookie
       jar'iga qo'shiladi.
    GRANDSTREAM_BASIC (agar berilgan bo'lsa) har doim qo'shimcha
    "Authorization: Basic" header sifatida yuboriladi (ba'zi tarmoqlarda /cgi
    yo'liga kirish uchun proksi darajasida talab qilinishi mumkin).
    """
    user = os.getenv("GRANDSTREAM_USER")
    password = os.getenv("GRANDSTREAM_PASSWORD")
    basic = os.getenv("GRANDSTREAM_BASIC")
    cookie = os.getenv("GRANDSTREAM_COOKIE")

    if not (user and password) and not cookie:
        raise SystemExit(
            "XATO: .env ichida na GRANDSTREAM_USER+GRANDSTREAM_PASSWORD, na "
            "GRANDSTREAM_COOKIE topilmadi. Avtomatik login uchun GRANDSTREAM_USER "
            "va GRANDSTREAM_PASSWORD'ni to'ldiring."
        )

    s = requests.Session()
    s.verify = False
    s.mount("https://", WeakDHAdapter())
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Referer": "https://grandstream.realsoft.uz/cdr/cdr",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    if basic:
        s.headers["Authorization"] = f"Basic {basic}"
    if cookie:
        _apply_cookie_string(s, cookie)
    if user and password:
        _login(s, user, password)
    return s
