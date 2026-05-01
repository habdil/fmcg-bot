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

## 10. System Architecture

Crawler -> Cleaner -> Relevance Filter -> Entity Extractor -> Signal Extractor -> Reason Extractor -> Scorer -> Neon PostgreSQL -> Gemini Polisher -> Telegram Bot

## 11. Database Strategy

Use Neon PostgreSQL. Direct connection is used for Alembic migrations and schema changes. Pooled connection is used for runtime services such as crawler, API, Telegram bot, and background jobs.

## 12. Telegram Bot Strategy

Telegram acts as a lightweight user interface for alerts, reports, search, trending insights, and subscriptions. It is intentionally simple and operational, so users can act on high urgency signals quickly.

## 13. AI Strategy

Gemini is used only to polish language and generate clear business summaries from extracted structured data. It must not invent facts and must rely only on title, clean content, extracted signals, reason, evidence, and source references.

## 14. Future Development

- LLM-based extraction
- pgvector semantic search
- Marketplace price monitoring
- Social media sentiment analysis
- Dashboard
- WhatsApp alerts
- Anomaly detection
- Forecasting
- Recommendation engine
