# Sorota Database Reset V2 Plan

Tanggal: 2026-05-09

Status: `LIVE RESET DONE BY USER`

## Tujuan

Reset database development lama dan menggantinya dengan schema v2 yang sesuai arah produk Sorota:

```text
AI pendamping keputusan bisnis UMKM Indonesia.
```

Data lama dianggap tidak perlu dipertahankan.

## Audit Singkat Schema Lama

Schema lama berisi campuran:

- `sources`, `articles`, `entities`, `article_entities`, `signals`, `crawl_logs`
- `products`, `product_price_snapshots`, `product_availability_snapshots`
- `chat_memories`
- `user_subscriptions`
- `answer_feedback`

Masalah utama:

- Belum ada `users`, `businesses`, dan `business_profiles`.
- Produk user dan produk pasar masih tercampur.
- Memory masih teks bebas, belum structured.
- Belum ada `chat_sessions`, `chat_messages`, `recommendations`, `price_surveys`, `suppliers`.
- Belum ada `ai_requests` untuk observability AI.

## Schema V2

Tabel baseline v2:

```text
users
user_channel_accounts
businesses
business_profiles
business_products
product_costs
suppliers
market_sources
market_products
market_prices
market_availability_snapshots
price_surveys
supplier_candidates
crawl_runs
crawled_documents
market_entities
document_entities
evidence_items
chat_sessions
chat_messages
user_memories
recommendations
ai_requests
user_subscriptions
scheduled_brief_runs
answer_feedback
```

Prinsip penting:

- `business_products` untuk produk milik user/UMKM.
- `market_products` dan `market_prices` untuk data pasar/crawler.
- `user_memories` untuk memory terstruktur, bukan raw chat history.
- `ai_requests` wajib menjadi tabel observability token, latency, provider, model, task, dan prompt version.
- `evidence_items` menggantikan konsep `signals` lama di level database.

## Perubahan Repo

Yang sudah disiapkan:

- SQLAlchemy models v2.
- Alembic baseline baru `20260509_0001_sorota_v2_initial`.
- Migration lama dihapus dari repo.
- Script reset DB:

```text
python scripts/reset_database.py --yes-i-understand
```

Script tersebut:

1. Drop schema `public`.
2. Create schema `public`.
3. Apply Alembic head v2.

## Status Reset Live DB

Reset live DB sudah dicoba dari Codex, tetapi koneksi ke database Neon eksternal ditolak oleh sandbox/approval:

```text
Permission denied connecting to ep-calm-shadow-an3hmytt.c-6.us-east-1.aws.neon.tech:5432
```

Command kemudian diminta dengan escalation, tetapi approval ditolak.

Setelah itu user menjalankan reset database sendiri dan mengonfirmasi reset aman/sukses. Jadi database live sekarang dianggap sudah memakai baseline v2.

Seed source dasar belum dijalankan dari Codex karena approval akses DB untuk command berikut ditolak:

```text
python scripts/seed_sources.py
```

## Verifikasi Lokal

Sudah dijalankan:

```text
python -m compileall database_migration crawling_bot telegram_bot chat_engine scripts -q
python -c "from database_migration.models import Base; print('\n'.join(sorted(Base.metadata.tables)))"
pytest
python -m alembic -c database_migration/alembic.ini heads
python -m alembic -c database_migration/alembic.ini history
```

Hasil:

```text
compileall: lulus
pytest: 25 passed
Alembic head: 20260509_0001
```

## Next Action

Setelah reset, jalankan seed source dasar:

```text
python scripts/seed_sources.py
```

Setelah seed source, lanjut refactor service berikutnya:

1. `ai_requests` persistence dari OpenAI provider.
2. `users` dan `user_channel_accounts` resolver dari Telegram chat.
3. `business_profiles` onboarding.
4. `business_products` + `product_costs` untuk margin/HPP.
5. `price_surveys` untuk survey harga pasar.
