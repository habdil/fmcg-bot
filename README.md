# Sorota Business Assistant

Sorota adalah backend AI pendamping keputusan bisnis untuk UMKM Indonesia. Sistem ini menggabungkan chat Telegram, crawling sumber publik, data harga pasar, dan analisa bisnis praktis agar owner UMKM bisa mengambil keputusan harian dengan lebih cepat.

Fokus produk mengikuti `docs/SOROTA_PRODUCT_BRIEF.md`:

- pricing, margin, HPP, dan rekomendasi harga jual
- survey harga pasar dan pembanding supplier
- insight stok, demand, kompetitor, dan kondisi pasar
- jawaban chat yang singkat, praktis, dan source-grounded
- OpenAI API sebagai provider utama melalui gateway internal

## Architecture

```text
Telegram/User Channel
  -> Chat Engine
  -> Domain Guard
  -> Query Planner
  -> Context/Evidence Selector
  -> Business Tools and Price Data
  -> Answer Composer
  -> Memory and Observability

Crawler
  -> Cleaner
  -> Business Relevance Filter
  -> Entity Extractor
  -> Signal Extractor
  -> Scorer
  -> PostgreSQL
```

## Tech Stack

- Python 3.11+
- PostgreSQL / Neon
- SQLAlchemy ORM
- Alembic migration
- Pydantic validation
- FastAPI
- python-telegram-bot
- OpenAI Responses API
- BeautifulSoup, feedparser, httpx
- Docker

## Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Isi `.env` dengan koneksi database, token Telegram, dan `OPENAI_API_KEY`.

## Database

Jalankan migration:

```powershell
alembic -c database_migration/alembic.ini upgrade head
```

Schema v2 mengikuti brief Sorota: user, business profile, product/cost, supplier, market price, price survey, chat memory terstruktur, recommendation, dan `ai_requests` untuk observability.

## Seed Sources

```powershell
python scripts/seed_sources.py
python scripts/seed_price_sources.py
```

`seed_sources.py` mengisi sumber berita bisnis umum. `seed_price_sources.py` mengisi metadata target harga pasar yang dipakai untuk survey harga.

## Run Crawler

```powershell
python scripts/run_crawler.py
python scripts/run_crawler.py --max 10
python scripts/run_price_crawler.py --dry-run
```

Crawler membaca source aktif, mengambil artikel RSS, membersihkan konten, menghitung relevansi bisnis UMKM, mengekstrak entity/signal, menyimpan evidence ke PostgreSQL, lalu menyediakan data untuk jawaban chat.

## Telegram Bot

Jalankan webhook server:

```powershell
uvicorn telegram_bot.webhook:app --reload
```

Set webhook:

```powershell
python scripts/set_telegram_webhook.py
```

Command utama:

- `/start`
- `/menu`
- `/ask <pertanyaan>`
- `/analyze <produk/topik>`
- `/crawl [max]`
- `/crawl_harga`
- `/alert`
- `/report`
- `/search <keyword>`
- `/insight <keyword>`
- `/trend`
- `/weekly`
- `/compare <produk A> | <produk B>`
- `/forecast <keyword>`
- `/trending`
- `/price_check <produk>` atau `/harga <produk>`
- `/price_add <produk> | <harga> | <sumber> | <url> | <lokasi>`
- `/price_collect <produk> | <sumber> | <url> | <lokasi>`
- `/subscribe`
- `/unsubscribe`

Contoh:

```text
Margin kopi saya terlalu kecil nggak?
Kalau HPP ayam geprek Rp11.500 dan jual Rp18.000, masih aman?
/harga gula pasir 1 kg
/insight minyak goreng
/compare ayam | telur
/price_add gula pasir 1 kg | 16900 | Katalog Supplier A | https://example.com/gula | Jakarta
```

## Response Principles

Sorota harus menjawab seperti pendamping bisnis praktis:

- langsung ke keputusan yang bisa diambil
- tidak mengarang harga, supplier, kompetitor, atau data pasar
- menjelaskan angka penting jika ada
- menyebut data yang belum cukup
- memakai crawling/survey hanya saat diperlukan
- tidak mengirim raw crawl panjang ke prompt final

## Tests

```powershell
pytest
```

## Docker

```powershell
docker compose up --build
docker compose --profile jobs run --rm crawler
```

## Development Notes

- Ikuti `docs/SOROTA_DEVELOPMENT_SKILL.md`.
- Semua request AI baru harus lewat gateway internal.
- Pertanyaan sederhana tidak boleh memicu crawling berat.
- Kalkulasi bisnis harus dilakukan oleh code, bukan diserahkan ke LLM.
- Update `docs/SOROTA_REFACTOR_EXECUTION_REPORT.md` setelah task selesai.
