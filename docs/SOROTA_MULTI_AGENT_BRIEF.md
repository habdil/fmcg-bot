# Sorota Multi-Agent Brief

Dokumen ini menjelaskan konsep multi-agent untuk Sorota: bagaimana beberapa agent bekerja bersama untuk memahami customer, mengelola memori bisnis, mencari data pasar, membaca tren, dan memperbaiki kualitas jawaban Telegram bot dari waktu ke waktu.

Tujuan utamanya bukan membuat banyak agent sekadar terlihat kompleks. Tujuannya adalah memisahkan tanggung jawab agar setiap agent punya fungsi jelas, data yang jelas, tool yang jelas, dan batasan yang jelas.

## 1. Ringkasan Konsep

Sorota sebaiknya dibangun sebagai sistem agentik dengan satu orchestrator utama dan beberapa specialist agent.

Model besarnya:

```text
Telegram User
  -> Conversation Orchestrator
    -> Customer Understanding Agent
    -> Business Memory Agent
    -> Market Crawler Agent
    -> Trend Radar Agent
    -> Price & Supplier Agent
    -> Business Analyst Agent
    -> Response Coach Agent
    -> Reminder Agent
    -> Quality & Safety Agent
```

Prinsip penting:

- Chat harus tetap cepat.
- User biasa tidak boleh otomatis memicu crawling berat setiap chat.
- Agent boleh belajar dari chat, tetapi harus belajar secara terstruktur.
- Data luar harus lewat tool boundary, idealnya lewat MCP setelah tool internal stabil.
- Agent tidak boleh mengubah prompt, strategi bisnis, atau data penting secara otomatis tanpa audit.
- Semua keputusan yang berdampak ke user harus punya jejak: data apa yang dipakai, agent apa yang jalan, dan kenapa rekomendasi itu muncul.

## 2. Masalah Yang Ingin Diselesaikan

Saat bot hanya punya satu ChatEngine besar, masalah yang muncul:

- Bot terasa kaku karena semua pertanyaan diproses seperti analisis formal.
- Bot lambat jika terlalu sering mencari data luar.
- Memori user belum cukup aktif untuk memahami karakteristik bisnis.
- Crawling belum sepenuhnya berdasarkan kebutuhan customer.
- Feedback user belum berubah menjadi peningkatan kualitas jawaban yang konsisten.
- Sulit membedakan mana tugas real-time dan mana tugas background.

Multi-agent menyelesaikan ini dengan memisahkan:

- Agent real-time untuk chat cepat.
- Agent background untuk crawling, trend, dan enrichment.
- Agent evaluasi untuk memperbaiki kualitas jawaban.
- Agent memori untuk memahami user secara bertahap.

## 3. Desain Besar Arsitektur

### 3.1 Real-Time Path

Dipakai saat user sedang chat.

```text
User message
  -> Conversation Orchestrator
  -> Customer Understanding Agent
  -> Business Memory Agent
  -> Tool call ringan jika perlu
  -> Business Analyst Agent
  -> Response Coach Agent
  -> Reply Telegram
```

Target latency:

- Sapaan, reminder, profile update: kurang dari 1 detik.
- Kalkulasi HPP, margin, harga jual: 1 sampai 3 detik.
- Analisis berbasis database internal: 3 sampai 8 detik.
- Analisis yang butuh data baru: dijawab sementara dulu, lalu agent background mengisi data untuk follow-up.

### 3.2 Background Path

Dipakai untuk pekerjaan berat.

```text
User need detected
  -> Agent task queue
  -> Market Crawler Agent
  -> Trend Radar Agent
  -> Price & Supplier Agent
  -> Store signals, prices, source metadata
  -> Optional follow-up notification
```

Contoh:

User bertanya:

```text
Supplier telur murah daerah Bandung ada nggak?
```

Real-time reply:

```text
Aku cek dari data yang sudah ada dulu. Kalau belum cukup, aku jadwalkan pencarian supplier Bandung dan kabari hasil ringkasnya.
```

Background agent:

- Mencari sumber harga/supplier.
- Menyimpan kandidat supplier.
- Membandingkan harga.
- Menghasilkan follow-up insight.

## 4. Agent 1: Conversation Orchestrator

### Misi

Mengatur agent mana yang perlu bekerja untuk setiap pesan user.

Orchestrator bukan agent yang paling pintar, tapi agent yang paling disiplin. Ia menentukan apakah pesan harus dijawab cepat, disimpan sebagai memori, dijadikan reminder, dianalisis, atau dijadikan tugas background.

