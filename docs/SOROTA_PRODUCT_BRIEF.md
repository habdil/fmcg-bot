# Sorota Product Brief

Dokumen ini menerjemahkan arah produk Sorota dari chatbot/crawling intelligence menjadi AI pendamping keputusan bisnis untuk UMKM Indonesia. Brief ini menjadi pegangan awal sebelum refactor teknis, desain database, pemilihan OpenAI/ChatGPT API sebagai AI provider utama, dan pemisahan tool/MCP.

## 1. Ringkasan Produk

Sorota adalah platform AI pendamping bisnis UMKM Indonesia yang membantu pelaku usaha mengambil keputusan harian dengan lebih cepat, praktis, dan berbasis data pasar.

Sorota membantu UMKM untuk:

- Menganalisa kondisi bisnis.
- Melakukan survey harga pasar.
- Mencari harga termurah atau supplier alternatif.
- Memahami kompetitor.
- Menghitung margin, HPP, dan harga jual.
- Mendapatkan rekomendasi bisnis melalui percakapan AI.

Posisi inti Sorota:

```text
AI pendamping keputusan bisnis harian untuk UMKM Indonesia.
```

Chat adalah interface. Produk utamanya adalah business decision engine yang memanfaatkan data user, data pasar, dan analisa bisnis praktis.

## 2. Problem Statement

Banyak UMKM Indonesia mengambil keputusan bisnis berdasarkan feeling, asumsi, atau informasi pasar yang tidak terstruktur.

Masalah utama yang ingin diselesaikan:

- Sulit menentukan harga jual yang sehat.
- Sulit mengetahui harga pasar terbaru.
- Sulit membandingkan supplier.
- Sulit memahami apakah margin masih aman.
- Sulit membaca kondisi kompetitor.
- Sulit menentukan produk mana yang perlu dipush, direstock, atau dihentikan.
- Sulit mendapatkan insight cepat tanpa konsultan, dashboard rumit, atau spreadsheet kompleks.

Dampak untuk UMKM:

- Margin terlalu kecil.
- Salah pricing.
- Salah restock.
- Kalah kompetitor.
- Keputusan harian lambat.
- Bisnis sulit berkembang karena tidak punya data pembanding.

## 3. Solusi

Sorota menyediakan AI bisnis yang bisa diajak ngobrol oleh pelaku UMKM untuk menjawab pertanyaan bisnis harian.

Contoh pertanyaan:

```text
Harga ayam sekarang normalnya berapa?
Margin kopi saya terlalu kecil nggak?
Supplier plastik murah dimana?
Produk mana yang harus saya push minggu ini?
Harga jual nasi ayam saya kemahalan nggak?
Kalau HPP saya Rp11.500, jual Rp18.000 masih sehat nggak?
```

Sorota sebaiknya menjawab dengan pola:

1. Memahami konteks bisnis user.
2. Mengambil data relevan dari profil user, produk, harga pasar, supplier, atau hasil crawling.
3. Melakukan perhitungan jika dibutuhkan.
4. Memberikan insight singkat.
5. Memberikan rekomendasi tindakan yang jelas.

Output yang diharapkan bukan sekadar informasi, tapi arahan keputusan:

```text
Harga jual Rp18.000 masih cukup aman jika target margin Anda 30%.
Namun jika biaya tambahan seperti kemasan dan komisi platform belum masuk,
harga yang lebih sehat ada di kisaran Rp19.000-Rp20.000.
```

## 4. Target Market

### Primary Target

UMKM Indonesia dengan keputusan operasional harian:

- Kuliner.
- Retail kecil.
- Fashion.
- Laundry.
- Warung.
- Toko kelontong.
- Coffee shop kecil.
- Reseller.

### Secondary Target

- Pebisnis pemula.
- Owner toko online.
- Franchise kecil.
- Agen kecil.
- Distributor kecil.

## 5. Value Proposition

Sorota membantu UMKM:

- Mengambil keputusan bisnis lebih cepat.
- Mengurangi kesalahan pricing dan restock.
- Mendapat insight pasar tanpa riset manual panjang.
- Memahami kondisi produk dan margin.
- Meningkatkan peluang keuntungan.
- Memiliki pendamping bisnis yang mudah digunakan lewat chat.

Nilai utama:

```text
Sorota membuat insight bisnis terasa sesederhana bertanya lewat chat.
```

## 6. Prinsip Produk

Sorota bukan:

