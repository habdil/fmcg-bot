from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from crawling_bot.database import session_scope
from crawling_bot.services.source_service import upsert_source


# =============================================================================
# SEED SOURCES — KHUSUS FMCG
#
# Dibagi ke dalam 5 kelompok berdasarkan kebutuhan analisis FMCG:
#   1. Trade Publication F&B & FMCG (tren produk, inovasi, kategori)
#   2. Retail & Modern Trade Indonesia (pergerakan channel distribusi)
#   3. Regulasi & Kebijakan Pemerintah Indonesia (compliance, BPOM, Kemendag)
#   4. Komoditas & Supply Chain (harga bahan baku CPO, gula, gandum)
#   5. Consumer Behavior & Marketing (insight perilaku konsumen)
#
# CATATAN:
# - Credibility score: 0.0 → 1.0 (berdasarkan reputasi editorial & akurasi)
# - Beberapa sumber trade publication bisa butuh verifikasi URL secara berkala
# - Sumber komoditas umumnya update mingguan/bulanan, bukan harian
# =============================================================================

SEED_SOURCES_FMCG = [

    # =========================================================================
    # 📰 1. TRADE PUBLICATION — F&B & FMCG GLOBAL / ASIA
    # =========================================================================

    {
        "name": "FoodNavigator Asia RSS",
        "url": "https://www.foodnavigator-asia.com/feed/view/372210",
        "credibility_score": 0.85,
        "category": "trade_publication",
        "notes": (
            "Trade pub utama F&B Asia Pasifik. Cakupan: inovasi produk, "
            "regulasi pangan, tren konsumen, teknologi pengolahan. "
            "Update harian, sangat relevan untuk FMCG kategori food & beverage."
        ),
    },
    {
        "name": "Food Business News RSS",
        "url": "https://www.foodbusinessnews.net/rss/articles",
        "credibility_score": 0.83,
        "category": "trade_publication",
        "notes": (
            "Media industri F&B Amerika yang diakui global. "
            "Fokus: M&A perusahaan FMCG besar, inovasi produk, tren kategori. "
            "Bagus untuk benchmark strategi korporat pemain global."
        ),
    },
    {
        "name": "Food & Beverage Asia RSS",
        "url": "https://www.foodbeverageasia.com/feed",
        "credibility_score": 0.80,
        "category": "trade_publication",
        "notes": (
            "Media industri F&B Asia sejak 2002. "
            "Cakupan: manufaktur, kemasan, teknologi proses, tren pasar Asia. "
            "Relevan untuk analisis supply chain & inovasi kategori."
        ),
    },
    {
        "name": "The Grocer UK RSS",
        "url": "https://www.thegrocer.co.uk/34272.rss",
        "credibility_score": 0.86,
        "category": "trade_publication",
        "notes": (
            "Media FMCG & grocery retail terkemuka di UK. "
            "Cakupan: tren kategori, private label, promosi, data pasar. "
            "Bagus untuk benchmark strategi retail FMCG global."
        ),
    },
    {
        "name": "Packaging World RSS",
        "url": "https://www.packworld.com/rss.xml",
        "credibility_score": 0.78,
        "category": "trade_publication",
        "notes": (
            "Fokus inovasi kemasan produk FMCG global. "
            "Relevan untuk tren sustainable packaging, material baru, "
            "dan compliance regulasi kemasan."
        ),
    },
    {
        "name": "Cosmetics & Toiletries RSS",
        "url": "https://www.cosmeticsandtoiletries.com/feed",
        "credibility_score": 0.80,
        "category": "trade_publication",
        "notes": (
            "Trade pub khusus FMCG personal care & beauty. "
            "Cakupan: formulasi produk, bahan aktif, regulasi, tren kategori. "
            "Penting untuk pemain FMCG segmen HPC (Home & Personal Care)."
        ),
    },
    {
        "name": "Retail Asia RSS",
        "url": "https://retailasia.com/rss/feed",
        "credibility_score": 0.79,
        "category": "trade_publication",
        "notes": (
            "Cakupan industri ritel Asia termasuk grocery & convenience store. "
            "Relevan untuk memantau tren modern trade di Asia Tenggara."
        ),
    },

    # =========================================================================
    # 🏪 2. RETAIL & MODERN TRADE — INDONESIA
    # =========================================================================

    {
        "name": "SWA Magazine RSS",
        "url": "https://swa.co.id/feed",
        "credibility_score": 0.78,
        "category": "retail_indonesia",
        "notes": (
            "Media bisnis & marketing Indonesia terkemuka. "
            "Cakupan: strategi brand FMCG, riset konsumen, tren ritel. "
            "Sering publish studi kasus perusahaan FMCG lokal & multinasional."
        ),
    },
    {
        "name": "Marketing.co.id RSS",
        "url": "https://marketing.co.id/feed",
        "credibility_score": 0.74,
        "category": "retail_indonesia",
        "notes": (
            "Portal marketing & bisnis Indonesia. "
            "Cakupan: insight konsumen, strategi brand, tren channel distribusi, "
            "dan analisis kategori produk FMCG Indonesia."
        ),
    },
    {
        "name": "Majalah Franchise & Bisnis RSS",
        "url": "https://www.franchisebisnis.com/feed",
        "credibility_score": 0.70,
        "category": "retail_indonesia",
        "notes": (
            "Relevan untuk memantau ekspansi jaringan ritel & convenience store "
            "yang menjadi channel utama distribusi FMCG di Indonesia."
        ),
    },
    {
        "name": "Katadata Bisnis RSS",
        "url": "https://katadata.co.id/rss",
        "credibility_score": 0.80,
        "category": "retail_indonesia",
        "notes": (
            "Media data & bisnis Indonesia dengan analisis mendalam. "
            "Sering publish data pertumbuhan kategori, consumer spending, "
            "dan analisis pemain FMCG di pasar Indonesia."
        ),
    },

    # =========================================================================
    # ⚖️ 3. REGULASI & KEBIJAKAN PEMERINTAH INDONESIA
    # =========================================================================

    {
        "name": "Kemendag Berita Perdagangan RSS",
        "url": "https://statistik.kemendag.go.id/rss/category/berita-perdagangan",
        "credibility_score": 0.85,
        "category": "regulation_indonesia",
        "notes": (
            "Sumber resmi berita perdagangan dari Kementerian Perdagangan RI. "
            "Krusial untuk memantau kebijakan impor/ekspor bahan baku FMCG, "
            "regulasi harga eceran tertinggi (HET), dan kebijakan distribusi."
        ),
    },
    {
        "name": "Kemendag Perdagangan Dalam Negeri RSS",
        "url": "https://statistik.kemendag.go.id/rss/category/perdagangan-dalam-negeri",
        "credibility_score": 0.85,
        "category": "regulation_indonesia",
        "notes": (
            "Data perdagangan dalam negeri dari Kemendag. "
            "Relevan untuk analisis distribusi domestik, "
            "monitoring stok dan harga komoditas kebutuhan pokok."
        ),
    },
    {
        "name": "Kemendag Ekspor Impor RSS",
        "url": "https://statistik.kemendag.go.id/rss/category/indonesia-export-import",
        "credibility_score": 0.86,
        "category": "regulation_indonesia",
        "notes": (
            "Data ekspor-impor resmi Indonesia. "
            "Penting untuk memantau arus bahan baku impor FMCG "
            "(susu, gandum, gula, bahan kimia HPC) dan ekspor produk jadi."
        ),
    },
    {
        "name": "Kementan Pertanian RSS",
        "url": "https://www.pertanian.go.id/home/rss.html",
        "credibility_score": 0.82,
        "category": "regulation_indonesia",
        "notes": (
            "Kementerian Pertanian RI. "
            "Krusial untuk FMCG berbasis agrikultur: data produksi CPO, gula, "
            "beras, jagung — komoditas utama bahan baku food & beverage."
        ),
    },
    {
        "name": "BPS Berita Resmi Statistik RSS",
        "url": "https://www.bps.go.id/id/rss-pressrelease",
        "credibility_score": 0.90,
        "category": "regulation_indonesia",
        "notes": (
            "Badan Pusat Statistik RI — data resmi inflasi, IHK, daya beli, "
            "dan pertumbuhan ekonomi. Baseline penting untuk proyeksi "
            "consumer spending dan penetapan harga produk FMCG."
        ),
    },

    # =========================================================================
    # 🌿 4. KOMODITAS & SUPPLY CHAIN
    # =========================================================================

    {
        "name": "Reuters Commodities RSS",
        "url": "https://feeds.reuters.com/reuters/commoditiesNews",
        "credibility_score": 0.91,
        "category": "commodity",
        "notes": (
            "Feed Reuters khusus komoditas global. "
            "Cakupan: harga CPO, gula, gandum, kedelai — semua bahan baku kritis FMCG. "
            "Update real-time, menjadi acuan trading desk global."
        ),
    },
    {
        "name": "GAPKI (Asosiasi Petani Kelapa Sawit) RSS",
        "url": "https://gapki.id/news/feed/",
        "credibility_score": 0.80,
        "category": "commodity",
        "notes": (
            "Gabungan Pengusaha Kelapa Sawit Indonesia. "
            "Sumber data produksi, ekspor, dan kebijakan industri sawit Indonesia. "
            "Langsung relevan untuk FMCG berbasis minyak nabati & oleokimia."
        ),
    },
    {
        "name": "Oil World / USDA WASDE via AgriMoney RSS",
        "url": "https://www.agrimoney.com/rss/feed/",
        "credibility_score": 0.78,
        "category": "commodity",
        "notes": (
            "Berita komoditas agrikultur global: minyak nabati, gandum, gula, susu. "
            "Bagus untuk early warning signal perubahan harga bahan baku FMCG."
        ),
    },
    {
        "name": "Successful Farming Commodity Markets RSS",
        "url": "https://www.agriculture.com/rss/markets",
        "credibility_score": 0.74,
        "category": "commodity",
        "notes": (
            "Data pasar komoditas pertanian AS yang memengaruhi harga global. "
            "Relevan untuk pemantauan harga kedelai, jagung, dan gandum."
        ),
    },
    {
        "name": "Pertamina News RSS",
        "url": "https://www.pertamina.com/rss",
        "credibility_score": 0.81,
        "category": "commodity",
        "notes": (
            "Berita resmi Pertamina — harga BBM & energi sangat memengaruhi "
            "biaya distribusi dan logistik seluruh rantai pasok FMCG Indonesia."
        ),
    },

    # =========================================================================
    # 🧠 5. CONSUMER BEHAVIOR & MARKETING INSIGHT
    # =========================================================================

    {
        "name": "Nielsen IQ Insights RSS",
        "url": "https://nielseniq.com/global/en/insights/feed/",
        "credibility_score": 0.87,
        "category": "consumer_insight",
        "notes": (
            "Riset konsumen dan pasar FMCG dari Nielsen IQ. "
            "Cakupan: panel rumah tangga, share kategori, tren belanja, "
            "dan penetrasi produk di berbagai channel. Benchmark industri."
        ),
    },
    {
        "name": "Kantar Insights RSS",
        "url": "https://www.kantar.com/inspiration/rss",
        "credibility_score": 0.86,
        "category": "consumer_insight",
        "notes": (
            "Riset brand equity, consumer behavior, dan tren pasar dari Kantar. "
            "Sering publish Brand Footprint (brand FMCG paling dipilih konsumen) "
            "yang menjadi acuan benchmark strategi pemasaran."
        ),
    },
    {
        "name": "Mintel Food & Drink RSS",
        "url": "https://www.mintel.com/blog/feed/?category=food-and-drink",
        "credibility_score": 0.85,
        "category": "consumer_insight",
        "notes": (
            "Riset tren konsumen & inovasi produk kategori F&B dari Mintel. "
            "Sangat berguna untuk pemetaan whitespace dan pipeline NPD (New Product Development)."
        ),
    },
    {
        "name": "Think with Google Consumer Trends RSS",
        "url": "https://www.thinkwithgoogle.com/feed/",
        "credibility_score": 0.82,
        "category": "consumer_insight",
        "notes": (
            "Insight perilaku konsumen digital dari Google. "
            "Relevan untuk memantau tren pencarian produk FMCG, "
            "pergeseran preferensi konsumen, dan peluang di e-commerce."
        ),
    },
    {
        "name": "Euromonitor Consumer Goods RSS",
        "url": "https://www.euromonitor.com/rss/articles",
        "credibility_score": 0.85,
        "category": "consumer_insight",
        "notes": (
            "Analisis pasar consumer goods global dari Euromonitor International. "
            "Cakupan: ukuran pasar, proyeksi pertumbuhan kategori, "
            "dan analisis pemain di 100+ negara termasuk Indonesia."
        ),
    },
]


# =============================================================================
# SUMMARY per kategori untuk logging
# =============================================================================

CATEGORY_LABELS = {
    "trade_publication": "📰 Trade Publication F&B/FMCG",
    "retail_indonesia":  "🏪 Retail & Modern Trade Indonesia",
    "regulation_indonesia": "⚖️  Regulasi & Kebijakan Pemerintah",
    "commodity":         "🌿 Komoditas & Supply Chain",
    "consumer_insight":  "🧠 Consumer Behavior & Marketing",
}


def main() -> None:
    counts: dict[str, int] = {k: 0 for k in CATEGORY_LABELS}

    with session_scope() as session:
        for item in SEED_SOURCES_FMCG:
            upsert_source(
                session,
                name=item["name"],
                url=item["url"],
                source_type="rss",
                credibility_score=item["credibility_score"],
                is_active=True,
            )
            cat = item.get("category", "unknown")
            if cat in counts:
                counts[cat] += 1

    print(f"\n✅ Seeded {len(SEED_SOURCES_FMCG)} FMCG sources.\n")
    for cat, label in CATEGORY_LABELS.items():
        print(f"   {label}: {counts[cat]} sumber")
    print()


if __name__ == "__main__":
    main()
