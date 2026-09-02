import { useState } from "react";

function CopyIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="12" height="12" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
      <path d="m15 5 4 4" />
    </svg>
  );
}

// Format tanggal singkat ala "27 Jul" (mirip gaya ChatGPT/WhatsApp)
function formatTimestamp(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("id-ID", { day: "numeric", month: "short" });
}

export default function ChatMessage({
  id,
  sender,
  text,
  loading,
  createdAt,      // waktu pesan dibuat, ditampilkan sebagai tanggal kecil
  user,           // data user login ({ nama, ... }), untuk inisial avatar
  onEditMessage,  // (messageId, newText) => void, dipanggil saat simpan hasil edit
}) {
  const isUser = sender === "user";

  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  const [copied, setCopied] = useState(false);

  const avatarLabel = isUser
    ? (user?.nama || "?").trim().charAt(0).toUpperCase() || "U"
    : "AI";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (err) {
      console.error("Gagal menyalin teks:", err);
    }
  };

  const startEdit = () => {
    setDraft(text);
    setIsEditing(true);
  };

  const cancelEdit = () => {
    setDraft(text);
    setIsEditing(false);
  };

  const saveEdit = () => {
    if (!draft.trim() || draft === text) {
      setIsEditing(false);
      return;
    }
    onEditMessage && onEditMessage(id, draft.trim());
    setIsEditing(false);
  };

  const timestamp = formatTimestamp(createdAt);

  return (
    <div className={`message-row ${isUser ? "user" : "bot"}`}>

      <div className={`avatar ${isUser ? "user" : "bot"}`}>
        {avatarLabel}
      </div>

      <div className="message-col">

        <div className={`message-bubble ${isUser ? "user" : "bot"} ${loading ? "loading" : ""}`}>

          {isEditing ? (
            <div className="message-edit-box">
              <textarea
                className="message-edit-textarea"
                value={draft}
                autoFocus
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    saveEdit();
                  } else if (e.key === "Escape") {
                    cancelEdit();
                  }
                }}
              />
              <div className="message-edit-actions">
                <button type="button" className="message-edit-btn save" onClick={saveEdit}>
                  Simpan & kirim ulang
                </button>
                <button type="button" className="message-edit-btn cancel" onClick={cancelEdit}>
                  Batal
                </button>
              </div>
            </div>
          ) : (
            text
          )}

        </div>

        {/* Tanggal + ikon aksi, tampil DI LUAR bubble (minimalis, seperti ChatGPT). */}
        {!loading && !isEditing && (
          <div className="message-footer">
            {timestamp && <span className="message-timestamp">{timestamp}</span>}

            <div className="message-icons">
              <button
                type="button"
                className="message-icon-btn"
                title="Salin teks"
                onClick={handleCopy}
              >
                {copied ? <CheckIcon /> : <CopyIcon />}
              </button>

              {isUser && onEditMessage && (
                <button
                  type="button"
                  className="message-icon-btn"
                  title="Edit pesan"
                  onClick={startEdit}
                >
                  <PencilIcon />
                </button>
              )}
            </div>
          </div>
        )}

      </div>

    </div>
  );
}