- Social media bisnis.
- Marketplace.
- ERP rumit.
- Dashboard enterprise berat.
- Chatbot general purpose.

Sorota adalah:

- AI business intelligence untuk UMKM Indonesia.
- AI decision assistant untuk pricing, margin, supplier, kompetitor, dan kondisi pasar.
- Sistem personalisasi bisnis berbasis data user dan data pasar.

Prinsip penting:

- Jawaban harus praktis dan bisa ditindaklanjuti.
- Jika data tidak cukup, AI harus menyatakan keterbatasan dan meminta data tambahan.
- Angka harga, margin, dan rekomendasi harus bisa dijelaskan asalnya.
- Data user harus disimpan secara terstruktur, bukan hanya chat history mentah.
- Crawling atau survey harga tidak boleh selalu live di setiap chat jika membuat bot lambat.

## 7. Key Features

### 7.1 AI Business Assistant

Chat AI untuk konsultasi bisnis UMKM.

Kemampuan awal:

- Menjawab pertanyaan bisnis harian.
- Menjelaskan kondisi margin dan pricing.
- Memberi rekomendasi berdasarkan profil bisnis user.
- Mengarahkan user jika data yang dibutuhkan belum lengkap.

### 7.2 Business Profile Memory

Sorota menyimpan data bisnis user secara terstruktur.

Contoh data:

- Nama bisnis.
- Jenis usaha.
- Lokasi.
- Produk utama.
- Target margin.
- Harga jual.
- HPP.
- Supplier.
- Preferensi keputusan bisnis.

Contoh manfaat:

```text
User: Harga saya kemarin masih aman nggak?
Sorota: Untuk produk ayam geprek Anda, harga jual terakhir Rp18.000
dengan estimasi HPP Rp11.500. Margin kotornya sekitar 36,1%,
masih aman untuk target margin 30%.
```

### 7.3 Market Price Survey

Survey harga pasar dan kompetitor berdasarkan kategori, produk, dan lokasi.

Kemampuan:

- Mencari harga pasar dari sumber publik.
- Menyimpan hasil survey harga.
- Membandingkan harga user dengan harga pasar.
- Memberi kisaran harga normal, murah, dan mahal.

### 7.4 Cheapest Price Finder

Membantu mencari supplier atau harga termurah.

Kemampuan:

- Membandingkan beberapa sumber harga.
- Memberi daftar kandidat supplier.
- Menjelaskan tradeoff harga, lokasi, minimum order, dan kepercayaan sumber jika tersedia.

### 7.5 Business Calculator

Fitur hitung bisnis yang wajib ada untuk UMKM.

Kalkulasi awal:

- HPP.
- Margin.
- Markup.
- Rekomendasi harga jual.
- Simulasi kenaikan biaya.
- Simulasi diskon.

### 7.6 Business Insight

Analisa produk dan performa usaha sederhana.

Contoh insight:

- Produk dengan margin paling sehat.
- Produk dengan harga terlalu rendah.
- Produk yang layak dipush.
- Produk yang perlu dicek ulang HPP-nya.
- Risiko restock berdasarkan harga pasar.

### 7.7 Local Market Intelligence

Insight berdasarkan area/lokasi.

Catatan: fitur ini penting untuk positioning, tapi sebaiknya tidak dipaksakan penuh di MVP jika data lokal belum kuat.

### 7.8 Community Layer

Forum atau sharing supplier dan strategi antar UMKM.

Catatan: fitur ini opsional dan sebaiknya masuk fase setelah core AI business assistant stabil.

## 8. MVP Yang Disarankan

MVP Sorota sebaiknya dipersempit agar cepat stabil.

In scope MVP:

- Chat AI business assistant.
- OpenAI/ChatGPT API sebagai provider AI utama.
- Onboarding profil bisnis.
- Simpan data user dan bisnis.
- Simpan produk, harga jual, HPP, dan target margin.
- Kalkulasi margin dan rekomendasi harga jual.
- Survey harga pasar sederhana.
- Riwayat insight/rekomendasi.
- Jawaban personal berdasarkan data user.

Out of scope MVP:

- Community layer.
- Dashboard web kompleks.
- Forecasting advanced.
- Integrasi marketplace penuh.
- Multi-channel penuh selain channel yang sedang diprioritaskan.
- ERP/inventory management lengkap.

## 9. Personalization dan Database

Personalisasi Sorota harus berbasis data terstruktur.

Entity awal yang dibutuhkan:

