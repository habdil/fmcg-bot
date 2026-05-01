Create a complete backend project called:

FMCG Business Intelligence Crawling Engine

This project is a backend data engine for collecting public FMCG-related information, processing it into structured business signals, storing it in Neon PostgreSQL, and exposing insights through a Telegram bot.

This is NOT a news portal.
This is an AI-ready business intelligence crawling engine for FMCG sub-distributors.

==================================================
MAIN OBJECTIVE
==================================================

Build a system that can:
1. Crawl FMCG-related public sources such as RSS feeds and news articles.
2. Extract structured business signals from raw content.
3. Explain WHY a signal happened.
4. Attach source references used by the system.
5. Store clean structured data in Neon PostgreSQL.
6. Use Gemini AI only to polish/rewrite insight language.
7. Serve alerts, reports, and search results via Telegram bot.

Target users:
- FMCG sub-distributors
- sales operation teams
- procurement teams
- distribution managers
- business intelligence teams

Main business questions:
- Are prices increasing or decreasing?
- Is there a shortage risk?
- Is stock availability affected?
- Is distribution disrupted?
- Is demand increasing or decreasing?
- Is there negative or positive sentiment toward a brand?
- Is there a regulation change affecting FMCG distribution?

==================================================
TECH STACK
==================================================

Use:

- Python 3.11+
- Neon PostgreSQL
- SQLAlchemy ORM
- Alembic migration
- Pydantic validation
- BeautifulSoup / Scrapy for crawling
- feedparser for RSS
- httpx or requests for HTTP client
- python-dotenv for env variables
- FastAPI for Telegram webhook server
- python-telegram-bot for Telegram bot
- Google Gen AI SDK for Gemini
- Uvicorn
- Docker
- Optional: pgvector for future embedding support

Important:
Before implementation, follow the latest official documentation for:
- SQLAlchemy
- Alembic
- Neon PostgreSQL connection pooling
- Google Gen AI Python SDK
- Gemini structured output
- python-telegram-bot
- FastAPI

Do not use deprecated API patterns.
Pin dependency versions where reasonable.

==================================================
NEON DATABASE CONNECTION STRATEGY
==================================================

Use two database URLs:

DATABASE_URL_DIRECT=
DATABASE_URL_POOLER=

Usage:
- DATABASE_URL_DIRECT is used for Alembic migrations, schema changes, and admin jobs.
- DATABASE_URL_POOLER is used for runtime services such as crawler, FastAPI app, Telegram bot, and background workers.

Reason:
Neon provides direct and pooled connections. The pooled connection is better for application runtime because crawlers, APIs, and bots may open many short-lived connections. The direct connection is safer for migrations and schema-level operations.

==================================================
PROJECT STRUCTURE
==================================================

Create this structure:

fmcg-intelligence-engine/
├── database_migration/
│   ├── alembic/
│   ├── alembic.ini
│   ├── env.py
│   └── models/
│       ├── __init__.py
│       ├── base.py
│       ├── source.py
│       ├── article.py
│       ├── entity.py
│       ├── signal.py
│       ├── crawl_log.py
│       └── user_subscription.py
│
├── crawling_bot/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── crawlers/
│   │   ├── __init__.py
│   │   ├── rss_crawler.py
│   │   └── article_crawler.py
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── cleaner.py
│   │   ├── relevance_filter.py
│   │   ├── entity_extractor.py
│   │   ├── signal_extractor.py
│   │   ├── scorer.py
│   │   └── reason_extractor.py
│   ├── ai/
│   │   ├── __init__.py
│   │   └── gemini_polisher.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── article_service.py
│   │   ├── source_service.py
│   │   ├── signal_service.py
│   │   └── crawl_log_service.py
│   └── schemas/
│       ├── __init__.py
│       ├── article_schema.py
│       ├── signal_schema.py
│       ├── entity_schema.py
│       └── insight_schema.py
│
├── telegram_bot/
│   ├── __init__.py
│   ├── main.py
│   ├── webhook.py
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start_handler.py
│   │   ├── menu_handler.py
│   │   ├── alert_handler.py
│   │   ├── search_handler.py
│   │   ├── report_handler.py
│   │   └── trending_handler.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── telegram_service.py
│   │   ├── insight_service.py
│   │   └── subscription_service.py
│   └── keyboards/
│       ├── __init__.py
│       └── menu.py
│
├── scripts/
│   ├── run_crawler.py
│   ├── seed_sources.py
│   └── set_telegram_webhook.py
│
├── tests/
│   ├── test_signal_extractor.py
│   ├── test_scorer.py
│   └── test_relevance_filter.py
│
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── BRIEF_DOCUMENT.md

