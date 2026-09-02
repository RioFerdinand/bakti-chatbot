import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import Login from "./components/login";
import Register from "./components/regist";
import ChatPage from "./components/chatPage";
import Profile from "./components/profile";

function App() {

  // Cek apakah user sudah login
  const user = JSON.parse(localStorage.getItem("user"));
  console.log("User di App:", user);

  return (
    <BrowserRouter>

      <Routes>

        {/* Halaman awal */}
        <Route
          path="/"
          element={
            user ? <Navigate to="/chat" /> : <Login />
          }
        />

        {/* Login */}
        <Route
          path="/login"
          element={
            user ? <Navigate to="/chat" /> : <Login />
          }
        />

        {/* Register */}
        <Route
          path="/register"
          element={
            user ? <Navigate to="/chat" /> : <Register />
          }
        />

        {/* Chat */}
        <Route
          path="/chat"
          element={
            user ? <ChatPage /> : <Navigate to="/chatPage" />
          }
        />

        {/* Profile */}
        <Route
          path="/profile"
          element={
            user ? <Profile /> : <Navigate to="/logout" />
          }
        />

        {/* Jika route tidak ditemukan */}
        <Route
          path="*"
          element={<Navigate to="/" />}
        />

      </Routes>

    </BrowserRouter>
  );
}

export default App;