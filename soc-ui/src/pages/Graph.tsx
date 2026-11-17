import { Background, BackgroundVariant, ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { api } from "../lib/api";

const TYPES = ["USER_ACTION", "NETWORK_FLOW", "AUDIT_EVENT", "EVENT", "DNS_RESOLVE", "INCIDENT_LINK"];
const ECOLOR: Record<string, string> = {
  USER_ACTION: "#00ff41",
  NETWORK_FLOW: "#00c853",
  AUDIT_EVENT: "#7cfc00",
  EVENT: "#2e7d32",
  DNS_RESOLVE: "#64ffda",
  INCIDENT_LINK: "#ff003c",
};
const NEON = "#00ff41";
const GLOW = "0 0 6px rgba(0,255,65,0.9)";
const NODE_BG = "#020604";
const SUGGEST: { label: string; node: string; desc: string; reading: string }[] = [
  { label: "C2 · 100.64.39.157", node: "100.64.39.157", desc: "susp 0.99 · 65 incident + 50 flow · posible C2/exfil",
    reading: "Una IP externa contactada por 41 vecinos internos y marcada en 65 incidentes: patrón clásico de C2. Mira cuántos hosts distintos le hablan por NETWORK_FLOW y en qué ventana; eso es lo que M3 resume en n_users/frac_fw." },
  { label: "Lateral · USER-0719", node: "ORG-0004/user:USER-0719", desc: "99 hosts distintos · movimiento lateral",
    reading: "Una sola credencial actuando en 99 máquinas: imposible de ver fila por fila. Cada arista es un acceso; si muchos caen en ±5 min, M3 lo cuenta como n_neigh alto y dispara." },
  { label: "Lateral · USER-0728", node: "ORG-0004/user:USER-0728", desc: "60 hosts distintos · segunda credencial",
    reading: "Segunda credencial en movimiento (60 hosts). Compara con USER-0719: ¿atraviesan los mismos hosts? Eso es propagación coordinada." },
  { label: "Víctima · 10.187.253.125", node: "ORG-0005/10.187.253.125", desc: "susp 0.92 · 12k incident links · host golpeado",
    reading: "Al revés que los anteriores: aquí el centro es la víctima, con 12k incident-links entrando. Copia un incident_id y ábrelo en Incidente para ver la cadena y el reporte." },
  { label: "DNS · vcenter", node: "ORG-0005/vcenter", desc: "7.5k resolves · caza DNS tunneling",
    reading: "Todo el DNS pasa por aquí (7.5k resolves). Un pico de subdominios raros o consultas fuera de horario es la huella del tunneling/DGA." },
];

export default function Graph() {
  const [node, setNode] = useState(SUGGEST[0].node);
  const [q, setQ] = useState(SUGGEST[0].node);
  const [tipos, setTipos] = useState<string[]>(["USER_ACTION", "NETWORK_FLOW"]);
  const [lim, setLim] = useState(60);
  const [depth, setDepth] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["vec", q, tipos.join(","), lim, depth],
    queryFn: () => api.vecindario(q, tipos.join(","), lim, depth),
    enabled: q.length > 3,
  });

  const { nodes, edges } = useMemo(() => {
    const all = (data?.nodes ?? []).filter((n) => n.id !== q);
    // orden: sospechosos primero, luego por signal_count
    const vis = [...all].sort((a, b) => (a.depth - b.depth) || (b.suspicion - a.suspicion) || (b.signal_count - a.signal_count));
    const firstRadius = 680, ringGap = 260;
    const firstHopRings = Math.max(1, Math.ceil(vis.filter((n) => n.depth === 1).length / 18));
    const secondRadius = firstRadius + (firstHopRings - 1) * ringGap + 520;
    const ns = [
      {
        id: q,
        position: { x: 0, y: 0 },
        data: { label: `★ ${q.split("/").pop()}` },
        style: {
          borderColor: NEON, borderWidth: 3, width: 220,
          background: "#001a08", color: NEON,
          fontFamily: "monospace", fontSize: 12, whiteSpace: "pre-line" as const,
          textShadow: GLOW, boxShadow: "0 0 18px rgba(0,255,65,0.45)",
        },
      },
      ...vis.map((n) => {
        const layer = vis.filter((x) => x.depth === n.depth);
        const i = layer.findIndex((x) => x.id === n.id);
        const ring = Math.floor(i / 18);
        const k = i % 18;
        const perRing = Math.min(18, layer.length - ring * 18);
        const ang = (2 * Math.PI * k) / Math.max(perRing, 1) - Math.PI / 2;
        const R = (n.depth === 1 ? firstRadius : secondRadius) + ring * ringGap;
        const hot = n.suspicion > 0;
        return {
          id: n.id,
          position: { x: R * Math.cos(ang), y: R * Math.sin(ang) },
          data: { label: `${n.id.split("/").pop()}\n${n.type} · ${n.signal_count.toLocaleString()}` },
          style: {
            borderColor: hot ? "#ff003c" : NEON,
            borderWidth: hot ? 2 : 1,
            width: 200, background: NODE_BG, color: hot ? "#ff5c7a" : NEON,
            fontFamily: "monospace", fontSize: 11, whiteSpace: "pre-line" as const,
            textShadow: hot ? "0 0 6px rgba(255,0,60,0.9)" : GLOW,
            boxShadow: hot ? "0 0 14px rgba(255,0,60,0.4)" : "0 0 10px rgba(0,255,65,0.25)",
          },
        };
      }),
    ];
    const ids = new Set(ns.map((n) => n.id));
    const es = (data?.edges ?? [])
      .filter((e) => ids.has(e.src) && ids.has(e.dst))
      .slice(0, 300)
      .map((e, i) => ({
        id: `e${i}`,
        source: e.src,
        target: e.dst,
        label: e.type,
        labelStyle: { fill: ECOLOR[e.type] ?? NEON, fontFamily: "monospace", fontSize: 10 },
        labelBgStyle: { fill: "#000" },
        style: { stroke: ECOLOR[e.type] ?? NEON, strokeWidth: 1.5 },
      }));
    return { nodes: ns, edges: es };
  }, [data, q]);

  return (
    <div>
      <h2 className="text-lg font-semibold text-[#00ff41]" style={{ textShadow: "0 0 8px rgba(0,255,65,0.7)" }}>Proveniencia_ <span className="text-xs font-normal text-mut">({depth} {depth === 1 ? "salto" : "saltos"}, layout por nivel)</span></h2>
      <section className="mt-2 rounded-md border border-line bg-panel p-4">
        <h3 className="font-semibold">Qué estás viendo</h3>
        <p className="mt-1 text-sm text-txt/90">
          El nodo ★ es tu punto de partida y cada punto verde es una máquina o credencial que habló con él
          (1.7M aristas disponibles). <b className="text-[#ff5c7a]">Rojo = suspicion_score &gt; 0</b>,
          verde = tráfico sin sospecha registrada. Anillo 1 = vecinos directos; anillo 2 = vecinos de esos vecinos.
        </p>
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-[#00ff41]">Cómo leerlo (3 reglas)</summary>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-txt/90">
            <li><b>Concentración:</b> muchos vecinos del mismo tipo en poco tiempo = campaña, no ruido. M3 cuenta eso en ±5 min.</li>
            <li><b>Color de arista:</b> USER_ACTION (accesos) y NETWORK_FLOW (conexiones) dan contexto; INCIDENT_LINK (rojo) indica vínculo en los datos, no confirmación independiente.</li>
            <li><b>Sospecha:</b> el borde rojo hereda el suspicion del motor Precinct, no del modelo — úsalo para priorizar, confirma con Cola/Incidente.</li>
          </ul>
        </details>
        <details className="mt-1 text-sm">
          <summary className="cursor-pointer text-[#00ff41]">Qué hace M3 con este vecindario</summary>
          <p className="mt-1 text-txt/90">
            Por evento, M3 resume el vecindario causal previo en 8 números y aplica XGBoost. La métrica publicada (F1 0.719 / recall malicious 0.96) es de una evaluación antigua no causal con ±5 min; no mide este endpoint. Usa el resultado como apoyo exploratorio, no como veredicto.
          </p>
        </details>
      </section>
      <form className="mt-2 flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); setQ(node); }}>
        <input value={node} onChange={(e) => setNode(e.target.value)}
          placeholder="ORG-0004/user:USER-0719 o ORG-0004/HOST-0032"
          className="mono min-w-[320px] flex-1 rounded-md border border-line bg-panel px-3 py-2 text-sm" />
        <button className="rounded-md border border-line bg-panel px-4 text-sm">Explorar</button>
      </form>
      <div className="mt-2">
        <p className="text-xs text-mut">Entidades de ejemplo del dataset:</p>
        <div className="mt-1 flex flex-wrap gap-2">
          {SUGGEST.map((s) => (
            <button key={s.node} title={s.desc} onClick={() => { setNode(s.node); setQ(s.node); }}
              className={`mono rounded border px-2 py-1 text-xs ${s.node === q ? "border-line bg-ink text-txt" : "border-line bg-panel text-mut"}`}>
              {s.label}
            </button>
          ))}
        </div>
        <p className="mono mt-1 text-xs text-mut">{SUGGEST.find((s) => s.node === q)?.desc ?? "nodo manual"}</p>
        {(() => {
          const sel = SUGGEST.find((s) => s.node === q);
          return sel ? (
            <p className="mt-1 rounded border border-[#0f3d1e] bg-black p-2 text-sm text-[#00ff41]">
              <b>Qué mirar aquí:</b> {sel.reading}
            </p>
          ) : (
            <p className="mt-1 text-xs text-mut">Nodo manual: busca anillos densos del mismo tipo de arista y bordes rojos; eso es lo que M3 cuantifica.</p>
          );
        })()}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <span className="text-xs text-mut">Profundidad:</span>
        {[1, 2].map((n) => (
          <button key={n} onClick={() => setDepth(n)}
            className={`mono rounded border px-2 py-1 text-xs ${depth === n ? "border-line bg-ink text-txt" : "border-line bg-panel text-mut"}`}>{n} {n === 1 ? "salto" : "saltos"}</button>
        ))}
        <span className="ml-2 text-xs text-mut">Máx. vecinos por nivel:</span>
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
            {data.node} · {data.n_edges} aristas · mostrando {nodes.length - 1} vecinos en {depth} nivel(es) (sospechosos primero por nivel)
          </p>
          <div className="mt-2 h-[520px] rounded-md border border-[#0f3d1e] bg-black">
            <ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark" style={{ background: "#000" }} proOptions={{ hideAttribution: true }}>
              <Background variant={BackgroundVariant.Dots} gap={24} size={1.5} color="#0f3d1e" bgColor="#000" />
            </ReactFlow>
          </div>
          <p className="mt-1 text-xs text-mut">Rojo = suspicion_score &gt; 0 · anillo 1 = relación directa · anillo 2 = segundo salto. Máximo 120 vecinos por nivel.</p>
        </>
      )}
    </div>
  );
}
