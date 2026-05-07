# Telegram AI Chatbot Refactor Plan

Dokumen ini menjadi rencana kerja refactor besar untuk mengubah bot dari command-based Telegram bot menjadi AI business assistant berbasis chat bebas. Fokus tahap awal adalah Telegram saja sampai end-to-end stabil. WhatsApp menjadi channel berikutnya setelah engine inti terbukti jalan.

## 1. Tujuan Produk

Target utama:

- User bisa chat bebas tanpa perlu mengingat command seperti `/analyze`, `/trend`, atau `/compare`.
- Bot hanya menjawab pertanyaan seputar bisnis, FMCG, distribusi, harga, stok, demand, supply, market, kompetitor, regulasi, dan intelligence operasional.
- Jika pertanyaan tidak relevan dengan bisnis, bot menolak dengan sopan dan singkat.
- Jawaban bersifat dynamic, source-grounded, dan dipersonalisasi berdasarkan profil user.
- Sistem crawl public sources terlebih dahulu saat dibutuhkan, menyimpan evidence ke database, lalu menyusun jawaban untuk customer.
- Telegram menjadi channel testing penuh. WhatsApp ditambahkan setelah flow Telegram stabil.
- Bot mengirim business brief otomatis setiap hari pukul 08.00, 12.30, dan 17.30 WIB.

Prinsip penting:

- AI boleh memahami, merencanakan, menulis, dan mempersonalisasi.
- Sistem tetap mengontrol evidence, source, price rule, limitation, dan audit trail.
- Tidak boleh mengarang harga, data stok, source, atau sebab kejadian jika evidence tidak tersedia.
- Semua jawaban analitis harus bisa ditelusuri ke evidence yang disimpan.

## 2. Scope Tahap Awal

In scope untuk fase Telegram:

- Free-text Telegram chat sebagai primary interface.
- AI business gate untuk menentukan apakah pertanyaan layak dijawab.
- AI query planner untuk memahami intent dan kebutuhan data.
- Crawl-first flow untuk pertanyaan bisnis yang butuh data baru.
- Evidence extraction, scoring, dan save ke PostgreSQL.
- Claude-heavy final answer composer untuk kualitas jawaban.
- Gemini sebagai helper untuk preprocessing, extraction, dan fallback.
- Personalization berdasarkan profil user Telegram.
- Scheduled daily business brief pukul 08.00, 12.30, dan 17.30 WIB.
- Logging AI request/response dan audit evidence.
- Test coverage untuk gate, planner, composer, scheduled brief, dan Telegram adapter.

Out of scope untuk fase awal:

- WhatsApp channel.
- Dashboard web.
- Paid user billing.
- Marketplace scraping penuh.
- Numerical forecasting advanced.
- Social media sentiment ingestion.
- Multi-tenant enterprise role management.

## 3. Target UX Telegram

User tidak perlu command analisis. Contoh chat valid:

```text
Harga minyak goreng buat distributor kecil minggu ini gimana?
Produk sembako apa yang lagi ramai hari ini?
Ada risiko stok gula nggak di Jawa Timur?
Bandingin minyak goreng sama gula buat stok minggu depan.
Apa yang harus saya pantau buat toko grosir hari ini?
```

Contoh chat tidak valid:

```text
Bikinin puisi.
Siapa pacar artis ini?
Ajari hack akun.
Rekomendasi film malam ini.
```

Jawaban untuk topik tidak valid:

```text
Maaf, saya hanya bisa membantu pertanyaan terkait bisnis, FMCG, distribusi, harga, stok, demand, supply, market intelligence, dan keputusan operasional.
```

Command yang masih boleh dipertahankan sementara:

- `/start`: onboarding singkat dan meminta profil user.
- `/menu`: daftar contoh pertanyaan, bukan command analisis.
- `/subscribe`: mengaktifkan scheduled brief.
- `/unsubscribe`: mematikan scheduled brief.
- `/profile`: melihat atau mengubah profil bisnis user.

Command lama seperti `/analyze`, `/trend`, `/weekly`, `/compare`, `/forecast`, `/search`, dan `/trending` bisa dipertahankan sebagai compatibility layer sementara, tetapi tidak dipromosikan di UI.

## 4. Arsitektur Baru

Arsitektur target:

```text
Telegram inbound message
-> Telegram adapter
-> Chat Engine
   -> Business Guard
   -> User Profile Resolver
   -> Query Planner
   -> Crawl Orchestrator
   -> Evidence Extractor
   -> Evidence Store
   -> Analyst Composer
   -> Quality Guard
   -> Conversation Store
-> Telegram response
```

Channel adapter harus tipis. Telegram hanya menangani:

- menerima message
- mengenali chat_id dan username
- mengirim typing/progress message
- mengirim response yang sudah di-split
- menerima subscribe/unsubscribe/profile command

Business logic dipindahkan ke shared engine agar nanti WhatsApp tinggal menjadi adapter baru.

## 5. Struktur Modul yang Disarankan

Tambahkan package baru:

