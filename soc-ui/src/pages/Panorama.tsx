import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import Bar from "../components/Bar";
import { ConfusionM1, F1Macro, M4bCard, MalRecall, PerClassF1, PrAucMal } from "../components/ModelDash";

export default function Panorama() {
  const { data, error } = useQuery({ queryKey: ["stats"], queryFn: api.stats });
  const metrics = useQuery({ queryKey: ["metrics"], queryFn: api.modelMetrics });
  if (error) return <p className="text-sm text-mal">No responde :8000. Levanta <span className="mono">uv run uvicorn app.main:app --port 8000</span> y recarga.</p>;
  if (!data) return <p className="text-sm text-mut">Leyendo /stats (conteos fijos del EDA)…</p>;
  const ir = (data.benign / data.malicious).toFixed(0);
  return (
    <div>
      <section className="radius-panel border border-line bg-panel p-5">
        <p className="hero-label">Seis días de telemetría Precinct · 4 organizaciones · 19 productos. El equipo revisa millones de señales para cazar pocas.</p>
        <p className="hero-num mt-2">{ir}:1 <span className="text-[18px] font-medium tracking-normal text-mut">benignas por cada maliciosa</span></p>
        <p className="mono mt-2 text-[12px] text-mut">{data.total.toLocaleString()} eventos · {data.malicious.toLocaleString()} leads maliciosos (0.38%) · {data.graph.nodes.toLocaleString()} nodos / {(data.graph.edges / 1e6).toFixed(1)}M aristas · {data.graph.incidents.toLocaleString()} incidentes</p>
      </section>
      <p className="mt-2 text-sm text-mut">Empieza por la Cola: filtra malicious + block y puntúa. Esta página es el mapa, no el trabajo.</p>

      <h2 className="mb-2 mt-6 text-lg font-semibold">Modelos <span className="text-sm font-normal text-mut">(test temporal 80/20, sin shuffle)</span></h2>
      {!metrics.data ? (
        <p className="text-sm text-mut">Leyendo /model/metrics…</p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <F1Macro m={metrics.data} />
            <MalRecall m={metrics.data} />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <PerClassF1 m={metrics.data} />
            <PrAucMal m={metrics.data} />
          </div>
          <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
            <ConfusionM1 />
            <M4bCard m={metrics.data} />
          </div>
        </>
      )}

      <h2 className="mb-2 mt-6 text-lg font-semibold">Datos <span className="text-sm font-normal text-mut">(de dónde viene el volumen)</span></h2>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Bar title="¿De dónde viene el ruido?" note="Respuesta: backup de AWS y AD de Windows. El SOC vive filtrando esto." data={data.top_products} color="#6e7f7a" />
        <Bar title="¿Quién genera el volumen?" note="Respuesta: Microsoft + AWS = 2/3. Modela el vendor como feature, no como filtro." data={data.top_vendors} color="#2fbf8f" />
        <Bar title="¿Qué severidad trae cada evento?" note="Respuesta: ~49% llega vacía. Se imputa como nivel propio, nunca mediana." data={data.severity} color="#e9a13b" />
        <Bar title="¿Qué hizo Precinct con cada alerta?" note="Respuesta: casi todo quedó Unprocessed; Disrupted son 5,779 decisiones automáticas, no de analista." data={data.disposition} color="#ff4d4d" />
        <Bar title="¿De dónde viene el ruido por tipo?" note="Respuesta: auditoría y management dominan; firewall_action es minoría." data={data.top_types} color="#6e7f7a" />
        <Bar title="¿Por dónde se movería M3?" note="Respuesta: USER_ACTION (692k) une credenciales a hosts: la materia prima del grafo." data={data.graph.edge_types} color="#2fbf8f" />
      </div>
    </div>
  );
}
