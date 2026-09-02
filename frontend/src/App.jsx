import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";

// Halaman user (chatbot)
import Login from "./components/login";
import Register from "./components/regist";
import ChatPage from "./components/chatPage";
import GuestChatPage from "./components/guestChatPage";
import Profile from "./components/profile";

// Halaman admin
import AdminDashboard from "./components/admin/dashboard";

function App() {
  // Satu-satunya sumber kebenaran soal siapa yang login: object "user" di
  // localStorage, isinya termasuk field `role` ("user" atau "admin").
  // Tidak ada localStorage/login terpisah untuk admin -- itu inti dari
  // "auto-detect": satu form login, backend yang menentukan peran.
  const [user, setUser] = useState(() => {
  return JSON.parse(localStorage.getItem("user"));
});

const isAdmin = user?.role === "admin";

useEffect(() => {
  const handleAuthChange = () => {
    const currentUser = JSON.parse(localStorage.getItem("user"));
    setUser(currentUser);
  };

  window.addEventListener("authChange", handleAuthChange);

  return () => {
    window.removeEventListener("authChange", handleAuthChange);
  };
}, []);

  return (
    <BrowserRouter>
      <Routes>

        {/* Halaman awal: kalau belum login -> mode tamu (knowledge base publik) */}
        <Route
          path="/"
          element={
            !user ? (
              <GuestChatPage />
            ) : isAdmin ? (
              <Navigate to="/admin/dashboard" replace />
            ) : (
              <Navigate to="/chat" replace />
            )
          }
        />

        {/* Login (satu-satunya halaman login, untuk user maupun admin) */}
        <Route
          path="/login"
          element={
            !user ? (
              <Login />
            ) : isAdmin ? (
              <Navigate to="/admin/dashboard" replace />
            ) : (
              <Navigate to="/chat" replace />
            )
          }
        />

        {/* Register (hanya untuk akun user biasa -- akun admin dibuat lewat
            script make_admin.py di backend, bukan dari sini) */}
        <Route
          path="/register"
          element={user ? <Navigate to="/chat" replace /> : <Register />}
        />

        {/* Chat: kalau sudah login pakai ChatPage (knowledge base lengkap +
            riwayat tersimpan), kalau belum pakai GuestChatPage. Admin
            diarahkan ke dashboard-nya sendiri, bukan halaman chat. */}
        <Route
          path="/chat"
          element={
            !user ? <GuestChatPage /> : isAdmin ? <Navigate to="/admin/dashboard" replace /> : <ChatPage />
          }
        />

        {/* Profile (khusus user biasa) */}
        <Route
          path="/profile"
          element={user && !isAdmin ? <Profile /> : <Navigate to="/login" replace />}
        />

        {/* Dashboard admin: HANYA bisa diakses kalau role-nya admin.
            User biasa yang coba akses langsung dilempar ke /chat. */}
        <Route
          path="/admin/dashboard"
          element={isAdmin ? <AdminDashboard /> : <Navigate to={user ? "/chat" : "/login"} replace />}
        />

        {/* Jika route tidak ditemukan */}
        <Route path="*" element={<Navigate to="/" replace />} />

      </Routes>
    </BrowserRouter>
  );
}

export default App;
