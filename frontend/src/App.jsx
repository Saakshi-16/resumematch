import { Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Login from "./pages/Login.jsx";
import Analyze from "./pages/Analyze.jsx";
import Report from "./pages/Report.jsx";
import Chat from "./pages/Chat.jsx";
import Evaluation from "./pages/Evaluation.jsx";
import HowItWorks from "./pages/HowItWorks.jsx";
import { getUser } from "./api.js";

// Only logged-in users may open these pages
function Protected({ children }) {
  return getUser() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/" element={<Navigate to="/analyze" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/analyze" element={<Protected><Analyze /></Protected>} />
          <Route path="/report" element={<Protected><Report /></Protected>} />
          <Route path="/chat" element={<Protected><Chat /></Protected>} />
          <Route path="/evaluation" element={<Protected><Evaluation /></Protected>} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="*" element={<div className="card"><h2>Page not found</h2></div>} />
        </Routes>
      </main>
      <footer className="footer">ResumeMatch · RAG demo built with React, Django, Gemini &amp; Docker</footer>
    </>
  );
}
