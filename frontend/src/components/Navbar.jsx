import { NavLink, useNavigate } from "react-router-dom";
import { getUser } from "../api.js";

export default function Navbar() {
  const navigate = useNavigate();
  const user = getUser();

  function logout() {
    localStorage.removeItem("user");
    sessionStorage.clear();
    navigate("/login");
  }

  return (
    <header className="navbar">
      <div className="brand">🎯 Resume<span>Match</span></div>
      <nav>
        {user && <NavLink to="/analyze">Analyze</NavLink>}
        {user && <NavLink to="/report">Report</NavLink>}
        {user && <NavLink to="/chat">Chat</NavLink>}
        {user && <NavLink to="/evaluation">Evaluation</NavLink>}
        <NavLink to="/how-it-works">How it works</NavLink>
        {user ? (
          <button className="nav-btn" onClick={logout}>Logout</button>
        ) : (
          <NavLink to="/login">Login</NavLink>
        )}
      </nav>
    </header>
  );
}
