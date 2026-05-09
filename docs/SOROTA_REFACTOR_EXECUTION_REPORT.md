# Sorota Refactor Execution Report

Tanggal: 2026-05-10

## Current Task

Nama task: Domain alignment ke Sorota UMKM

Status terbaru: `READY FOR USER TEST`

Tujuan:

- Menghapus konteks produk lama dari repo aktif.
- Menyelaraskan copy, prompt, guardrail, template response, README, dan script dengan `docs/SOROTA_PRODUCT_BRIEF.md`.
- Memastikan Sorota diposisikan sebagai AI pendamping keputusan bisnis untuk UMKM Indonesia.

## File Yang Berubah

- `README.md`
- `.env.example`
- `docker-compose.yml`
- `chat_engine/analyst_composer.py`
- `chat_engine/domain_guard.py`
- `crawling_bot/config.py`
- `crawling_bot/ai/answer_composer.py`
- `crawling_bot/ai/gemini_polisher.py`
- `crawling_bot/ai/gemini_report_polisher.py`
- `crawling_bot/ai/query_parser.py`
- `crawling_bot/processors/entity_extractor.py`
- `crawling_bot/processors/relevance_filter.py`
- `scripts/disable_broken_sources.py`
- `scripts/run_crawler.py`
- `scripts/run_price_crawler.py`
- `scripts/seed_sources.py`
- `telegram_bot/handlers/crawl_handler.py`
- `telegram_bot/handlers/menu_handler.py`
- `telegram_bot/handlers/start_handler.py`
- `telegram_bot/services/insight_service.py`
- `telegram_bot/services/response_template_service.py`
- `telegram_bot/services/telegram_service.py`
- `telegram_bot/webhook.py`
- `tests/test_analyst_ai.py`
- `tests/test_chat_engine.py`
- `tests/test_insight_summary.py`
- `tests/test_relevance_filter.py`
- `tests/test_response_template_service.py`

File lama yang dihapus:

- Script seed source domain lama yang tidak sesuai product brief Sorota.

## Ringkasan Perubahan

- Domain guard sekarang menerima konteks bisnis UMKM seperti harga jual, HPP, margin, supplier, kompetitor, restock, stok, demand, dan operasional.
- Persona jawaban chat diarahkan ke Sorota sebagai advisor keputusan bisnis UMKM Indonesia.
- Template laporan dan alert memakai label Sorota, bukan label domain lama.
- Relevance filter crawler diperluas ke kebutuhan UMKM seperti kuliner, warung, coffee shop, laundry, fashion, reseller, supplier, kemasan, harga, HPP, dan margin.
- Composer dan polisher aktif diarahkan lewat AI gateway internal agar sejalan dengan OpenAI-first strategy.
- README ditulis ulang mengikuti product brief Sorota.
- User agent crawler, nama service Docker, webhook title, menu Telegram, dan status DB disesuaikan ke Sorota.
- Seed source lama yang tidak sesuai domain baru dihapus.
- Test expectation disesuaikan dengan terminologi Sorota.

## Verifikasi Teknis

Sudah dijalankan:

```powershell
python -m compileall database_migration crawling_bot telegram_bot chat_engine scripts -q
pytest
```

Hasil:

- `compileall`: lulus.
- `pytest`: 25 passed.
- Scan istilah domain lama pada teks, binary, dan nama file: tidak ada match di repo yang bisa diedit.

## Cara Menjalankan Untuk User Test

```powershell
uvicorn telegram_bot.webhook:app --reload
```

## Langkah Testing End-User

1. Buka chat Telegram bot.
2. Kirim pertanyaan: `Kalau HPP ayam geprek Rp11.500 dan jual Rp18.000, masih aman?`
3. Kirim pertanyaan: `Harga gula pasir 1 kg hari ini berapa?`
4. Jalankan `/menu`.
5. Jalankan `/trend`.

Expected result:

- Bot memperkenalkan diri sebagai Sorota atau business assistant.
- Jawaban berfokus pada keputusan UMKM, margin, harga, supplier, stok, atau pasar.
- Tidak ada label domain lama di pesan user-facing.
- Jika data harga belum ada, bot menyatakan keterbatasan dan menyarankan cek supplier/sumber harga.

