import { useEffect, useRef, useState } from "react";
import { getAnalysisId, postJSON } from "../api.js";
import RichText from "../components/RichText.jsx";
import { NoAnalysis } from "./Report.jsx";

const SUGGESTED = [
  "What are the candidate's strongest skills for this job?",
  "Which required skills are missing from the resume?",
  "Does the candidate have experience deploying ML models?",
  "Write 3 interview questions based on the gaps.",
];

export default function Chat() {
  const id = getAnalysisId();
  const [messages, setMessages] = useState(() => JSON.parse(sessionStorage.getItem("chat") || "[]"));
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState({});
  const bottom = useRef(null);

  useEffect(() => {
    sessionStorage.setItem("chat", JSON.stringify(messages));
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (!id) return <NoAnalysis />;

  async function ask(question) {
    const q = question.trim();
    if (!q || loading) return;
    setInput("");
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: q }]);
    setLoading(true);
    try {
      const data = await postJSON("/api/chat/", { analysis_id: id, question: q, history });
      setMessages((m) => [...m, { role: "assistant", content: data.answer, sources: data.sources }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠️ ${err.message}`, sources: [] }]);
    }
    setLoading(false);
  }

  return (
    <div className="chat-page">
      <div className="chat-head">
        <h1>Chat with the match</h1>
        {messages.length > 0 && <button className="btn btn-ghost small-btn" onClick={() => setMessages([])}>Clear chat</button>}
      </div>
      <p className="muted">Ask anything about the resume or the job. Answers are grounded in retrieved passages, with citations.</p>

      <div className="card chat-box">
        {messages.length === 0 && (
          <div className="suggested">
            <p className="muted">Try one of these:</p>
            {SUGGESTED.map((s) => <button key={s} className="chip" onClick={() => ask(s)}>{s}</button>)}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">
              {m.role === "assistant" ? <RichText text={m.content} /> : m.content}
              {m.sources?.length > 0 && (
                <div className="sources">
                  <button className="link" onClick={() => setOpen((o) => ({ ...o, [i]: !o[i] }))}>
                    {open[i] ? "Hide" : "Show"} {m.sources.length} sources
                  </button>
                  {open[i] && m.sources.map((s) => (
                    <div key={s.id} className="source">
                      <div className="source-top">
                        <span className="cite">{s.n}</span>
                        <b>{s.source_name}</b>
                        {s.section && <span className="sec">{s.section}</span>}
                        <span className="muted small">page {s.page}{s.rerank != null ? ` · relevance ${Math.round(s.rerank * 100)}%` : ""}</span>
                      </div>
                      <p>{s.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <div className="msg assistant"><div className="bubble typing">Searching documents and thinking…</div></div>}
        <div ref={bottom} />
      </div>

      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); ask(input); }}>
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask a question about the resume or job…" />
        <button className="btn" disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}