```text
chat_engine/
  __init__.py
  engine.py
  domain_guard.py
  query_planner.py
  crawl_orchestrator.py
  evidence_selector.py
  analyst_composer.py
  quality_guard.py
  personalization.py
  conversation_store.py
  scheduler.py
  schemas.py
  ai/
    __init__.py
    base.py
    router.py
    anthropic_provider.py
    gemini_provider.py
    prompts/
      business_guard.md
      query_planner.md
      analyst_composer.md
      quality_guard.md
      daily_brief.md
```

Telegram package tetap ada, tetapi handler free text diarahkan ke `chat_engine.engine`.

```text
telegram_bot/
  handlers/
    chat_handler.py
    profile_handler.py
    subscription_handler.py
  services/
    telegram_service.py
```

Existing crawling modules tetap digunakan:

```text
crawling_bot/
  main.py
  crawlers/
  processors/
  services/
```

## 6. AI Provider Strategy

Karena target user adalah kualitas, komposisi awal dibuat Claude-heavy.

Pembagian tugas:

```text
Claude Sonnet class
- primary query planner untuk pertanyaan valid bisnis
- primary final answer composer
- premium report style
- reasoning untuk rekomendasi bisnis

Claude Haiku class
- business guard ringan
- quick classification
- optional quality review
- fallback murah untuk pertanyaan sederhana

Gemini Flash / Flash-Lite class
- extraction helper
- article summarization helper
- evidence cleanup
- Indonesian polishing fallback
- fallback saat Claude gagal atau rate limit
```

Flow default:

```text
1. Business guard:
   Claude Haiku atau Gemini Flash-Lite.

2. Query planning:
   Claude Sonnet class untuk pertanyaan bisnis yang butuh analisis.

3. Crawl + local processing:
   Existing crawler dan rule-based processors.

4. Evidence compression:
   Gemini Flash-Lite atau local rule, agar raw article panjang tidak langsung dikirim ke Claude.

5. Final answer:
   Claude Sonnet class.

6. Quality check:
   Claude Haiku atau local quality guard.
```

Catatan biaya:

- Jangan kirim semua raw article ke Claude.
- Kirim maksimal evidence terpilih, misalnya 5 sampai 10 item.
- Untuk pertanyaan ringan, boleh gunakan Claude Haiku atau Gemini saja.
- Claude Sonnet class dipakai untuk final answer yang penting, bukan semua preprocessing.

## 7. AI Router

Buat AI router agar provider bisa diganti lewat config.

Env yang disarankan:

```text
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL_PRIMARY=
ANTHROPIC_MODEL_FAST=
ANTHROPIC_MODEL_REVIEWER=

GEMINI_API_KEY=
GEMINI_MODEL_FAST=
GEMINI_MODEL_POLISHER=

AI_PRIMARY_PROVIDER=anthropic
AI_FAST_PROVIDER=anthropic
AI_EXTRACTION_PROVIDER=gemini
AI_REVIEW_PROVIDER=anthropic

AI_MAX_EVIDENCE_ITEMS=8
AI_MAX_ARTICLE_CHARS=2500
AI_RESPONSE_TIMEOUT_SECONDS=90
AI_ENABLE_REVIEW=true
```

Model ID spesifik harus divalidasi ulang saat implementasi, karena provider sering mengganti model name dan pricing.

Provider interface:

```python
class AIProvider:
    def generate_json(self, prompt: str, schema: type[T]) -> T: ...
    def generate_text(self, prompt: str) -> str: ...
```

Router interface:

```python
class AIRouter:
    def guard_provider(self) -> AIProvider: ...
    def planner_provider(self) -> AIProvider: ...
    def extraction_provider(self) -> AIProvider: ...
    def composer_provider(self) -> AIProvider: ...
    def reviewer_provider(self) -> AIProvider: ...
```

## 8. Business Guard

Business guard adalah pintu pertama.

Input:

- user message
- optional user profile
- recent conversation context singkat

Output schema:

```text
is_business_related: bool
category: business | fmcg | distribution | price | stock | market | regulation | unrelated | unsafe
confidence: low | medium | high
refusal_reason: string | null
normalized_question: string
```

Rules:

- Jika tidak business-related, jangan crawl.
- Jika topik unsafe, jangan jawab substansi.
- Jika ambigu, tanya klarifikasi singkat.
- Guard tidak boleh menjawab analisis bisnis.

Contoh ambiguous:

```text
User: minyak sekarang gimana?
Bot: Maksudnya minyak goreng untuk bisnis/FMCG, atau minyak mentah/BBM?
```

Namun jika profil user adalah distributor FMCG, default ke minyak goreng.

## 9. Query Planner

Query planner mengubah chat bebas menjadi rencana kerja.

Input:

- normalized user question
- user profile
- chat history ringkas

Output schema:

