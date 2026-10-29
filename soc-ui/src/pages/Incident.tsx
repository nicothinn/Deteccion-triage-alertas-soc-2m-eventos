import { ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { SEVC, api } from "../lib/api";

export default function Incident() {
  const { id } = useParams();
  const [manual, setManual] = useState("");
  const incId = id ?? manual;
  const { data, isLoading } = useQuery({
    queryKey: ["incident", incId], queryFn: () => api.incident(incId), enabled: incId.length > 7,
  });

  const { nodes, edges } = useMemo(() => {
    const evs = (data?.events ?? []).slice(0, 10) as Record<string, string | number>[];
    const nodes = evs.map((e, i) => ({
      id: String(e["artifact_id"] ?? i),
      position: { x: i * 230, y: (i % 2) * 70 },
      data: { label: `${e["message_type"]}\n${e["action"] || ""}` },
      style: {
        borderColor: SEVC[(e["label_binary"] as keyof typeof SEVC) ?? "benign"],
        borderWidth: 2, width: 200, fontFamily: "monospace", fontSize: 11, whiteSpace: "pre-line" as const,
      },
    }));
    const edges = nodes.slice(1).map((n, i) => ({
      id: `e${i}`, source: nodes[i].id, target: n.id,
      style: { stroke: "#8a96a6" },
    }));
    return { nodes, edges };
  }, [data]);

  return (
    <div>
      <h2 className="text-lg font-semibold">Incidente</h2>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => { e.preventDefault(); if (manual) location.hash = `#/incidente/${manual}`; window.location.href = `/incidente/${manual}`; }}
      >
        <input
          value={manual} onChange={(e) => setManual(e.target.value)}
          placeholder="pega un incident_id (o abre desde la Cola)"
          className="mono w-full rounded-md border border-line bg-panel px-3 py-2 text-sm"
        />
        <button className="rounded-md border border-line bg-panel px-4 text-sm">Abrir</button>
      </form>

      {!incId && <p className="mt-3 text-sm text-mut">Sin incidente: ve a Cola y pulsa el hash de incidente de un evento malicioso.</p>}
      {isLoading && <p className="mt-3 text-sm text-mut">Cargando {data ? "" : incId}…</p>}

      {data && (
        <>
          <p className="mono mt-3 text-xs text-mut">{data.incident_id} · {data.n} eventos totales (mostrando cadena de 10)</p>
          <div className="mt-2 h-[300px] rounded-md border border-line">
            <ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark" />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <section className="overflow-auto rounded-md border border-line bg-panel" style={{ maxHeight: 320 }}>
              <table className="soc">
                <thead><tr><th>Hora</th><th>Tipo</th><th>Src</th><th>Etiqueta</th></tr></thead>
                <tbody>
                  {(data.events as Record<string, string | number>[]).slice(0, 30).map((e) => (
                    <tr key={String(e["artifact_id"])}>
                      <td className="mono">{new Date(Number(e["timestamp"]) * 1000).toISOString().slice(5, 19).replace("T", " ")}</td>
                      <td className="mono">{String(e["message_type"])}</td>
                      <td className="mono">{String(e["src_ip"] || "—")}</td>
                      <td className="mono">{String(e["label_binary"])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="rounded-md border border-line bg-panel p-4">
              <h3 className="font-semibold">Reporte</h3>
              {data.report ? (
                <>
                  <p className="mt-1 text-sm">{data.report.mo_name} · suspicion {data.report.suspicion_score} · {data.report.report_source}</p>
                  <p className="mt-2 max-h-56 overflow-auto text-sm leading-relaxed text-txt/90">{data.report.report_text}</p>
                </>
              ) : <p className="mt-1 text-sm text-mut">Sin reporte asociado.</p>}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
