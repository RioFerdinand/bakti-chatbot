"""
summarizer.py
Meringkas transkrip/notulen rapat mentah menjadi struktur rapi
(judul, ringkasan, poin penting, action items, peserta) memakai
model LLM yang sama dipakai ai.py (lewat Ollama).
"""
import json
import re

from langchain_ollama import OllamaLLM

# Samakan dengan model yang dipakai ai.py, biar konsisten satu Ollama saja
LLM_MODEL = "llama3.1"

SUMMARY_PROMPT = """Kamu adalah asisten yang meringkas transkrip atau notulen rapat.
Kamu HARUS menjawab HANYA dalam format JSON valid, tanpa teks lain, tanpa markdown
code block, tanpa penjelasan tambahan. Struktur JSON yang wajib diikuti persis:

{{
  "judul": "judul singkat rapat",
  "ringkasan": "ringkasan umum 2-4 kalimat",
  "poin_penting": ["poin 1", "poin 2"],
  "action_items": [
    {{"tugas": "deskripsi tugas", "penanggung_jawab": "nama atau -", "tenggat": "tanggal atau -"}}
  ],
  "peserta": ["nama1", "nama2"]
}}

Jika suatu informasi tidak disebutkan di transkrip, isi dengan array kosong atau
string "-". Jangan mengarang informasi yang tidak ada di transkrip.

Transkrip rapat:
{transcript}

Jawaban (HANYA JSON):"""

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = OllamaLLM(model=LLM_MODEL, temperature=0.2)
    return _llm


def _extract_json(raw_text: str) -> dict:
    """Ambil blok JSON dari output model, jaga-jaga kalau model nambahin teks lain."""
    raw_text = raw_text.strip()
    raw_text = re.sub(r"^```(json)?", "", raw_text).strip()
    raw_text = re.sub(r"```$", "", raw_text).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw_text[start : end + 1])
        raise


def summarize_meeting(transcript: str) -> dict:
    """
    Kirim transkrip rapat ke LLM, minta diringkas dalam format JSON terstruktur.
    Return dict dengan keys: judul, ringkasan, poin_penting, action_items, peserta.
    """
    if not transcript.strip():
        raise ValueError("Transkrip rapat kosong")

    llm = _get_llm()
    prompt = SUMMARY_PROMPT.format(transcript=transcript)

    try:
        raw = llm.invoke(prompt)
    except Exception as e:
        raise RuntimeError(f"Gagal menghubungi Ollama: {e}")

    try:
        data = _extract_json(raw)
    except (json.JSONDecodeError, ValueError):
        # Fallback minimal kalau model gagal kasih JSON valid
        data = {
            "judul": "Ringkasan Rapat",
            "ringkasan": raw.strip()[:800],
            "poin_penting": [],
            "action_items": [],
            "peserta": [],
        }

    data.setdefault("judul", "Ringkasan Rapat")
    data.setdefault("ringkasan", "-")
    data.setdefault("poin_penting", [])
    data.setdefault("action_items", [])
    data.setdefault("peserta", [])

    return data
