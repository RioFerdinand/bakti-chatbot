import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Globe, Lock as LockIcon, Plus, FileText, LogOut } from "lucide-react";
import "./dashboard.css";

const CATEGORIES = [
  {
    id: "public",
    label: "Public",
    desc: "Bisa diakses semua pengguna",
    icon: Globe,
  },
  {
    id: "non-public",
    label: "Non Public",
    desc: "Hanya untuk admin/internal",
    icon: LockIcon,
  },
];

const ACCEPTED_EXT = [".pdf", ".doc", ".docx", ".xlsx", ".xls", ".txt", ".csv"];

export default function Dashboard() {
  const [category, setCategory] = useState("public");
  const [activeTab, setActiveTab] = useState("semua");
  const [files, setFiles] = useState([]); // { id, name, category }
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  const addFiles = (fileList) => {
    const newFiles = Array.from(fileList).map((file) => ({
      id: crypto.randomUUID(),
      name: file.name,
      category,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
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

  const handleLogout = () => {
  localStorage.removeItem("user");
  navigate("/login");
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
        <h1>Admin Panel</h1>
        <button className="logout-btn" onClick={handleLogout}>
          <LogOut size={16} /> Keluar
        </button>
      </div>

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
          className={`dropzone ${isDragging ? "dragging" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
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
          <h3>Seret &amp; lepas berkas</h3>
          <p className="dropzone-sub">atau klik untuk memilih · PDF, DOC, XLSX, TXT, CSV</p>
          <span className="pill">
            Kategori: {CATEGORIES.find((c) => c.id === category)?.label}
          </span>
        </div>
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

        {visibleFiles.length === 0 ? (
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
              <li key={f.id} className="file-item">
                <FileText size={18} strokeWidth={2} />
                <span className="file-name">{f.name}</span>
                <span className={`file-tag ${f.category}`}>
                  {CATEGORIES.find((c) => c.id === f.category)?.label}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}