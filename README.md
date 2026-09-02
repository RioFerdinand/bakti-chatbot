# 🦙 RAG Chatbot Llama (Lokal & Gratis)

Chatbot berbasis **RAG (Retrieval-Augmented Generation)** yang menjawab pertanyaan berdasarkan
dokumen PDF/Word milikmu, menggunakan model **Llama** yang berjalan lokal lewat **Ollama** —
tanpa biaya API sama sekali.

## 🧩 Arsitektur

```
User → Streamlit (UI) → FastAPI (backend) → RAG (ChromaDB) → Llama (Ollama) → Jawaban
```

## 📁 Struktur Folder

```
RAG-Chatbot/
├── backend/
│   ├── app.py        # Server FastAPI (endpoint /upload, /chat, /reindex)
│   ├── rag.py         # Kelola ChromaDB (simpan & cari potongan dokumen)
│   ├── loader.py       # Baca & pecah file PDF/Word jadi chunk
│   ├── chatbot.py       # Kirim prompt ke Llama via Ollama
│   └── config.py       # Konfigurasi terpusat (baca dari .env)
├── frontend/
│   └── app.py         # UI chat berbasis Streamlit
├── data/
│   ├── pdf/           # Taruh file PDF di sini
│   └── word/           # Taruh file Word di sini
├── chroma_db/          # Vector database (dibuat otomatis)
├── requirements.txt
├── .env.example
└── README.md
```

## 🛠️ Prasyarat yang Harus Diinstal

| Aplikasi | Link | Wajib? |
|---|---|---|
| Python 3.11/3.12 | https://www.python.org/downloads/ | ✅ |
| Git | https://git-scm.com/downloads | ✅ |
| Ollama | https://ollama.com/download | ✅ |
| Visual Studio Code | https://code.visualstudio.com/ | Disarankan |

## 🚀 Langkah Instalasi

### 1. Clone / salin project ini, lalu masuk ke foldernya
```bash
cd RAG-Chatbot
```

### 2. Buat virtual environment
```bash
python -m venv venv
```
Aktifkan:
- Windows: `venv\Scripts\activate`
- Mac/Linux: `source venv/bin/activate`

### 3. Install semua library Python
```bash
pip install -r requirements.txt
```

### 4. Install Ollama & download model
Setelah Ollama terinstal, jalankan di terminal:
```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```
Cek apakah berhasil:
```bash
ollama list
```

### 5. Siapkan file konfigurasi
```bash
cp .env.example .env
```
(Boleh diubah sesuai kebutuhan, defaultnya sudah langsung jalan)

### 6. Taruh dokumenmu
Masukkan file PDF ke `data/pdf/` dan file Word ke `data/word/`.

## ▶️ Menjalankan Aplikasi

Butuh **3 terminal terpisah** (Ollama, backend, frontend):

**Terminal 1 — pastikan Ollama jalan** (biasanya otomatis jalan sebagai service setelah install)
```bash
ollama serve
```

**Terminal 2 — jalankan backend FastAPI**
```bash
    cd backend
uvicorn app:app --reload --port 8000
```
Backend akan berjalan di `http://localhost:8000`
Dokumentasi API otomatis tersedia di `http://localhost:8000/docs`

**Terminal 3 — jalankan frontend Streamlit**
```bash
cd frontend
streamlit run app.py
```
UI chatbot akan terbuka otomatis di browser (`http://localhost:8501`)

## 💬 Cara Pakai
1. Buka UI Streamlit di browser.
2. Di sidebar kiri, upload file PDF/Word lalu klik **"Upload & Index"**
   — atau jika sudah menaruh banyak file langsung di folder `data/pdf` dan `data/word`,
   klik **"Re-index Semua Dokumen"**.
3. Ketik pertanyaan di kotak chat. Chatbot akan menjawab berdasarkan isi dokumenmu,
   lengkap dengan nama file sumber di bawah jawaban.

## ⚙️ Kustomisasi

- **Ganti model**: ubah `LLM_MODEL` di `.env` (misalnya ke `phi3` atau `llama3.2:1b` untuk laptop dengan RAM terbatas).
- **Jumlah konteks yang diambil**: ubah parameter `k` di `frontend/app.py` (default 4 potongan dokumen).
- **Ukuran chunk**: ubah `chunk_size` dan `chunk_overlap` di `backend/loader.py`.

## 💻 Spesifikasi Laptop yang Disarankan

| Komponen | Minimum | Rekomendasi |
|---|---|---|
| RAM | 8 GB | 16 GB |
| Storage | 15 GB kosong | SSD 50 GB+ |
| CPU | Intel i5 Gen 8 / Ryzen 5 | Intel i7 / Ryzen 7 |
| GPU | Tidak wajib | NVIDIA (opsional, mempercepat) |

Jika RAM hanya 8 GB, gunakan model yang lebih ringan seperti `llama3.2:3b` atau `phi3:mini`.

## 🧪 Uji Cepat Lewat API (opsional, pakai Postman/curl)

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "Apa isi dokumen ini?", "k": 4}'
```

## ❗ Troubleshooting

- **"Backend: tidak terhubung"** di Streamlit → pastikan `uvicorn` di Terminal 2 masih jalan.
- **Error koneksi ke Ollama** → pastikan `ollama serve` jalan dan model sudah di-`pull`.
- **Jawaban kosong/tidak relevan** → pastikan dokumen sudah di-index (cek folder `chroma_db/` sudah terisi), atau coba `Re-index Semua Dokumen`.
- **Proses lambat di laptop 8GB RAM** → ganti ke model lebih kecil seperti `llama3.2:3b` di file `.env`.

---
Dibuat 100% gratis dan berjalan lokal — tidak ada biaya lisensi atau API key berbayar.