Known issue:

- Nama folder repo masih memakai nama lama karena itu bagian dari path workspace, bukan kode aplikasi.

## Next Action

- User test flow Telegram dengan pertanyaan margin, harga, dan menu.
- Jika output sudah sesuai, lanjutkan task kecil berikutnya: onboarding profil bisnis atau kalkulator margin/HPP yang lebih eksplisit.

## Progress Log

### 2026-05-10 - Chat UX dan Seed Sorota

Status terbaru: `READY FOR USER TEST`

Tujuan:

- Menghapus progress message yang terasa internal seperti menyebut database ke user.
- Membuat chat Telegram terasa lebih natural sebagai asisten bisnis.
- Merapikan seed source agar default crawler lebih fokus ke kebutuhan UMKM Indonesia.

File yang berubah:

- `telegram_bot/handlers/chat_handler.py`
- `telegram_bot/handlers/ask_handler.py`
- `chat_engine/analyst_composer.py`
- `crawling_bot/ai/answer_composer.py`
- `crawling_bot/schemas/analyst_schema.py`
- `telegram_bot/services/insight_service.py`
- `telegram_bot/services/response_template_service.py`
- `scripts/seed_sources.py`
- `scripts/seed_price_sources.py`
- `tests/test_chat_engine.py`
- `tests/test_insight_summary.py`

Ringkasan:

- Progress chat sekarang memakai bahasa user-facing seperti `Sebentar, aku cek pembanding harga dan hitung konteksnya dulu.`
- Error, feedback, dan lock message dibuat lebih ramah dan tidak membocorkan exception teknis.
- Fallback jawaban harga memakai gaya `Aku belum menemukan harga...` dan tidak menyebut database.
- Beberapa label teknis seperti `signal`, `evidence`, dan `source-grounded` dikurangi dari output user-facing.
- `seed_sources.py` ditulis ulang menjadi seed Sorota: 12 sumber total, 8 aktif, fokus Indonesia business/economy; global dan capital market dinonaktifkan default.
- `seed_sources.py` mendapat opsi `--deactivate-unlisted` untuk mematikan source lama dari seed script yang tidak ada di daftar Sorota terbaru.
- `seed_price_sources.py` ditandai sebagai `sorota_price_reference` dengan use case price survey, supplier comparison, dan margin check.

Verifikasi teknis:

```powershell
python scripts/seed_sources.py --dry-run
python scripts/seed_price_sources.py --dry-run
python -m compileall database_migration crawling_bot telegram_bot chat_engine scripts -q
pytest
```

Hasil:

- `seed_sources --dry-run`: 12 total, 8 active, 4 inactive.
- `seed_price_sources --dry-run`: 6 sources, 54 products, 22 ready.
- `compileall`: lulus.
- `pytest`: 25 passed.
- Scan copy teknis lama pada handler/chat output: tidak ada match untuk frasa lama seperti `Saya cek harga dari database`.

Langkah testing end-user:

1. Kirim chat biasa: `Harga gula 1 kg sekarang berapa?`
2. Kirim chat margin: `Kalau HPP kopi Rp8.000 dan jual Rp15.000, aman nggak?`
3. Kirim koreksi setelah jawaban: `terlalu panjang, ringkas aja`
4. Jalankan `/analyze minyak goreng 2 liter`

Expected result:

- Bot tidak menyebut database, crawler, evidence, atau exception teknis di chat biasa.
- Bot memberi progress singkat yang terasa natural.
- Jawaban tetap jujur jika data pembanding belum cukup.
- Seed source baru lebih fokus ke konteks pasar Indonesia untuk UMKM.

### 2026-05-10 - Telegram Polling Startup Fix

Status terbaru: `READY FOR USER TEST`

Tujuan:

- Memperbaiki error saat menjalankan `python -m telegram_bot.main`.
- Mencegah token Telegram bocor di log HTTP INFO.

File yang berubah:

- `telegram_bot/main.py`
- `telegram_bot/webhook.py`

Ringkasan:

