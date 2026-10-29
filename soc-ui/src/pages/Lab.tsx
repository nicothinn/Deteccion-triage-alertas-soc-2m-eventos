import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export default function Lab() {
  const { data, error } = useQuery({ queryKey: ["metrics"], queryFn: api.modelMetrics });
  if (error) return <p className="text-sm text-mal">Sin backend.</p>;
  if (!data) return <p className="text-sm text-mut">Cargando métricas…</p>;
  if (data.note) return <p className="text-sm text-mut">{data.note}</p>;
  const rows = Object.entries(data.per_class);
  return (
    <div>
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        <div className="rounded-md border border-line bg-panel p-3">
          <p className="text-xs text-mut">Modelo</p><p className="mono text-lg font-bold">{data.model}</p>
        </div>
        <div className="rounded-md border border-line bg-panel p-3">
          <p className="text-xs text-mut">F1-macro (temporal 80/20)</p><p className="mono text-lg font-bold">{data.f1_macro}</p>
        </div>
        <div className="rounded-md border border-line bg-panel p-3">
          <p className="text-xs text-mut">Train / test</p><p className="mono text-lg font-bold">{data.n_train.toLocaleString()} / {data.n_test.toLocaleString()}</p>
        </div>
        <div className="rounded-md border border-line bg-panel p-3">
          <p className="text-xs text-mut">Recall malicious</p><p className="mono text-lg font-bold text-mal">{data.per_class["malicious"]?.recall}</p>
        </div>
      </div>

      <div className="mt-4 overflow-auto rounded-md border border-line bg-panel">
        <table className="soc">
          <thead><tr><th>Tier</th><th>Precision</th><th>Recall</th><th>F1</th><th>PR-AUC</th><th>Support</th></tr></thead>
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k}>
                <td className="mono">{k}</td><td className="mono">{v.precision}</td>
                <td className="mono">{v.recall}</td><td className="mono">{v.f1}</td>
                <td className="mono">{v.pr_auc}</td><td className="mono">{v.support.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.m2 && (
        <section className="mt-4 rounded-md border border-line bg-panel p-4">
          <h3 className="panel-title">M2 texto ({data.m2.encoder}) — F1-macro {data.m2.f1_macro}</h3>
          <p className="mono mt-1 text-xs text-txt/90">
            malicious P {data.m2.per_class["malicious"]?.precision} · R {data.m2.per_class["malicious"]?.recall} · F1 {data.m2.per_class["malicious"]?.f1} · PR-AUC {data.m2.per_class["malicious"]?.pr_auc} · recall@1%FPR {data.m2.recall_mal_at_1fpr}
          </p>
          <p className="mono mt-1 text-xs text-mut">
            suspicious F1 {data.m2.per_class["suspicious"]?.f1} · train {data.m2.n_train.toLocaleString()} / test {data.m2.n_test.toLocaleString()} · el texto rescata malicious, colapsa suspicious (mismo trade que logreg en variantes)
          </p>
        </section>
      )}

      {data.m4b && (
        <section className="mt-4 rounded-md border border-line bg-panel p-4">
          <h3 className="panel-title">M4b ATT&CK por técnica (XGBoost ×6) — micro {data.m4b.micro_f1} / macro {data.m4b.macro_f1}</h3>
          <p className="mono mt-1 text-xs text-txt/90">
            hamming {data.m4b.hamming} · subset-acc {data.m4b.subset_acc} · train {data.m4b.n_train.toLocaleString()} / test {data.m4b.n_test.toLocaleString()}
          </p>
          <p className="mono mt-1 text-xs text-mut">
            T1190 F1 1.00 (trivial) · T1041/T1567 F1 0.07 (ni lineal ni XGB separan a nivel evento) · T1204 F1 0.39 (10/10 a base de FPs) · T1486/T1566 sin soporte — ver notebooks/m4b
          </p>
        </section>
      )}

      {data.m3 && (
        <section className="mt-4 rounded-md border border-line bg-panel p-4">
          <h3 className="panel-title">M3 grafo (SAGE-mean ±5min) — F1-macro {data.m3.f1_macro}</h3>
          <p className="mono mt-1 text-xs text-txt/90">
            malicious P {data.m3.per_class["malicious"]?.precision} · R {data.m3.per_class["malicious"]?.recall} · F1 {data.m3.per_class["malicious"]?.f1} · recall@1%FPR {data.m3.recall_mal_at_1fpr}
          </p>
          <p className="mono mt-1 text-xs text-mut">
            suspicious F1 {data.m3.per_class["suspicious"]?.f1} · el vecindario aporta contexto pero no ranking a FPR estricto · deep-dive explícito en la Cola
          </p>
        </section>
      )}

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <section className="rounded-md border border-line bg-panel p-4">
          <h3 className="font-semibold">Configuración M1</h3>
          <dl className="mono mt-2 grid grid-cols-2 gap-1 text-xs text-txt/90">
            {Object.entries(data.config).map(([k, v]) => (
              <><dt className="text-mut">{k}</dt><dd>{String(v)}</dd></>
            ))}
          </dl>
          <p className="mt-2 text-xs text-mut">Complejidad fit O(T·n·d): 200 árboles × 112,848 filas. Inferencia un pase raíz-hoja por árbol: &lt;50ms.</p>
        </section>
        <section className="rounded-md border border-line bg-panel p-4">
          <h3 className="font-semibold">Lectura para el paper</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-txt/90">
            <li>Malicious recall {data.per_class["malicious"]?.recall} con precisión {data.per_class["malicious"]?.precision}: el tabular no ve payload ni cadena.</li>
            <li>Suspicious sí se recupera (F1 {data.per_class["suspicious"]?.f1}): las reglas dejan huella tabular.</li>
            <li>M2 (texto MiniLM) ataca el recall malicious; M3 (GraphSAGE ±5min) ataca la precisión a nivel incidente.</li>
            <li>Accuracy 0.88 es vacía con IR 245:1 — reportar F1-macro + PR-AUC.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