```text
intent:
  analysis | price | supply | demand | sentiment | regulation | comparison | daily_brief | forecast_like | recommendation

business_context:
  user_role
  business_type
  location
  product_focus
  urgency

entities:
  products
  brands
  companies
  locations
  categories
  pack_sizes

data_need:
  crawl_needed: bool
  database_lookup_needed: bool
  price_snapshot_needed: bool
  comparison_needed: bool

crawl_plan:
  max_sources
  max_articles_per_source
  preferred_source_types
  search_terms

response_style:
  short | normal | detailed | ba_report
```

Planner tidak boleh membuat fakta final. Planner hanya menentukan cara menjawab.

## 10. Crawl-First Flow

Flow untuk pertanyaan bisnis valid:

```text
1. User bertanya.
2. Guard validasi topik.
3. Planner membuat search terms dan data need.
4. Bot kirim progress message:
   "Saya cek sumber publik dulu, lalu susun ringkasan bisnis yang bisa dipakai untuk keputusan Anda."
5. Crawl orchestrator menjalankan crawler terbatas.
6. Existing processors ekstrak relevance, entity, signal, reason, score.
7. Evidence disimpan ke DB.
8. Evidence selector memilih rows paling relevan.
9. Claude menyusun jawaban final dari evidence terpilih.
10. Quality guard cek no hallucination, no unsupported price, source coverage.
11. Bot kirim jawaban.
12. Conversation dan final answer disimpan ke DB.
```

Urutan simpan yang disarankan:

```text
raw/crawled evidence -> save minimal -> compose answer -> send -> save final answer
```

Alasannya:

- Jika final answer terkirim, evidence dasarnya sudah ada.
- Jika AI gagal, evidence tetap bisa dipakai untuk retry.
- Audit trail lebih kuat.

## 11. Evidence Selection

Jangan kirim semua hasil crawl ke AI composer.

Evidence selector harus memilih berdasarkan:

- relevance dengan query
- impact_score
- confidence_score
- recency
- source credibility
- diversity source
- signal severity
- product/location match

Default:

```text
max_evidence_items: 8
max_sources_per_answer: 5
max_chars_per_evidence: 1000
```

Evidence payload ke Claude:

```text
source_name
source_url
article_title
article_url
published_at
signal_type
product
location
severity
confidence_score
reason
evidence_text
summary
price_snapshot_summary if available
availability_snapshot_summary if available
```

## 12. Dynamic Answer Design

Jawaban tidak harus selalu template yang sama. Composer memilih format berdasarkan intent.

Istilah internal seperti `signal`, `signal_type`, `evidence_text`, `confidence_score`, `source_coverage`, dan `snapshot_count` tidak boleh muncul di jawaban user. Istilah tersebut tetap dipakai di backend, database, prompt internal, dan quality check, tetapi harus diterjemahkan menjadi bahasa bisnis yang natural.

Mapping bahasa user:

```text
signal -> hal yang perlu diperhatikan / indikasi / perkembangan
price_increase -> tekanan harga naik
price_decrease -> harga mulai melemah / ada ruang harga turun
shortage -> risiko stok terbatas
distribution_disruption -> distribusi berpotensi terganggu
demand_increase -> permintaan mulai menguat
demand_decrease -> permintaan melemah
negative_sentiment -> isu negatif terhadap produk/brand
positive_sentiment -> minat pasar terlihat positif
regulation_change -> perubahan aturan atau kebijakan
confidence -> tingkat keyakinan
source coverage -> sumber yang dipakai
evidence -> dasar informasi
```

Untuk pertanyaan cepat:

```text
Jawaban singkat
- Intinya
- Kenapa penting
- Yang sebaiknya dilakukan
- Catatan data
```

Untuk analisis produk:

```text
Ringkasan
Apa yang terjadi
Harga
Pasokan
Permintaan pasar
Dampak bisnis
Rekomendasi
Sumber yang dipakai
Limitasi
```

Untuk comparison:

```text
Kesimpulan cepat
Produk A vs Produk B
Risiko utama
Kapan pilih A
Kapan pilih B
Rekomendasi stok/pricing
Sumber yang dipakai
```

Untuk daily hype:

```text
Yang lagi ramai
Produk/topik yang ramai
Kenapa ramai
Dampak untuk user
Yang sebaiknya dilakukan hari ini
Sumber yang dipakai
```

Response harus tetap memuat:

- tingkat keyakinan dengan bahasa natural, misalnya "keyakinan sedang" atau "data masih terbatas"
- sumber yang dipakai, terutama jika membahas berita, jadwal, event, aturan, promo, distribusi, atau pengumuman resmi
- catatan keterbatasan jika data kurang
- larangan menyebut harga pasti jika data harga tidak ditemukan
- rekomendasi yang actionable

Struktur jawaban default:

```text
Intinya
...

Apa yang terjadi
...

Kenapa ini penting
...

Dampak untuk bisnis Anda
...

Yang sebaiknya dilakukan
...

Sumber
1. Nama sumber - Judul
   URL
2. Nama sumber - Judul
   URL

Catatan
...
```

### 12.1 Source and Schedule Rules

Jika jawaban menyebut jadwal, tanggal, event, rilis data, aturan baru, promo, distribusi, operasi pasar, pembatasan, deadline, atau pengumuman resmi, maka jawaban wajib menyertakan sumber di bagian "Sumber".

