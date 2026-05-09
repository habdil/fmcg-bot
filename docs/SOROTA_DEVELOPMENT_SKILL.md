# Sorota Development Skill

Dokumen ini adalah repo-local development skill untuk mengarahkan refactor Sorota. Gunakan dokumen ini sebagai pegangan ketika mengembangkan chat engine, AI gateway, database memory, prompt, dan market intelligence.

Catatan: ini bukan skill global Codex yang sudah terpasang di `~/.codex/skills`. Ini adalah instruksi project-level agar development Sorota konsisten.

## 1. Keputusan Utama

Sorota menggunakan strategi:

```text
OpenAI-first, provider-agnostic internally.
```

Artinya:

- Untuk MVP/refactor awal, gunakan OpenAI API sebagai satu-satunya provider aktif.
- Jangan jalankan Claude, Gemini, dan OpenAI bersamaan di production.
- Jangan memanggil SDK OpenAI langsung dari banyak modul.
- Semua panggilan model harus lewat AI gateway internal.
- Kode tetap dibuat cukup rapi agar provider bisa diganti di masa depan tanpa rewrite besar.

Istilah "ChatGPT API" di project ini berarti OpenAI API untuk membangun pengalaman chat Sorota.

## 2. Prinsip Produk Yang Harus Dijaga

Sorota bukan chatbot umum. Sorota adalah AI pendamping keputusan bisnis untuk UMKM Indonesia.

Jawaban Sorota harus:

- Singkat.
- Praktis.
- Berbasis data yang tersedia.
- Mengandung rekomendasi tindakan.
- Menyebutkan data yang kurang jika konteks belum cukup.
- Tidak mengarang harga, supplier, kompetitor, margin, atau data pasar.

Untuk pertanyaan sederhana, Sorota harus menjawab cepat tanpa crawling berat.

Untuk pertanyaan yang butuh data pasar, Sorota boleh melakukan survey/crawling terkontrol, menyimpan hasilnya, lalu menjawab berdasarkan evidence.

## 3. AI Gateway

Semua request AI harus melewati gateway.

Target struktur:

```text
chat_engine/
  ai_gateway/
    __init__.py
    client.py
    schemas.py
    openai_provider.py
    prompts/
      intent_router.md
      memory_extractor.md
      answer_composer.md
```

Gateway minimal harus menyediakan:

```python
class AIGateway:
    def generate_text(self, request: AITextRequest) -> AITextResponse:
        ...

    def generate_json(self, request: AIJsonRequest) -> AIJsonResponse:
        ...
```

Response gateway harus selalu mengembalikan metadata:

- `provider`
- `model`
- `prompt_version`
- `input_tokens`
- `output_tokens`
- `cached_tokens`
- `latency_ms`
- `finish_reason`
- `raw_error` jika gagal

Tujuannya agar kualitas, biaya, dan latency bisa diukur.

## 4. OpenAI API Direction

Gunakan OpenAI Responses API sebagai jalur utama untuk request model baru.

Gunakan structured output untuk task yang harus valid secara program:

- Intent routing.
- Memory extraction.
- Business profile extraction.
- Product/cost extraction.
- Safety/business-domain classification.

Gunakan text response biasa untuk:

- Final answer composer.
- Business explanation.
- Summary singkat untuk user.

Referensi resmi:

- Models: https://developers.openai.com/api/docs/models
- Responses API: https://platform.openai.com/docs/api-reference/responses
- Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- Prompt Caching: https://platform.openai.com/docs/guides/prompt-caching
- Prompting: https://platform.openai.com/docs/guides/prompting

## 5. Environment Config

Gunakan config/env agar model bisa diganti tanpa edit banyak file.