- Menambahkan `ensure_bot_initialized()` untuk memastikan cached bot user tersedia sebelum `Application.start()` mengakses `bot.id`.
- Menambahkan hook `.post_init(ensure_bot_initialized)` pada polling app.
- Memanggil helper yang sama pada webhook lifecycle setelah `initialize()` dan sebelum `start()`.
- Menurunkan log `httpx` dan `httpcore` ke `WARNING` agar URL Telegram yang berisi token tidak tampil di console saat `LOG_LEVEL=INFO`.

Verifikasi teknis:

```powershell
python -m compileall telegram_bot chat_engine crawling_bot scripts database_migration -q
pytest
```

Hasil:

- `compileall`: lulus.
- `pytest`: 25 passed.

Langkah testing end-user:

```powershell
python -m telegram_bot.main
```

Expected result:

- Bot polling start tanpa error `ExtBot is not properly initialized`.
- Console tidak menampilkan URL Telegram lengkap yang berisi token.

Known issue:

- Token Telegram pernah tampil di terminal log sebelumnya. Token tersebut sebaiknya di-rotate melalui BotFather.

### 2026-05-10 - Runtime Crawl, Margin, and Auth Fix

Status terbaru: `READY FOR USER TEST`

Tujuan:

- Memperbaiki error runtime dari log polling Telegram.
- Mencegah pertanyaan HPP/margin memicu crawler harga.
- Mengurangi noise OpenAI `401 Unauthorized`.
- Mencegah race condition entity saat crawler berjalan paralel.
- Menonaktifkan source/target harga yang terbukti rusak.

File yang berubah:

- `chat_engine/query_planner.py`
- `chat_engine/analyst_composer.py`
- `chat_engine/ai/openai_provider.py`
- `crawling_bot/services/article_service.py`
- `crawling_bot/price_targets.py`
- `scripts/seed_sources.py`
- `tests/test_chat_engine.py`

Ringkasan:

- Query HPP/margin dengan dua angka uang sekarang masuk intent `recommendation`, `crawl_needed=False`, dan `price_snapshot_needed=False`.
- Menambahkan kalkulator lokal untuk pertanyaan seperti `HPP Rp11.500, jual Rp18.000 masih aman?`.
- Kalkulator memberi margin kotor, laba kotor, markup, dan saran singkat tanpa memanggil OpenAI/crawler.
- Entity insert sekarang memakai PostgreSQL `ON CONFLICT DO NOTHING` sehingga crawler paralel tidak gagal saat entity yang sama muncul bersamaan.
- OpenAI provider men-disable panggilan OpenAI selama 10 menit setelah auth error `401/403`, sehingga fallback tidak spam warning untuk setiap artikel.
- `Bisnis.com RSS` dinonaktifkan karena endpoint seed mengembalikan `404` pada runtime.
- Target harga PIHPS dinonaktifkan sampai fetcher API khusus dibuat.
- Target harga Poultry Indonesia dinonaktifkan karena kategori harga lama `404`.

Verifikasi teknis:

```powershell
python scripts/seed_sources.py --dry-run
python scripts/seed_price_sources.py --dry-run
python -m pytest tests/test_chat_engine.py -q
python -m compileall database_migration crawling_bot telegram_bot chat_engine scripts -q
pytest
```

Hasil:

- `seed_sources --dry-run`: 12 total, 7 active, 5 inactive.
- `seed_price_sources --dry-run`: 6 sources, 54 products, 9 ready, 45 disabled.
- `tests/test_chat_engine.py`: 8 passed.
- `compileall`: lulus.
- `pytest`: 26 passed.

Langkah testing end-user:

1. Jalankan ulang seed:

```powershell
python scripts/seed_sources.py --deactivate-unlisted
python scripts/seed_price_sources.py
```

2. Jalankan bot:

```powershell
python -m telegram_bot.main
```

3. Kirim:

```text
Kalau HPP ayam geprek Rp. 11.500 dan jual Rp. 18.000, masih aman??
```

Expected result:

- Bot langsung menjawab margin sekitar 36,1%.
- Tidak ada crawl berita/harga untuk pertanyaan HPP tersebut.
- Tidak ada error duplicate entity saat crawler paralel.
- Source Bisnis.com, PIHPS price, dan Poultry price tidak jalan jika seed ulang sudah diterapkan.