==================================================
DATABASE DESIGN
==================================================

Create SQLAlchemy models and Alembic migrations for these tables.

1. sources

Fields:
- id UUID primary key
- name string not null
- url text not null
- source_type string not null
  Examples: rss, news_site, marketplace, social_media
- credibility_score float default 0.5
- is_active boolean default true
- created_at timestamp UTC
- updated_at timestamp UTC

2. articles

Fields:
- id UUID primary key
- source_id foreign key to sources
- title text not null
- url text unique not null
- raw_content text nullable
- clean_content text nullable
- summary text nullable
- reason text nullable
- evidence_text text nullable
- ai_polished_summary text nullable
- published_at timestamp nullable
- crawled_at timestamp UTC
- language string default "id"
- category string nullable
  Examples: price, supply, demand, regulation, brand, logistics, commodity
- relevance_score float default 0
- impact_score float default 0
- confidence_score float default 0
- urgency string default "low"
  Values: low, medium, high
- content_hash string unique
- created_at timestamp UTC
- updated_at timestamp UTC

3. entities

Fields:
- id UUID primary key
- name string not null
- entity_type string not null
  Examples: product, company, commodity, location, brand
- normalized_name string not null
- created_at timestamp UTC

4. article_entities

Fields:
- id UUID primary key
- article_id foreign key to articles
- entity_id foreign key to entities
- relevance_score float default 0.5

5. signals

Fields:
- id UUID primary key
- article_id foreign key to articles
- signal_type string not null
  Examples:
  price_increase,
  price_decrease,
  shortage,
  oversupply,
  demand_increase,
  demand_decrease,
  negative_sentiment,
  positive_sentiment,
  regulation_change,
  distribution_disruption
- product string nullable
- company string nullable
- location string nullable
- value string nullable
- severity integer default 1
  Range: 1 to 5
- confidence_score float default 0.5
- reason text nullable
- evidence_text text nullable
- explanation text nullable
- source_count integer default 1
- related_article_count integer default 1
- created_at timestamp UTC

6. crawl_logs

Fields:
- id UUID primary key
- source_id foreign key nullable
- status string not null
  Examples: success, failed, skipped, partial_success
- message text nullable
- total_found integer default 0
- total_crawled integer default 0
- total_processed integer default 0
- total_saved integer default 0
- total_skipped integer default 0
- total_failed integer default 0
- started_at timestamp UTC
- finished_at timestamp nullable UTC

7. user_subscriptions

Fields:
- id UUID primary key
- telegram_chat_id string unique not null
- username string nullable
- is_active boolean default true
- subscribed_products text nullable
- subscribed_locations text nullable
- minimum_urgency string default "high"
- created_at timestamp UTC
- updated_at timestamp UTC

==================================================
CRAWLER PIPELINE
==================================================

Implement this pipeline:

1. Load active sources from database.
2. If source_type is rss, fetch article entries from RSS feed.
3. For each URL, fetch article detail.
4. Extract title, date, raw HTML, and raw text.
5. Clean HTML into plain text.
6. Generate content_hash.
7. Deduplicate by URL and content_hash.
8. Check FMCG relevance.
9. Extract entities:
   - product
   - company
   - brand
   - location
   - commodity
10. Extract business signals.
11. Extract reason and evidence text.
12. Compute scores.
13. Use Gemini to polish summary only if GEMINI_API_KEY is available.
14. Store article, entities, signals, reason, evidence, source reference, and scores.
15. Write crawl log.

Crawler must not crash if one source fails.
Failures must be logged into crawl_logs.

==================================================
FMCG KEYWORDS
==================================================

Initial FMCG keywords:

