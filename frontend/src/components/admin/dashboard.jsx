import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Globe, Lock as LockIcon, Plus, FileText, LogOut, Trash2, RefreshCw } from "lucide-react";
import "./dashboard.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const CATEGORIES = [
  {
    id: "public",
    label: "Public",
    desc: "Bisa diakses semua pengguna (termasuk yang belum login)",
    icon: Globe,
  },
  {
    id: "non-public",
    label: "Non Public",
    desc: "Cuma bisa diakses user yang sudah login",
    icon: LockIcon,
  },
];

const ACCEPTED_EXT = [".pdf"]; // sesuaikan kalau ingest.py sudah support tipe lain

export default function Dashboard() {
  const [category, setCategory] = useState("public");
  const [activeTab, setActiveTab] = useState("semua");
  const [files, setFiles] = useState([]); // { name, category, size_kb }
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [message, setMessage] = useState(null); // {type: "error"|"success", text}
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const user = JSON.parse(localStorage.getItem("user")) || {};

  const loadFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/admin/documents?user_id=${user.id}`);
      if (!res.ok) throw new Error("Gagal memuat daftar dokumen");
      const data = await res.json();
      setFiles(data);
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const uploadOne = async (file) => {
    const formData = new FormData();
    formData.append("user_id", user.id);
    formData.append("category", category);
    formData.append("file", file);

    const res = await fetch(`${API_URL}/admin/documents`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `Gagal upload ${file.name}`);
    }
  };

  const addFiles = async (fileList) => {
    setUploading(true);
    setMessage(null);

    const fileArray = Array.from(fileList);
    const invalid = fileArray.find(
      (f) => !ACCEPTED_EXT.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    if (invalid) {
      setMessage({ type: "error", text: `Format ${invalid.name} tidak didukung, cuma PDF` });
      setUploading(false);
      return;
    }

    try {
      for (const file of fileArray) {
        await uploadOne(file);
      }
      await loadFiles();
      setMessage({
        type: "success",
        text: `${fileArray.length} file berhasil diupload. Jangan lupa klik "Re-index" biar chatbot bisa pakai dokumen ini.`,
      });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
  };

  const handleSelect = (e) => {
    if (e.target.files?.length) addFiles(e.target.files);
    e.target.value = "";
  };

  const handleDelete = async (file) => {
    const confirmed = window.confirm(`Hapus "${file.name}"? Ini tidak bisa dibatalkan.`);
    if (!confirmed) return;

    try {
      const res = await fetch(
        `${API_URL}/admin/documents/${encodeURIComponent(file.name)}?user_id=${user.id}&category=${file.category}`,
        { method: "DELETE" }
      );
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Gagal menghapus file");
      }
      await loadFiles();
      setMessage({
        type: "success",
        text: `"${file.name}" dihapus. Jangan lupa klik "Re-index" biar perubahannya kepakai.`,
      });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    }
  };

  const handleReindex = async () => {
    setReindexing(true);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/admin/reingest?user_id=${user.id}`, {
        method: "POST",
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Gagal re-index");
      }
      setMessage({ type: "success", text: "Re-index selesai! Chatbot sekarang pakai dokumen terbaru." });
    } catch (err) {
      setMessage({ type: "error", text: err.message });
    } finally {
      setReindexing(false);
    }
  };

  const handleLogout = () => {
  localStorage.removeItem("user");
  localStorage.removeItem("token");

  // Paksa aplikasi kembali ke halaman utama
  window.location.assign("/");
  };

  const counts = {
    semua: files.length,
    public: files.filter((f) => f.category === "public").length,
    "non-public": files.filter((f) => f.category === "non-public").length,
  };

  const visibleFiles =
    activeTab === "semua" ? files : files.filter((f) => f.category === activeTab);

  return (
    <div className="dash-page">
      <div className="dash-topbar">
        <div>
          <h1>Admin Panel</h1>
          <p className="subtitle" style={{ margin: "2px 0 0" }}>
            Masuk sebagai {user.nama || "Admin"}
          </p>
        </div>
        <button className="logout-btn" onClick={handleLogout}>
          <LogOut size={16} /> Keluar
        </button>
      </div>

      {message && (
        <div className={`admin-alert ${message.type}`}>{message.text}</div>
      )}

      {/* Card 1: Pilih Kategori & Unggah */}
      <div className="card">
        <div className="card-header">
          <h2>Pilih Kategori &amp; Unggah</h2>
          <p className="subtitle">Pilih kategori terlebih dahulu sebelum mengunggah berkas</p>
        </div>
        <div className="divider" />

        <div className="category-grid">
          {CATEGORIES.map(({ id, label, desc, icon: Icon }) => {
            const selected = category === id;
            return (
              <button
                key={id}
                type="button"
                className={`category-card ${selected ? "selected" : ""}`}
                onClick={() => setCategory(id)}
              >
                <div className="category-icon">
                  <Icon size={20} strokeWidth={2} />
                </div>
                <div className="category-text">
                  <span className="category-label">{label}</span>
                  <span className="category-desc">{desc}</span>
                </div>
                <span className={`radio ${selected ? "checked" : ""}`} />
              </button>
            );
          })}
        </div>

        <div
          className={`dropzone ${isDragging ? "dragging" : ""} ${uploading ? "disabled" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            if (!uploading) setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={uploading ? undefined : handleDrop}
          onClick={() => !uploading && inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED_EXT.join(",")}
            onChange={handleSelect}
            hidden
          />
          <div className="plus-icon">
            <Plus size={28} strokeWidth={2} />
          </div>
          <h3>{uploading ? "Mengunggah..." : "Seret & lepas berkas"}</h3>
          <p className="dropzone-sub">atau klik untuk memilih · PDF</p>
          <span className="pill">
            Kategori: {CATEGORIES.find((c) => c.id === category)?.label}
          </span>
        </div>

        <button
          className="reindex-btn"
          onClick={handleReindex}
          disabled={reindexing || uploading}
        >
          <RefreshCw size={16} className={reindexing ? "spin" : ""} />
          {reindexing ? "Sedang re-index..." : "Re-index Knowledge Base"}
        </button>
      </div>

      {/* Card 2: Daftar Berkas */}
      <div className="card">
        <div className="list-header">
          <div>
            <h2>Daftar Berkas</h2>
            <p className="subtitle">
              {visibleFiles.length} dari {files.length} berkas ditampilkan
            </p>
          </div>
          <div className="tabs">
            <button
              className={`tab ${activeTab === "semua" ? "active" : ""}`}
              onClick={() => setActiveTab("semua")}
            >
              Semua ({counts.semua})
            </button>
            <button
              className={`tab ${activeTab === "public" ? "active" : ""}`}
              onClick={() => setActiveTab("public")}
            >
              Public ({counts.public})
            </button>
            <button
              className={`tab ${activeTab === "non-public" ? "active" : ""}`}
              onClick={() => setActiveTab("non-public")}
            >
              Non Public ({counts["non-public"]})
            </button>
          </div>
        </div>
        <div className="divider" />

        {loading ? (
          <div className="empty-state">
            <p className="dropzone-sub">Memuat...</p>
          </div>
        ) : visibleFiles.length === 0 ? (
          <div className="empty-state">
            <div className="plus-icon">
              <Plus size={28} strokeWidth={2} />
            </div>
            <h3>Belum ada berkas</h3>
            <p className="dropzone-sub">Unggah berkas di atas untuk mulai</p>
          </div>
        ) : (
          <ul className="file-list">
            {visibleFiles.map((f) => (
              <li key={`${f.category}-${f.name}`} className="file-item">
                <FileText size={18} strokeWidth={2} />
                <span className="file-name">{f.name}</span>
                <span className="file-size">{f.size_kb} KB</span>
                <span className={`file-tag ${f.category}`}>
                  {CATEGORIES.find((c) => c.id === f.category)?.label}
                </span>
                <button
                  className="delete-file-btn"
                  onClick={() => handleDelete(f)}
                  title="Hapus dokumen"
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
