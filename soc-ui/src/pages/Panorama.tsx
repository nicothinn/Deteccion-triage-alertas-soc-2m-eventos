import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import Bar from "../components/Bar";

export default function Panorama() {
  const { data, error } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  if (error) return <p className="text-sm text-mal">No responde :8000. Levanta <span className="mono">uv run uvicorn app.main:app --port 8000</span> y recarga.</p>;
  if (!data) return <p className="text-sm text-mut">Leyendo /stats (conteos fijos del EDA)…</p>;
  const ir = (data.benign / data.malicious).toFixed(0);
  return (
    <div>
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
        {[
          ["Eventos (6 días)", data.total.toLocaleString()],
          ["Maliciosos", `${data.malicious.toLocaleString()} (0.38%)`],
          ["Desbalance IR", `${ir}:1`],
          [`Grafo: ${data.graph.nodes.toLocaleString()} nodos / ${(data.graph.edges / 1e6).toFixed(1)}M aristas`, `${data.graph.incidents.toLocaleString()} incidentes`],
        ].map(([k, v]) => (
          <div key={k} className="rounded-md border border-line bg-panel p-3">
            <p className="text-xs text-mut">{k}</p>
            <p className="mono text-lg font-bold">{v}</p>
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Bar title="¿De dónde viene el ruido?" note="Respuesta: backup de AWS y AD de Windows. El SOC vive filtrando esto." data={data.top_products} color="#8a96a6" />
        <Bar title="¿Quién genera el volumen?" note="Respuesta: Microsoft + AWS = 2/3. Modela el vendor como feature, no como filtro." data={data.top_vendors} color="#3aa88f" />
        <Bar title="¿Qué severidad trae cada evento?" note="Respuesta: ~49% llega vacía. Se imputa como nivel propio, nunca mediana." data={data.severity} color="#d99a2b" />
        <Bar title="¿Qué hizo Precinct con cada alerta?" note="Respuesta: casi todo quedó Unprocessed; Disrupted son 5,779 decisiones automáticas, no de analista." data={data.disposition} color="#d64545" />
        <Bar title="¿De dónde viene el ruido por tipo?" note="Respuesta: auditoría y management dominan; firewall_action es minoría." data={data.top_types} color="#8a96a6" />
        <Bar title="¿Por dónde se movería M3?" note="Respuesta: USER_ACTION (692k) une credenciales a hosts: la materia prima del grafo." data={data.graph.edge_types} color="#3aa88f" />
      </div>
    </div>
  );
}
