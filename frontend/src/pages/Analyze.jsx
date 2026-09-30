import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getJSON, postForm, setAnalysisId } from "../api.js";

const STEPS = [
  "Reading documents & repairing PDF text",
  "Section-aware chunking & embeddings",
  "Extracting job requirements (LLM)",
  "HyDE: imagining matching resume lines",
  "Hybrid search + cross-encoder reranking",
  "Judging each requirement (LLM)",
  "Hallucination check & scoring",
];

const OK_TYPES = [".pdf", ".docx", ".txt", ".md"];

// Upload box: click to choose a file OR drag & drop a file onto it
function DropZone({ file, onFile, icon, onError }) {
  const [over, setOver] = useState(false);
  function pick(f) {
    if (!f) return;
    if (!OK_TYPES.some((t) => f.name.toLowerCase().endsWith(t))) {
      onError("Please use a PDF, DOCX or TXT file.");
      return;
    }
    onError("");
    onFile(f);
  }
  return (
    <label
      className={over ? "dropzone over" : "dropzone"}
      onDragOver={(e) => { e.preventDefault(); setOver(true); }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]); }}
    >
      <input type="file" accept=".pdf,.docx,.txt,.md" onChange={(e) => pick(e.target.files[0])} />
      <span className="drop-icon">{icon}</span>
      <span>{file ? file.name : "Drag & drop a PDF, DOCX or TXT file here, or click to choose"}</span>
    </label>
  );
}

export default function Analyze() {
  const navigate = useNavigate();
  const [resume, setResume] = useState(null);
  const [jdMode, setJdMode] = useState("paste");
  const [jdText, setJdText] = useState("");
  const [jdFile, setJdFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [health, setHealth] = useState(null);

  // Stop the browser from opening a file if it is dropped outside the upload boxes
  useEffect(() => {
    const stop = (e) => e.preventDefault();
    window.addEventListener("dragover", stop);
    window.addEventListener("drop", stop);
    return () => {
      window.removeEventListener("dragover", stop);
      window.removeEventListener("drop", stop);
    };
  }, []);

  useEffect(() => {
    getJSON("/api/health/").then(setHealth).catch(() => {});
  }, []);

  // Move the progress text forward while we wait for the backend
  useEffect(() => {
    if (!loading) return;
    setStep(0);
    const t = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 2200);
    return () => clearInterval(t);
  }, [loading]);

  async function run(useSample) {
    setError("");
    const form = new FormData();
    if (useSample) {
      form.append("use_sample", "1");
    } else {
      if (!resume) return setError("Please choose your resume file.");
      form.append("resume", resume);
      if (jdMode === "file") {
        if (!jdFile) return setError("Please choose the job description file.");
        form.append("jd_file", jdFile);
      } else {
        if (jdText.trim().length < 50) return setError("Please paste the full job description.");
        form.append("jd_text", jdText);
      }
    }
    setLoading(true);
    try {
      const data = await postForm("/api/analyze/", form);
      setAnalysisId(data.id);
      navigate("/report");
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  if (loading) {
    return (
      <div className="card progress-card">
        <div className="spinner" />
        <h2>Analyzing…</h2>
        <ol className="steps">
          {STEPS.map((s, i) => (
            <li key={s} className={i < step ? "done" : i === step ? "active" : ""}>{s}</li>
          ))}
        </ol>
        <p className="muted small">This usually takes 10–30 seconds (the first run on a new server can take longer while models load).</p>
      </div>
    );
  }

  return (
    <div>
      <h1>Analyze a resume</h1>
      <p className="muted">Upload a resume and a job description. ResumeMatch checks every requirement against evidence found in the resume.</p>

      {health && !health.llm_configured && (
        <div className="banner warn">⚠️ No Gemini API key configured: analysis will use keyword matching only. Add <code>GEMINI_API_KEY</code> for the full AI analysis.</div>
      )}

      <div className="grid-2">
        <div className="card">
          <h3>1. Resume</h3>
          <DropZone file={resume} onFile={setResume} icon="📄" onError={setError} />
        </div>

        <div className="card">
          <h3>2. Job description</h3>
          <div className="tabs">
            <button className={jdMode === "paste" ? "tab active" : "tab"} onClick={() => setJdMode("paste")}>Paste text</button>
            <button className={jdMode === "file" ? "tab active" : "tab"} onClick={() => setJdMode("file")}>Upload file</button>
          </div>
          {jdMode === "paste" ? (
            <textarea rows="8" placeholder="Paste the full job description here…" value={jdText} onChange={(e) => setJdText(e.target.value)} />
          ) : (
            <DropZone file={jdFile} onFile={setJdFile} icon="🧾" onError={setError} />
          )}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button className="btn btn-lg" onClick={() => run(false)}>Analyze match →</button>
        <button className="btn btn-ghost" onClick={() => run(true)}>Try with sample resume & job</button>
      </div>
    </div>
  );
}
