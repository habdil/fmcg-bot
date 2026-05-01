# FMCG Business Intelligence Crawling Engine

Backend data engine for collecting public FMCG-related information, processing it into structured business signals, storing it in Neon PostgreSQL, and exposing insights through a Telegram bot.

This is not a news portal. It is an AI-ready business intelligence crawling engine for FMCG sub-distributors.

## Architecture

Crawler -> Cleaner -> Relevance Filter -> Entity Extractor -> Signal Extractor -> Reason Extractor -> Scorer -> Neon PostgreSQL -> Gemini Polisher -> Telegram Bot

## Tech Stack

- Python 3.11+
- Neon PostgreSQL
- SQLAlchemy ORM
- Alembic migration
- Pydantic validation
- BeautifulSoup, feedparser, httpx
- FastAPI
- python-telegram-bot
- Google Gen AI SDK for Gemini
- Docker

## Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with your Neon, Telegram, and optional Gemini credentials.

## Neon Database Setup

Create a Neon project and copy two connection strings:

- `DATABASE_URL_DIRECT`: regular direct Postgres connection for Alembic migrations.
- `DATABASE_URL_POOLER`: pooled connection with `-pooler` host for runtime services.

Runtime services use pooled connections because crawler, API, and bot workloads can create many short-lived database sessions. Migrations use direct connections because schema changes are safer outside PgBouncer transaction pooling.

## Alembic Migration

```powershell
alembic -c database_migration/alembic.ini upgrade head
```

The Alembic env reads `DATABASE_URL_DIRECT`.

## Seed Sources

```powershell
python scripts/seed_sources.py
```

RSS URLs are starter values and should be reviewed before production use.

## Run Crawler

```powershell
python scripts/run_crawler.py
python scripts/run_crawler.py --max 10
```

The crawler reads active sources, fetches RSS entries, extracts article content, deduplicates by URL and content hash, filters FMCG relevance, extracts entities and signals, computes scores, optionally asks Gemini to polish the summary, stores results, and writes crawl logs.

## Telegram Bot Setup

1. Create a bot with BotFather.
2. Put the token in `TELEGRAM_BOT_TOKEN`.
3. Set your public HTTPS base URL in `TELEGRAM_WEBHOOK_URL`.
4. Optionally restrict access with comma-separated `TELEGRAM_ALLOWED_CHAT_IDS`.

Run webhook server:

```powershell
uvicorn telegram_bot.webhook:app --reload
```

Set Telegram webhook:

```powershell
python scripts/set_telegram_webhook.py
```

Bot commands:

- `/start`
- `/menu`
- `/analyze <question>`
- `/ask <question>`
- `/crawl [max]`
- `/alert`
- `/report`
- `/search <keyword>`
- `/insight <keyword>`
- `/trend`
- `/weekly`
- `/compare <product A> | <product B>`
- `/forecast <keyword>`
- `/trending`
- `/subscribe`
- `/unsubscribe`

Example Telegram workflow:

```text
/analyze Tolong analisis produk minyak goreng 2 liter
Tolong analisis produk minyak kita 2 liter
/crawl 3
/insight minyak goreng
/trend
/weekly
/compare minyak goreng | gula
/forecast susu
```

Analyst commands use a crawl-first flow by default because early databases may still have limited evidence. The bot crawls a small batch of public sources, stores fresh evidence in PostgreSQL, then reads the structured signals for the response.

`/analyze` and plain text questions use:

```text
Telegram question -> parse topic -> crawl public sources -> store evidence in PostgreSQL -> retrieve relevant signals -> Gemini composes a source-grounded report
```

`/trend`, `/weekly`, `/alert`, `/report`, `/search`, `/insight`, `/forecast`, `/trending`, and `/compare` also crawl first, then build the response from the refreshed evidence store.

Gemini is constrained to the evidence stored in the database. If the crawler does not find pack-size-specific evidence, the answer must say that explicitly.

`/forecast` is a rule-based operational outlook from stored public signals. It is not a numerical market forecast.

## Business Analyst Bot Responses

The Telegram bot is designed to answer as an FMCG business intelligence analyst, not as a general chatbot. Responses separate:

- FACT: data extracted from crawled sources or stored database rows.
- SIGNAL: structured interpretation such as `price_increase`, `shortage`, or `demand_increase`.
- REASON: why the signal likely happened, based only on evidence text.
- BUSINESS IMPACT: operational meaning for FMCG sub-distributors.
- RECOMMENDATION: practical actions to consider.
- LIMITATION: missing data, weak coverage, or uncertainty.

Response types:

1. Product Deep Analysis: `/analyze minyak goreng`, `/insight minyak goreng`, or plain text like `produk minyak goreng sekarang gimana?`
2. Daily Trend Brief: `/trend` or `trend hari ini`
3. Weekly Intelligence Report: `/weekly` or `laporan mingguan FMCG`
4. Alert / Early Warning: `/alert` and future push alerts for subscribed users
5. Search / Query Insight: `/search gula` or `cari insight tentang gula`
6. Comparative Analysis: `/compare minyak goreng | gula` or `bandingkan minyak goreng vs gula`

Every analytical response includes source coverage where possible:

- total crawled sources
- total crawled/relevant articles
- strong signal count
- price snapshot count
- latest source date
- source names, limited to the top visible sources when long

