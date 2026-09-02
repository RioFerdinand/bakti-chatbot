import { useState } from "react";
import "./authCard.css";

import { Link, useNavigate } from "react-router-dom";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      setError("Email dan password wajib diisi");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Login gagal");
      }

      // data = { id, nama, email, role }
      localStorage.setItem("user", JSON.stringify(data));

      // Auto-detect: kalau role-nya admin, langsung ke dashboard admin.
      // User biasa tidak pernah lihat opsi ini sama sekali -- terdeteksi
      // otomatis dari data yang dikirim backend, bukan dari pilihan di UI.
      const destination = data.role === "admin" ? "/admin/dashboard" : "/chat";

      // Pakai full page reload (bukan navigate) supaya App.jsx
      // membaca ulang localStorage yang baru saja diupdate
      window.location.href = destination;
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">

        <h2>Selamat Datang</h2>
        <p>BAKTI Assistant</p>

        <div className="switch">
          <Link to="/login" className="active">
            Masuk
          </Link>

          <Link to="/register">
            Daftar
          </Link>
        </div>

        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
        />

        {error && <p className="error-text">{error}</p>}

        <button onClick={handleLogin} disabled={loading}>
          {loading ? "Memproses..." : "Masuk"}
        </button>

      </div>
    </div>
  );
}