### Input

- Pesan user.
- Chat ID.
- Profil bisnis user.
- Riwayat feedback style.
- Status data internal.
- Status task background yang sedang berjalan.

### Output

- Routing decision.
- Tool plan.
- Agent task list.
- Response mode: instant, normal, async follow-up.

### Contoh routing

```text
"halo"
-> instant greeting

"ingatkan saya besok jam 9 bayar supplier"
-> Reminder Agent

"Aku jual ayam geprek di Bandung target margin 30%"
-> Customer Understanding Agent + Business Memory Agent

"HPP 11.500 jual 18.000 aman nggak?"
-> Price & Supplier Agent calculator + Business Analyst Agent

"trend minuman murah buat anak sekolah apa?"
-> Trend Radar Agent + Business Analyst Agent
```

### Guardrail

- Jangan panggil crawler untuk sapaan, reminder, atau kalkulasi sederhana.
- Jangan panggil banyak agent jika satu tool cukup.
- Jika data kurang, jawab batasan data secara jelas dan buat background task.

### KPI

- Latency rata-rata chat.
- Jumlah tool call per chat.
- Persentase jawaban yang selesai tanpa crawling.
- Persentase pertanyaan yang berhasil dirouting benar.

## 5. Agent 2: Customer Understanding Agent

### Misi

Mempelajari karakteristik user dari percakapan.

Agent ini fokus memahami:

- User jual apa.
- Lokasi bisnis.
- Skala bisnis.
- Target margin.
- Supplier utama.
- Masalah yang sering muncul.
- Gaya bahasa yang disukai user.
- Tingkat risiko yang nyaman untuk user.
- Tujuan bisnis jangka pendek.

### Input

- Pesan user baru.
- Riwayat chat ringkas.
- Feedback user.
- Profil bisnis yang sudah tersimpan.

### Output

Structured insight, bukan paragraf bebas.

Contoh output:

```json
{
  "business_type": "kuliner",
  "location": "Bandung",
  "main_products": ["ayam geprek", "es teh"],
  "target_margin_percent": 30,
  "known_supplier": "Pasar Ciroyom",
  "risk_preference": "hati-hati",
  "response_style": "singkat, natural, langsung rekomendasi",
  "open_needs": [
    "butuh pantauan harga ayam",
    "butuh strategi promo tanpa menurunkan margin"
  ]
}
```

### Learning Method

Yang boleh dipelajari otomatis:

- Fakta bisnis yang user sebut eksplisit.
- Preferensi gaya jawaban.
- Produk yang sering dibahas.
- Reminder dan rutinitas kerja.
- Masalah bisnis yang berulang.

Yang harus minta konfirmasi:

- Data sensitif.
- Angka omzet.
- Biaya tetap.
- Target profit besar.
- Kesimpulan yang hanya inferensi, bukan pernyataan user.

Contoh:

```text
User: "Kayaknya pembeli saya kebanyakan anak sekolah."

Agent tidak boleh langsung menyimpan sebagai fakta pasti.
Agent simpan sebagai hypothesis:
"segmentasi kemungkinan: anak sekolah, confidence medium"
```

### Guardrail

- Jangan menyimpan gosip atau data pribadi yang tidak relevan.
- Jangan menganggap inferensi sebagai fakta.
- Jangan menghapus memori lama tanpa event eksplisit.
- Simpan confidence score.

### KPI

- Akurasi ekstraksi profil.
- Berapa sering user merasa "jawabannya nyambung".
- Berapa banyak pertanyaan lanjutan yang bisa dikurangi karena memori sudah cukup.

## 6. Agent 3: Business Memory Agent

### Misi

Mengelola memori jangka pendek dan jangka panjang user.

Customer Understanding Agent mengekstrak insight. Business Memory Agent memutuskan bagaimana insight itu disimpan, diperbarui, dikonfirmasi, atau dihapus.

### Jenis Memori

Short-term memory:

- Topik percakapan aktif.
- Jawaban terakhir.
- Feedback terakhir.
- Task yang baru dibuat.

Long-term memory:

- Profil bisnis.
- Produk utama.
- Target margin.
- Supplier.
- Lokasi.
- Preferensi jawaban.
- Preferensi risiko.

Episodic memory:

- Keputusan penting yang pernah dibuat.
- Rekomendasi yang pernah diberikan.
- Hasil follow-up.

