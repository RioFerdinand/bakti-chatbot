import { useState, useEffect } from "react";
import "./meetingReport.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function MeetingReportModal({ onClose }) {
  const [transcript, setTranscript] = useState("");
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  const user = JSON.parse(localStorage.getItem("user")) || {};

  const loadHistory = async () => {
    if (!user?.id) return;
    try {
      const res = await fetch(`${API_URL}/reports/${user.id}`);
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      // Diamkan, riwayat gak krusial buat fungsi utama modal ini
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const appendExtractedText = (text) => {
    setTranscript((prev) => (prev.trim() ? prev + "\n\n" + text : text));
  };

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setExtracting(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_URL}/extract-notes`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Gagal membaca teks dari foto");

      appendExtractedText(data.extracted_text);
    } catch (err) {
      setError(err.message || "Gagal membaca teks dari foto.");
    } finally {
      setExtracting(false);
      e.target.value = "";
    }
  };

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setExtracting(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${API_URL}/extract-pdf-text`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Gagal membaca teks dari PDF");

      appendExtractedText(data.extracted_text);
    } catch (err) {
      setError(err.message || "Gagal membaca teks dari PDF.");
    } finally {
      setExtracting(false);
      e.target.value = "";
    }
  };

  const handleGenerate = async () => {
    if (!transcript.trim() || loading) return;
    if (!user?.id) {
      setError("Sesi login tidak ditemukan, silakan login ulang.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/generate-report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, user_id: user.id }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Gagal membuat laporan");
      }

      setResult(data);
      loadHistory(); // refresh daftar riwayat setelah berhasil generate baru
    } catch (err) {
      setError(err.message || "Gagal membuat laporan. Pastikan backend & Ollama sedang berjalan.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setTranscript("");
    setError("");
  };

  return (
    <div className="report-overlay">
      <div className="report-modal">
        <div className="report-header">
          <h3>Ringkasan Rapat → PDF (Template BAKTI)</h3>
          <button className="report-close" onClick={onClose}>✕</button>
        </div>

        {!result && (
          <>
            <div className="report-upload-row">
              <label className="report-upload-btn">
                📷 {extracting ? "Membaca..." : "Upload Foto Catatan"}
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handlePhotoUpload}
                  disabled={extracting}
                  hidden
                />
              </label>
              <label className="report-upload-btn">
                📄 {extracting ? "Membaca..." : "Upload PDF Notulen"}
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handlePdfUpload}
                  disabled={extracting}
                  hidden
                />
              </label>
            </div>
            <p className="report-upload-hint">
              Bisa upload lebih dari satu — hasil bacaannya digabung otomatis.
              Teksnya bisa diedit dulu di bawah sebelum dibuat PDF.
            </p>

            <textarea
              className="report-textarea"
              placeholder="Paste transkrip rapat, atau upload foto/PDF di atas..."
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              rows={9}
            />
            <button
              className="report-generate-btn"
              onClick={handleGenerate}
              disabled={!transcript.trim() || loading || extracting}
            >
              {loading ? "Membuat laporan..." : "Buat Ringkasan PDF"}
            </button>

            {history.length > 0 && (
              <div className="report-history">
                <span className="report-label">Riwayat Laporan</span>
                <ul>
                  {history.map((r) => (
                    <li key={r.id}>
                      <span>{r.judul}</span>
                      <a
                        href={`${API_URL}/download-report/${r.pdf_filename}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        {error && <p className="report-error">{error}</p>}

        {result && (
          <div className="report-result">
            <div>
              <span className="report-label">Judul</span>
              <p>{result.judul}</p>
            </div>
            <div>
              <span className="report-label">Ringkasan</span>
              <p>{result.ringkasan}</p>
            </div>

            {result.poin_penting?.length > 0 && (
              <div>
                <span className="report-label">Poin Penting</span>
                <ul>
                  {result.poin_penting.map((p, i) => <li key={i}>{p}</li>)}
                </ul>
              </div>
            )}

            {result.action_items?.length > 0 && (
              <div>
                <span className="report-label">Action Items</span>
                <ul>
                  {result.action_items.map((a, i) => (
                    <li key={i}>{a.tugas} — {a.penanggung_jawab} ({a.tenggat})</li>
                  ))}
                </ul>
              </div>
            )}

            <a
              className="report-download-btn"
              href={`${API_URL}/download-report/${result.pdf_filename}`}
              target="_blank"
              rel="noreferrer"
            >
              Download PDF
            </a>
            <button className="report-reset-btn" onClick={handleReset}>
              Buat ringkasan lain
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
