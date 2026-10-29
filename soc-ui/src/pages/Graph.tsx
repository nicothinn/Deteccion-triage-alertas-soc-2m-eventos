import { ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../lib/api";

const TYPES = ["USER_ACTION", "NETWORK_FLOW", "AUDIT_EVENT", "EVENT", "DNS_RESOLVE", "INCIDENT_LINK"];

export default function Graph() {
  const [node, setNode] = useState("ORG-0001/user:USER-0001");
  const [q, setQ] = useState("ORG-0001/user:USER-0001");
  const [tipos, setTipos] = useState<string[]>(["USER_ACTION", "NETWORK_FLOW"]);
  const { data, isLoading } = useQuery({
    queryKey: ["vec", q, tipos.join(",")],
    queryFn: () => api.vecindario(q, tipos.join(",")),
    enabled: q.length > 3,
  });

  const { nodes, edges } = useMemo(() => {
    const ns = (data?.nodes ?? []).slice(0, 40).map((n, i) => ({
      id: n.id,
      position: { x: (i % 8) * 220, y: Math.floor(i / 8) * 140 },
      data: { label: `${n.id.split("/").pop()}\n${n.type} · ${n.signal_count}` },
      style: {
        borderColor: n.id === q ? "#d99a2b" : n.suspicion > 0 ? "#d64545" : "#263242",
        borderWidth: n.id === q ? 3 : 1, width: 200, fontFamily: "monospace", fontSize: 11, whiteSpace: "pre-line" as const,
      },
    }));
    const ids = new Set(ns.map((n) => n.id));
    const es = (data?.edges ?? []).filter((e) => ids.has(e.src) && ids.has(e.dst)).slice(0, 80).map((e, i) => ({
      id: `e${i}`, source: e.src, target: e.dst, label: e.type,
      style: { stroke: "#8a96a6" },
    }));
    return { nodes: ns, edges: es };
  }, [data, q]);

  return (
    <div>
      <h2 className="text-lg font-semibold">Proveniencia (1 salto)</h2>
      <form className="mt-2 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); setQ(node); }}>
        <input value={node} onChange={(e) => setNode(e.target.value)}
          placeholder="ORG-0004/user:USER-0001 o ORG-0004/HOST-0001"
          className="mono min-w-[320px] flex-1 rounded-md border border-line bg-panel px-3 py-2 text-sm" />
        <button className="rounded-md border border-line bg-panel px-4 text-sm">Explorar</button>
      </form>
      <div className="mt-2 flex flex-wrap gap-2">
        {TYPES.map((t) => (
          <label key={t} className="mono flex items-center gap-1 rounded border border-line bg-panel px-2 py-1 text-xs text-mut">
            <input type="checkbox" checked={tipos.includes(t)}
              onChange={() => setTipos((s) => (s.includes(t) ? s.filter((x) => x !== t) : [...s, t]))} />{t}
          </label>
        ))}
      </div>
      {isLoading && <p className="mt-3 text-sm text-mut">Muestreando 1.7M aristas…</p>}
      {data && (
        <>
          <p className="mono mt-3 text-xs text-mut">{data.n_edges} aristas vecinas · mostrando {nodes.length} nodos</p>
          <div className="mt-2 h-[420px] rounded-md border border-line">
            <ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark" />
          </div>
        </>
      )}
    </div>
  );
}