Untuk informasi berbasis jadwal, composer harus menulis tanggal secara jelas. Hindari hanya memakai "hari ini", "besok", atau "minggu depan" tanpa konteks jika sumber menyebut tanggal spesifik.

Contoh gaya yang diinginkan:

```text
Ada jadwal yang perlu diperhatikan pada 10 Mei 2026. Jika pengumuman ini berkaitan dengan distribusi pangan, dampaknya untuk sub-distributor adalah potensi perubahan harga beli, prioritas alokasi stok, atau kebutuhan validasi ulang ke supplier.

Yang sebaiknya dilakukan:
- Jangan mengambil stok besar sebelum update resmi keluar.
- Cek harga supplier pagi dan siang.
- Siapkan alternatif supplier jika ada indikasi pembatasan distribusi.

Sumber:
1. Antara Ekonomi - Judul berita
   https://...
```

Jika sumber tidak cukup kuat, bot harus mengatakan:

```text
Saya menemukan pembahasan terkait topik ini, tetapi belum ada sumber yang cukup jelas untuk memastikan jadwal atau dampaknya. Saya sarankan ini dipakai sebagai bahan pantauan, bukan dasar keputusan final.
```

### 12.2 Tone and Explanation Rules

Gaya bahasa:

- Natural, seperti asisten analis bisnis.
- Tidak teknis.
- Tidak memakai label mentah database.
- Tidak memakai istilah "signal" di jawaban user.
- Tidak terlalu panjang jika user bertanya singkat.
- Memberi alasan, bukan hanya kesimpulan.
- Menjelaskan kenapa sebuah berita penting untuk stok, harga, margin, cashflow, supplier, atau distribusi.
- Mengutamakan saran yang bisa langsung dilakukan user.

Contoh buruk:

```text
Signal utama: price_increase dan shortage. Confidence medium. Source coverage 4 articles.
```

Contoh baik:

```text
Harga mulai menunjukkan tekanan naik, sementara beberapa sumber juga menyebut pasokan perlu dipantau. Untuk distributor kecil, ini berarti keputusan restock sebaiknya lebih hati-hati: validasi harga supplier dulu, lalu ambil buffer terbatas untuk SKU yang paling cepat jalan.
```

### 12.3 Price Response Rules

Jika user bertanya harga, atau hasil crawl menemukan harga yang relevan, bot boleh menampilkan harga sebagai data pendukung. Namun harga harus berasal dari price snapshot, halaman produk yang berhasil dicek, katalog resmi, sumber retail/wholesale yang diizinkan, input manual/internal, atau integrasi data yang compliant.

Harga dari berita biasa tidak boleh diperlakukan sebagai harga pasti.

Jika harga ditemukan, response cukup ringkas:

```text
Harga yang berhasil kami pantau
- Gula pasir 1 kg terlihat di kisaran Rp 16.900 - Rp 18.200 dari sumber yang berhasil dicek.
- Data ini bisa dipakai sebagai pembanding awal, bukan patokan final harga supplier.

Sumber:
1. Indogrosir - Gula pasir 1 kg
   Diambil: 7 Mei 2026, 08.10 WIB
   URL...
```

Jika harga tidak ditemukan, gunakan fallback user-facing berikut:

```text
Maaf, kami belum berhasil menemukan harga untuk produk ini dari sumber yang kami cek.
```

Jika user menanyakan produk, ukuran, atau wilayah spesifik:

```text
Maaf, kami belum berhasil menemukan harga gula 1 kg untuk wilayah yang Anda maksud dari sumber yang kami cek.
```

Setelah fallback harga, bot boleh tetap memberi konteks bisnis dari berita atau sumber publik:

```text
Untuk sementara, analisis ini memakai berita dan pembahasan publik yang berhasil kami temukan. Jadi rekomendasinya lebih cocok dipakai sebagai bahan pantauan, bukan sebagai patokan harga beli.
```

Jika user tidak bertanya harga tetapi crawl menemukan harga, tampilkan sebagai catatan pendek saja:

```text
Tambahan data harga:
Saat pengecekan, ada sumber retail/wholesale yang menampilkan gula 1 kg di kisaran Rp 16.900 - Rp 18.200. Data ini berguna sebagai pembanding, tetapi belum cukup untuk menyimpulkan harga pasar atau harga supplier.
```

Quality guard untuk harga:

- Jangan menulis "harga pasar hari ini adalah..." kecuali sumber dan coverage benar-benar mendukung.
- Gunakan "berdasarkan sumber yang berhasil kami cek", "terlihat di kisaran", atau "bisa dipakai sebagai pembanding awal".
- Wajib tampilkan sumber dan waktu cek jika menyebut harga.
- Jika tidak ada data harga, jangan menebak dari berita.

## 13. Personalization

Personalization membuat jawaban terasa relevan untuk user.

Data profil user:

```text
telegram_chat_id
username
business_type: sub_distributor | grosir | retailer | manufacturer | analyst | other
business_scale: small | medium | large | unknown
location
product_focus
preferred_language: id | en
response_style: short | normal | detailed | ba_report
risk_preference: conservative | balanced | aggressive
scheduled_brief_enabled: bool
scheduled_brief_times: 08:00,12:30,17:30
created_at
updated_at
```

Cara membangun profil:

1. Explicit onboarding:

```text
Halo, saya bisa bantu intelligence bisnis FMCG. Agar jawaban lebih relevan, boleh info bisnis Anda?
Contoh: "Saya sub-distributor sembako di Surabaya, fokus minyak goreng dan gula."
```

2. Profile inference:

Jika user pernah bilang "saya distributor kecil di Bandung", sistem bisa menyarankan:

```text
Saya tangkap profil Anda: distributor kecil di Bandung, fokus sembako. Mau saya pakai ini untuk personalisasi jawaban berikutnya?
```

3. Manual update:

```text
User: ubah profil saya jadi grosir di Jakarta, fokus beras dan minyak goreng.
```

Personalization rules:

- Distributor kecil: jawaban lebih taktis, fokus stok, supplier, margin, cashflow.
- Procurement team: fokus validasi supplier, kontrak, pergerakan harga, dan mitigasi risiko.
- Business analyst: format lebih terstruktur, dengan rincian sumber yang lebih lengkap.
- Retailer: fokus perputaran barang, promo, ketersediaan stok, dan permintaan pelanggan.
- Lokasi tersedia: prioritaskan evidence lokasi tersebut jika ada.
- Produk fokus tersedia: jadikan watchlist default scheduled brief.

## 14. Conversation Memory

Conversation memory harus dibatasi agar tidak mahal dan tidak berisiko.

Simpan:

- original user message
- normalized query
- intent
- entities
- answer summary
- evidence IDs
- user feedback

Jangan perlu simpan raw AI prompt penuh jika mengandung data sensitif, kecuali untuk debug terbatas.

Context yang dikirim ke AI:

```text
last 3-5 conversation summaries
active user profile
current question
selected evidence
```

## 15. Scheduled Business Media Brief

Tambahkan fitur push otomatis ke subscriber Telegram.

Fokus scheduled brief adalah berita dan pembahasan bisnis yang sedang ramai di media pada hari itu. Ini bukan product price alert dan bukan laporan harga SKU rutin. Harga boleh muncul sebagai catatan tambahan jika saat crawling ditemukan data harga yang jelas, tetapi fokus utamanya tetap:

- berita bisnis
- FMCG dan retail
- distribusi dan supply chain
- komoditas dan pangan
- regulasi pemerintah yang berdampak ke bisnis
- inflasi, daya beli, kurs, dan suku bunga jika relevan dengan operasional bisnis
- perusahaan besar, marketplace, atau retail modern jika berpotensi memengaruhi pasar
- isu ekspor-impor, logistik, atau bahan baku

Brief harus menjawab:

```text
Apa yang lagi ramai di media bisnis?
Kenapa ini penting?
Apa dampaknya untuk user?
Apa yang perlu dipantau atau dilakukan?
Sumbernya dari mana?
```

Jadwal:

```text
08.00 WIB - Morning Business Media Brief
12.30 WIB - Midday Business Media Update
17.30 WIB - Evening Business Media Wrap
```

Timezone:

```text
Asia/Jakarta
```

### 15.1 Brief 08.00 WIB

Tujuan:

- Memberi gambaran berita bisnis yang mulai ramai sejak malam sampai pagi.
- Membantu user tahu isu bisnis apa yang perlu dipantau sebelum aktivitas operasional berjalan.
- Menyaring berita umum agar hanya yang relevan dengan bisnis, FMCG, retail, distribusi, komoditas, regulasi, dan market operation yang masuk.

Isi:

```text
Morning Business Media Brief
- Berita bisnis yang paling ramai pagi ini
- Kenapa berita itu penting untuk operasional bisnis
- Dampak yang mungkin terasa ke harga, stok, demand, supplier, atau distribusi
- Yang sebaiknya dipantau sebelum jam operasional berjalan
- Sumber yang dipakai
```

Contoh arah jawaban:

```text
Pagi ini media bisnis banyak membahas harga pangan, daya beli, dan distribusi. Untuk sub-distributor sembako, isu yang paling relevan adalah potensi perubahan harga beli dan ketersediaan barang fast-moving. Prioritas pagi ini adalah cek harga supplier, pantau berita kebijakan pangan, dan jangan mengambil stok besar hanya dari satu sumber informasi.
```

### 15.2 Brief 12.30 WIB

Tujuan:

- Update tengah hari setelah berita bisnis pagi mulai berkembang.
- Menjelaskan apakah ada isu baru yang lebih penting daripada brief pagi.
- Membantu user mengambil keputusan operasional siang/sore dengan konteks media bisnis terbaru.

Isi:

```text
Midday Business Media Update
- Update berita bisnis yang berkembang sejak pagi
- Isu yang mulai lebih ramai di media
- Dampak yang mungkin terasa ke operasional, supplier, stok, atau permintaan
- Yang sebaiknya dicek sebelum order/alokasi sore
- Sumber yang dipakai
```

