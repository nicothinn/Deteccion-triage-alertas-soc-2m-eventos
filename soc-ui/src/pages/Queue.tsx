import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, parseIncidentIds, type QueueFilters, type SocEvent } from "../lib/api";

function ts(e: SocEvent) {
  return new Date(e.timestamp * 1000).toISOString().slice(5, 19).replace("T", " ");
}

const PAGE_SIZE = 60;
const EMPTY_EVENTS: SocEvent[] = [];
const EMPTY_DRAFT = { label: "all", org_id: "", message_type: "", severity: "", search: "", from: "", to: "" };

export default function Queue() {
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [filterError, setFilterError] = useState("");
  const [filters, setFilters] = useState<QueueFilters>({ label: "all", org_id: "", message_type: "", severity: "", search: "" });
  const [offset, setOffset] = useState(0);
  const { data, isLoading, error } = useQuery({
    queryKey: ["queue", filters, offset],
    queryFn: () => api.queue(filters, PAGE_SIZE, offset),
  });
  const events = data?.items ?? EMPTY_EVENTS;
  const [sel, setSel] = useState<string | null>(null);
  const [score, setScore] = useState<null | Awaited<ReturnType<typeof api.score>>>(null);
  const [scoring, setScoring] = useState(false);
  const [expl, setExpl] = useState<null | Awaited<ReturnType<typeof api.explain>>>(null);
  const [g3, setG3] = useState<null | Awaited<ReturnType<typeof api.scoreGraph>>>(null);
  const [g3loading, setG3loading] = useState(false);
  const [fbNote, setFbNote] = useState("");
  const [fbMsg, setFbMsg] = useState("");

  const ev = useMemo(() => events.find((d) => d.artifact_id === sel) ?? events[0], [events, sel]);
  const incs = ev ? parseIncidentIds(ev.incident_ids) : [];

  function goToPage(nextOffset: number) {
    setOffset(Math.max(0, nextOffset));
    setSel(null);
    setScore(null);
    setExpl(null);
    setG3(null);
    setFbMsg("");
  }

  function applyFilters(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const start_ts = draft.from ? Date.parse(`${draft.from}T00:00:00Z`) / 1000 : undefined;
    const end_ts = draft.to ? Date.parse(`${draft.to}T00:00:00Z`) / 1000 + 86400 : undefined;
    if (start_ts !== undefined && end_ts !== undefined && start_ts >= end_ts) {
      setFilterError("La fecha Desde debe ser igual o anterior a Hasta.");
      return;
    }
    setFilterError("");
    setFilters({ label: draft.label, org_id: draft.org_id, message_type: draft.message_type,
      severity: draft.severity, search: draft.search, start_ts, end_ts });
    goToPage(0);
  }

  function clearFilters() {
    setDraft(EMPTY_DRAFT);
    setFilterError("");
    setFilters({ label: "all", org_id: "", message_type: "", severity: "", search: "" });
    goToPage(0);
  }

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
      setFbMsg(`Guardado (${r.n} correcciones) para revisión y entrenamiento posterior.`);
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
          Eventos históricos ordenados por etiqueta Precinct (maliciosos, sospechosos, benignos), no por la predicción del modelo.
          Filtra la muestra y puntúa cada evento a la derecha; los datos vienen de <span className="mono">/queue</span>.
        </p>
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-[#00ff41]">Cómo se puntúa (M1 + M2; M3 manual)</summary>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-txt/90">
            <li><b>M1 tabular</b> y <b>M2 texto</b> puntúan el evento seleccionado; sus métricas reflejan el test temporal, no garantía de acierto en producción.</li>
            <li>La cola muestra etiquetas Precinct del dataset; no son la salida de esos modelos hasta que pulses Puntuar.</li>
            <li><b>M3 grafo</b> (~s): junta el vecindario ±5min del artifact y busca cadenas. Botón “Consultar vecindario M3”.</li>
            <li><b>Técnicas ATT&CK</b> vienen del tier decidido (mapeo oráculo, no predicción aprendida): malicious → T1190+T1041+T1567.</li>
            <li><b>Feedback:</b> guarda una decisión para revisión y entrenamiento posterior; no reentrena automáticamente.</li>
          </ul>
        </details>
      </section>
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1.2fr_1fr]">
      <section>
        <div className="mb-2 flex items-center gap-2">
          <h2 className="text-lg font-semibold">Cola de eventos</h2>
          <span className="mono ml-auto text-xs text-mut">{data ? `${data.total.toLocaleString()} resultados` : ""}</span>
        </div>
        <form onSubmit={applyFilters} className="mb-3 grid grid-cols-2 gap-2 rounded-md border border-line bg-panel p-3 md:grid-cols-3 xl:grid-cols-4">
          <label className="text-xs text-mut">Etiqueta
            <select value={draft.label} onChange={(e) => setDraft({ ...draft, label: e.target.value })} className="mt-1 w-full rounded border border-line bg-ink px-2 py-1.5 text-sm text-txt">
              <option value="all">todas</option><option value="malicious">maliciosas</option><option value="suspicious">sospechosas</option><option value="benign">benignas</option>
            </select>
          </label>
          <label className="text-xs text-mut">Organización
            <input value={draft.org_id} onChange={(e) => setDraft({ ...draft, org_id: e.target.value })} placeholder="ORG-0004" className="mt-1 w-full rounded border border-line bg-ink px-2 py-1.5 text-sm text-txt" />
          </label>
          <label className="text-xs text-mut">Tipo de evento
            <input value={draft.message_type} onChange={(e) => setDraft({ ...draft, message_type: e.target.value })} placeholder="firewall_action" className="mt-1 w-full rounded border border-line bg-ink px-2 py-1.5 text-sm text-txt" />
          </label>
          <label className="text-xs text-mut">Severidad
            <input value={draft.severity} onChange={(e) => setDraft({ ...draft, severity: e.target.value })} placeholder="warning" className="mt-1 w-full rounded border border-line bg-ink px-2 py-1.5 text-sm text-txt" />
          </label>
          <label className="text-xs text-mut">Desde (UTC)
            <input type="date" value={draft.from} onChange={(e) => setDraft({ ...draft, from: e.target.value })} className="mt-1 w-full rounded border border-line bg-ink px-2 py-1.5 text-sm text-txt" />
          </label>
          <label className="text-xs text-mut">Hasta (UTC)
            <input type="date" value={draft.to} onChange={(e) => setDraft({ ...draft, to: e.target.value })} className="mt-1 w-full rounded border border-line bg-ink px-2 py-1.5 text-sm text-txt" />
          </label>
          <label className="col-span-2 text-xs text-mut md:col-span-1">Buscar ID, IP, host o regla
            <input value={draft.search} onChange={(e) => setDraft({ ...draft, search: e.target.value })} placeholder="texto exacto o parcial" className="mt-1 w-full rounded border border-line bg-ink px-2 py-1.5 text-sm text-txt" />
          </label>
          <div className="col-span-2 flex items-end gap-2 md:col-span-3 xl:col-span-1">
            <button className="rounded border border-line bg-txt px-3 py-1.5 text-sm font-semibold text-ink">Aplicar</button>
            <button type="button" onClick={clearFilters} className="rounded border border-line px-3 py-1.5 text-sm text-mut">Limpiar</button>
          </div>
        </form>
        {filterError && <p role="alert" className="mb-2 text-sm text-mal">{filterError}</p>}
        {isLoading && <p className="text-sm text-mut">Cargando cola desde FastAPI…</p>}
        {error && <p role="alert" className="text-sm text-mal">No se pudo cargar la cola: {error instanceof Error ? error.message : "error desconocido"}</p>}
        <div className="overflow-auto rounded-md border border-line bg-panel" style={{ maxHeight: 560 }}>
          <table className="soc">
            <thead><tr><th>#</th><th>Sev</th><th>Hora UTC</th><th>Tipo</th><th>Origen</th><th>Acción</th><th>Etiqueta</th></tr></thead>
            <tbody>
              {events.map((e, i) => (
                <tr key={e.artifact_id} onClick={() => { setSel(e.artifact_id); setScore(null); setExpl(null); setG3(null); setFbMsg(""); }}
                    className={ev?.artifact_id === e.artifact_id ? "sel" : ""}>
                  <td className="mono text-mut">{offset + i + 1}</td>
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
          {!isLoading && events.length === 0 && <p className="p-4 text-sm text-mut">No hay eventos con estos filtros.</p>}
        </div>
        <div className="mt-2 flex items-center justify-between text-xs text-mut">
          <span>{data && events.length ? `${offset + 1}–${offset + events.length} de ${data.total.toLocaleString()}` : "0 resultados"}</span>
          <div className="flex gap-2">
            <button disabled={offset === 0 || isLoading} onClick={() => goToPage(offset - PAGE_SIZE)} className="rounded border border-line px-3 py-1 disabled:opacity-40">Anterior</button>
            <button disabled={!data || offset + events.length >= data.total || isLoading} onClick={() => goToPage(offset + PAGE_SIZE)} className="rounded border border-line px-3 py-1 disabled:opacity-40">Siguiente</button>
          </div>
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
