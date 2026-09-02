import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import ChatMessage from "./messageBubble";
import logo from "../assets/bakti.png";
import "./chat.css";
import "./guestChatPage.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function GuestChatPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);

  const chatBodyRef = useRef(null);

  useEffect(() => {
    const el = chatBodyRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const sendMessage = async () => {
    const question = text.trim();
    if (!question || sending) return;

    setText("");
    setMessages((prev) => [...prev, { sender: "user", text: question }]);
    setMessages((prev) => [...prev, { sender: "bot", text: "Mengetik...", loading: true }]);
    setSending(true);

    try {
      const res = await fetch(`${API_URL}/chat/guest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      setMessages((prev) => {
        const copy = [...prev];
        const idx = copy.findIndex((m) => m.loading);
        if (idx !== -1) copy[idx] = { sender: "bot", text: data.answer };
        return copy;
      });
    } catch (err) {
      setMessages((prev) => {
        const copy = [...prev];
        const idx = copy.findIndex((m) => m.loading);
        if (idx !== -1) {
          copy[idx] = {
            sender: "bot",
            text: `⚠️ Gagal menghubungi server: ${err.message}`,
          };
        }
        return copy;
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="guest-page">

      <div className="guest-login-banner">
        <span>
          Kamu sedang memakai mode <strong>umum</strong> (informasi publik saja).
          Login untuk akses knowledge base yang lebih lengkap dan riwayat chat tersimpan.
        </span>
        <div className="guest-login-banner-actions">
          <button onClick={() => navigate("/login")}>Login</button>
          <button className="secondary" onClick={() => navigate("/register")}>
            Daftar
          </button>
        </div>
      </div>

      <div className="chat-container">

        <div className="chat-header">
          <img src={logo} className="logo" alt="" />
          <h2>Assistant</h2>
        </div>

        <div className="chat-body-wrapper">
          <img src={logo} className="watermark" alt="" />

          <div className="chat-body" ref={chatBodyRef}>
            {messages.length === 0 && (
              <ChatMessage
                sender="bot"
                text="Halo! Aku Bakti AI. Tanyakan seputar informasi umum BAKTI (sejarah, visi misi, layanan). Login untuk akses informasi yang lebih lengkap."
              />
            )}

            {messages.map((msg, index) => (
              <ChatMessage
                key={index}
                sender={msg.sender}
                text={msg.text}
                loading={msg.loading}
              />
            ))}
          </div>
        </div>

        <div className="chat-input-wrapper">
          <div className="chat-input">
            <input
              value={text}
              placeholder="Tulis pesan..."
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendMessage();
              }}
            />
            <button onClick={sendMessage} disabled={!text.trim() || sending}>
              ➤
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
