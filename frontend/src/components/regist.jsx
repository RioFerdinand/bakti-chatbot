import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "./authCard.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Register() {
  const navigate = useNavigate();

  const [nama, setNama] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async () => {
    if (!nama.trim() || !email.trim() || !password.trim()) {
      setError("Semua field wajib diisi");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          nama,
          email,
          password,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Registrasi gagal");
      }

      navigate("/login");
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
          <Link to="/login">Masuk</Link>
          <Link to="/register" className="active">
            Daftar
          </Link>
        </div>

        <input
          type="text"
          placeholder="Nama Pengguna"
          value={nama}
          onChange={(e) => setNama(e.target.value)}
        />

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
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleRegister();
            }
          }}
        />

        {error && <p className="error-text">{error}</p>}

        <button onClick={handleRegister} disabled={loading}>
          {loading ? "Memproses..." : "Daftar"}
        </button>
      </div>
    </div>
  );
}