### Output

- Memory update.
- Memory conflict warning.
- Context pack ringkas untuk ChatEngine.

Contoh context pack:

```json
{
  "business_summary": "User menjalankan bisnis kuliner di Bandung, produk utama ayam geprek dan es teh.",
  "pricing_goal": "target margin minimal 30%",
  "supplier_context": "supplier utama Pasar Ciroyom",
  "style": "jawab singkat, natural, langsung rekomendasi",
  "risk": "hati-hati"
}
```

### Guardrail

- Jangan mengirim semua memori ke AI.
- Kirim context pack ringkas saja.
- Konflik memori harus ditandai, bukan ditimpa diam-diam.
- User harus bisa reset memori.

### KPI

- Context pack semakin pendek tapi relevan.
- Response semakin personal tanpa prompt terlalu panjang.
- Konflik memori terdeteksi.

## 7. Agent 4: Market Crawler Agent

### Misi

Mencari dan memperbarui data pasar dari sumber luar secara terjadwal atau berdasarkan kebutuhan user yang terdeteksi.

Agent ini bukan dipanggil setiap chat. Ia bekerja di background.

### Input

- Open needs dari Customer Understanding Agent.
- Produk utama user.
- Lokasi user.
- Source list aktif.
- Query trend.
- Crawl schedule.

### Output

- Artikel relevan.
- Harga pasar.
- Supplier candidate.
- Kompetitor candidate.
- Raw evidence.
- Crawl health report.

### Contoh Task

```json
{
  "task_type": "market_price_refresh",
  "product": "ayam broiler",
  "location": "Bandung",
  "priority": "high",
  "reason": "User sering tanya margin ayam geprek"
}
```

### Source Strategy

Prioritas sumber:

- Sumber resmi pemerintah atau lembaga.
- Marketplace atau katalog supplier yang stabil.
- Media bisnis yang relevan.
- Website kompetitor lokal.
- Social signal jika sudah punya parser yang aman.

### Guardrail

- Respect robots.txt dan terms sumber.
- Rate limit per domain.
- Tidak scraping agresif.
- Simpan metadata source, timestamp, dan confidence.
- Jika sumber 404 atau berubah, disable otomatis dan laporkan.

### KPI

- Freshness data.
- Success rate crawler.
- Jumlah sumber aktif sehat.
- Jumlah insight yang benar-benar dipakai dalam chat.

## 8. Agent 5: Trend Radar Agent

### Misi

Membaca tren yang relevan untuk bisnis user.

Trend Radar Agent tidak hanya mencari berita terbaru. Ia mencari pola:

- Produk yang mulai naik permintaannya.
- Bahan baku yang mulai naik harga.
- Menu yang sedang ramai.
- Kompetitor yang agresif promo.
- Perubahan perilaku konsumen.
- Event musiman yang memengaruhi penjualan.

### Input

- Artikel hasil crawling.
- Price snapshots.
- Search signal.
- Riwayat pertanyaan user.
- Profil bisnis user.
- Kalender musiman.

### Output

Trend signal:

```json
{
  "trend": "permintaan menu ayam pedas meningkat",
  "relevance": "high",
  "affected_products": ["ayam geprek"],
  "suggested_action": "uji promo bundle ayam geprek + es teh",
  "confidence": 0.72,
  "evidence_ids": ["article-123", "price-456"]
}
```

### Guardrail

- Bedakan tren kuat, sinyal lemah, dan spekulasi.
- Jangan menyarankan stok besar jika confidence rendah.
- Selalu beri basis data ringkas.

### KPI

- Tren yang berujung action.
- Akurasi sinyal terhadap feedback user.
- Jumlah alert yang dianggap berguna oleh user.

## 9. Agent 6: Price & Supplier Agent

### Misi

Membantu user mengambil keputusan harga, HPP, margin, supplier, dan stok.

Agent ini harus sangat praktis.

### Tugas Utama

- Hitung margin.
- Rekomendasikan harga jual.
- Bandingkan supplier.
- Cek apakah promo masih aman.
- Cek dampak kenaikan bahan baku.
- Cari supplier alternatif.

### Input

- Produk user.
- HPP.
- Harga jual.
- Target margin.
- Harga pasar internal.
- Supplier candidate.

### Output

```json
{
  "gross_profit": 6500,
  "gross_margin_percent": 36.1,
  "status": "aman",
  "recommended_price_range": [18000, 20000],
  "reason": "margin di atas target 30%, tetapi belum memasukkan kemasan dan komisi platform"
}
```