Important: the response is not generated directly from raw crawl text. The crawler first saves cleaned articles, extracted entities, and signals to Neon PostgreSQL. The report then reads those fresh structured records so every answer remains auditable and source-grounded.

Confidence is labelled `HIGH`, `MEDIUM`, or `LOW` based on source count, evidence clarity, recency, strong signals, and price/stock snapshot availability.

## Price Tracking Data

Exact prices are shown only when `product_price_snapshots` contains price data from allowed sources, APIs, CSV/manual imports, or future compliant integrations.

News crawling alone cannot produce exact market prices. If price snapshots do not exist, the bot must say:

```text
Detailed price tracking is not available yet. Current analysis is based on news and public signal extraction, not marketplace/retail price time-series.
```

The price tracking schema supports:

- `products`
- `product_price_snapshots`
- `product_availability_snapshots`

When price snapshots exist, the bot can show daily average price, day-over-day change, percentage change, total movement, trend direction, highest price, lowest price, average price, source count, and region/location if available.

Example price movement:

```text
Price Movement
- 28 Apr 2026: Rp 15.200
- 29 Apr 2026: Rp 15.500 (+Rp 300 / +1.97%)
- 30 Apr 2026: Rp 16.100 (+Rp 600 / +3.87%)
- 01 Mei 2026: Rp 16.500 (+Rp 400 / +2.48%)

Total movement:
+Rp 1.300 (+8.55%) in 3 days
```

Do not add exact price statements unless the value exists in `product_price_snapshots`.

## Example Analyst Responses

Example `/analyze minyak goreng`:

```text
📊 FMCG Product Intelligence Brief — Minyak Goreng
Product: Minyak Goreng
Period: Last 7 Days
Status: HIGH ATTENTION
Confidence: 82%

1. Executive Summary
Minyak goreng terindikasi perlu dipantau. Signal utama berasal dari price_increase dan shortage.

2. Price Movement
Detailed price tracking is not available yet. Current analysis is based on news and public signal extraction, not marketplace/retail price time-series.

3. Availability / Stock Signal
Belum ada stock snapshot. Terdapat signal shortage dari artikel publik, sehingga availability perlu dipantau.

6. Reason Analysis
- Pasokan disebut terbatas oleh sumber. (Source: Example Source)

7. Business Impact
- Margin sub-distributor berpotensi tertekan.
- Stock planning dan alokasi distribusi perlu diprioritaskan untuk SKU fast-moving.

8. Recommended Action
- Monitor harga supplier harian.
- Siapkan buffer stock terbatas untuk SKU prioritas.

10. Limitations
- Analisis hanya memakai data publik yang sudah dicrawl dan tersimpan.
- Detailed stock/availability snapshots are not available yet.
```

Example `/trend`:

```text
🔥 FMCG Daily Trend Brief
Date: 01 Mei 2026
Data Coverage: 12 artikel relevan dari CNBC Indonesia Business RSS, Kontan RSS +3 more
Confidence: MEDIUM

Top Products Today:
1. Minyak Goreng
   Status: HIGH ATTENTION
   Main Signals: price_increase (2), shortage (1)
   Why it matters: Pasokan disebut terbatas oleh sumber.
   Business implication: Risiko supply dapat memengaruhi buffer stock, lead time, dan prioritas distribusi.

Analyst Note:
Pasar FMCG terindikasi memiliki tekanan harga naik, risiko availability.
```

Example `/weekly`:

```text
📈 Weekly FMCG Intelligence Report
Period: Last 7 Days
Confidence: MEDIUM

Executive Summary
Pasar FMCG terindikasi memiliki tekanan harga naik dan risiko availability.

Top Weekly Movements:
1. Gula
   Trend Direction: naik (6 signal vs 2 periode sebelumnya)
   Price Movement: Terindikasi naik: 3 signal naik vs 0 signal turun.
   Availability: 2 signal shortage/distribution risk.
   Demand: Demand belum jelas.
   Reason: Evidence menyebut pasokan terbatas.

Week-over-Week Insight:
Jumlah signal minggu ini lebih tinggi dibanding periode sebelumnya.
```

## Gemini Setup

Set:

```env
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash
```

Gemini is used only after structured data is prepared by the system. It polishes language and structured summaries, but must not invent facts, prices, sources, or causes. If the API key is missing or the request fails, the engine falls back to rule-based Markdown responses.

## Example Output

```json
{
  "title": "Harga minyak goreng naik karena pasokan terbatas",
  "category": "price",
  "entities": {
    "product": ["minyak goreng"],
    "location": ["Jawa Tengah"]
  },
  "signals": [
    {
      "signal_type": "price_increase",
      "severity": 4,
      "confidence_score": 0.82,
      "reason": "Harga naik karena pasokan terbatas.",
      "evidence_text": "Harga minyak goreng naik di Jawa Tengah karena pasokan terbatas."
    }
  ],
  "urgency": "high"
}
```

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

- Keep extraction grounded in article text.
- Do not hardcode secrets.
- Use `DATABASE_URL_DIRECT` only for migrations/admin jobs.
- Use `DATABASE_URL_POOLER` for crawler, API, bot, and runtime workers.
- Add source-specific parsers later if generic article extraction is not enough.

## Future Improvements

- LLM-based extraction
- pgvector semantic search
- Marketplace price monitoring
- Social media sentiment analysis
- Dashboard
- WhatsApp alerts
- Anomaly detection
- Forecasting
- Recommendation engine