Contoh arah jawaban:

```text
Dibanding pagi, media bisnis mulai lebih banyak membahas tekanan harga pangan dan kebijakan distribusi. Jika bisnis Anda fokus sembako, validasi stok dan harga supplier siang ini lebih penting daripada menunggu update sore.
```

### 15.3 Brief 17.30 WIB

Tujuan:

- Merangkum berita bisnis yang paling penting sepanjang hari.
- Menjelaskan isu mana yang perlu dibawa ke watchlist besok.
- Memberi arahan pantauan untuk penutupan hari dan persiapan operasional besok.

Isi:

```text
Evening Business Media Wrap
- Ringkasan berita bisnis yang paling penting hari ini
- Isu yang perlu masuk watchlist besok
- Dampak yang mungkin terasa ke harga, stok, supplier, distribusi, atau permintaan
- Yang sebaiknya dicek sebelum closing
- Apa yang perlu dicek besok pagi
- Sumber yang dipakai
```

Contoh arah jawaban:

```text
Menjelang sore, berita bisnis hari ini paling banyak mengarah ke harga pangan, distribusi, dan daya beli. Untuk distributor kecil, isu ini sebaiknya masuk watchlist besok pagi: validasi harga supplier, cek ketersediaan barang utama, dan hindari overstock jika belum ada kepastian permintaan.
```

Harga dalam scheduled brief:

- Jangan menjadi fokus utama.
- Tampilkan hanya jika data harga ditemukan jelas dari sumber yang bisa dipakai.
- Jika tidak ada harga, tidak perlu memunculkan fallback harga kecuali brief memang membahas pertanyaan harga dari user.
- Jika harga muncul, gunakan sebagai pembanding awal dan sertakan sumber serta waktu cek.

## 16. Scheduler Design

Pilihan implementasi:

1. Telegram bot job queue
2. APScheduler di FastAPI lifespan
3. Separate worker service

Rekomendasi MVP:

```text
APScheduler atau python-telegram-bot JobQueue
```

Untuk production lebih rapi:

```text
separate scheduler worker
```

Alasan:

- Scheduled brief bisa memakan waktu karena crawl + AI.
- Jangan sampai request webhook terganggu oleh job panjang.
- Worker lebih mudah di-scale dan di-retry.

Docker Compose target:

```text
services:
  fmcg-engine:
    command: uvicorn telegram_bot.webhook:app --host 0.0.0.0 --port 8000

  scheduler:
    command: python scripts/run_scheduler.py

  crawler:
    command: python scripts/run_crawler.py
```

MVP boleh menjalankan scheduler di proses bot terlebih dahulu, tetapi perlu lock agar job tidak double run.

## 17. Scheduled Brief Data Flow

```text
Scheduler trigger 08.00/12.30/17.30 WIB
-> create brief job
-> run crawl with controlled source/article limit
-> collect recent signals
-> apply user personalization per subscriber
-> compose brief
-> send Telegram message
-> store brief run result
```

Perlu idempotency:

```text
brief_key = date + time_slot + chat_id
```

Jika job restart, jangan kirim duplikat untuk chat_id dan time_slot yang sama.

Recommended crawl limit:

```text
08.00: max_sources=8, max_articles_per_source=2
12.30: max_sources=8, max_articles_per_source=2
17.30: max_sources=10, max_articles_per_source=2
```

Jika cost/latency tinggi, scheduled brief bisa memakai DB recent evidence dulu, lalu crawl hanya jika data terlalu sedikit.

## 18. Database Changes

Tambahan tabel minimum:

### 18.1 user_profiles

```text
id
telegram_chat_id
business_type
business_scale
location
product_focus
preferred_language
response_style
risk_preference
created_at
updated_at
```

### 18.2 conversations

```text
id
telegram_chat_id
channel
status
started_at
updated_at
```

### 18.3 conversation_messages

```text
id
conversation_id
telegram_chat_id
role: user | assistant | system
message_text
normalized_intent
entities_json
evidence_ids_json
created_at
```

### 18.4 ai_call_logs

```text
id
provider
model
task_type: guard | planner | extraction | composer | reviewer | brief
input_tokens
output_tokens
latency_ms
status
error_message
created_at
```

### 18.5 scheduled_brief_runs

```text
id
telegram_chat_id
brief_date
time_slot: 08:00 | 12:30 | 17:30
brief_key unique
status: pending | sent | failed | skipped
message_text
evidence_ids_json
sent_at
error_message
created_at
```

Existing `user_subscriptions` bisa tetap dipakai, lalu diperluas atau direlasikan ke `user_profiles`.

## 19. Telegram Handler Refactor

Current:

```text
telegram_bot/main.py
-> CommandHandler banyak command
-> MessageHandler free_text_analysis
```

Target:

```text
telegram_bot/main.py
-> /start
-> /menu
-> /subscribe
-> /unsubscribe
-> /profile
-> MessageHandler(filters.TEXT & ~filters.COMMAND, chat_handler)
```