Contoh target:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_DEFAULT_MODEL=...
OPENAI_INTENT_MODEL=...
OPENAI_MEMORY_MODEL=...
OPENAI_ANSWER_MODEL=...
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_OUTPUT_TOKENS=900
OPENAI_REASONING_EFFORT=low
```

Aturan:

- `OPENAI_API_KEY` tidak boleh hardcoded.
- Jika model task-specific kosong, fallback ke `OPENAI_DEFAULT_MODEL`.
- Default model harus dipilih dari dokumentasi resmi OpenAI yang sedang berlaku.
- Jangan menyimpan API key ke dokumen, log, test fixture, atau database.

## 6. Task Routing

Pisahkan task AI berdasarkan kebutuhan.

### 6.1 Intent Router

Tujuan:

- Menentukan apakah pertanyaan user relevan dengan bisnis UMKM.
- Menentukan intent utama.
- Menentukan data yang dibutuhkan.
- Menentukan apakah butuh tool/crawling/calculator.

Output harus JSON terstruktur.

Contoh enum intent:

```text
business_advice
pricing
margin_analysis
market_price_survey
supplier_search
competitor_analysis
product_performance
profile_update
smalltalk
out_of_scope
```

### 6.2 Memory Extractor

Tujuan:

- Mengambil fakta bisnis penting dari chat.
- Mengubah input bebas menjadi data terstruktur.
- Menandai apakah fakta perlu konfirmasi user.

Jangan simpan semua chat sebagai memory permanen.

### 6.3 Answer Composer

Tujuan:

- Menyusun jawaban final.
- Menggunakan konteks yang sudah dipilih oleh context builder.
- Tidak melakukan kalkulasi utama jika hasil kalkulasi sudah tersedia dari code.

Format jawaban default:

```text
Jawaban singkat.
Angka penting jika ada.
Analisa bisnis.
Rekomendasi tindakan.
Data yang masih kurang jika perlu.
```

## 7. Token Budget

Masalah utama yang ingin diperbaiki adalah token terlalu besar dan jawaban AI jelek. Karena itu setiap task harus punya budget.

Target awal:

```text
intent_router:
  input: kecil, hanya user message + profil super ringkas
  output: JSON pendek

memory_extractor:
  input: user message + assistant answer terakhir jika perlu
  output: JSON pendek

answer_composer:
  input: user message + selected context + tool results
  output: jawaban maksimal beberapa paragraf
