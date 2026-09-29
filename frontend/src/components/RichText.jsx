// Displays AI text nicely: bullet points, **bold** and citation badges like [1].

function inline(text, key) {
  const parts = text.split(/(\*\*[^*]+\*\*|\[\d+(?:,\s*\d+)*\])/g);
  return parts.map((p, i) => {
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={`${key}-${i}`}>{p.slice(2, -2)}</strong>;
    if (/^\[\d+(?:,\s*\d+)*\]$/.test(p)) return <span key={`${key}-${i}`} className="cite">{p.slice(1, -1)}</span>;
    return p;
  });
}

export default function RichText({ text }) {
  const lines = (text || "").split("\n");
  const blocks = [];
  let list = [];
  const flush = () => {
    if (list.length) blocks.push(<ul key={`ul-${blocks.length}`}>{list}</ul>);
    list = [];
  };
  lines.forEach((line, i) => {
    const t = line.trim();
    if (/^([-*•]|\d+\.)\s+/.test(t)) {
      list.push(<li key={i}>{inline(t.replace(/^([-*•]|\d+\.)\s+/, ""), i)}</li>);
    } else {
      flush();
      if (t) blocks.push(<p key={i}>{inline(t.replace(/^#+\s*/, ""), i)}</p>);
    }
  });
  flush();
  return <div className="rich">{blocks}</div>;
}