`chat_handler`:

```text
1. reject_if_not_allowed
2. resolve user profile
3. send typing/progress message
4. call ChatEngine.handle_message
5. split and send response
```

Untuk sementara, command lama bisa diarahkan ke engine juga:

```text
/analyze minyak goreng
-> same as free text "minyak goreng"
```

Namun UI dan README baru sebaiknya mengarahkan user ke chat bebas.

## 20. Quality Guard

Quality guard harus mengecek:

- Apakah jawaban di luar domain bisnis?
- Apakah menyebut harga exact tanpa data harga dari price snapshot atau halaman produk yang berhasil dicek?
- Apakah fallback "Maaf, kami belum berhasil menemukan harga..." muncul saat user bertanya harga tetapi data harga tidak ditemukan?
- Apakah menyebut sumber yang tidak ada di evidence?
- Apakah rekomendasi terlalu absolut?
- Apakah limitation hilang padahal data kurang?
- Apakah bagian sumber sudah ada saat dibutuhkan?
- Apakah confidence masuk akal?
- Apakah istilah internal seperti `signal`, `signal_type`, `evidence`, `source coverage`, `snapshot`, atau label mentah database muncul di jawaban user?
- Apakah jawaban yang menyebut jadwal, tanggal, event, aturan, promo, distribusi, atau pengumuman resmi sudah menyertakan sumber?
- Apakah penjelasan sudah menjawab "kenapa ini penting untuk bisnis user", bukan hanya merangkum berita?

Jika gagal:

```text
Composer retry dengan instruction tambahan
atau fallback ke structured rule-based answer
```

Contoh hard rule:

```text
If user asks price and no usable price data exists:
  final answer must say the system has not successfully found the price from checked sources.
  final answer must not infer exact price from news-only evidence.
```

## 21. Error Handling

Skenario dan fallback:

- AI guard gagal: gunakan local keyword guard.
- Planner gagal: gunakan fallback parser existing `AnalystQueryParser`.
- Crawler gagal total: jawab dengan evidence DB terakhir dan jelaskan limitation.
- Claude final composer gagal: fallback ke Gemini composer atau structured template.
- Provider rate limit: gunakan cheaper/fallback provider.
- Telegram send gagal: simpan status failed di message log.
- Scheduled brief gagal: retry terbatas, lalu mark failed.

Progress message:

```text
Saya cek sumber publik dulu, lalu susun ringkasan bisnis yang bisa dipakai untuk keputusan Anda. Ini bisa makan waktu beberapa menit.
```

Jika terlalu lama:

```text
Beberapa sumber sedang lambat. Saya pakai informasi terbaru yang sudah tersimpan dulu, lalu update lagi jika hasil baru selesai diproses.
```

## 22. Performance and Cost Controls

Default constraints:

```text
max_sources_per_user_query=8
max_articles_per_source=2
max_evidence_items=8
max_article_chars_for_ai=2500
max_final_answer_chars=3500
composer_timeout=90 seconds
```

Caching:

- Reuse recent crawl result for same topic within 30-60 minutes.
- Reuse daily brief evidence across all subscribers, lalu personalize final section per user.
- Store evidence compression result.

Concurrency:

- Keep global crawl lock for MVP.
- Add job queue later if multiple users.
- Prevent same chat from launching multiple heavy analysis at once.

## 23. Testing Plan

Unit tests:

- Business guard accepts valid business questions.
- Business guard rejects non-business questions.
- Query planner extracts product, location, intent, and data_need.
- Evidence selector limits and ranks evidence.
- Composer does not invent exact price without price snapshots.
- Composer returns the price-not-found fallback when the user asks for price and no usable price data exists.
- Composer includes limitation when evidence is weak.
- Composer does not expose internal terms such as `signal`, `signal_type`, `evidence_text`, or `source coverage`.
- Composer includes source links when the answer mentions schedules, dates, events, rules, promotions, distribution updates, or official announcements.
- Composer explains business meaning in plain language.
- Personalization changes recommendation by business_type.
- Scheduled brief builds 08.00, 12.30, and 17.30 variants.
- Scheduler idempotency prevents duplicate sends.

Integration tests:

- Free-text Telegram message calls ChatEngine.
- Valid business question triggers crawl + DB lookup + answer.
- Non-business question does not trigger crawl.
- Claude provider can be mocked.
- Gemini provider can be mocked.
- Fallback path works when provider raises exception.

Manual E2E tests:

```text
1. /start
2. User gives profile:
   "Saya sub-distributor sembako kecil di Surabaya, fokus minyak goreng dan gula."
3. User asks:
   "Hari ini minyak goreng gimana buat stok?"
4. Bot crawls, stores evidence, answers with personalized recommendation.
5. User asks:
   "Bikinin puisi dong."
6. Bot refuses non-business topic.
7. /subscribe
8. Simulate 08.00 scheduled brief.
9. Simulate 12.30 scheduled brief.
10. Simulate 17.30 scheduled brief.
```

