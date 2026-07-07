# call24 — Recording yuklab olish loyihasi

## Papka strukturasi
```
call24/
├── .env                    # MAXFIY — cookie shu yerda (git'ga yubormang)
├── .env.example            # namuna, .env yaratish uchun nusxa oling
├── data/
│   ├── Master.csv          # CDR eksport (har safar yangilanganda shu yerga qo'ying)
│   └── files.txt           # avtomatik generatsiya qilinadi, qo'lda tahrirlamang
├── recordings/              # yuklab olingan .wav fayllar, kun bo'yicha papkalarda
│   ├── 2026-06-30/
│   └── 2026-07-02/
├── downloaded.log           # har bir muvaffaqiyatli yuklashning tarixi
└── scripts/
    ├── grandstream_client.py   # umumiy autentifikatsiya (login/parol yoki cookie)
    ├── generate_files_list.py
    ├── downloadRecords.py
    └── sync.py                 # to'liq avtomatik oqim (tavsiya etiladi)
```

Fayl nomlash: to'g'ridan-to'g'ri qo'ng'iroqlar `auto-<unix>-<caller>-<callee>.wav`,
navbat (queue) orqali o'tgan qo'ng'iroqlar
`q<queue>-<caller>-<YYYYMMDD>-<HHMMSS>-<unique_id>-<agent>.wav` formatida saqlanadi
— bular UCM serverida ikki xil turda (`voice_recording` / `queue_recording`)
saqlanadi, `downloadRecords.py` fayl nomidan turini avtomatik aniqlaydi.

## Ishlatish tartibi (avtomatik, tavsiya etiladi)

1. Birinchi marta ishlatishda `.env.example`'ni `.env`ga ko'chirib, `GRANDSTREAM_USER`
   va `GRANDSTREAM_PASSWORD`'ni (UCM admin panel login/parol) kiriting:
   ```
   cp .env.example .env
   nano .env
   ```
   Skript o'zi challenge-response (MD5) login qilib, sessiyani avtomatik oladi
   va har safar yangilaydi — parol tarmoqqa hech qachon ochiq yuborilmaydi.
2. Bitta buyruq bilan hammasini bajarish — UCM'da CDR yangilanadi, yangi CSV
   yuklab olinadi, `data/Master.csv` yangilanadi (eskisi `.bak`ga saqlanadi),
   `files.txt` eski ma'lumotlar bilan solishtirib birlashtiriladi va yangi
   recording'lar yuklab olinadi:
   ```
   python3 scripts/sync.py
   ```

## Qo'lda bosqichma-bosqich ishlatish (muqobil)

Agar CSV'ni o'zingiz qo'lda joylashtirmoqchi bo'lsangiz yoki faqat bitta
bosqichni qayta ishga tushirmoqchi bo'lsangiz:

1. Yangi CDR eksportini `data/Master.csv` ga qo'ying (eski faylni almashtirib yuborish mumkin).
2. files.txt'ni yangilash (eski yozuvlar saqlanadi, faqat yangilari qo'shiladi):
   ```
   python3 scripts/generate_files_list.py
   ```
3. Yuklab olish (allaqachon diskda bor fayllar avtomatik o'tkazib yuboriladi):
   ```
   python3 scripts/downloadRecords.py
   ```
   (`GRANDSTREAM_COOKIE` yoki `GRANDSTREAM_BASIC` — ikkalasidan biri `.env`da bo'lsa yetarli.)

## Nega eski fayllar qayta yuklanmaydi?
`downloadRecords.py` har bir faylni yuklashdan oldin diskda (`recordings/YYYY-MM-DD/...`)
borligini va hajmi to'g'ri (>1KB) ekanligini tekshiradi. Agar mavjud bo'lsa — "skip"
deb o'tkazib yuboradi. Shuning uchun `files.txt`ga necha marta yangi yozuv qo'shilsa ham,
eski yozuvlar uchun qayta tarmoq so'rovi yuborilmaydi.

`generate_files_list.py` ham xuddi shunday — har safar ishlatilganda eski `data/files.txt`
ni o'qib, faqat yangi (hali ro'yxatda yo'q) yozuvlarni qo'shadi, eskilarini o'chirmaydi.
