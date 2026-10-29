import { ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../lib/api";

const TYPES = ["USER_ACTION", "NETWORK_FLOW", "AUDIT_EVENT", "EVENT", "DNS_RESOLVE", "INCIDENT_LINK"];
const ECOLOR: Record<string, string> = {
  USER_ACTION: "#3aa88f",
  NETWORK_FLOW: "#6aa8ff",
  AUDIT_EVENT: "#d99a2b",
  EVENT: "#8a96a6",
  DNS_RESOLVE: "#b07fe8",
  INCIDENT_LINK: "#d64545",
};
const SUGGEST = ["ORG-0004/user:USER-0719", "ORG-0004/HOST-0032", "ORG-0004/user:USER-0720", "ORG-0004/HOST-0061"];

export default function Graph() {
  const [node, setNode] = useState(SUGGEST[0]);
  const [q, setQ] = useState(SUGGEST[0]);
  const [tipos, setTipos] = useState<string[]>(["USER_ACTION", "NETWORK_FLOW"]);
  const [lim, setLim] = useState(60);
  const { data, isLoading } = useQuery({
    queryKey: ["vec", q, tipos.join(","), lim],
    queryFn: () => api.vecindario(q, tipos.join(","), 400),
    enabled: q.length > 3,
  });

  const { nodes, edges } = useMemo(() => {
    const all = (data?.nodes ?? []).filter((n) => n.id !== q);
    // orden: sospechosos primero, luego por signal_count
    const sorted = [...all].sort((a, b) => (b.suspicion - a.suspicion) || (b.signal_count - a.signal_count));
    const vis = sorted.slice(0, lim);
    const R1 = 420, R2 = 700;
    const ns = [
      {
        id: q,
        position: { x: 0, y: 0 },
        data: { label: `★ ${q.split("/").pop()}` },
        style: {
          borderColor: "#d99a2b", borderWidth: 3, width: 220,
          fontFamily: "monospace", fontSize: 12, whiteSpace: "pre-line" as const,
          background: "#2a2410",
        },
      },
      ...vis.map((n, i) => {
        const ring = i < 18 ? 0 : 1;
        const k = ring === 0 ? i : i - 18;
        const per = ring === 0 ? Math.min(vis.length, 18) : vis.length - 18;
        const ang = (2 * Math.PI * k) / Math.max(per, 1) - Math.PI / 2;
        const R = ring === 0 ? R1 : R2;
        return {
          id: n.id,
          position: { x: R * Math.cos(ang), y: R * Math.sin(ang) },
          data: { label: `${n.id.split("/").pop()}\n${n.type} · ${n.signal_count.toLocaleString()}` },
          style: {
            borderColor: n.suspicion > 0 ? "#d64545" : "#263242",
            borderWidth: n.suspicion > 0 ? 2 : 1,
            width: 200, fontFamily: "monospace", fontSize: 11, whiteSpace: "pre-line" as const,
          },
        };
      }),
    ];
    const ids = new Set(ns.map((n) => n.id));
    const es = (data?.edges ?? [])
      .filter((e) => ids.has(e.src) && ids.has(e.dst) && (e.src === q || e.dst === q))
      .slice(0, 300)
      .map((e, i) => ({
        id: `e${i}`,
        source: e.src,
        target: e.dst,
        label: e.type,
        style: { stroke: ECOLOR[e.type] ?? "#8a96a6", strokeWidth: 1.5 },
      }));
    return { nodes: ns, edges: es };
  }, [data, q, lim]);

  return (
    <div>
      <h2 className="text-lg font-semibold">Proveniencia (1 salto, layout estrella)</h2>
      <form className="mt-2 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); setQ(node); }}>
        <input value={node} onChange={(e) => setNode(e.target.value)}
          placeholder="ORG-0004/user:USER-0719 o ORG-0004/HOST-0032"
          className="mono min-w-[320px] flex-1 rounded-md border border-line bg-panel px-3 py-2 text-sm" />
        <button className="rounded-md border border-line bg-panel px-4 text-sm">Explorar</button>
      </form>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className="text-xs text-mut">Atajos:</span>
        {SUGGEST.map((s) => (
          <button key={s} onClick={() => { setNode(s); setQ(s); }}
            className={`mono rounded border px-2 py-1 text-xs ${s === q ? "border-line bg-ink text-txt" : "border-line bg-panel text-mut"}`}>
            {s.split("/").pop()}
          </button>
        ))}
        <span className="ml-2 text-xs text-mut">Nodos:</span>
        {[25, 60, 120].map((n) => (
          <button key={n} onClick={() => setLim(n)}
            className={`mono rounded border px-2 py-1 text-xs ${lim === n ? "border-line bg-ink text-txt" : "border-line bg-panel text-mut"}`}>{n}</button>
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {TYPES.map((t) => (
          <label key={t} className="mono flex items-center gap-1 rounded border border-line bg-panel px-2 py-1 text-xs text-mut">
            <input type="checkbox" checked={tipos.includes(t)}
              onChange={() => setTipos((s) => (s.includes(t) ? s.filter((x) => x !== t) : [...s, t]))} />
            <span style={{ color: ECOLOR[t] }}>■</span> {t}
          </label>
        ))}
      </div>
      {isLoading && <p className="mt-3 text-sm text-mut">Muestreando 1.7M aristas…</p>}
      {data && (
        <>
          <p className="mono mt-3 text-xs text-mut">
            {data.node} · {data.n_edges} aristas vecinas · mostrando {nodes.length - 1} vecinos (sospechosos primero)
          </p>
          <div className="mt-2 h-[520px] rounded-md border border-line">
            <ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark" />
          </div>
          <p className="mt-1 text-xs text-mut">Borde rojo = suspicion_score &gt; 0 · aristas solo hacia ★ (1 salto real, sin ruido cruzado).</p>
        </>
      )}
    </div>
  );
}
