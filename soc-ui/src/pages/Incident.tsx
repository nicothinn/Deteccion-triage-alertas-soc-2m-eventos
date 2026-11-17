import { ReactFlow } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { SEVC, api } from "../lib/api";

const EVENT_PAGE_SIZE = 30;

const INCIDENTS = [
  { id: "acee85e0-4b4e-11ef-a07e-73bb772fb986", label: "Precinct: Data Theft · 501 señales", reading: "Precinct agrupó 501 señales bajo la etiqueta Data Theft. La vista pagina una muestra de la secuencia; esa clasificación no es una confirmación independiente de un analista." },
  { id: "04bdda80-4b51-11ef-98d0-55d447741aef", label: "Precinct: Data Theft · 445 señales", reading: "Otro incidente etiquetado Data Theft por Precinct. Compara los metadatos y la infraestructura del dataset; no implica que un analista validara la clasificación." },
  { id: "ac8def50-4b4e-11ef-a07e-73bb772fb986", label: "Precinct: Data Theft · 120 señales", reading: "Ejemplo intermedio para recorrer eventos y relaciones; Data Theft es la etiqueta automática del conjunto." },
  { id: "7954cad0-4dee-11ef-9f66-fbdc83d0625f", label: "Precinct: Data Theft · 20 señales", reading: "Secuencia pequeña para revisar en una sola sesión; la etiqueta sigue siendo la clasificación de Precinct." },
  { id: "f93306f0-4df2-11ef-9440-1101dfaeda6b", label: "Precinct: Data Theft · 10 señales", reading: "Secuencia breve etiquetada Data Theft por Precinct; úsala para explorar tipos de evento y su orden temporal." },
  { id: "5beb8d60-4b52-11ef-99eb-59db075a1435", label: "Precinct: Data Theft · 7 señales", reading: "Secuencia pequeña con reporte de Precinct. Sirve para explorar pocos eventos, no para medir por sí sola el rendimiento del modelo." },
];

export default function Incident() {
  const { id } = useParams();
  const [manual, setManual] = useState("");
  const [offset, setOffset] = useState(0);
  const incId = id ?? manual;
  const { data, isLoading } = useQuery({
    queryKey: ["incident", incId, offset],
    queryFn: () => api.incident(incId, EVENT_PAGE_SIZE, offset),
    enabled: incId.length > 7,
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
      <h2 className="text-lg font-semibold">Incidente <span className="text-xs font-normal text-mut">(eventos relacionados + reporte Precinct)</span></h2>
      <section className="mt-2 rounded-md border border-line bg-panel p-4">
        <h3 className="font-semibold">Qué estás viendo</h3>
        <p className="mt-1 text-sm text-txt/90">
          Cada incidente Precinct es un conjunto de señales encadenadas + un reporte en lenguaje natural.
          En cada página, la cadena visual muestra hasta 10 eventos y la tabla hasta 30, en orden temporal. El reporte resume el MO (aquí casi todo es <b>Data Theft</b>).
        </p>
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-[#00ff41]">Cómo leer la cadena</summary>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-txt/90">
            <li>Lee de izquierda a derecha: es orden temporal, no topología.</li>
            <li>El color muestra la etiqueta automática de Precinct (rojo = malicious); no equivale a confirmación de un analista.</li>
            <li>Secuencias de 501 vs 7 señales: compara su tamaño y contexto; las etiquetas y reportes provienen de Precinct, no de revisión humana.</li>
          </ul>
        </details>
      </section>
      <div className="mt-2 flex flex-wrap gap-2">
        <select
          value={INCIDENTS.some((x) => x.id === incId) ? incId : ""}
          onChange={(e) => { if (e.target.value) window.location.href = `/incidente/${e.target.value}`; }}
          className="mono min-w-[320px] flex-1 rounded-md border border-line bg-panel px-3 py-2 text-sm">
          <option value="">Elige un incidente del dataset…</option>
          {INCIDENTS.map((x) => (
            <option key={x.id} value={x.id}>{x.label}</option>
          ))}
        </select>
      </div>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => { e.preventDefault(); if (manual) location.hash = `#/incidente/${manual}`; window.location.href = `/incidente/${manual}`; }}
      >
        <input
          value={manual} onChange={(e) => setManual(e.target.value)}
          placeholder="…o pega un incident_id manual (o abre desde la Cola)"
          className="mono w-full rounded-md border border-line bg-panel px-3 py-2 text-sm"
        />
        <button className="rounded-md border border-line bg-panel px-4 text-sm">Abrir</button>
      </form>
      {(() => {
        const sel = INCIDENTS.find((x) => x.id === incId);
        return sel ? (
          <p className="mt-2 rounded border border-[#0f3d1e] bg-black p-2 text-sm text-[#00ff41]">
            <b>Qué mirar aquí:</b> {sel.reading}
          </p>
        ) : null;
      })()}

      {!incId && <p className="mt-3 text-sm text-mut">Sin incidente: ve a Cola y pulsa el hash de incidente de un evento malicioso.</p>}
      {isLoading && <p className="mt-3 text-sm text-mut">Cargando {data ? "" : incId}…</p>}

      {data && (
        <>
          <p className="mono mt-3 text-xs text-mut">{data.incident_id} · {data.n} eventos totales</p>
          <div className="mt-2 h-[300px] rounded-md border border-line">
            <ReactFlow nodes={nodes} edges={edges} fitView colorMode="dark" />
          </div>
          <div className="mt-2 flex items-center justify-between text-xs text-mut">
            <span>{data.n ? `${offset + 1}–${Math.min(offset + data.events.length, data.n)} de ${data.n} eventos` : "Sin eventos"}</span>
            <div className="flex gap-2">
              <button disabled={offset === 0 || isLoading} onClick={() => setOffset(Math.max(0, offset - EVENT_PAGE_SIZE))} className="rounded border border-line px-3 py-1 disabled:opacity-40">Anterior</button>
              <button disabled={offset + data.events.length >= data.n || isLoading} onClick={() => setOffset(offset + EVENT_PAGE_SIZE)} className="rounded border border-line px-3 py-1 disabled:opacity-40">Siguiente</button>
            </div>
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
              <h3 className="font-semibold">Reporte de Precinct</h3>
              <p className="mt-1 text-xs text-mut">Resumen generado desde metadatos del incidente, no informe independiente de un analista.</p>
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