```

Aturan context:

- Jangan kirim raw crawl panjang langsung ke final answer.
- Jangan kirim seluruh chat history.
- Jangan kirim semua database user.
- Ambil hanya profil bisnis, produk, harga, supplier, dan evidence yang relevan.
- Batasi evidence menjadi yang paling kuat, bukan yang paling banyak.
- Ringkas data panjang sebelum masuk prompt.

Prompt caching:

- Letakkan instruksi statis di awal prompt.
- Letakkan data user dan pertanyaan dinamis di akhir prompt.
- Pakai prompt version yang stabil.
- Log `cached_tokens` jika tersedia dari response usage.

## 8. Database Memory

Personalisasi harus berbasis database terstruktur.

Prioritas entity:

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
- `ai_requests`

`ai_requests` penting untuk observability:

```text
id
user_id
session_id
task_name
provider
model
prompt_version
input_tokens
output_tokens
cached_tokens
latency_ms
status
error_message
created_at
```

Reset database:

- Jika data masih dev/testing dan noisy, reset setelah schema v2 siap.
- Jika ada data user penting, archive dulu lalu migrasi selektif.
- Jangan migrasi raw chat lama ke memory permanen tanpa extraction dan validation.

## 9. Refactor Rules

Saat refactor:

- Pertahankan behavior yang masih berguna sampai flow baru stabil.
- Pisahkan modul besar menjadi service kecil yang bisa dites.
- Kalkulasi bisnis harus dilakukan oleh code, bukan diserahkan ke LLM.
- LLM boleh menjelaskan hasil kalkulasi, bukan menjadi sumber kebenaran angka.
- Crawling tidak boleh default terjadi untuk semua chat.
- Setiap perubahan besar harus punya test minimal untuk path utama.

Urutan implementasi yang disarankan:

1. Buat AI gateway OpenAI.
2. Tambahkan logging token/latency.
3. Buat intent router structured output.
4. Buat context builder hemat token.
5. Buat business calculator.
6. Buat memory extractor.
7. Refactor answer composer.
8. Rapikan database schema v2.
9. Baru pertimbangkan MCP untuk tool yang sudah stabil.

## 10. Development Workflow

Gunakan workflow kecil-per-kecil.

Prinsip:

- Develop satu fitur kecil dulu.
- Jangan menggabungkan terlalu banyak perubahan dalam satu batch.
- Setelah fitur selesai, berikan langkah testing end-user.
- User mencoba dari sisi pengguna nyata.
- Lanjut fitur berikutnya hanya setelah hasil testing jelas.

Siklus kerja:

```text
1. Pilih 1 fitur kecil
2. Jelaskan scope fitur
3. Implementasi
4. Verifikasi teknis
5. Tulis langkah testing end-user
6. User mencoba
7. Catat feedback
8. Fix atau lanjut fitur berikutnya
```

Ukuran fitur kecil yang ideal:

- Bisa diselesaikan dan dites dalam satu siklus.
- Punya output yang bisa dilihat user.
- Punya cara testing yang jelas.
- Tidak membutuhkan reset database kecuali memang phase database.

Contoh fitur kecil:

- OpenAI provider bisa dipakai dari router.
- Logging token dan latency muncul di log.
- Intent router bisa mendeteksi pertanyaan margin.
- Calculator margin menghasilkan angka benar.
- Jawaban harga tidak ditemukan lebih ringkas.
- Profil bisnis user bisa disimpan.

Setiap selesai fitur, berikan:

- File yang berubah.
- Perintah teknis yang sudah dijalankan.
- Hasil verifikasi.
- Cara menjalankan aplikasi/bot.
- Skenario testing end-user.
- Expected result.
- Known issue jika ada.
- Update report di `docs/SOROTA_REFACTOR_EXECUTION_REPORT.md`.

Template testing end-user:

```text
Fitur yang dites:
Cara menjalankan:
Data/env yang perlu disiapkan:
Langkah testing:
1. ...
2. ...
3. ...
Expected result:
Known issue:
```

Aturan sebelum lanjut:

- Jika user menemukan bug blocking, perbaiki dulu.
- Jika hanya ada feedback minor, catat dan lanjut sesuai prioritas.
- Jika hasil testing tidak sesuai target produk, revisi fitur sebelum masuk fitur besar berikutnya.
- Jangan lanjut ke task besar berikutnya sebelum report docs diperbarui.

## 11. Reporting Rules

Setiap selesai task atau fitur kecil, wajib update:

```text
docs/SOROTA_REFACTOR_EXECUTION_REPORT.md
```

Isi minimal report:

- Nama task/fitur.
- Status terbaru: `DONE`, `READY FOR USER TEST`, `BLOCKED`, atau `NEEDS FIX`.
- Tujuan task.
- File yang berubah.
- Verifikasi teknis yang dijalankan.
- Hasil verifikasi.
- Cara menjalankan untuk user test.
- Langkah testing end-user.
- Expected result.
- Known issue.
- Next action yang disarankan.

Jika task gagal atau terblokir, report tetap harus ditulis dengan:

- Apa yang gagal.
- Error utama.
- Dampaknya.
- Opsi perbaikan.

Progress log harus ditambahkan setiap ada perubahan penting:

```text
Tanggal
Status
Ringkasan pekerjaan
Hasil verifikasi
Catatan/known issue
```

Aturan final response setelah task selesai:

- Sebutkan file report yang diupdate.
- Ringkas apa yang selesai.
- Sertakan perintah test yang sudah dijalankan.
- Sertakan langkah testing end-user yang perlu user coba.

## 12. MCP Positioning

Jangan mulai dari MCP.

Mulai dari service internal yang jelas:

- `get_business_profile`
- `save_business_profile`
- `calculate_margin`
- `recommend_price`
- `get_market_prices`
- `save_market_price_survey`
- `find_supplier_candidates`

Setelah service stabil, baru expose sebagai MCP jika memang dibutuhkan.

MCP tidak otomatis mengurangi token. Token turun karena context builder, prompt, structured memory, dan tool result yang ringkas.

## 13. Quality Checklist

Sebelum menganggap refactor berhasil, cek:

- Semua call AI lewat gateway.
- Token usage tercatat.
- Latency tercatat.
- Prompt version tercatat.
- Intent router menghasilkan JSON valid.
- Memory extractor tidak menyimpan data sembarangan.
- Final answer tidak menerima raw crawl panjang.
- Jawaban punya rekomendasi praktis.
- Pertanyaan sederhana tidak memicu crawling.
- Pertanyaan non-bisnis ditolak singkat.
- Test utama berjalan.
- Execution report sudah diperbarui.

## 14. Response Style Sorota

Sorota harus menjawab seperti pendamping bisnis praktis, bukan laporan konsultan panjang.

Contoh gaya:

```text
Margin Anda sekitar 36%, masih aman untuk target 30%.

Tapi biaya kemasan dan komisi platform belum masuk. Kalau biaya tambahan sekitar Rp2.000 per porsi, harga jual yang lebih sehat ada di Rp19.000-Rp20.000.

Saran saya: jangan diskon dulu. Naikkan harga sedikit atau bundling dengan minuman supaya margin tidak turun.
```

Hindari:

- Jawaban panjang generik.
- Terlalu banyak teori bisnis.
- Angka tanpa sumber/perhitungan.
- Rekomendasi yang tidak bisa dilakukan user.
- Memasukkan semua evidence ke jawaban.
