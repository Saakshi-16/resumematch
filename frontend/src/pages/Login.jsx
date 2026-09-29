import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { postJSON } from "../api.js";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await postJSON("/api/login/", { username, password });
      localStorage.setItem("user", JSON.stringify(data));
      navigate("/analyze");
    } catch (err) {
      setError(err.message === "Failed to fetch" ? "Cannot reach the server. Is Django running?" : err.message);
    }
    setLoading(false);
  }

  return (
    <div className="login-layout">
      <div className="login-hero">
        <h1>Know exactly how well your resume fits the job.</h1>
        <p>ResumeMatch uses <b>Retrieval-Augmented Generation (RAG)</b> to check every job requirement against real evidence from your resume, with a match score, gaps, suggestions and citations.</p>
        <ul className="hero-points">
          <li>📄 Upload resume (PDF / DOCX / TXT)</li>
          <li>🔎 Hybrid search: semantic + keyword</li>
          <li>💬 Chat with citations</li>
          <li>📊 Built-in retrieval evaluation</li>
        </ul>
      </div>
      <form className="card login-card" onSubmit={handleSubmit}>
        <h2>Sign in</h2>
        <label>Username</label>
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter username" required />
        <label>Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter password" required />
        {error && <p className="error">{error}</p>}
        <button className="btn" type="submit" disabled={loading}>{loading ? "Signing in..." : "Login"}</button>
        <p className="hint">Demo login: <b>admin</b> / <b>admin123</b></p>
      </form>
    </div>
  );
}
