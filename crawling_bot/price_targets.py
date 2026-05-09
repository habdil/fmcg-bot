"""Konfigurasi price targets — produk dan URL yang dipantau harganya.

Digunakan oleh:
- crawling_bot.services.price_crawler_service  (on-demand crawl dari ChatEngine)
- scripts.run_price_crawler                    (scheduled/manual crawl)
- scripts.seed_price_sources                   (listing konfigurasi)

Untuk menambah produk baru: tambah PriceTarget di dalam PriceSourceConfig
yang sesuai, isi URL, dan set enabled=True.

=============================================================================
STATUS SUMBER (per Mei 2026)
=============================================================================
  [OK]  KlikIndogrosir             — aktif, playwright, harga grosir B2B
  [API] PIHPS Bank Indonesia       — disabled sampai fetcher API khusus dibuat
  [DOWN] Panel Harga Badan Pangan  — under maintenance, semua disabled
  [404]  Info Pangan Jakarta        — endpoint publik berubah, perlu reverifikasi
  [OK]  Tokopedia (search pages)   — aktif, playwright, harga eceran marketplace
  [404] Poultry Indonesia          — kategori harga lama 404, disabled

=============================================================================
PANDUAN KATEGORI PRODUK (prioritas UMKM kuliner & retail kecil)
=============================================================================
  A. Protein & Lauk    : ayam, daging sapi, telur, tahu, tempe, ikan
  B. Bahan Pokok       : beras, minyak goreng, gula, tepung, mie
  C. Bumbu & Rempah    : bawang merah, bawang putih, cabe merah, cabe rawit
  D. Minuman (kuliner) : kopi, susu, teh, sirup
  E. Gas & Energi      : LPG 3kg, LPG 12kg
  F. Kemasan           : plastik kresek, cup, mika kotak nasi, kertas nasi
=============================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PriceTarget:
    product_name: str
    url: str
    reference_label: str
    location: str | None = None
    enabled: bool = True
    # "httpx"      → request biasa, untuk situs tanpa anti-bot
    # "playwright" → Chromium headless, untuk situs dengan Cloudflare/JS-heavy
    fetch_method: str = "httpx"
    # Keyword untuk matching query user, misal: ["minyak goreng", "tropical", "bimoli"]
    # Jika kosong, sistem akan match dari product_name secara otomatis
    match_keywords: list[str] = field(default_factory=list)


@dataclass
class PriceSourceConfig:
    source_name: str
    source_url: str
    targets: list[PriceTarget] = field(default_factory=list)
    notes: str = ""


PRICE_SOURCE_CONFIGS: list[PriceSourceConfig] = [

    # =========================================================================
    # KlikIndogrosir — Platform online grosir Indogrosir
    # fetch_method="playwright" karena situs pakai bot-protection (403 tanpa browser)
    # Harga cenderung lebih dekat ke HPP/harga beli UMKM
    # =========================================================================
    PriceSourceConfig(
        source_name="KlikIndogrosir",
        source_url="https://www.klikindogrosir.com",
        notes="Grosir B2B Indogrosir. Harga relevan untuk estimasi HPP UMKM.",
        targets=[

            # --- A. Protein & Lauk ---
            PriceTarget(
                product_name="Telur Ayam Negeri Curah",
                url="https://klikindogrosir.com/product_details/0079631",
                reference_label="KlikIndogrosir – Telur Ayam Negeri Curah",
                fetch_method="playwright",
                match_keywords=["telur", "telur ayam", "telur negeri", "telur ayam ras"],
                enabled=True,
            ),

            # --- B. Bahan Pokok ---
            PriceTarget(
                product_name="Beras SPHP Medium 5kg",
                url="https://www.klikindogrosir.com/product_details/1699371",
                reference_label="KlikIndogrosir – Beras SPHP Medium 5kg",
                fetch_method="playwright",
                match_keywords=["beras", "beras medium", "beras sphp", "beras murah"],
                enabled=True,
            ),
            PriceTarget(
                product_name="Minyak Goreng Tropical 2L",
                url="https://klikindogrosir.com/product_details/1511121",
                reference_label="KlikIndogrosir – Minyak Goreng Tropical 2L",
                fetch_method="playwright",
                match_keywords=["minyak goreng", "tropical", "minyak"],
                enabled=True,
            ),
            PriceTarget(
                product_name="Minyak Goreng Bimoli 2L",
                url="",  # <- cari URL di klikindogrosir.com lalu isi di sini
                reference_label="KlikIndogrosir – Minyak Goreng Bimoli 2L",
                fetch_method="playwright",
                match_keywords=["minyak goreng", "bimoli", "minyak"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Gula Pasir Premium 1kg",
                url="https://klikindogrosir.com/product_details/1285041",
                reference_label="KlikIndogrosir – Gula Pasir Premium 1kg",
                fetch_method="playwright",
                match_keywords=["gula", "gula pasir"],
                enabled=True,
            ),
            PriceTarget(
                product_name="Gulaku Gula Tebu 1kg",
                url="https://klikindogrosir.com/product_details/0646901",
                reference_label="KlikIndogrosir – Gulaku Gula Tebu 1kg",
                fetch_method="playwright",
                match_keywords=["gula", "gulaku", "gula tebu"],
                enabled=True,
            ),
            PriceTarget(
                product_name="Tepung Terigu Segitiga Biru 25kg",
                url="https://www.klikindogrosir.com/product_details/0815001",
                reference_label="KlikIndogrosir – Tepung Terigu Segitiga Biru 25kg",
                fetch_method="playwright",
                match_keywords=["tepung", "terigu", "segitiga biru"],
                enabled=True,
            ),
            PriceTarget(
                product_name="Mie Goreng Indomie 90g",
                url="https://klikindogrosir.com/product_details/1312541",
                reference_label="KlikIndogrosir – Mie Goreng Indomie 90g",
                fetch_method="playwright",
                match_keywords=["mie", "indomie", "mie goreng", "mi goreng"],
                enabled=True,
            ),

            # --- C. Bumbu & Rempah ---
            PriceTarget(
                product_name="Bawang Merah",
                url="https://www.klikindogrosir.com/product_details/0555921",
                reference_label="KlikIndogrosir – Bawang Merah",
                fetch_method="playwright",
                match_keywords=["bawang merah", "bawang"],
                enabled=True,
            ),

            # --- D. Minuman (kuliner) ---
            PriceTarget(
                product_name="Frisian Flag Gold SKM Putih 6x38g",
                url="https://klikindogrosir.com/product_details/0431351",
                reference_label="KlikIndogrosir – Frisian Flag SKM Putih 6x38g",
                fetch_method="playwright",
                match_keywords=["susu kental manis", "skm", "frisian flag", "susu"],
                enabled=True,
            ),
            PriceTarget(
                product_name="Teh Celup Sariwangi 25s",
                url="",  # <- cari URL di klikindogrosir.com
                reference_label="KlikIndogrosir – Teh Sariwangi 25s",
                fetch_method="playwright",
                match_keywords=["teh", "sariwangi", "teh celup"],
                enabled=False,
            ),
        ],
    ),

    # =========================================================================
    # PIHPS Bank Indonesia — Pusat Informasi Harga Pangan Strategis Nasional
    # Sumber resmi BI untuk harga pasar tradisional nasional
    # STATUS: disabled sampai fetcher API khusus dibuat.
    # Data update harian, sangat relevan untuk referensi harga UMKM
    #
    # Catatan teknis:
    #   - Satu URL = semua komoditas dalam satu tabel
    #   - Crawler perlu extract per-baris berdasarkan nama komoditas
    #   - API backend: /hargapangan/WebSite/TabelHarga/GetGridDataKomoditas
    # =========================================================================
    PriceSourceConfig(
        source_name="PIHPS Bank Indonesia",
        source_url="https://www.bi.go.id/hargapangan",
        notes=(
            "Pusat Informasi Harga Pangan Strategis Nasional dari Bank Indonesia. "
            "Harga pasar tradisional nasional, update harian. "
            "Semua komoditas tampil di satu tabel — crawler extract per baris. "
            "API: /hargapangan/WebSite/TabelHarga/GetGridDataKomoditas"
        ),
        targets=[

            # --- A. Protein & Lauk ---
            PriceTarget(
                product_name="Daging Ayam Ras",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Daging Ayam Ras (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["ayam", "ayam ras", "daging ayam", "ayam potong"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Daging Sapi Murni",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Daging Sapi Murni (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["daging sapi", "sapi", "daging"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Telur Ayam Ras",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Telur Ayam Ras (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["telur", "telur ayam", "telur ras"],
                enabled=False,
            ),

            # --- B. Bahan Pokok ---
            PriceTarget(
                product_name="Beras Kualitas Medium I",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Beras Kualitas Medium I (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["beras", "beras medium"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Beras Kualitas Super I",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Beras Kualitas Super I (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["beras premium", "beras super", "beras"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Minyak Goreng Curah",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Minyak Goreng Curah (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["minyak goreng curah", "minyak curah"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Gula Pasir Lokal",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Gula Pasir Lokal (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["gula pasir", "gula"],
                enabled=False,
            ),

            # --- C. Bumbu & Rempah ---
            PriceTarget(
                product_name="Bawang Merah",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Bawang Merah (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["bawang merah", "bawang"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Bawang Putih Bonggol",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Bawang Putih Bonggol (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["bawang putih", "bawang"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Cabai Merah Keriting",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Cabai Merah Keriting (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["cabe merah", "cabai merah", "cabai", "cabe"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Cabai Rawit Merah",
                url="https://www.bi.go.id/hargapangan/TabelHarga/PasarTradisionalKomoditas",
                reference_label="PIHPS BI – Cabai Rawit Merah (pasar tradisional)",
                fetch_method="playwright",
                match_keywords=["cabe rawit", "cabai rawit", "rawit"],
                enabled=False,
            ),
        ],
    ),

    # =========================================================================
    # Panel Harga Pangan Nasional (Badan Pangan)
    # STATUS: UNDER MAINTENANCE per Mei 2026 — semua target disabled
    # Cek kembali di: panelharga.badanpangan.go.id atau hubungi support@badanpangan.go.id
    # =========================================================================
    PriceSourceConfig(
        source_name="Panel Harga Pangan Nasional",
        source_url="https://panelharga.badanpangan.go.id",
        notes=(
            "Data resmi Badan Pangan Nasional. "
            "STATUS: Under maintenance per Mei 2026. Semua target disabled."
        ),
        targets=[
            PriceTarget(
                product_name="Ayam Ras Segar",
                url="",
                reference_label="Panel Harga Badan Pangan – Daging Ayam Ras",
                match_keywords=["ayam", "ayam ras", "ayam potong", "daging ayam"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Daging Sapi Murni",
                url="",
                reference_label="Panel Harga Badan Pangan – Daging Sapi",
                match_keywords=["daging sapi", "sapi", "daging"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Telur Ayam Ras",
                url="",
                reference_label="Panel Harga Badan Pangan – Telur Ayam Ras",
                match_keywords=["telur", "telur ayam", "telur ras"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Beras Medium",
                url="",
                reference_label="Panel Harga Badan Pangan – Beras Medium",
                match_keywords=["beras", "beras medium"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Beras Premium",
                url="",
                reference_label="Panel Harga Badan Pangan – Beras Premium",
                match_keywords=["beras premium", "beras"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Minyak Goreng Curah",
                url="",
                reference_label="Panel Harga Badan Pangan – Minyak Goreng Curah",
                match_keywords=["minyak goreng curah", "minyak curah"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Gula Pasir",
                url="",
                reference_label="Panel Harga Badan Pangan – Gula Pasir",
                match_keywords=["gula pasir", "gula"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Bawang Merah",
                url="",
                reference_label="Panel Harga Badan Pangan – Bawang Merah",
                match_keywords=["bawang merah", "bawang"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Bawang Putih Bonggol",
                url="",
                reference_label="Panel Harga Badan Pangan – Bawang Putih",
                match_keywords=["bawang putih", "bawang"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Cabai Merah Keriting",
                url="",
                reference_label="Panel Harga Badan Pangan – Cabai Merah Keriting",
                match_keywords=["cabe merah", "cabai merah", "cabai"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Cabai Rawit Merah",
                url="",
                reference_label="Panel Harga Badan Pangan – Cabai Rawit Merah",
                match_keywords=["cabe rawit", "cabai rawit", "rawit"],
                enabled=False,
            ),
        ],
    ),

    # =========================================================================
    # Info Pangan Jakarta — Dinas KPKP Pemprov DKI Jakarta
    # STATUS: Endpoint publik lama (404 per Mei 2026) — perlu reverifikasi URL
    # Alternatif: cek https://infopangan.jakarta.go.id langsung di browser
    # =========================================================================
    PriceSourceConfig(
        source_name="Info Pangan Jakarta",
        source_url="https://infopangan.jakarta.go.id",
        notes=(
            "Harga pangan harian pasar tradisional Jakarta dari Dinas KPKP. "
            "STATUS: Endpoint publik berubah (404 per Mei 2026). "
            "Perlu verifikasi URL aktif sebelum enable. "
            "Relevan untuk UMKM Jabodetabek."
        ),
        targets=[
            PriceTarget(
                product_name="Daging Ayam Ras",
                url="",  # <- endpoint publik berubah, reverifikasi dulu
                reference_label="Info Pangan Jakarta – Daging Ayam Ras",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["ayam", "ayam ras", "daging ayam", "ayam potong"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Daging Sapi",
                url="",
                reference_label="Info Pangan Jakarta – Daging Sapi",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["daging sapi", "sapi"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Telur Ayam Ras",
                url="",
                reference_label="Info Pangan Jakarta – Telur Ayam Ras",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["telur", "telur ayam"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Tahu Putih",
                url="",
                reference_label="Info Pangan Jakarta – Tahu Putih",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["tahu", "tahu putih"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Tempe",
                url="",
                reference_label="Info Pangan Jakarta – Tempe",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["tempe"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Beras IR 64",
                url="",
                reference_label="Info Pangan Jakarta – Beras IR 64",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["beras", "beras ir64"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Minyak Goreng Curah",
                url="",
                reference_label="Info Pangan Jakarta – Minyak Goreng Curah",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["minyak goreng curah", "minyak curah"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Gula Pasir Lokal",
                url="",
                reference_label="Info Pangan Jakarta – Gula Pasir Lokal",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["gula pasir", "gula"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Bawang Merah",
                url="",
                reference_label="Info Pangan Jakarta – Bawang Merah",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["bawang merah", "bawang"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Bawang Putih",
                url="",
                reference_label="Info Pangan Jakarta – Bawang Putih",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["bawang putih", "bawang"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Cabai Merah Keriting",
                url="",
                reference_label="Info Pangan Jakarta – Cabai Merah Keriting",
                location="Jakarta",
                fetch_method="playwright",
                match_keywords=["cabe merah", "cabai merah", "cabai"],
                enabled=False,
            ),
        ],
    ),

    # =========================================================================
    # Tokopedia — Referensi harga kemasan & bahan baku dari marketplace
    # URL "find" page = halaman kategori/search Tokopedia, bukan produk tunggal
    # fetch_method="playwright" karena Tokopedia butuh JS rendering
    # Berguna untuk: kemasan, kopi, susu, gas LPG — harga eceran & supplier alt
    # =========================================================================
    PriceSourceConfig(
        source_name="Tokopedia",
        source_url="https://www.tokopedia.com",
        notes=(
            "Marketplace terbesar Indonesia. Dipakai sebagai referensi harga kemasan, "
            "bahan baku, dan supplier alternatif untuk UMKM. "
            "URL pointing ke halaman search/find kategori — crawler extract harga terendah dari listing."
        ),
        targets=[

            # --- E. Gas & Energi ---
            PriceTarget(
                product_name="Gas LPG 3kg",
                url="https://www.tokopedia.com/find/gas-lpg-3-kg",
                reference_label="Tokopedia – Gas LPG 3kg (search page)",
                fetch_method="playwright",
                match_keywords=["gas lpg", "lpg 3kg", "gas melon", "gas 3kg", "gas"],
                enabled=False,  # aktifkan setelah crawler bisa parse listing page Tokopedia
            ),

            # --- F. Kemasan ---
            PriceTarget(
                product_name="Kantong Plastik Kresek Grosir",
                url="https://www.tokopedia.com/find/grosir-plastik-kresek",
                reference_label="Tokopedia – Grosir Kantong Plastik Kresek (search page)",
                fetch_method="playwright",
                match_keywords=["plastik", "kresek", "kantong plastik", "tas plastik"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Cup Plastik Minuman 12oz",
                url="https://www.tokopedia.com/find/cup-plastik-minuman-12-oz",
                reference_label="Tokopedia – Cup Plastik Minuman 12oz (search page)",
                fetch_method="playwright",
                match_keywords=["cup plastik", "gelas plastik", "cup minuman", "cup 12oz"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Mika Kotak Nasi",
                url="https://www.tokopedia.com/find/mika-kotak-nasi",
                reference_label="Tokopedia – Mika Kotak Nasi (search page)",
                fetch_method="playwright",
                match_keywords=["mika kotak nasi", "kotak nasi", "kemasan nasi", "bungkus nasi"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Kertas Nasi Putih",
                url="https://www.tokopedia.com/find/kertas-nasi",
                reference_label="Tokopedia – Kertas Nasi Putih (search page)",
                fetch_method="playwright",
                match_keywords=["kertas nasi", "bungkus nasi kertas"],
                enabled=False,
            ),

            # --- D. Minuman (kuliner coffee shop) ---
            PriceTarget(
                product_name="Biji Kopi Robusta 1kg",
                url="https://www.tokopedia.com/find/biji-kopi-robusta-1kg",
                reference_label="Tokopedia – Biji Kopi Robusta 1kg (search page)",
                fetch_method="playwright",
                match_keywords=["kopi", "biji kopi", "robusta", "kopi robusta"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Biji Kopi Arabika 1kg",
                url="https://www.tokopedia.com/find/biji-kopi-arabika-1kg",
                reference_label="Tokopedia – Biji Kopi Arabika 1kg (search page)",
                fetch_method="playwright",
                match_keywords=["kopi arabika", "arabika", "biji kopi"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Susu Full Cream Bubuk 1kg",
                url="https://www.tokopedia.com/find/susu-bubuk-full-cream-1-kg",
                reference_label="Tokopedia – Susu Full Cream Bubuk 1kg (search page)",
                fetch_method="playwright",
                match_keywords=["susu bubuk", "full cream", "susu"],
                enabled=False,
            ),
        ],
    ),

    # =========================================================================
    # Poultry Indonesia — Portal industri perunggasan Indonesia
    # Sumber berita harga ayam hidup, ayam potong, dan telur
    # fetch_method="httpx" karena situs HTML biasa (tidak ada bot-protection berat)
    # Crawler perlu extract angka harga dari artikel terbaru
    # =========================================================================
    PriceSourceConfig(
        source_name="Poultry Indonesia",
        source_url="https://www.poultryindonesia.com",
        notes=(
            "Portal industri perunggasan Indonesia. "
            "Memuat data harga ayam broiler, ayam potong, dan telur tingkat peternak & pasar. "
            "STATUS: kategori harga lama 404 pada 2026-05-10. Semua target disabled."
        ),
        targets=[
            PriceTarget(
                product_name="Ayam Broiler",
                url="https://www.poultryindonesia.com/id/category/harga/",
                reference_label="Poultry Indonesia – Harga Ayam Broiler (halaman kategori)",
                fetch_method="httpx",
                match_keywords=["ayam broiler", "ayam hidup", "ayam potong", "ayam", "daging ayam"],
                enabled=False,
            ),
            PriceTarget(
                product_name="Telur Ayam Ras",
                url="https://www.poultryindonesia.com/id/category/harga/",
                reference_label="Poultry Indonesia – Harga Telur Ayam Ras (halaman kategori)",
                fetch_method="httpx",
                match_keywords=["telur", "telur ayam", "telur ras"],
                enabled=False,
            ),
        ],
    ),
]