- FMCG
- fast moving consumer goods
- barang konsumsi
- makanan
- minuman
- sembako
- minyak goreng
- gula
- beras
- tepung
- susu
- mie instan
- sabun
- deterjen
- personal care
- household product
- retail
- minimarket
- supermarket
- distributor
- grosir
- stok
- pasokan
- distribusi
- logistik
- kelangkaan
- harga naik
- harga turun
- promo
- diskon
- inflasi
- daya beli
- konsumsi rumah tangga

Initial company, brand, and entity list:

- Unilever
- Indofood
- Mayora
- Wings
- Nestle
- Garudafood
- Wilmar
- Sinar Mas
- Alfamart
- Indomaret
- Hypermart
- Aqua
- Danone
- P&G
- Frisian Flag
- Ajinomoto
- Orang Tua
- Kapal Api
- ABC
- Sasa
- Sosro

==================================================
BUSINESS SIGNAL EXTRACTION RULES
==================================================

Implement initial rule-based signal extraction.

Rules:

1. price_increase
Triggered by:
- harga naik
- kenaikan harga
- harga melonjak
- semakin mahal
- inflasi
- biaya bahan baku naik

2. price_decrease
Triggered by:
- harga turun
- penurunan harga
- diskon besar
- harga melemah
- deflasi

3. shortage
Triggered by:
- langka
- kelangkaan
- stok kosong
- stok habis
- sulit ditemukan
- pasokan terbatas

4. oversupply
Triggered by:
- stok melimpah
- kelebihan pasokan
- oversupply
- persediaan tinggi

5. demand_increase
Triggered by:
- permintaan meningkat
- demand naik
- penjualan naik
- banyak dicari
- konsumsi meningkat

6. demand_decrease
Triggered by:
- permintaan turun
- penjualan turun
- daya beli melemah
- konsumsi menurun

7. negative_sentiment
Triggered by:
- boikot
- keluhan
- viral negatif
- ditarik dari peredaran
- protes konsumen
- isu keamanan produk

8. positive_sentiment
Triggered by:
- viral
- banyak diminati
- tren positif
- disukai konsumen
- penjualan laris

9. regulation_change
Triggered by:
- aturan baru
- regulasi
- pajak
- larangan
- pembatasan
- kebijakan pemerintah

10. distribution_disruption
Triggered by:
- banjir
- kemacetan distribusi
- gangguan logistik
- pelabuhan terganggu
- pengiriman terhambat
- jalan putus

==================================================
REASON AND EVIDENCE EXTRACTION
==================================================

For every detected signal, also extract:

1. reason
A short explanation of why the signal happened.

Example:
Signal: price_increase
Reason: "The price increase appears to be caused by rising raw material costs and limited supply."

2. evidence_text
Short extracted supporting text from the article.

Example:
"Artikel menyebutkan bahwa harga gula meningkat akibat gangguan produksi dan pasokan yang terbatas."

3. source_references
Include:
- article title
- source name
- source URL
- published_at

Important:
The reason must be grounded in the article text.
Do not invent causes.

If the reason is unclear, set:
reason = "The article indicates this signal, but the direct cause is not clearly stated."

==================================================
SCORING SYSTEM
==================================================

Implement scorer.py.

relevance_score:
Based on:
- number of FMCG keywords found
- number of FMCG entities found
- title relevance
- content relevance

signal_severity_score:
Map severity 1-5 into 0.2-1.0.

freshness_score:
- published within 24 hours: 1.0
- within 3 days: 0.8
- within 7 days: 0.6
- older: 0.3
- unknown date: 0.5

impact_score formula:
impact_score =
0.35 * source_credibility_score +
0.25 * signal_severity_score +
0.20 * relevance_score +
0.20 * freshness_score

confidence_score:
Based on:
- source credibility
- article completeness
- number of supporting signals
- presence of evidence_text
- presence of clear reason

urgency:
- high if impact_score >= 0.75
- high if signal_type is shortage, price_increase, or distribution_disruption with severity >= 3
- medium if impact_score >= 0.45
- low otherwise

==================================================
AI GEMINI POLISHING LAYER
==================================================

Use Gemini only for language polishing and structured summarization.

Important rules:
- Gemini must NOT invent facts.
- Gemini must only use:
  - title
  - clean_content
  - extracted signals
  - reason
  - evidence_text
  - source_references
- Gemini output must be validated using Pydantic.
- If Gemini fails, fallback to rule-based summary.
- Use Google Gen AI Python SDK.
- Use structured JSON output when possible.

