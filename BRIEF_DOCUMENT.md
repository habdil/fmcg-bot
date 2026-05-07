# FMCG Business Intelligence Crawling Engine

## 1. Background

This system helps FMCG sub-distributors monitor public market information and convert it into structured business intelligence.

## 2. Problem

Sub-distributors often lack fast visibility into price changes, shortages, stock availability, distribution disruption, brand sentiment, demand shifts, and regulation changes.

## 3. Objective

Build a crawling engine that collects public information, extracts business signals, explains the reason behind each signal, attaches sources, and prepares the data for AI-generated summaries and Telegram delivery.

## 4. Target Users

- FMCG sub-distributors
- Procurement teams
- Sales operations
- Business intelligence teams
- Warehouse and distribution managers

## 5. Data Sources

- RSS feeds
- Business news
- Commodity news
- Retail news
- Government and public regulation news
- Public retail or wholesale price pages when allowed and technically accessible

Future sources:
- Marketplace price tracking
- Social media sentiment
- Internal stock and sales data

## 6. Core Output

The core output is structured AI-ready JSON, not final editorial news. Each record contains source metadata, extracted entities, business signals, reason, evidence, source references, scores, urgency, and optional Gemini-polished business summary.

## 7. Business Signals

- `price_increase`: indication that FMCG prices or costs are increasing.
- `price_decrease`: indication that prices are decreasing or discount pressure is high.
- `shortage`: indication of scarcity, empty stock, or limited supply.
- `oversupply`: indication of excess supply or high inventory.
- `demand_increase`: indication of stronger demand, sales, or consumption.
- `demand_decrease`: indication of weaker demand, sales, or purchasing power.
- `positive_sentiment`: positive consumer or market response to a brand or product.
- `negative_sentiment`: boycott, complaints, product safety issue, or other adverse sentiment.
- `regulation_change`: new public policy, tax, restriction, or distribution rule.
- `distribution_disruption`: logistics, route, port, flood, or delivery disruption.

## 8. Reason and Evidence

Each insight must include what happened, why it happened when stated by the source, evidence from the article, and source references. If the direct cause is unclear, the system must explicitly state that the article indicates the signal but does not clearly state the cause.

## 9. Decision Support Use Cases

- Price increase signal helps distributors prepare price adjustment.
- Shortage signal helps prepare buffer stock.
- Distribution disruption signal helps search alternative supply routes.
- Negative sentiment signal helps monitor brand demand risk.
- Demand increase signal helps plan inventory allocation.

## 10. Price Information Rules

When users ask about product prices, the system should prioritize stored price snapshots or newly crawled price pages from allowed public sources such as retail, wholesale, marketplace, official catalog, or manual/internal inputs.

Price answers must be careful and data-oriented:

- Show the source name.
- Show the product name and pack size when available.
- Show the observed price or price range when available.
- Show the crawl or observation time.
- State that the price is based on sources successfully checked, not a guaranteed market-wide price.
- Do not claim the price is fully accurate for all suppliers, regions, or stores.

If the system cannot find a usable price, the user-facing response should say:

```text
Maaf, kami belum berhasil menemukan harga untuk produk ini dari sumber yang kami cek.
```

If the user asked for a specific pack size or location, include it in the response:

```text
Maaf, kami belum berhasil menemukan harga gula 1 kg untuk wilayah yang Anda maksud dari sumber yang kami cek.
```

When price is unavailable, the answer can still continue with business context from news and public information:

```text
Untuk sementara, analisis ini memakai berita dan pembahasan publik yang berhasil kami temukan. Jadi rekomendasinya lebih cocok dipakai sebagai bahan pantauan, bukan sebagai patokan harga beli.
```

If price data is found during crawling even when the user did not explicitly ask for price, it can be included as a short supporting note, but it must not dominate the answer unless price is the user's main question.

## 11. User-Facing Response Style

User-facing responses should avoid internal technical labels such as `signal`, `signal_type`, `evidence_text`, or `source_coverage`. Those terms can remain inside the database and internal AI prompts, but users should receive natural business language.

Preferred response language:

- "tekanan harga naik" instead of `price_increase`
- "risiko stok terbatas" instead of `shortage`
- "permintaan mulai menguat" instead of `demand_increase`
- "sumber yang dipakai" instead of `source_coverage`
- "dasar informasi" instead of `evidence`

For news, schedules, regulations, promotions, distribution updates, or official announcements, the response must include source references and explain why the information matters for the user's business.

## 12. System Architecture

Crawler -> Cleaner -> Relevance Filter -> Entity Extractor -> Signal Extractor -> Reason Extractor -> Scorer -> Neon PostgreSQL -> Gemini Polisher -> Telegram Bot

## 13. Database Strategy

Use Neon PostgreSQL. Direct connection is used for Alembic migrations and schema changes. Pooled connection is used for runtime services such as crawler, API, Telegram bot, and background jobs.

## 14. Telegram Bot Strategy

Telegram acts as a lightweight user interface for alerts, reports, search, trending insights, and subscriptions. It is intentionally simple and operational, so users can act on high urgency signals quickly.

## 15. AI Strategy

Gemini is used only to polish language and generate clear business summaries from extracted structured data. It must not invent facts and must rely only on title, clean content, extracted signals, reason, evidence, and source references.

## 16. Future Development

- LLM-based extraction
- pgvector semantic search
- Marketplace price monitoring
- Social media sentiment analysis
- Dashboard
- WhatsApp alerts
- Anomaly detection
- Forecasting
- Recommendation engine