## 24. Implementation Phases

### Phase 0 - Planning and Guardrails

Output:

- This planning document.
- Final architecture agreement.
- Decide exact provider model IDs before implementation.

### Phase 1 - AI Provider Abstraction

Tasks:

- Add Anthropic dependency.
- Create AI provider interface.
- Create Anthropic provider.
- Wrap existing Gemini provider into same interface.
- Add AI router.
- Add fake provider for tests.

Success criteria:

- Tests can run without real API keys.
- Provider choice controlled by env.

### Phase 2 - Chat Engine MVP

Tasks:

- Add `chat_engine.engine`.
- Add business guard.
- Add query planner.
- Add evidence selector.
- Add analyst composer.
- Add local fallbacks.

Success criteria:

- Free-text business question returns an answer.
- Non-business question is refused.
- No Telegram-specific logic inside engine.

### Phase 3 - Telegram Refactor

Tasks:

- Add `telegram_bot/handlers/chat_handler.py`.
- Route free text to ChatEngine.
- Keep `/start`, `/menu`, `/subscribe`, `/unsubscribe`, `/profile`.
- Hide/deprecate old command-heavy UX.
- Update README usage.

Success criteria:

- User can test full flow in Telegram without `/analyze`.

### Phase 4 - Persistence and Personalization

Tasks:

- Add user profile model and migration.
- Add conversation models and migration.
- Add AI call logs.
- Add profile update flow.
- Use profile in composer.

Success criteria:

- Same question can produce different recommendation for distributor vs analyst.
- Evidence IDs and final answer are stored.

### Phase 5 - Scheduled Briefs

Tasks:

- Add scheduled brief service.
- Add scheduler runner.
- Add brief run table.
- Add time slots 08.00, 12.30, 17.30 WIB.
- Add subscriber personalization.
- Add retry/idempotency.

Success criteria:

- Scheduler can send simulated 08.00, 12.30, 17.30 briefs.
- Duplicate sends are prevented.

### Phase 6 - Quality and Cost Optimization

Tasks:

- Add quality guard.
- Add token/cost logs.
- Add timeout and fallback behavior.
- Add recent crawl cache.
- Tune evidence limit.

Success criteria:

- Answer quality is stable.
- Cost per answer can be observed.
- Failures degrade gracefully.

### Phase 7 - WhatsApp Adapter Later

Tasks:

- Add WhatsApp webhook.
- Map WhatsApp inbound/outbound format.
- Reuse ChatEngine.
- Reuse profile and subscription logic.

Success criteria:

- WhatsApp channel does not duplicate business logic.

## 25. Recommended MVP Build Order

Practical order:

```text
1. AI provider abstraction
2. Business guard with fallback
3. ChatEngine free-text flow
4. Telegram chat handler
5. Claude final composer
6. Evidence selector
7. User profile personalization
8. Scheduled brief service
9. Scheduler runner
10. Quality guard and AI call logs
```

This order keeps Telegram testable early while avoiding a big-bang rewrite.

## 26. Acceptance Criteria

MVP is acceptable when:

- User can ask normal business questions without slash commands.
- Bot refuses non-business questions.
- Bot crawls or reads database evidence before answering.
- Bot includes sources used and limitations in user-friendly language.
- Bot does not invent exact prices.
- Bot says "Maaf, kami belum berhasil menemukan harga..." when users ask price and no usable price data exists.
- Bot does not expose internal terms such as `signal`, `signal_type`, `evidence_text`, or `source coverage` in user-facing answers.
- Bot includes source links when discussing schedules, dates, events, regulations, promotions, distribution updates, or official announcements.
- Bot explains why a development matters for the user's business, not only what the news says.
- Bot personalizes recommendation from user profile.
- Bot sends scheduled briefs at 08.00, 12.30, and 17.30 WIB.
- Tests pass without real AI API keys.
- Real provider failures have fallback behavior.
- Telegram E2E works before WhatsApp work starts.

## 27. Open Decisions

Need confirmation before implementation:

- Exact Anthropic model IDs to use for primary, fast, and reviewer.
- Exact Gemini model IDs to use for extraction and fallback.
- Whether scheduled brief is opt-in only or sent to all allowed chats by default.
- Whether profile inference requires explicit user confirmation before saving.
- Whether old slash commands should be removed immediately or kept temporarily.
- Whether scheduler runs inside bot process for MVP or as separate worker from day one.

## 28. My Recommendation

Use Telegram as the full proving ground first. Build the AI chat engine as channel-independent from day one, but do not implement WhatsApp yet.

Best initial composition:

```text
Claude Sonnet class:
  final answer and complex planning

Claude Haiku class:
  guard and review

Gemini Flash / Flash-Lite class:
  extraction, compression, and fallback
```

Best initial product behavior:

```text
Free chat first.
No command dependency.
Business-only strict gate.
Crawl and save evidence before final answer.
Personalized recommendation.
Scheduled business brief 3 times per day.
```

This gives a strong quality path without throwing away the current crawler, database, scoring, and Telegram work.