Gemini output fields:
- polished_title
- polished_summary
- business_reason
- recommended_action
- risk_level
- source_note

Example Gemini prompt behavior:
"Rewrite this extracted signal into a clear business insight for FMCG sub-distributors. Do not add new facts. Use only the provided evidence."

==================================================
AI-READY OUTPUT FORMAT
==================================================

Each processed article/insight must be representable as:

{
  "title": "...",
  "source": {
    "name": "...",
    "url": "...",
    "credibility_score": 0.8
  },
  "article_url": "...",
  "published_at": "...",
  "category": "supply",
  "entities": {
    "product": ["minyak goreng"],
    "company": ["Wilmar"],
    "location": ["Jawa Tengah"],
    "commodity": ["CPO"]
  },
  "signals": [
    {
      "signal_type": "shortage",
      "severity": 4,
      "confidence_score": 0.82,
      "reason": "Distribution was disrupted due to flooding.",
      "evidence_text": "The article mentions flooding and delayed shipments.",
      "explanation": "This may affect product availability in the local market."
    }
  ],
  "reason": "The shortage risk is linked to delayed distribution and limited supply.",
  "evidence_text": "Relevant extracted evidence from the article.",
  "source_references": [
    {
      "title": "...",
      "source": "...",
      "url": "...",
      "published_at": "..."
    }
  ],
  "crawl_stats": {
    "crawled_source_count": 5,
    "related_article_count": 3
  },
  "relevance_score": 0.87,
  "impact_score": 0.81,
  "confidence_score": 0.78,
  "urgency": "high",
  "ai_polished_summary": "..."
}

==================================================
TELEGRAM BOT INTEGRATION
==================================================

Telegram is the main user interface.

Use BotFather to create the bot and get TELEGRAM_BOT_TOKEN.

Bot commands:

1. /start
Show introduction and explain what the bot does.

2. /menu
Show available commands.

3. /alert
Show high urgency FMCG alerts.

4. /report
Show daily summary:
- top price signals
- top shortage signals
- top demand signals
- top sentiment signals

5. /search <keyword>
Search insights by product, company, location, or commodity.

Example:
/search minyak goreng
/search gula
/search Indofood
/search Jawa Barat

6. /trending
Show most frequent entities and signals.

7. /subscribe
Subscribe current Telegram chat to high urgency alerts.

8. /unsubscribe
Disable alert subscription.

Telegram output must be simple and actionable.

Example Telegram alert:

⚠️ FMCG Business Alert

Product: Cooking Oil
Urgency: HIGH
Signal: Shortage Risk

Reason:
Distribution appears disrupted due to flooding and delayed shipments.

Evidence:
The article mentions limited supply and delayed deliveries in Central Java.

Business Impact:
Sub-distributors may need to monitor supplier availability and prepare buffer stock.

Sources:
1. Source Name - Article Title
2. Source Name - Article Title

Generated Summary:
Gemini-polished business summary here.

==================================================
TELEGRAM WEBHOOK
==================================================

Implement FastAPI webhook for Telegram.

Files:
- telegram_bot/webhook.py
- telegram_bot/main.py
- scripts/set_telegram_webhook.py

Environment variables:
- TELEGRAM_BOT_TOKEN
- TELEGRAM_WEBHOOK_URL
- TELEGRAM_ALLOWED_CHAT_IDS

If TELEGRAM_ALLOWED_CHAT_IDS is set, only allow those chats.
If empty, allow all chats during development.

==================================================
ENVIRONMENT VARIABLES
==================================================

Create .env.example:

DATABASE_URL_DIRECT=
DATABASE_URL_POOLER=

GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_URL=
TELEGRAM_ALLOWED_CHAT_IDS=

CRAWLER_USER_AGENT=FMCGIntelligenceBot/1.0
CRAWLER_TIMEOUT=20
MAX_ARTICLES_PER_SOURCE=50

APP_ENV=development
LOG_LEVEL=INFO

==================================================
REQUIREMENTS.TXT
==================================================

Include at minimum:

sqlalchemy
alembic
psycopg2-binary
pydantic
pydantic-settings
python-dotenv
requests
httpx
beautifulsoup4
feedparser
lxml
python-dateutil
fastapi
uvicorn
python-telegram-bot
google-genai

