import { useRef, useState } from "react";

export default function ChatInput({
  sendMessage,
  onSendFile, // dipanggil sebagai onSendFile(file, caption)
  disabled = false,
}) {
  const [text, setText] = useState("");
  const [attachedFile, setAttachedFile] = useState(null);
  const [attachedPreview, setAttachedPreview] = useState(null);

  const fileInputRef = useRef(null);

  // Simpan file yang dipilih/di-paste sebagai lampiran, TANPA langsung mengirim.
  // Kalau berupa gambar, buat preview thumbnail-nya.
  const attachFile = (file) => {
    if (!file) return;

    setAttachedFile(file);

    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = () => setAttachedPreview(reader.result);
      reader.onerror = () => setAttachedPreview(null);
      reader.readAsDataURL(file);
    } else {
      setAttachedPreview(null);
    }
  };

  const clearAttachment = () => {
    setAttachedFile(null);
    setAttachedPreview(null);
  };

  const handleSend = () => {
    if (disabled) return;

    if (attachedFile) {
      // Ada lampiran (gambar/dokumen) -> kirim file + caption (boleh kosong)
      if (onSendFile) onSendFile(attachedFile, text);
      setText("");
      clearAttachment();
      return;
    }

    if (!text.trim()) return;

    sendMessage(text);
    setText("");
  };

  const handleFilePicked = (e) => {
    const file = e.target.files?.[0];
    // reset input supaya bisa pilih file yang sama lagi di kemudian hari
    e.target.value = "";

    if (!file || disabled) return;

    // Hanya taruh sebagai lampiran dulu, belum dikirim
    attachFile(file);
  };

  // Tangkap Ctrl+V gambar dari clipboard (screenshot, copy gambar, dsb.)
  const handlePaste = (e) => {
    if (disabled) return;

    const items = e.clipboardData?.items;
    if (!items) return;

    for (const item of items) {
      if (item.kind === "file" && item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) {
          e.preventDefault(); // supaya tidak ikut paste teks/gambar mentah ke input
          attachFile(file);
        }
        break;
      }
    }
  };

  return (
    <div className="chat-input-wrapper">

      {/* Preview lampiran (gambar/file) sebelum dikirim */}
      {attachedFile && (
        <div className="attachment-preview">
          {attachedPreview ? (
            <img src={attachedPreview} alt={attachedFile.name} className="attachment-thumb" />
          ) : (
            <div className="attachment-file-chip">📄 {attachedFile.name}</div>
          )}
          <button
            type="button"
            className="attachment-remove-btn"
            title="Hapus lampiran"
            onClick={clearAttachment}
          >
            ✕
          </button>
        </div>
      )}

      <div className="chat-input">
        {/* Input tersembunyi: lampirkan gambar/dokumen dari perangkat */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf,.docx,.doc"
          style={{ display: "none" }}
          onChange={handleFilePicked}
        />

        <button
          type="button"
          className="icon-btn"
          title="Lampirkan gambar/dokumen"
          disabled={disabled}
          onClick={() => fileInputRef.current?.click()}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 11.5 12.5 20a4.5 4.5 0 1 1-6.36-6.36l8-8a3 3 0 1 1 4.24 4.24l-7.6 7.6a1.5 1.5 0 1 1-2.12-2.12l6.9-6.9" />
          </svg>
        </button>

        <input
          value={text}
          placeholder={
            disabled
              ? "Pilih atau buat percakapan dulu..."
              : attachedFile
              ? "Tambahkan keterangan (opsional)..."
              : "Tulis pesan, atau paste/kirim foto/dokumen..."
          }
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onPaste={handlePaste}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSend();
            }
          }}
        />

        <button onClick={handleSend} disabled={disabled || (!text.trim() && !attachedFile)}>
          ➤
        </button>
      </div>
    </div>
  );
}