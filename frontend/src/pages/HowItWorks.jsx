const STEPS = [
  ["📄", "1. Load & repair", "Text is extracted from PDF / DOCX / TXT. Broken PDF spacing like 'F AISS' is repaired to 'FAISS'."],
  ["✂️", "2. Section-aware chunking", "Headings (Experience, Projects, Skills…) are detected; text is split into ~500-character overlapping chunks that never mix sections."],
  ["🧮", "3. Embed", "Each chunk becomes a 384-dimensional vector (BAAI/bge-small-en-v1.5, running locally on CPU)."],
  ["💭", "4. HyDE", "For each job requirement, the LLM imagines a resume line that would satisfy it, and we search with that too. This bridges job-ad vs resume wording."],
  ["🔎", "5. Hybrid search", "Semantic search (vectors) + BM25 keyword search for every query, merged with Reciprocal Rank Fusion."],
  ["🎯", "6. Rerank", "A cross-encoder (ms-marco-MiniLM-L-6-v2) reads each (requirement, passage) pair together and re-orders the top 15."],
  ["⚖️", "7. Judge", "Gemini labels each requirement match / partial / missing using only the retrieved evidence, with an exact quote."],
  ["🛡️", "8. Verify", "Every quote is fuzzy-matched against the real resume. Unverifiable 'matches' are flagged and downgraded (hallucination check)."],
  ["📊", "9. Score & evaluate", "The score is computed in Python. An ablation study measures each component with Hit@K, MRR, nDCG and F1 vs gold labels."],
];

export default function HowItWorks() {
  return (
    <div>
      <h1>How ResumeMatch works</h1>
      <p className="muted">ResumeMatch is a <b>Retrieval-Augmented Generation (RAG)</b> system: instead of letting an AI guess, it first <b>retrieves</b> real evidence from the documents, asks the AI to <b>generate</b> a judgement from only that evidence, and then <b>verifies</b> the AI's claims.</p>

      <div className="pipeline">
        {STEPS.map(([icon, title, text]) => (
          <div key={title} className="card pipe-step">
            <span className="pipe-icon">{icon}</span>
            <h3>{title}</h3>
            <p>{text}</p>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card">
          <h3>Why two-stage retrieval?</h3>
          <p><b>Stage 1 (bi-encoder + BM25)</b> encodes the query and the chunks <i>separately</i>, which is fast enough to search everything but approximate.</p>
          <p><b>Stage 2 (cross-encoder)</b> reads query and chunk <i>together</i>, which is far more precise but too slow for everything, so it only re-scores the top 15 candidates.</p>
        </div>
        <div className="card">
          <h3>Tech stack</h3>
          <ul>
            <li><b>Frontend:</b> React, React Router, CSS (Vite)</li>
            <li><b>Backend:</b> Django JSON APIs</li>
            <li><b>Embeddings / reranker:</b> fastembed (ONNX, CPU)</li>
            <li><b>Keyword search:</b> BM25 (own implementation)</li>
            <li><b>LLM:</b> Google Gemini API</li>
            <li><b>Storage:</b> JSON + NumPy vectors per analysis</li>
            <li><b>Deployment:</b> Docker on AWS EC2</li>
          </ul>
        </div>
      </div>

      <div className="card">
        <h3>Reliability</h3>
        <ul>
          <li>Every component degrades gracefully: no reranker → skip stage 2; no embeddings → keyword search; no LLM → keyword skill analysis.</li>
          <li>The score is deterministic code (must-have ×2, nice-to-have ×1, partial = 0.5), not an LLM guess.</li>
          <li>Chat answers must cite passages and say "I couldn't find that" instead of guessing.</li>
        </ul>
      </div>
    </div>
  );
}
