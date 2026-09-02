import { useState } from "react";
import "./sidebar.css";
import Profile from "./profile";

export default function Sidebar({
  chats,
  currentChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onOpenMeetingSummary, // TAMBAHAN
}) {
  const user = JSON.parse(localStorage.getItem("user")) || {};
  const [showProfile, setShowProfile] = useState(false);

  return (
    <div className="sidebar">

      <button
        className="new-chat"
        onClick={onNewChat}
      >
        + Percakapan Baru
      </button>

      {/* TAMBAHAN: tombol buka modal Ringkasan Rapat -> PDF/Word */}
      <button
        className="new-chat report-btn"
        onClick={onOpenMeetingSummary}
      >
        📄 Ringkasan Rapat → PDF/WORD
      </button>

      <h4>Riwayat</h4>

      <ul>

        {chats.map((chat) => (

          <li
            key={chat.id}
            className={`chat-item ${currentChatId === chat.id ? "active" : ""}`}
            onClick={() => onSelectChat(chat.id)}
          >
            <span className="chat-title">{chat.title}</span>

            <button
              className="delete-chat"
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm("Hapus percakapan ini?")) {
                  onDeleteChat(chat.id);
                }
              }}
              title="Hapus"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                <path d="M10 11v6" />
                <path d="M14 11v6" />
                <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
              </svg>
            </button>
          </li>

        ))}

      </ul>

      <div
        className="profile-small"
        onClick={() => setShowProfile(true)}
        style={{ cursor: "pointer" }}
      >
        <div className="sidebar-avatar">
          {(user.nama || "?").trim().charAt(0).toUpperCase()}
        </div>
        <div>
          <h5>{user.nama || "Pengguna"}</h5>
        </div>
      </div>

      {showProfile && (
        <Profile user={user} onClose={() => setShowProfile(false)} />
      )}

    </div>
  );
}