### Guardrail

- Kalkulasi harus deterministic.
- Jangan pakai AI untuk matematika sederhana.
- AI hanya dipakai untuk menjelaskan hasil dan rekomendasi.
- Pisahkan HPP, biaya tambahan, dan margin final.

### KPI

- Jawaban kalkulasi cepat.
- Angka konsisten.
- User bisa langsung ambil keputusan.

## 10. Agent 7: Business Analyst Agent

### Misi

Mengubah data menjadi rekomendasi bisnis yang bisa dilakukan user.

Agent ini bukan crawler dan bukan memory manager. Ia membaca context pack dan tool result, lalu menyusun insight.

### Input

- User question.
- Business context pack.
- Tool results.
- Evidence summary.
- Trend signal.

### Output

- Jawaban akhir.
- Action items.
- Risiko.
- Sumber atau basis ringkas.
- Follow-up question jika data kurang.

### Answer Style

Untuk Telegram, format default:

```text
Jawaban singkat dulu.

Angkanya:
- HPP:
- Harga jual:
- Margin:

Rekomendasi:
1. ...
2. ...

Catatan:
...
```

### Guardrail

- Jangan terlalu formal.
- Jangan menyebut internal system seperti DB, crawler, embedding, atau signal row.
- Jangan pura-pura punya data jika data tidak ada.
- Jangan memberi saran finansial ekstrem tanpa basis.

### KPI

- User tidak perlu bertanya ulang karena jawaban terlalu abstrak.
- Feedback negatif turun.
- Rekomendasi lebih sering dipakai.

## 11. Agent 8: Response Coach Agent

### Misi

Memperbaiki kualitas jawaban sebelum dikirim ke user dan belajar dari feedback.

Agent ini fokus pada gaya, bukan fakta utama.

### Input

- Draft jawaban Business Analyst Agent.
- Preferensi style user.
- Feedback historis.
- Quality rules.

### Output

- Final answer yang lebih natural.
- Style correction note.
- Feedback example untuk future few-shot.

### Yang Dipelajari

- User suka jawaban singkat atau detail.
- User tidak suka istilah teknis tertentu.
- User lebih nyaman dengan bahasa santai atau formal.
- User sering minta format tertentu.

### Cara Improve Secara Aman

Jangan biarkan agent otomatis mengubah prompt production secara langsung.

Gunakan alur:

```text
Feedback user
  -> Response Coach Agent
  -> Save feedback example
  -> Weekly quality summary
  -> Suggested prompt/rule improvement
  -> Human review
  -> Deploy
```

Untuk perubahan kecil per user, boleh otomatis:

- Simpan preferensi style.
- Tambah few-shot per user.
- Hindari frasa yang user tidak suka.

Untuk perubahan global, wajib review.

### KPI

- Feedback "terlalu kaku" turun.
- Jawaban makin sesuai gaya user.
- Panjang jawaban sesuai preferensi.

## 12. Agent 9: Reminder & Follow-Up Agent

### Misi

Menjadikan Sorota terasa seperti asisten bisnis harian.

### Tugas

- Membuat reminder.
- Mengirim follow-up hasil background task.
- Mengingatkan cek stok.
- Mengingatkan bayar supplier.
- Mengingatkan update harga.
- Mengirim brief harian jika user subscribe.

### Input

- Reminder eksplisit dari user.
- Rutinitas yang dikonfirmasi user.
- Background task result.
- Jadwal harian.

### Output

```text
Pengingat: bayar supplier ayam
```

Atau:

```text
Update supplier ayam Bandung sudah masuk.
Harga pembanding paling rendah yang ketemu: ...
```

### Guardrail

- Jangan membuat reminder dari inferensi tanpa konfirmasi.
- Jangan spam.
- User harus bisa stop reminder.
- Follow-up hanya dikirim jika relevan dan diminta.

### KPI

- Reminder terkirim tepat waktu.
- Follow-up dibaca/dibalas.
- User merasa terbantu, bukan terganggu.

## 13. Agent 10: Quality & Safety Agent

### Misi

Menjaga agar sistem tidak ngawur, tidak boros tool call, dan tidak melanggar batas data.

### Tugas

- Mengecek apakah jawaban terlalu spekulatif.
- Mengecek apakah rekomendasi punya basis.
- Mengecek apakah tool call berlebihan.
- Mengecek apakah data user sensitif ikut masuk prompt.
- Memberi score kualitas jawaban.