Pin versions where reasonable and use latest non-deprecated APIs.

==================================================
SEED SOURCES
==================================================

Create scripts/seed_sources.py.

Seed initial sources:
- CNBC Indonesia Business RSS
- Kontan RSS
- Bisnis.com RSS
- Detik Finance RSS
- Antara Ekonomi RSS

If actual RSS URLs are uncertain, use placeholders and mark them clearly in comments so they can be changed easily.

Each source must include:
- name
- url
- source_type = rss
- credibility_score
- is_active

==================================================
README.MD
==================================================

README must include:

1. Project overview
2. System architecture
3. Tech stack
4. Environment setup
5. Neon database setup
6. Explanation of DATABASE_URL_DIRECT vs DATABASE_URL_POOLER
7. Alembic migration guide
8. Seed source guide
9. Run crawler guide
10. Telegram BotFather setup
11. Set Telegram webhook guide
12. Gemini setup
13. Example output
14. Development notes
15. Future improvements

==================================================
BRIEF_DOCUMENT.MD
==================================================

Create a complete BRIEF_DOCUMENT.md with this structure:

Title:
FMCG Business Intelligence Crawling Engine

Sections:

1. Background
This system helps FMCG sub-distributors monitor public market information and convert it into structured business intelligence.

2. Problem
Sub-distributors often lack fast visibility into:
- price changes
- shortages
- stock availability
- distribution disruption
- brand sentiment
- demand shifts
- regulation changes

3. Objective
Build a crawling engine that collects public information, extracts business signals, explains the reason behind each signal, attaches sources, and prepares the data for AI-generated summaries and Telegram delivery.

4. Target Users
- FMCG sub-distributors
- procurement teams
- sales operations
- business intelligence teams
- warehouse/distribution managers

5. Data Sources
- RSS feeds
- business news
- commodity news
- retail news
- government/public regulation news
Future:
- marketplace price tracking
- social media sentiment
- internal stock/sales data

6. Core Output
Structured AI-ready JSON, not final editorial news.

7. Business Signals
Explain each signal:
- price_increase
- price_decrease
- shortage
- oversupply
- demand_increase
- demand_decrease
- positive_sentiment
- negative_sentiment
- regulation_change
- distribution_disruption

8. Reason and Evidence
Each insight must include:
- what happened
- why it happened
- evidence from the article
- source references

9. Decision Support Use Cases
Examples:
- Price increase signal helps distributors prepare price adjustment.
- Shortage signal helps prepare buffer stock.
- Distribution disruption signal helps search alternative supply routes.
- Negative sentiment signal helps monitor brand demand risk.
- Demand increase signal helps plan inventory allocation.

10. System Architecture
Crawler → Cleaner → Relevance Filter → Entity Extractor → Signal Extractor → Reason Extractor → Scorer → Neon PostgreSQL → Gemini Polisher → Telegram Bot

11. Database Strategy
Use Neon PostgreSQL.
Direct connection for migration.
Pooled connection for runtime services.

12. Telegram Bot Strategy
Telegram acts as a lightweight user interface for alerts, reports, search, and subscriptions.

13. AI Strategy
Gemini is used only to polish language and generate clear business summaries from extracted structured data.

14. Future Development
- LLM-based extraction
- pgvector semantic search
- marketplace price monitoring
- social media sentiment analysis
- dashboard
- WhatsApp alerts
- anomaly detection
- forecasting
- recommendation engine

==================================================
CODING REQUIREMENTS
==================================================

- Generate actual working project skeleton.
- Do not only explain.
- Create files and starter code.
- Use type hints.
- Use modular architecture.
- Use service/processor separation.
- Use environment variables.
- Do not hardcode secrets.
- Use UTC timestamps.
- Handle crawler failures gracefully.
- Deduplicate articles.
- Log all crawl activities.
- Use Pydantic validation.
- Use SQLAlchemy ORM.
- Use Alembic migrations.
- Keep code clean and extendable.
- Include basic tests for relevance filter, signal extractor, and scorer.

==================================================
FINAL INSTRUCTION
==================================================

Generate the complete project skeleton and starter code according to this brief.
Make sure it is ready to run after installing dependencies, setting .env, running migrations, seeding sources, and running the crawler.