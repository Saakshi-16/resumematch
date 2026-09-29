import { useState } from "react";
import { postJSON } from "../api.js";

function best(rows, key) {
  return Math.max(...rows.map((r) => r[key]));
}

function AblationTable({ rows, k }) {
  const cols = [
    ["hit_at_1", "Hit@1", "%"],
    ["hit_at_k", `Hit@${k}`, "%"],
    ["mrr", "MRR", ""],
    ["ndcg", "nDCG@5", ""],
  ];
  return (
    <div className="table-card">
      <table>
        <thead>
          <tr><th>Pipeline configuration</th>{cols.map(([, label]) => <th key={label}>{label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.config}>
              <td><b>{r.config}</b></td>
              {cols.map(([key, , unit]) => (
                <td key={key} className={r[key] === best(rows, key) && rows.length > 1 ? "best" : ""}>{r[key]}{unit}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Evaluation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      setData(await postJSON("/api/evaluate/"));
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }

  const j = data?.judgement;
  return (
    <div>
      <h1>Evaluation &amp; ablation study</h1>
      <div className="card metric-help">
        <div><b>Hit@K</b>: % of queries where a correct passage is in the top K results.</div>
        <div><b>MRR</b> (Mean Reciprocal Rank): 1.0 = the correct passage is always ranked first.</div>
        <div><b>nDCG@5</b>: rewards ranking <i>all</i> correct passages near the top (1.0 = perfect order).</div>
        <div><b>Macro-F1</b>: balance of precision and recall across match / partial / missing verdicts.</div>
      </div>
      <button className="btn btn-lg" onClick={run} disabled={loading}>{loading ? "Running… (10–40 s)" : "▶ Run evaluation"}</button>
      {error && <p className="error">{error}</p>}

      {data && (
        <>
          {data.notes.map((n) => <div key={n} className="banner warn" style={{ marginTop: 16 }}>ℹ️ {n}</div>)}

          <div className="card" style={{ marginTop: 20 }}>
            <h3>A. Requirement → evidence retrieval ({data.requirements.n} hand-labelled requirements)</h3>
            <p className="muted small">Can the pipeline find the resume passage that proves each requirement? This is the retrieval used to build the report.</p>
            <AblationTable rows={data.requirements.rows} k={data.k} />
          </div>

          <div className="card">
            <h3>B. Chat question retrieval ({data.qa.n} questions)</h3>
            <p className="muted small">Questions about the resume and the job, each with a known correct passage.</p>
            <AblationTable rows={data.qa.rows} k={data.k} />
          </div>

          {j && (
            <div className="card">
              <h3>C. Judgement accuracy vs hand-labelled gold verdicts ({j.n} requirements)</h3>
              <div className="metric-grid">
                <div className="metric-box"><span className="big">{j.accuracy}%</span><span className="muted small">Accuracy</span></div>
                <div className="metric-box"><span className="big">{j.macro_f1}</span><span className="muted small">Macro-F1</span></div>
                {j.grounding_rate != null && (
                  <div className="metric-box"><span className="big">{j.grounding_rate}%</span><span className="muted small">Evidence verified (grounding)</span></div>
                )}
              </div>

              <div className="grid-2" style={{ marginTop: 16 }}>
                <div>
                  <h4>Confusion matrix</h4>
                  <table className="matrix">
                    <thead>
                      <tr><th>Gold ↓ / Predicted →</th>{j.labels.map((l) => <th key={l}>{l}</th>)}</tr>
                    </thead>
                    <tbody>
                      {j.labels.map((g) => (
                        <tr key={g}>
                          <th>{g}</th>
                          {j.labels.map((p) => (
                            <td key={p} className={g === p ? "diag" : j.matrix[g][p] ? "off" : ""}>{j.matrix[g][p]}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="table-card">
                  <h4>Per requirement</h4>
                  <table>
                    <thead><tr><th>Requirement</th><th>Gold</th><th>AI</th></tr></thead>
                    <tbody>
                      {j.details.map((d) => (
                        <tr key={d.requirement}>
                          <td>{d.requirement}</td>
                          <td>{d.gold}</td>
                          <td><span className={`pill ${d.correct ? "good" : "bad"}`}>{d.predicted}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