### Output

```json
{
  "quality_score": 0.82,
  "risk_flags": [],
  "needs_revision": false,
  "notes": "jawaban cukup ringkas dan memakai data margin yang valid"
}
```

### Guardrail

- Jangan menahan semua jawaban, karena latency bisa naik.
- Untuk chat sederhana, quality check cukup rule-based.
- Untuk rekomendasi besar, boleh pakai AI reviewer.

### KPI

- Hallucination turun.
- Tool cost turun.
- Jawaban berisiko tertahan sebelum dikirim.

## 14. MCP Positioning

MCP cocok dipakai setelah tool internal stabil.

Tool yang paling cocok diexpose sebagai MCP:

```text
get_business_profile
save_business_profile
calculate_margin
recommend_price
get_market_prices
search_business_signals
create_reminder
list_reminders
create_crawl_task
get_trend_signals
save_response_feedback
```

Prinsip MCP untuk Sorota:

- MCP adalah boundary, bukan otak utama.
- MCP result harus kecil dan structured.
- MCP tidak boleh mengembalikan dump database panjang.
- MCP tool harus punya permission dan rate limit.
- MCP tool harus logging semua pemanggilan.

Contoh MCP result yang baik:

```json
{
  "tool": "calculate_margin",
  "result": {
    "hpp": 11500,
    "selling_price": 18000,
    "gross_profit": 6500,
    "gross_margin_percent": 36.1,
    "status": "above_target"
  }
}
```

Contoh MCP result yang buruk:

```json
{
  "all_database_rows": [
    "... ratusan baris ..."
  ]
}
```

## 15. Learning Loop

Learning loop yang disarankan:

```text
1. User chat
2. Customer Understanding Agent ekstrak kebutuhan
3. Business Memory Agent update profil atau hypothesis
4. Orchestrator memilih tool/agent
5. Business Analyst Agent menjawab
6. Response Coach Agent merapikan gaya
7. Feedback user disimpan
8. Background agents mengisi data yang kurang
9. Quality summary dibuat berkala
10. Improvement proposal dibuat untuk human review
```

Yang boleh self-improve otomatis:

- Preferensi style per user.
- Memory profil user.
- Ranking sumber yang sering berhasil.
- Query crawling berdasarkan kebutuhan user.
- Template follow-up personal.

Yang tidak boleh self-improve otomatis:

- Prompt global production.
- Source crawling baru yang berisiko.
- Keputusan bisnis besar tanpa basis data.
- Penghapusan data user.
- Perubahan schema database.

## 16. Data Model Yang Disarankan

Tabel atau konsep yang dibutuhkan:

### `agent_tasks`

Menyimpan task background.

Field utama:

- `id`
- `agent_name`
- `task_type`
- `status`
- `priority`
- `payload_json`
- `result_json`
- `error_message`
- `created_at`
- `started_at`
- `finished_at`

### `agent_runs`

Audit setiap agent run.

Field utama:

- `id`
- `agent_name`
- `chat_id`
- `input_summary`
- `output_summary`
- `tool_calls_json`
- `latency_ms`
- `token_usage_json`
- `status`

### `user_needs`

Kebutuhan customer yang terdeteksi.

Field utama:

- `chat_id`
- `need_type`
- `product`
- `location`
- `description`
- `confidence_score`
- `status`
- `last_seen_at`

### `trend_signals`

Sinyal tren yang sudah diproses.

Field utama:

- `signal_type`
- `product`
- `location`
- `trend_summary`
- `confidence_score`
- `evidence_ids_json`
- `suggested_action`
- `valid_until`

### `response_quality_examples`

Dataset untuk memperbaiki jawaban.

Field utama:

- `chat_id`
- `question`
- `bad_answer`
- `feedback`
- `improved_answer`
- `style_tags_json`
- `intent`

## 17. Event Flow Detail

### 17.1 Saat User Memberi Profil Bisnis

```text
User:
"Aku jual ayam geprek di Bandung, target margin 30%"

Flow:
1. Orchestrator deteksi profile update.
2. Customer Understanding Agent ekstrak data.
3. Business Memory Agent simpan.
4. Response Coach Agent balas natural.

Reply:
"Siap, aku catat: bisnis kuliner di Bandung, produk ayam geprek, target margin 30%. Nanti jawaban pricing aku pakai patokan itu."
```