- `users`
- `businesses`
- `business_profiles`
- `products`
- `product_costs`
- `suppliers`
- `market_prices`
- `price_surveys`
- `chat_sessions`
- `user_memories`
- `recommendations`

Prinsip memory:

- Jangan menyimpan semua chat mentah sebagai konteks utama.
- Ekstrak fakta penting dari chat menjadi data terstruktur.
- Ambil hanya data relevan saat menjawab.
- Pisahkan memory permanen, data bisnis, dan riwayat percakapan.

Contoh memory terstruktur:

```json
{
  "business_type": "kuliner",
  "location": "Bandung",
  "main_products": ["ayam geprek", "es teh"],
  "target_margin_percent": 30,
  "known_supplier": "Pasar Kosambi",
  "pricing_preference": "harga tetap kompetitif tapi margin minimal aman"
}
```

## 10. Arah Arsitektur

Target arsitektur:

```text
User Channel
  -> Chat Adapter
  -> Intent Router
  -> Context Builder
  -> Tool/Service Layer
  -> Business Reasoning
  -> Response Composer
  -> Memory Writer
```

Komponen utama:

- Chat adapter: Telegram, WhatsApp, web chat, atau channel lain.
- AI gateway: wrapper tipis untuk memanggil OpenAI API tanpa mengikat seluruh chat engine ke provider tertentu.
- Intent router: menentukan jenis pertanyaan user.
- Context builder: mengambil profil bisnis, produk, harga, dan memory relevan.
- Tool/service layer: menjalankan kalkulasi, survey harga, retrieval, crawler, atau query database.
- Business reasoning: menyusun analisa dan rekomendasi.
- Response composer: membuat jawaban yang singkat, praktis, dan personal.
- Memory writer: menyimpan fakta baru, insight, dan rekomendasi.

## 11. AI Provider Strategy: OpenAI First

Untuk MVP dan refactor awal, Sorota menggunakan satu AI provider terlebih dahulu:

```text
Active provider: OpenAI API / ChatGPT API
```

Keputusan ini dipilih agar sistem lebih mudah distabilkan:

- Debugging lebih sederhana.
- Latency lebih mudah diukur.
- Prompt lebih mudah dioptimasi.
- Token dan biaya lebih mudah dikontrol.
- Tidak ada kompleksitas membandingkan tiga provider di production.

Walaupun hanya memakai satu provider, kode tetap perlu memakai AI gateway internal:

```text
chat_engine
  -> ai_gateway
  -> openai_provider
```

Prinsip implementasi:

- Chat engine tidak boleh memanggil SDK OpenAI langsung dari banyak tempat.
- Semua request AI lewat satu adapter/gateway.
- Model name, timeout, max output token, dan reasoning effort harus bisa diatur dari config/env.
- Provider lama seperti Claude/Gemini boleh dipertahankan sementara hanya sebagai legacy atau eksperimen, bukan jalur utama MVP.
- Perbandingan provider tidak dijalankan otomatis di production karena mahal dan lambat.

Task AI yang perlu dipisah:

- `intent_router`: klasifikasi pertanyaan user.
- `memory_extractor`: ekstraksi fakta bisnis yang perlu disimpan.
- `answer_composer`: penyusun jawaban final.
- `evaluator` atau `quality_check`: opsional untuk evaluasi internal, bukan jalur utama user.

Rekomendasi API surface:

- Gunakan OpenAI Responses API sebagai jalur utama untuk generasi jawaban baru.
- Gunakan structured output untuk intent routing dan memory extraction agar hasil mudah divalidasi.
- Gunakan prompt caching dengan struktur prompt yang stabil: instruksi statis di awal, data user dinamis di akhir.
- Simpan usage/token/latency per request untuk mengukur apakah refactor benar-benar membuat bot lebih ringan.

Referensi resmi OpenAI:

- Models: https://developers.openai.com/api/docs/models
- Responses API: https://platform.openai.com/docs/api-reference/responses
- Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- Prompt Caching: https://platform.openai.com/docs/guides/prompt-caching
- Prompting: https://platform.openai.com/docs/guides/prompting

## 12. MCP Positioning

MCP cocok dipakai sebagai tool boundary, bukan sebagai solusi utama untuk semua masalah performa.

Candidate MCP tools:

- `get_business_profile`
- `save_business_profile`
- `get_user_products`
- `save_product`
- `calculate_margin`
- `recommend_price`
- `get_market_prices`
- `save_market_price_survey`
- `find_cheapest_supplier`
- `search_competitor_prices`
- `save_business_insight`

Manfaat MCP:

- Tool lebih modular.
- Integrasi data lebih jelas.
- Chat engine tidak perlu memuat semua logic langsung.
- Lebih mudah menambah sumber data baru.

Risiko MCP:

- Bisa menambah latency jika terlalu banyak tool call.
- Bisa membuat sistem lebih kompleks jika tool belum jelas.
- Tidak menggantikan kebutuhan optimasi prompt, cache, retrieval, dan database.

Rekomendasi:

```text
Rapikan domain dan tool internal dulu.
Setelah boundary jelas, expose tool penting sebagai MCP.
```

## 13. Performance Direction

Karena bot terasa berat dan lambat, refactor harus memperhatikan performa dari awal.

Prioritas optimasi:

- Pisahkan crawling dari request chat real-time.
- Gunakan cache untuk hasil survey harga yang masih relevan.
- Batasi dokumen yang masuk ke prompt.
- Pakai context builder yang selektif.
- Gunakan model kecil untuk intent routing jika memungkinkan.
- Gunakan model besar hanya untuk jawaban akhir yang butuh reasoning.
- Simpan summary atau structured insight, bukan seluruh percakapan panjang.
- Hindari multi-step agentic flow untuk pertanyaan sederhana.
- Log input token, output token, cached token, latency, dan prompt version di setiap request OpenAI.
- Buat token budget per task agar intent routing, memory extraction, dan final answer tidak saling membengkak.

Target UX:

```text
Pertanyaan sederhana harus terasa cepat.
Pertanyaan yang butuh survey/crawling boleh lebih lama, tapi user harus diberi status yang jelas.
```

## 14. Roadmap Refactor

### Phase 1: Product dan Domain Alignment

- Tetapkan Sorota sebagai AI decision assistant untuk UMKM.
- Finalisasi entity bisnis utama.
- Pisahkan fitur MVP dan non-MVP.
- Review flow bot yang sudah ada.

### Phase 2: OpenAI Gateway dan Prompt Baseline

- Tetapkan OpenAI API sebagai active provider.
- Buat AI gateway internal.
- Pindahkan pemanggilan AI dari modul lama ke gateway.
- Buat prompt baseline untuk intent router, memory extractor, dan answer composer.
- Tambahkan logging token, latency, model, prompt version, dan error.

### Phase 3: Database Personalization

- Buat atau rapikan schema user, business, product, cost, supplier, market price, dan memory.
- Tambahkan service untuk read/write business profile.
- Tambahkan extraction flow untuk menyimpan fakta penting dari chat.

### Phase 4: Chat Engine Refactor

- Pisahkan intent router.
- Pisahkan context builder.
- Pisahkan calculator/business tools.
- Pisahkan response composer.
- Tambahkan guardrail untuk pertanyaan non-bisnis.

### Phase 5: Market Intelligence Layer

- Rapikan survey harga pasar.
- Simpan evidence harga.
- Tambahkan cache dan freshness rule.
- Tambahkan comparison terhadap data produk user.

### Phase 6: MCP Tool Boundary

- Definisikan tool contract.
- Expose tool yang sudah stabil sebagai MCP.
- Hindari MCP untuk logic yang masih sering berubah.

### Phase 7: Optimization dan Testing

- Profile latency.
- Tambahkan unit test untuk calculator, intent, context, dan memory.
- Tambahkan integration test untuk flow chat utama.
- Ukur response time sebelum dan sesudah refactor.

## 15. Success Metrics

Produk:

- User bisa memasukkan profil bisnis dengan mudah.
- User bisa bertanya tanpa command.
- Jawaban terasa personal dan relevan.
- Rekomendasi mengandung tindakan konkret.

Teknis:

- Chat engine lebih modular.
- Context prompt lebih kecil.
- Data user tersimpan terstruktur.
- Pertanyaan sederhana tidak memicu crawling berat.
- Tool bisnis bisa dites secara terpisah.
- Semua panggilan AI lewat OpenAI gateway.
- Usage token dan latency tercatat untuk setiap response.

Bisnis:

- UMKM menggunakan Sorota untuk keputusan pricing, margin, supplier, dan restock.
- User kembali bertanya karena Sorota mengingat konteks bisnis mereka.
- Sorota memberi nilai yang berbeda dari chatbot umum.
