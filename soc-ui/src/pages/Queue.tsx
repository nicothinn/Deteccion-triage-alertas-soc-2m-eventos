import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, parseIncidentIds, type SocEvent } from "../lib/api";

function ts(e: SocEvent) {
  return new Date(e.timestamp * 1000).toISOString().slice(5, 19).replace("T", " ");
}

export default function Queue() {
  const [label, setLabel] = useState("all");
  const { data, isLoading, error } = useQuery({ queryKey: ["queue", label], queryFn: () => api.queue(label) });
  const [sel, setSel] = useState<string | null>(null);
  const [score, setScore] = useState<null | Awaited<ReturnType<typeof api.score>>>(null);
  const [scoring, setScoring] = useState(false);
  const [expl, setExpl] = useState<null | Awaited<ReturnType<typeof api.explain>>>(null);
  const [g3, setG3] = useState<null | Awaited<ReturnType<typeof api.scoreGraph>>>(null);
  const [g3loading, setG3loading] = useState(false);
  const [fbNote, setFbNote] = useState("");
  const [fbMsg, setFbMsg] = useState("");

  const ev = useMemo(() => data?.find((d) => d.artifact_id === sel) ?? data?.[0], [data, sel]);
  const incs = ev ? parseIncidentIds(ev.incident_ids) : [];

  async function runScore() {
    if (!ev) return;
    setScoring(true);
    try {
      setScore(await api.score(ev));
      setExpl(await api.explain(ev));
    } finally {
      setScoring(false);
    }
  }

  async function runGraph() {
    if (!ev) return;
    setG3loading(true);
    try {
      setG3(await api.scoreGraph(ev.artifact_id));
    } finally {
      setG3loading(false);
    }
  }

  async function sendFeedback(decision: string) {
    if (!ev) return;
    try {
      const r = await api.feedback(ev.artifact_id, decision, fbNote);
      setFbMsg(`Guardado (${r.n} correcciones). Gracias, el modelo re-entrena con esto.`);
      setFbNote("");
    } catch {
      setFbMsg("No se pudo guardar.");
    }
  }

  return (
    <div>
      <section className="rounded-md border border-line bg-panel p-4">
        <h3 className="font-semibold">Qué estás viendo</h3>
        <p className="mt-1 text-sm text-txt/90">
          La cola ordenada por riesgo: maliciosos primero, luego sospechosos recientes.
          Cada fila es 1 evento de 2M; elige una y puntúala a la derecha. Nada aquí es inventado: todo sale de <span className="mono">/queue</span> en vivo.
        </p>
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-[#00ff41]">Cómo se puntúa (cascada M1 → M2 → M3)</summary>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-txt/90">
            <li><b>M1 tabular</b> (&lt;50ms): filtra lo obvio por campos. Rápido pero ciega a malicious (recall 0.0045).</li>
            <li><b>M2 texto</b> (~100ms): lee el mensaje y confirma malicious (recall 0.97). Basta que uno diga malicious para escalar.</li>
            <li><b>M3 grafo</b> (~s): junta el vecindario ±5min del artifact y busca cadenas. Botón “Consultar vecindario M3”.</li>
            <li><b>Técnicas ATT&CK</b> vienen del tier decidido (mapeo oráculo, no predicción aprendida): malicious → T1190+T1041+T1567.</li>
            <li><b>Tu turno:</b> los botones escalar/monitorear/falso_positivo guardan tu corrección y el modelo re-entrena con ella.</li>
          </ul>
        </details>
      </section>
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_1fr]">
      <section>
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-lg font-semibold">Cola por riesgo</h2>
          <select
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            className="ml-auto rounded-md border border-line bg-panel px-2 py-1 text-sm"
          >
            <option value="all">todas</option>
            <option value="malicious">maliciosas</option>
            <option value="suspicious">sospechosas</option>
            <option value="benign">benignas</option>
          </select>
        </div>
        {isLoading && <p className="text-sm text-mut">Cargando cola desde FastAPI…</p>}
        {error && <p className="text-sm text-mal">Sin backend. Levanta <span className="mono">uv run uvicorn app.main:app</span></p>}
        <div className="overflow-auto rounded-md border border-line bg-panel" style={{ maxHeight: 560 }}>
          <table className="soc">
            <thead><tr><th>#</th><th>Sev</th><th>Hora UTC</th><th>Tipo</th><th>Origen</th><th>Acción</th><th>Etiqueta</th></tr></thead>
            <tbody>
              {data?.map((e, i) => (
                <tr key={e.artifact_id} onClick={() => { setSel(e.artifact_id); setScore(null); setExpl(null); setG3(null); setFbMsg(""); }}
                    className={ev?.artifact_id === e.artifact_id ? "sel" : ""}>
                  <td className="mono text-mut">{i + 1}</td>
                  <td className={`sevbar ${e.label_binary}`}><span className={`sev-ico ${e.label_binary}`} title={e.label_binary} /></td>
                  <td className="mono whitespace-nowrap">{ts(e)}</td>
                  <td className="mono">{e.message_type}</td>
                  <td className="mono">{e.src_ip || "—"}</td>
                  <td>{e.action || "—"}</td>
                  <td className="mono">{e.label_binary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-md border border-line bg-panel p-4">
        <h2 className="text-lg font-semibold">Detalle y puntuación</h2>
        {!ev ? <p className="text-sm text-mut">Elige una fila.</p> : (
          <>
            <p className="mono mt-2 break-all text-xs text-mut">{ev.artifact_id}</p>
            <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
              <dt className="text-mut">Tipo</dt><dd className="mono">{ev.message_type}</dd>
              <dt className="text-mut">Acción</dt><dd>{ev.action || "—"}</dd>
              <dt className="text-mut">Severidad</dt><dd>{ev.severity || "vacía"}</dd>
              <dt className="text-mut">Org</dt><dd className="mono">{ev.org_id}</dd>
              <dt className="text-mut">Técnicas</dt><dd className="mono">{ev.attack_techniques || "—"}</dd>
              <dt className="text-mut">Tácticas</dt><dd className="mono">{ev.attack_tactics || "—"}</dd>
            </dl>
            <p className="mono mt-2 max-h-24 overflow-auto rounded border border-line bg-ink p-2 text-xs">
              {ev.message_sanitized || "(sin mensaje)"}
            </p>
            {incs.length > 0 && (
              <p className="mt-2 text-sm">Incidente: <Link className="mono underline" to={`/incidente/${incs[0]}`}>{incs[0].slice(0, 8)}</Link></p>
            )}
            <button
              onClick={runScore} disabled={scoring}
              className="mt-3 w-full rounded-md bg-txt py-2 text-sm font-bold text-ink disabled:opacity-50">
              {scoring ? "Puntuando…" : "Puntuar con M1"}
            </button>
            {score && (
              <div className="border-t border-line pt-3 text-sm">
                <p><span className={`sev-ico ${score.label}`} />{" "}
                  <b className="mono">{score.label}</b> → {score.triage}</p>
                <p className="mono mt-1 text-xs text-mut">{JSON.stringify(score.proba)}</p>
                <p className="mono mt-1 text-xs text-mut">{score.model} · ATT&CK [{score.techniques.join(", ") || "—"}]</p>
                <p className="mono mt-1 text-xs text-mut">{score.techniques_source}</p>
                {score.m2 && (
                  <p className="mono mt-1 text-xs text-txt/90">
                    M2 texto: <b>{score.m2.label}</b> {JSON.stringify(score.m2.proba)} · {score.m2.model}
                  </p>
                )}
                <button
                  onClick={runGraph} disabled={g3loading}
                  className="mono mt-2 w-full rounded border border-line bg-panel px-2 py-1.5 text-xs hover:text-txt disabled:opacity-50">
                  {g3loading ? "Leyendo vecindario ±5min…" : "Consultar vecindario M3 (grafo)"}
                </button>
                {g3 && (
                  <p className="mono mt-1 text-xs text-txt/90">
                    M3 grafo: <b>{g3.label}</b> {JSON.stringify(g3.proba)} · {g3.n_vecinos} vecinos · {g3.model}
                  </p>
                )}
              </div>
            )}
            {expl && (
              <div className="border-t border-line pt-3 text-sm">
                <p className="panel-title">Por qué dice {expl.label}</p>
                <ul className="mono mt-1 space-y-0.5 text-xs">
                  {expl.top_features.slice(0, 8).map((f) => (
                    <li key={f.feature} className={f.active ? "text-txt" : "text-mut"}>
                      {f.active ? "■" : "□"} {f.feature} <span className="text-mut">({f.importance})</span>
                    </li>
                  ))}
                </ul>
                <p className="mt-1 text-xs text-mut">■ activa en este evento · importancia = ganancia LightGBM global.</p>
              </div>
            )}
            {score && (
              <div className="border-t border-line pt-3 text-sm">
                <p className="panel-title">Tu turno: ¿está bien puntuado?</p>
                <div className="mt-2 flex gap-2">
                  {(["escalar", "monitorear", "falso_positivo"] as const).map((d) => (
                    <button key={d} onClick={() => sendFeedback(d)}
                      className="mono flex-1 rounded border border-line bg-panel px-2 py-1.5 text-xs hover:text-txt">{d}</button>
                  ))}
                </div>
                <input value={fbNote} onChange={(e) => setFbNote(e.target.value)} placeholder="nota opcional (máx 500)"
                  className="mono mt-2 w-full rounded border border-line bg-panel px-2 py-1.5 text-xs" />
                {fbMsg && <p className="mt-1 text-xs text-mut">{fbMsg}</p>}
              </div>
            )}
          </>
        )}
      </section>
      </div>
    </div>
  );
}
