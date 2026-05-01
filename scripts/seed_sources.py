from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.database import session_scope
from crawling_bot.services.source_service import upsert_source


# =============================================================================
# CATATAN:
# - RSS URL bisa berubah sewaktu-waktu oleh publisher, cek secara berkala.
# - Credibility score: 0.0 (rendah) → 1.0 (sangat kredibel), berdasarkan
#   reputasi editorial, akurasi historis, dan transparansi sumber.
# - Beberapa sumber internasional (FT, WSJ) punya paywall pada konten penuh,
#   tapi RSS headline-nya tetap bisa diakses secara gratis.
# =============================================================================

SEED_SOURCES = [
    # -------------------------------------------------------------------------
    # 🇮🇩 SUMBER INDONESIA
    # -------------------------------------------------------------------------
    {
        "name": "CNBC Indonesia Business RSS",
        "url": "https://www.cnbcindonesia.com/rss",
        "credibility_score": 0.78,
        "notes": "Afiliasi CNBC global, fokus bisnis & pasar modal Indonesia.",
    },
    {
        "name": "Kontan RSS",
        "url": "https://www.kontan.co.id/rss",
        "credibility_score": 0.76,
        "notes": "Harian bisnis & investasi terkemuka di Indonesia.",
    },
    {
        "name": "Bisnis.com RSS",
        "url": "https://www.bisnis.com/rss",
        "credibility_score": 0.76,
        "notes": "Berita bisnis, ekonomi, dan keuangan nasional.",
    },
    {
        "name": "Detik Finance RSS",
        "url": "https://finance.detik.com/rss",
        "credibility_score": 0.74,
        "notes": "Rubrik keuangan dari portal berita terbesar Indonesia.",
    },
    {
        "name": "Antara Ekonomi RSS",
        "url": "https://www.antaranews.com/rss/ekonomi.xml",
        "credibility_score": 0.80,
        "notes": "Kantor berita resmi negara, akurasi tinggi untuk berita ekonomi makro.",
    },
    {
        "name": "Tempo Bisnis RSS",
        "url": "https://rss.tempo.co/bisnis",
        "credibility_score": 0.79,
        "notes": "Rubrik bisnis dari media investigatif terpercaya Tempo.",
    },
    {
        "name": "Republika Ekonomi RSS",
        "url": "https://www.republika.co.id/rss/ekonomi",
        "credibility_score": 0.72,
        "notes": "Berita ekonomi & bisnis dari Republika.",
    },
    {
        "name": "Liputan6 Bisnis RSS",
        "url": "https://www.liputan6.com/rss/bisnis",
        "credibility_score": 0.71,
        "notes": "Portal berita besar, cakupan bisnis & keuangan luas.",
    },
    {
        "name": "IDX Channel RSS",
        "url": "https://www.idxchannel.com/feed",
        "credibility_score": 0.75,
        "notes": "Fokus pasar modal dan saham Indonesia, afiliasi Bursa Efek Indonesia.",
    },
    {
        "name": "Investor Daily RSS",
        "url": "https://investor.id/feed",
        "credibility_score": 0.77,
        "notes": "Harian khusus investor dan pasar modal Indonesia.",
    },

    # -------------------------------------------------------------------------
    # 🌏 SUMBER INTERNASIONAL — ASIA PACIFIC
    # -------------------------------------------------------------------------
    {
        "name": "Nikkei Asia Business RSS",
        "url": "https://asia.nikkei.com/rss/feed/nar",
        "credibility_score": 0.85,
        "notes": "Afiliasi Nikkei Jepang, cakupan bisnis Asia Pasifik sangat kuat.",
    },
    {
        "name": "South China Morning Post Business RSS",
        "url": "https://www.scmp.com/rss/92/feed",
        "credibility_score": 0.80,
        "notes": "Media Hong Kong terkemuka untuk berita bisnis Asia.",
    },
    {
        "name": "Channel NewsAsia Business RSS",
        "url": "https://www.channelnewsasia.com/rssfeeds/8395986",
        "credibility_score": 0.79,
        "notes": "Media Singapura, fokus bisnis & ekonomi Asia Tenggara.",
    },
    {
        "name": "The Hindu BusinessLine RSS",
        "url": "https://www.thehindubusinessline.com/?service=rss",
        "credibility_score": 0.77,
        "notes": "Media bisnis India terkemuka, bagus untuk berita Asia Selatan.",
    },

    # -------------------------------------------------------------------------
    # 🌍 SUMBER INTERNASIONAL — GLOBAL
    # -------------------------------------------------------------------------
    {
        "name": "Reuters Business RSS",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "credibility_score": 0.92,
        "notes": "Kantor berita internasional paling kredibel, standar emas jurnalisme.",
    },
    {
        "name": "BBC Business RSS",
        "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "credibility_score": 0.90,
        "notes": "Berita bisnis global dari BBC, sangat kredibel dan netral.",
    },
    {
        "name": "AP Business News RSS",
        "url": "https://rsshub.app/apnews/topics/business-news",
        "credibility_score": 0.91,
        "notes": "Associated Press, lembaga berita non-profit terpercaya global.",
    },
    {
        "name": "CNBC Business RSS",
        "url": "https://www.cnbc.com/id/19746125/device/rss/rss.xml",
        "credibility_score": 0.82,
        "notes": "Berita bisnis & pasar keuangan Amerika, diakses global.",
    },
    {
        "name": "Yahoo Finance RSS",
        "url": "https://finance.yahoo.com/news/rssindex",
        "credibility_score": 0.75,
        "notes": "Agregator berita keuangan global, update sangat cepat.",
    },
    {
        "name": "MarketWatch RSS",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories/",
        "credibility_score": 0.80,
        "notes": "Bagian dari WSJ/Dow Jones, fokus pasar saham dan berita finansial.",
    },
    {
        "name": "Fortune Business RSS",
        "url": "https://fortune.com/feed/",
        "credibility_score": 0.82,
        "notes": "Media bisnis global bergengsi, terkenal dengan daftar Fortune 500.",
    },
    {
        "name": "Forbes Business RSS",
        "url": "https://www.forbes.com/business/feed/",
        "credibility_score": 0.78,
        "notes": "Berita bisnis, entrepreneurship, dan daftar kekayaan global.",
    },
    {
        "name": "Harvard Business Review RSS",
        "url": "https://hbr.org/feed",
        "credibility_score": 0.88,
        "notes": "Sangat kredibel untuk insight manajemen, strategi, dan leadership bisnis.",
    },
    {
        "name": "Nasdaq Market News RSS",
        "url": "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
        "credibility_score": 0.83,
        "notes": "Berita langsung dari bursa Nasdaq, data pasar saham real-time.",
    },
    {
        "name": "Financial Times RSS",
        "url": "https://www.ft.com/?format=rss",
        "credibility_score": 0.91,
        "notes": "Salah satu media bisnis paling prestisius di dunia. Konten penuh ber-paywall, tapi RSS headline bebas.",
    },
    {
        "name": "The Economist Business RSS",
        "url": "https://www.economist.com/business/rss.xml",
        "credibility_score": 0.90,
        "notes": "Analisis mendalam bisnis global, diakui sebagai referensi ekonomi terpercaya.",
    },
    {
        "name": "Al Jazeera Business RSS",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "credibility_score": 0.80,
        "notes": "Perspektif global non-Barat, bagus untuk berita bisnis emerging markets.",
    },

    # -------------------------------------------------------------------------
    # 📊 SUMBER KHUSUS — DATA & RISET
    # -------------------------------------------------------------------------
    {
        "name": "World Bank Data News RSS",
        "url": "https://www.worldbank.org/en/rss?lang=en&cat=news",
        "credibility_score": 0.90,
        "notes": "Data dan analisis ekonomi global dari lembaga internasional.",
    },
    {
        "name": "IMF News RSS",
        "url": "https://www.imf.org/en/News/rss",
        "credibility_score": 0.92,
        "notes": "Laporan dan analisis ekonomi makro global dari IMF.",
    },
    {
        "name": "WTO News RSS",
        "url": "https://www.wto.org/english/news_e/news_e.rss",
        "credibility_score": 0.88,
        "notes": "Berita perdagangan internasional resmi dari WTO.",
    },
    {
        "name": "TechCrunch Startups RSS",
        "url": "https://techcrunch.com/category/startups/feed/",
        "credibility_score": 0.79,
        "notes": "Berita startup, venture capital, dan bisnis teknologi global.",
    },
]


def main() -> None:
    indonesia_sources = [s for s in SEED_SOURCES if "🇮🇩" not in s.get("notes", "") 
                         and any(domain in s["url"] for domain in [
                             "cnbcindonesia", "kontan", "bisnis.com", "detik",
                             "antaranews", "tempo", "republika", "liputan6",
                             "idxchannel", "investor.id"
                         ])]
    international_sources = [s for s in SEED_SOURCES if s not in indonesia_sources]

    with session_scope() as session:
        for item in SEED_SOURCES:
            upsert_source(
                session,
                name=item["name"],
                url=item["url"],
                source_type="rss",
                credibility_score=item["credibility_score"],
                is_active=True,
            )

    print(f"✅ Seeded {len(SEED_SOURCES)} sources total.")
    print(f"   🇮🇩 Indonesia : {len(indonesia_sources)} sumber")
    print(f"   🌍 Internasional: {len(international_sources)} sumber")


if __name__ == "__main__":
    main()
