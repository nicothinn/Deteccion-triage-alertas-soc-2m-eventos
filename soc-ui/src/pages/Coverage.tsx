import { useQuery } from "@tanstack/react-query";
import Bar from "../components/Bar";
import { api } from "../lib/api";

export default function Coverage() {
  const { data } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  if (!data) return <p className="text-sm text-mut">Cargando cobertura desde FastAPI…</p>;
  const ir = (data.benign / data.malicious).toFixed(0);
  return (
    <div>
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {[
          ["Total eventos", data.total.toLocaleString()],
          ["Maliciosos", `${data.malicious.toLocaleString()} (0.38%)`],
          ["Sospechosos", data.suspicious.toLocaleString()],
          [`Desbalance IR`, `${ir}:1`],
        ].map(([k, v]) => (
          <div key={k} className="rounded-md border border-line bg-panel p-3">
            <p className="text-xs text-mut">{k}</p>
            <p className="mono text-lg font-bold">{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Bar title="¿Cómo atacan? Técnicas en los 7,728 maliciosos" note="Respuesta: T1190, explotar una app pública. M3-grafo debe unir estos pasos entre hosts." data={data.top_tech} color="#d64545" />
        <Bar title="¿De dónde viene el volumen?" note="Respuesta: auditoría Windows y management de AWS. firewall_action, lo que M1 mejor entiende, es minoría." data={data.top_types} color="#8a96a6" />
        <Bar title="¿Dónde están los puntos ciegos?" note="Respuesta: ORG-0004 concentra la mitad de la captura y ORG-0001 casi no aporta. Sesgo declarado en el paper." data={data.top_orgs} color="#3aa88f" />
        <section className="rounded-md border border-line bg-panel p-4">
          <h3 className="panel-title">Cómo leer esta página en el paper</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-txt/90">
            <li>Ventana {data.window}; split temporal 80/20, sin shuffle.</li>
            <li>Métrica: F1-macro + PR-AUC por clase. Accuracy prohibida con IR {ir}:1.</li>
            <li>M1 falla malicious (recall 0.0045) → justifica M2 texto y M3 grafo.</li>
            <li>~49% de eventos sin severidad: imputar como cadena vacía, no mediana.</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
