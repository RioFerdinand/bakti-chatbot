import { useEffect, useState } from "react";
import "./meetingSummaryModal.css";

export default function MeetingSummaryModal({ isOpen, onClose, userId, apiUrl }) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [history, setHistory] = useState([]);
  const [loadingAction, setLoadingAction] = useState(null); // "image" | "pdf" | "generate" | null
  const [error, setError] = useState("");

  useEffect(() => {
    if (isOpen && userId) {
      loadHistory();
    }
  }, [isOpen, userId]);

  const loadHistory = async () => {
    try {
      const res = await fetch(`${apiUrl}/reports/${userId}`);
      const data = await res.json();
      setHistory(data);
    } catch (err) {
      console.error("Gagal memuat riwayat laporan:", err);
    }
  };

  const handleUploadImage = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoadingAction("image");
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${apiUrl}/reports/extract-file`, { method: "POST", body: form }); // <-- DIUBAH (dulu /reports/extract-image)
      if (!res.ok) throw new Error((await res.json()).detail || "Gagal membaca gambar");
      const data = await res.json();
      setText((prev) => (prev ? prev + "\n" + data.text : data.text));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAction(null);
      e.target.value = "";
    }
  };

  const handleUploadPdf = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoadingAction("pdf");
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${apiUrl}/reports/extract-file`, { method: "POST", body: form }); // <-- DIUBAH (dulu /reports/extract-pdf)
      if (!res.ok) throw new Error((await res.json()).detail || "Gagal membaca PDF");
      const data = await res.json();
      setText((prev) => (prev ? prev + "\n" + data.text : data.text));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAction(null);
      e.target.value = "";
    }
  };

  const handleGenerate = async () => {
    if (!text.trim() || !userId) return;
    setLoadingAction("generate");
    setError("");
    try {
      const form = new FormData();
      form.append("user_id", userId);
      form.append("title", title.trim() || "Ringkasan Rapat");
      form.append("text", text);

      const res = await fetch(`${apiUrl}/reports/generate`, { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json()).detail || "Gagal membuat ringkasan");

      const report = await res.json();
      setHistory((prev) => [report, ...prev]);
      setText("");
      setTitle("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingAction(null);
    }
  };

  // BARU: hapus laporan dari riwayat (backend juga akan hapus file pdf/docx-nya)
  const handleDeleteReport = async (reportId) => {
    const confirmed = window.confirm("Hapus laporan ini? File PDF/Word-nya akan hilang permanen.");
    if (!confirmed) return;

    try {
      const res = await fetch(`${apiUrl}/reports/${reportId}`, { method: "DELETE" });
      if (!res.ok) throw new Error((await res.json()).detail || "Gagal menghapus laporan");
      setHistory((prev) => prev.filter((r) => r.id !== reportId));
    } catch (err) {
      setError(err.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="meeting-modal-overlay" onClick={onClose}>
      <div className="meeting-modal" onClick={(e) => e.stopPropagation()}>
        <div className="meeting-modal-header">
          <h2>Ringkasan Rapat → PDF (Template BAKTI)</h2>
          <button className="meeting-modal-close" onClick={onClose}>✕</button>
        </div>

        <input
          className="meeting-title-input"
          placeholder="Judul laporan (contoh: Rapat Mingguan Tim IT)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <div className="meeting-upload-row">
          <label className="meeting-upload-btn">
            📷 Upload Foto Catatan
            <input type="file" accept="image/*" hidden onChange={handleUploadImage} />
          </label>
          <label className="meeting-upload-btn">
            📄 Upload PDF Notulen
            <input type="file" accept="application/pdf" hidden onChange={handleUploadPdf} />
          </label>
        </div>

        <p className="meeting-hint">
          Bisa upload lebih dari satu — hasil bacaannya digabung otomatis. Teksnya bisa diedit dulu di bawah
          sebelum dibuat PDF.
          {loadingAction === "image" && " (membaca gambar...)"}
          {loadingAction === "pdf" && " (membaca PDF...)"}
        </p>

        <textarea
          className="meeting-textarea"
          placeholder="Paste transkrip rapat, atau upload foto/PDF di atas..."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />

        {error && <p className="meeting-error">⚠️ {error}</p>}

        <button
          className="meeting-generate-btn"
          onClick={handleGenerate}
          disabled={loadingAction === "generate" || !text.trim()}
        >
          {loadingAction === "generate" ? "Membuat Ringkasan..." : "Buat Ringkasan PDF/WORD"}
        </button>

        <hr className="meeting-divider" />

        <h4 className="meeting-history-label">Riwayat Laporan</h4>
        <ul className="meeting-history-list">
          {history.length === 0 && <li className="meeting-history-empty">Belum ada laporan.</li>}
          {history.map((r) => (
            <li key={r.id} className="meeting-history-item">
              <span className="meeting-history-title">{r.title}</span>
              <span className="meeting-history-links">
                <a href={`${apiUrl}/reports/download/${r.id}/pdf`} target="_blank" rel="noreferrer">PDF</a>
                {" · "}
                <a href={`${apiUrl}/reports/download/${r.id}/docx`} target="_blank" rel="noreferrer">Word</a>
                <button
                  className="meeting-history-delete"
                  onClick={() => handleDeleteReport(r.id)}
                  title="Hapus laporan"
                >
                  🗑
                </button>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}