import "./profile.css";

export default function Profile({ user, onClose }) {
  const handleLogout = () => {
    localStorage.removeItem("user");
    window.location.href = "/guestChatPage";
  };

  const initial = user?.nama ? user.nama.charAt(0).toUpperCase() : "?";

  return (
    <div className="profile-overlay" onClick={onClose}>
      <div className="profile-card" onClick={(e) => e.stopPropagation()}>

        <div className="profile-avatar">{initial}</div>

        <h3>{user?.nama}</h3>
        <p>{user?.email}</p>

        <button className="logout-btn" onClick={handleLogout}>
          Keluar
        </button>

      </div>
    </div>
  );
}