### 17.2 Saat User Bertanya Margin

```text
User:
"HPP 11.500 jual 18.000 aman nggak?"

Flow:
1. Orchestrator deteksi kalkulasi.
2. Price & Supplier Agent hitung deterministic.
3. Business Analyst Agent beri rekomendasi.
4. Response Coach Agent sesuaikan gaya user.
```

### 17.3 Saat User Butuh Data Baru

```text
User:
"Supplier telur murah Bandung ada nggak?"

Flow real-time:
1. Orchestrator cek database.
2. Jika data kurang, jawab batasan data.
3. Buat background task untuk Market Crawler Agent.

Flow background:
1. Market Crawler Agent cari kandidat.
2. Price & Supplier Agent normalisasi harga.
3. Trend Radar Agent cek relevansi.
4. Reminder & Follow-Up Agent kabari user jika selesai.
```

## 18. Roadmap Implementasi

### Phase 1: Tool Layer Internal

Target:

- Rapikan fungsi stabil menjadi `chat_engine/tools`.
- Pindahkan kalkulasi margin ke tool deterministic.
- Pindahkan access memory ke tool.
- Pindahkan reminder ke tool.

Deliverable:

- `calculate_margin`
- `get_business_profile`
- `save_business_profile`
- `create_reminder`
- `search_business_signals`

### Phase 2: Orchestrator Ringan

Target:

- Buat routing eksplisit sebelum ChatEngine.
- Bedakan instant, normal, background.
- Catat tool plan.

Deliverable:

- `ConversationOrchestrator`
- `RouteDecision`
- Test routing.

### Phase 3: Customer Understanding Agent

Target:

- Ekstraksi profil lebih rapi.
- Confidence score.
- Hypothesis vs confirmed fact.

Deliverable:

- `CustomerUnderstandingAgent`
- `BusinessMemoryAgent`
- Memory conflict detection.

### Phase 4: Background Agent Tasks

Target:

- Task queue sederhana berbasis DB.
- Crawler tidak dipanggil langsung dari chat user.
- Trend dan supplier refresh berjalan async.

Deliverable:

- `agent_tasks`
- `MarketCrawlerAgent`
- `TrendRadarAgent`

### Phase 5: Response Quality Loop

Target:

- Feedback user menjadi dataset.
- Response Coach Agent merapikan gaya.
- Quality summary berkala.

Deliverable:

- `ResponseCoachAgent`
- `QualitySafetyAgent`
- Weekly improvement report.

### Phase 6: MCP Server

Target:

- Expose tool yang stabil sebagai MCP.
- Batasi permission.
- Logging semua tool call.

Deliverable:

- `sorota_mcp_server`
- MCP tools untuk memory, margin, price, signal, reminder.

## 19. MVP Agent Yang Paling Penting

Untuk versi awal, jangan langsung bangun semua agent.

Prioritas MVP:

1. Conversation Orchestrator.
2. Customer Understanding Agent.
3. Business Memory Agent.
4. Price & Supplier Agent.
5. Response Coach Agent.
6. Market Crawler Agent background.

Alasan:

- Ini langsung memperbaiki chat yang kaku.
- Ini membuat jawaban lebih personal.
- Ini mengurangi crawling real-time.
- Ini memberi fondasi untuk MCP.

Trend Radar dan Quality Agent bisa menyusul setelah alur dasar stabil.

## 20. Pendapat Teknis

Konsep banyak agent bisa dilakukan, tetapi harus disiplin.

Yang sebaiknya dihindari:

- Membuat 10 agent AI yang semuanya memanggil LLM setiap chat.
- Membiarkan agent crawler jalan karena setiap user tanya.
- Mengirim seluruh database ke prompt.
- Membiarkan agent mengubah prompt global sendiri.
- Membuat MCP sebelum tool internal jelas.

Yang sebaiknya dilakukan:

- Mulai dari service/tool kecil yang deterministic.
- Pakai agent AI hanya untuk pemahaman bahasa, ranking, dan penyusunan rekomendasi.
- Jalankan crawling sebagai background task.
- Simpan hasil belajar dalam struktur data.
- Gunakan MCP sebagai boundary setelah tool stabil.

Kesimpulan:

```text
Sorota cocok dibuat multi-agent, tetapi bukan multi-agent yang semuanya aktif setiap chat.
Sorota harus menjadi sistem agentik yang hemat, terstruktur, dan memory-aware.
```
