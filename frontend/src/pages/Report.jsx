import { useEffect, useState } from "react";
import { Fragment } from "react";
import { Link } from "react-router-dom";
import { getAnalysisId, getJSON } from "../api.js";

const LABEL = { match: "✓ Match", partial: "◐ Partial", missing: "✗ Missing" };

function scoreColor(s) {
  if (s >= 75) return "var(--good)";
  if (s >= 50) return "var(--mid)";
  return "var(--bad)";
}

export default function Report() {
  const id = getAnalysisId();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState({});

  useEffect(() => {
    if (id) getJSON(`/api/analysis/${id}/`).then(setData).catch((e) => setError(e.message));
  }, [id]);

  if (!id) return <NoAnalysis />;
  if (error) return <div className="card"><p className="error">{error}</p><Link className="btn" to="/analyze">New analysis</Link></div>;
  if (!data) return <p>Loading report…</p>;

  const r = data.report;
  return (
    <div>
      <div className="report-head">
        <div>
          <h1>Match report</h1>
          <p className="muted">{data.resume_name} vs {data.jd_name} · role: <b>{r.role}</b></p>
        </div>
        <div className="head-actions">
          <Link className="btn" to="/chat">💬 Ask questions</Link>
          <Link className="btn btn-ghost" to="/analyze">New analysis</Link>
        </div>
      </div>

      {r.warnings?.map((w) => <div key={w} className="banner warn">⚠️ {w}</div>)}

      {r.pipeline?.length > 0 && (
        <div className="pipeline-chips">
          {r.pipeline.map((p, i) => (
            <Fragment key={p}>
              {i > 0 && <span className="arrow">→</span>}
              <span className={`pchip ${p.includes("skipped") ? "off" : ""}`}>{p}</span>
            </Fragment>
          ))}
        </div>
      )}

      <div className="grid-score">
        <div className="card score-card">
          <div className="ring" style={{ "--p": r.score, "--c": scoreColor(r.score) }}>
            <span>{r.score}%</span>
          </div>
          <p className="ring-label">Requirement match</p>
          <div className="mini-stats">
            {r.grounding_rate != null && (
              <div><b>{r.grounding_rate}%</b><span>evidence verified</span></div>
            )}
            {r.semantic_similarity != null && (
              <div><b>{r.semantic_similarity}%</b><span>semantic similarity</span></div>
            )}
          </div>
          <p className="muted small">Mode: {r.mode === "ai" ? "AI (Gemini) + RAG" : "Keyword backup"} · Search: {r.retrieval_mode}</p>
        </div>
        <div className="card">
          <h3>Summary</h3>
          <p>{r.summary}</p>
          <div className="counts">
            <span className="pill good">{r.matched.length} matched</span>
            <span className="pill mid">{r.partial.length} partial</span>
            <span className="pill bad">{r.missing.length} missing</span>
          </div>
          {r.strengths?.length > 0 && (
            <>
              <h4>Strengths</h4>
              <ul>{r.strengths.map((s) => <li key={s}>{s}</li>)}</ul>
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h3>Requirement-by-requirement</h3>
        <p className="muted small">For each requirement, resume passages were retrieved (hybrid search + HyDE + reranking), judged by the AI, and every quote was checked against the resume. Must-haves count double.</p>
        <div className="req-list">
          {r.requirements.map((q, i) => (
            <div key={i} className={`req ${q.status}`}>
              <div className="req-top">
                <span className={`status ${q.status}`}>{LABEL[q.status]}</span>
                <span className="req-name">{q.requirement}</span>
                <span className={`type ${q.type}`}>{q.type === "must" ? "Must-have" : "Nice-to-have"}</span>
              </div>
              {q.evidence && (
                <blockquote>
                  “{q.evidence}”
                  <span className="quote-meta">
                    {q.section && <span className="sec">{q.section}</span>}
                    {q.page && <span className="muted small">page {q.page}</span>}
                    {q.verified === true && <span className="ver ok" title={`similarity ${q.similarity ?? ""}`}>✓ verified</span>}
                    {q.verified === false && <span className="ver bad" title={`similarity ${q.similarity ?? ""}`}>⚠ not found in resume</span>}
                  </span>
                </blockquote>
              )}
              {q.reason && <p className="muted small">{q.reason}</p>}
              {q.retrieved?.length > 0 && (
                <>
                  <button className="link small" onClick={() => setOpen((o) => ({ ...o, [i]: !o[i] }))}>
                    {open[i] ? "Hide" : "Show"} retrieved passages
                  </button>
                  {open[i] && (
                    <div className="retrieved">
                      {q.retrieved.map((c, j) => (
                        <div key={j} className="source">
                          <div className="source-top">
                            <span className="cite">{j + 1}</span>
                            <span className="sec">{c.section}</span>
                            {c.rerank != null && <span className="muted small">reranker relevance {Math.round(c.rerank * 100)}%</span>}
                          </div>
                          <p>{c.text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

export function NoAnalysis() {
  return (
    <div className="card empty">
      <h2>No analysis yet</h2>
      <p className="muted">Upload a resume and job description first, or try the sample.</p>
      <Link className="btn" to="/analyze">Start analysis</Link>
    </div>
  );
}