Known issue:

- `OPENAI_API_KEY` di `.env` masih perlu dicek/dirotasi karena runtime menunjukkan `401 Unauthorized`.

### 2026-05-10 - OpenAI-Compatible Base URL

Status terbaru: `READY FOR USER TEST`

Tujuan:

- Mendukung endpoint OpenAI-compatible custom melalui env `OPENAI_BASE_URL`.
- Mengarahkan runtime ke base URL provider yang dipakai user.

File yang berubah:

- `crawling_bot/config.py`
- `chat_engine/ai/router.py`
- `chat_engine/ai/openai_provider.py`
- `.env.example`
- `.env`
- `tests/test_openai_provider.py`

Ringkasan:

- Menambahkan config `OPENAI_BASE_URL`, default `https://api.openai.com/v1`.
- `OpenAIProvider` sekarang membangun endpoint dari `{OPENAI_BASE_URL}/responses`.
- Base URL dinormalisasi agar trailing slash tidak membuat URL ganda.
- `.env` ditambahkan `OPENAI_BASE_URL=https://lb.jatevo.ai/v1`.
- Test baru memastikan custom base URL menjadi `https://lb.jatevo.ai/v1/responses`.

Verifikasi teknis:

```powershell
python -m compileall database_migration crawling_bot telegram_bot chat_engine scripts -q
pytest
```

Hasil:

- `compileall`: lulus.
- `pytest`: 27 passed.

Langkah testing end-user:

1. Pastikan `.env` berisi:

```env
OPENAI_BASE_URL=https://lb.jatevo.ai/v1
OPENAI_API_KEY=<key dari provider tersebut>
```

2. Restart bot:

```powershell
python -m telegram_bot.main
```

Expected result:

- Request AI menuju `https://lb.jatevo.ai/v1/responses`.
- Error `401 Unauthorized` hilang jika API key sesuai provider base URL tersebut.

### 2026-05-10 - Dynamic Assistant UX, Memory, Reminder

Status terbaru: `READY FOR USER TEST`

Tujuan:

- Membuat free-text chat Telegram terasa lebih natural dan cepat untuk user UMKM.
- Menambahkan memori profil bisnis dari chat biasa.
- Menambahkan reminder dan brief personal tanpa menunggu ChatEngine/crawler.
- Mengurangi antrean global dengan lock per chat.

File yang berubah:

- `telegram_bot/handlers/chat_handler.py`
- `telegram_bot/main.py`
- `telegram_bot/webhook.py`
- `telegram_bot/handlers/start_handler.py`
- `telegram_bot/services/memory_service.py`
- `telegram_bot/services/reminder_service.py`
- `telegram_bot/services/personal_brief_service.py`
- `tests/test_assistant_services.py`

Ringkasan:

- Bot sekarang bisa menangkap konteks seperti produk utama, lokasi, target margin, supplier, dan preferensi risiko dari pesan natural.
- Sapaan ringan langsung dibalas tanpa masuk ke ChatEngine.
- Pesan seperti `ingatkan saya besok jam 9 bayar supplier ayam` disimpan sebagai reminder dan dikirim oleh background loop.
- Pesan seperti `brief hari ini` menghasilkan brief personal berbasis profil bisnis tersimpan.
- Pertanyaan kalkulasi HPP/margin lokal tidak diberi progress message yang lambat, supaya terasa lebih responsif.
- Handler memakai lock per chat, jadi satu user tidak menghambat chat user lain.

Verifikasi teknis:

```powershell
python -m compileall database_migration crawling_bot telegram_bot chat_engine scripts -q
pytest
```

Hasil:

- `compileall`: lulus.
- `pytest`: 31 passed.

Contoh testing end-user:

```text
Aku jual ayam geprek dan es teh di Bandung, target margin 30%, supplier saya Pasar Ciroyom.
brief hari ini
ingatkan saya besok jam 9 bayar supplier ayam
Kalau HPP ayam geprek Rp. 11.500 dan jual Rp. 18.000, masih aman??
```
