import { useEffect, useState } from "react";
import Sidebar from "./sidebar";
import ChatWindow from "./chatWindow";
import MeetingSummaryModal from "./meetingSummaryModal"; // TAMBAHAN
import "./chat.css";

// URL backend FastAPI. Bisa dioverride lewat file .env (VITE_API_URL=...)
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function ChatPage() {
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [loadingChats, setLoadingChats] = useState(true);
  const [showMeetingModal, setShowMeetingModal] = useState(false); // TAMBAHAN

  const user = JSON.parse(localStorage.getItem("user"));

  // Ambil daftar chat milik user dari backend saat halaman dibuka,
  // lalu buka kembali chat terakhir yang aktif (kalau ada & masih ada di daftar)
  useEffect(() => {
    if (!user?.id) return;

    const loadChats = async () => {
      try {
        const res = await fetch(`${API_URL}/chats/${user.id}`);
        const data = await res.json();
        const list = data.map((c) => ({ id: c.id, title: c.title, messages: [], loaded: false }));
        setChats(list);

        const lastChatId = Number(localStorage.getItem("lastChatId"));
        if (lastChatId && list.some((c) => c.id === lastChatId)) {
          handleSelectChat(lastChatId, list);
        }
      } catch (err) {
        console.error("Gagal memuat riwayat chat:", err);
      } finally {
        setLoadingChats(false);
      }
    };

    loadChats();
  }, [user?.id]);

  const handleNewChat = async () => {
    if (!user?.id) return;

    const title = `New Chat ${chats.length + 1}`;

    try {
      const res = await fetch(`${API_URL}/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: user.id, title }),
      });
      const newChat = await res.json();

      setChats((prev) => [
        { id: newChat.id, title: newChat.title, messages: [], loaded: true },
        ...prev,
      ]);
      setCurrentChatId(newChat.id);
      localStorage.setItem("lastChatId", newChat.id);

    } catch (err) {
      console.error("Gagal membuat chat baru:", err);
    }
  };

  // Saat user klik salah satu chat di sidebar, ambil riwayat pesannya (kalau belum pernah di-load)
  const handleSelectChat = async (chatId, chatsOverride = null) => {
    setCurrentChatId(chatId);
    localStorage.setItem("lastChatId", chatId);

    const list = chatsOverride || chats;
    const target = list.find((c) => c.id === chatId);
    if (target?.loaded) return;

    try {
      const res = await fetch(`${API_URL}/chats/${chatId}/messages`);
      const data = await res.json();

      const messages = data.map((m) => {
        // Pesan hasil export menyimpan metadata file tersembunyi setelah karakter
        // NUL "\x00" (lihat main.py). Pisahkan supaya tidak ikut tampil di chat.
        const [displayText, metaRaw] = m.text.split("\x00");
        let fileUrl = null;
        let fileDownloadName = null;

        if (metaRaw) {
          try {
            const meta = JSON.parse(metaRaw);
            fileUrl = `${API_URL}/files/${meta.file_id}`;
            fileDownloadName = meta.display_name;
          } catch {
            // abaikan kalau metadata tidak valid, tampilkan pesan apa adanya
          }
        }

        return {
          sender: m.sender,
          text: displayText,
          id: m.id,
          createdAt: m.created_at,
          fileUrl,
          fileDownloadName,
        };
      });

      setChats((prev) =>
        prev.map((c) => (c.id === chatId ? { ...c, messages, loaded: true } : c))
      );
    } catch (err) {
      console.error("Gagal memuat pesan chat:", err);
    }
  };

 const appendMessage = (chatId, message) => {
    const withTimestamp = { createdAt: new Date().toISOString(), ...message };

    setChats((prev) => {
      const updated = prev.map((chat) =>
        chat.id !== chatId
          ? chat
          : { ...chat, messages: [...chat.messages, withTimestamp] }
      );

      // Pindahkan chat yang baru dapat pesan ke paling atas daftar riwayat
      const target = updated.find((c) => c.id === chatId);
      const rest = updated.filter((c) => c.id !== chatId);
      return target ? [target, ...rest] : updated;
    });
  };

  // Ganti judul chat di sidebar + simpan ke backend, dipanggil saat pesan pertama dikirim
  const renameChatTitle = async (chatId, text) => {
    const newTitle = text.trim().slice(0, 40) + (text.trim().length > 40 ? "..." : "");

    setChats((prev) =>
      prev.map((chat) =>
        chat.id === chatId ? { ...chat, title: newTitle } : chat
      )
    );

    try {
      await fetch(`${API_URL}/chats/${chatId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle }),
      });
    } catch (err) {
      console.error("Gagal mengganti judul chat:", err);
    }
  };

  const sendMessage = async (text) => {
    if (!text.trim() || !currentChatId) return;

    const chatId = currentChatId;

    // Kalau ini pesan pertama di chat ini, ganti judulnya sesuai isi pesan
    const target = chats.find((c) => c.id === chatId);
    if (target && target.messages.length === 0) {
      renameChatTitle(chatId, text);
    }

    appendMessage(chatId, { sender: "user", text });
    appendMessage(chatId, { sender: "bot", text: "Mengetik...", loading: true });

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, question: text }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      setChats((prev) =>
        prev.map((chat) => {
          if (chat.id !== chatId) return chat;
          const messages = [...chat.messages];
          const idx = messages.findIndex((m) => m.loading);
          if (idx !== -1) {
            // DIPERBAIKI: teruskan flag awaiting_export dari backend supaya
            // tombol Word/PDF di messageBubble bisa muncul, dan simpan id pesan
            // (dipakai untuk fitur edit pesan)
            messages[idx] = {
              sender: "bot",
              text: data.answer,
              awaitingExport: !!data.awaiting_export,
              id: data.bot_message_id,
            };
            if (idx - 1 >= 0 && messages[idx - 1].sender === "user") {
              messages[idx - 1] = { ...messages[idx - 1], id: data.user_message_id };
            }
          }
          return { ...chat, messages };
        })
      );
    } catch (err) {
      setChats((prev) =>
        prev.map((chat) => {
          if (chat.id !== chatId) return chat;
          const messages = [...chat.messages];
          const idx = messages.findIndex((m) => m.loading);
          if (idx !== -1) {
            messages[idx] = {
              sender: "bot",
              text: `⚠️ Gagal menghubungi server: ${err.message}`,
            };
          }
          return { ...chat, messages };
        })
      );
    }
  };

  // Kirim gambar (dari kamera/galeri) atau file dokumen (PDF/DOCX) ke backend
  // untuk dibaca (OCR/parsing) lalu diringkas/dijawab oleh AI.
  const sendFile = async (file, caption = "") => {
    if (!file || !currentChatId) return;

    const chatId = currentChatId;
    const isImage = file.type.startsWith("image/");

    // Kalau ini pesan pertama di chat ini, ganti judulnya
    const target = chats.find((c) => c.id === chatId);
    if (target && target.messages.length === 0) {
      renameChatTitle(chatId, caption.trim() || file.name);
    }

    // Buat preview gambar (kalau berupa gambar) untuk ditampilkan di bubble user
    let previewUrl = null;
    if (isImage) {
      previewUrl = await new Promise((resolve) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => resolve(null);
        reader.readAsDataURL(file);
      });
    }

    appendMessage(chatId, {
      sender: "user",
      text: caption.trim(),
      image: previewUrl,
      fileName: !isImage ? file.name : null,
    });
    appendMessage(chatId, {
      sender: "bot",
      text: "Membaca dan menganalisis file...",
      loading: true,
    });

    try {
      const formData = new FormData();
      formData.append("chat_id", chatId);
      formData.append("question", caption);
      formData.append("file", file);

      const res = await fetch(`${API_URL}/chat/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      setChats((prev) =>
        prev.map((chat) => {
          if (chat.id !== chatId) return chat;
          const messages = [...chat.messages];
          const idx = messages.findIndex((m) => m.loading);
          if (idx !== -1) {
            // DIPERBAIKI: sama seperti sendMessage, teruskan flag awaiting_export
            messages[idx] = {
              sender: "bot",
              text: data.answer,
              awaitingExport: !!data.awaiting_export,
            };
          }
          return { ...chat, messages };
        })
      );
    } catch (err) {
      setChats((prev) =>
        prev.map((chat) => {
          if (chat.id !== chatId) return chat;
          const messages = [...chat.messages];
          const idx = messages.findIndex((m) => m.loading);
          if (idx !== -1) {
            messages[idx] = {
              sender: "bot",
              text: `⚠️ Gagal memproses file: ${err.message}`,
            };
          }
          return { ...chat, messages };
        })
      );
    }
  };

  // BARU: dipanggil saat user klik tombol "Word" atau "PDF" di bawah pesan bot.
  // Backend harus punya endpoint POST /chat/{chat_id}/export yang mengembalikan file.
  const handleExportChoice = async (format) => {
    if (!currentChatId) return;
    const chatId = currentChatId;

    try {
      const res = await fetch(`${API_URL}/chat/${chatId}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ format }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }

      const disposition = res.headers.get("Content-Disposition") || "";
      const match = disposition.match(/filename="?([^"]+)"?/);
      const filename = match ? match[1] : format === "pdf" ? "Dokumen_Bakti.pdf" : "Dokumen_Bakti.docx";
      const fileId = res.headers.get("X-File-Id");

      const blob = await res.blob();
      // Trigger download langsung (blob sementara, hanya untuk aksi unduh pertama kali)
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);

      // Untuk tombol "unduh lagi" di bubble chat, pakai URL permanen dari backend
      // (bukan blob), supaya tetap berfungsi walau halaman di-refresh nanti.
      appendMessage(chatId, {
        sender: "bot",
        text: `✅ File ${filename} sudah dibuat, silakan unduh.`,
        fileUrl: fileId ? `${API_URL}/files/${fileId}` : null,
        fileDownloadName: filename,
      });
    } catch (err) {
      appendMessage(chatId, { sender: "bot", text: `⚠️ Gagal membuat file: ${err.message}` });
    }
  };

  // BARU: edit pesan user yang sudah pernah dikirim. Update teks di backend,
  // buang semua pesan setelahnya (balasan bot lama jadi tidak relevan lagi),
  // lalu minta jawaban baru dari AI berdasarkan teks yang sudah diedit.
  const editMessage = async (messageId, newText) => {
    if (!currentChatId || !newText.trim()) return;
    const chatId = currentChatId;

    try {
      const res = await fetch(`${API_URL}/chats/${chatId}/messages/${messageId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: newText }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }
    } catch (err) {
      console.error("Gagal mengedit pesan:", err);
      appendMessage(chatId, { sender: "bot", text: `⚠️ Gagal mengedit pesan: ${err.message}` });
      return;
    }

    // Potong riwayat lokal sampai pesan yang diedit, lalu update teksnya
    setChats((prev) =>
      prev.map((chat) => {
        if (chat.id !== chatId) return chat;
        const idx = chat.messages.findIndex((m) => m.id === messageId);
        if (idx === -1) return chat;
        const messages = chat.messages.slice(0, idx + 1);
        messages[idx] = { ...messages[idx], text: newText };
        return { ...chat, messages };
      })
    );

    appendMessage(chatId, { sender: "bot", text: "Mengetik...", loading: true });

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, question: newText, skip_user_save: true }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      setChats((prev) =>
        prev.map((chat) => {
          if (chat.id !== chatId) return chat;
          const messages = [...chat.messages];
          const idx = messages.findIndex((m) => m.loading);
          if (idx !== -1) {
            messages[idx] = {
              sender: "bot",
              text: data.answer,
              awaitingExport: !!data.awaiting_export,
              id: data.bot_message_id,
            };
          }
          return { ...chat, messages };
        })
      );
    } catch (err) {
      setChats((prev) =>
        prev.map((chat) => {
          if (chat.id !== chatId) return chat;
          const messages = [...chat.messages];
          const idx = messages.findIndex((m) => m.loading);
          if (idx !== -1) {
            messages[idx] = { sender: "bot", text: `⚠️ Gagal menghubungi server: ${err.message}` };
          }
          return { ...chat, messages };
        })
      );
    }
  };

  // Hapus chat dari backend + dari state, dan reset currentChatId kalau chat yang dihapus lagi dibuka
  const handleDeleteChat = async (chatId) => {
    try {
      await fetch(`${API_URL}/chats/${chatId}`, {
        method: "DELETE",
      });

      setChats((prev) => prev.filter((c) => c.id !== chatId));

      setCurrentChatId((prevId) => {
        if (prevId === chatId) {
          localStorage.removeItem("lastChatId");
          return null;
        }
        return prevId;
      });

    } catch (err) {
      console.error("Gagal menghapus chat:", err);
    }
  };

  return (
    <div className="container">

      <Sidebar
        chats={chats}
        currentChatId={currentChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
        onOpenMeetingSummary={() => setShowMeetingModal(true)} 
      />

      <ChatWindow
        chat={chats.find((c) => c.id === currentChatId)}
        user={user}
        sendMessage={sendMessage}
        userName={user?.nama}
        sendFile={sendFile}
        onExport={handleExportChoice}
        onEditMessage={editMessage}
      />

      {/* TAMBAHAN: modal Ringkasan Rapat -> PDF/Word */}
      <MeetingSummaryModal
        isOpen={showMeetingModal}
        onClose={() => setShowMeetingModal(false)}
        userId={user?.id}
        apiUrl={API_URL}
      />

    </div>
  );
}