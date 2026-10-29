// ponytail: una barra ECharts reutilizada en Panorama/Cobertura
import * as echarts from "echarts";
import { useEffect, useRef } from "react";

export default function Bar({ title, note, data, color, height = 260 }: {
  title: string; note: string; data: Record<string, number>; color: string; height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ch = echarts.init(ref.current, "dark");
    const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 10);
    ch.setOption({
      backgroundColor: "transparent",
      grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: true },
      xAxis: { type: "value", splitLine: { lineStyle: { color: "#263242" } } },
      yAxis: { type: "category", data: entries.map(([k]) => k), axisLine: { lineStyle: { color: "#263242" } } },
      series: [{ type: "bar", data: entries.map(([, v]) => v), itemStyle: { color, borderRadius: [0, 4, 4, 0] } }],
    });
    const onR = () => ch.resize();
    window.addEventListener("resize", onR);
    return () => { window.removeEventListener("resize", onR); ch.dispose(); };
  }, [data, color]);
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <h3 className="font-semibold">{title}</h3>
      <div ref={ref} style={{ height }} />
      <p className="mt-1 text-xs text-mut">{note}</p>
    </section>
  );
}
