// ponytail: dashboard de modelos para Panorama — ECharts directo, sin lib extra
import * as echarts from "echarts";
import { useEffect, useRef } from "react";
import type { ModelMetrics } from "../lib/api";

type Opt = echarts.EChartsOption;

function useChart(setup: () => Opt, deps: unknown[]) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const ch = echarts.init(ref.current, "dark");
    ch.setOption(setup());
    const onR = () => ch.resize();
    window.addEventListener("resize", onR);
    return () => { window.removeEventListener("resize", onR); ch.dispose(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return ref;
}

const baseGrid = { left: 8, right: 16, top: 24, bottom: 8, containLabel: true };
const axisLine = { lineStyle: { color: "#263242" } };
const splitLine = { lineStyle: { color: "#263242" } };
const title = (text: string) => ({ text, left: 8, textStyle: { fontSize: 13 } });

export function F1Macro({ m }: { m: ModelMetrics }) {
  const ref = useChart(() => {
    const opt: Opt = {
      backgroundColor: "transparent",
      title: title("F1-macro por modelo (test temporal)"),
      grid: baseGrid,
      xAxis: { type: "value", max: 1, splitLine },
      yAxis: { type: "category", data: ["M3 grafo", "M2 texto", "M1 tabular"], axisLine },
      series: [{
        type: "bar",
        data: [
          { value: m.m3?.f1_macro ?? 0, itemStyle: { color: "#3aa88f" } },
          { value: m.m2?.f1_macro ?? 0, itemStyle: { color: "#6aa8ff" } },
          { value: m.f1_macro, itemStyle: { color: "#d99a2b" } },
        ],
        label: { show: true, position: "right", color: "#e8edf2" },
        itemStyle: { borderRadius: [0, 4, 4, 0] },
      }],
    };
    return opt;
  }, [m]);
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <div ref={ref} style={{ height: 220 }} />
      <p className="mt-1 text-xs text-mut">M1 0.599 → M2 0.708 → M3 0.719. La ganancia viene de texto+grafo, no de más árboles.</p>
    </section>
  );
}

export function MalRecall({ m }: { m: ModelMetrics }) {
  const ref = useChart(() => {
    const fmt = (p: { value?: unknown }) => Number(p.value).toFixed(4);
    const opt: Opt = {
      backgroundColor: "transparent",
      title: title("Recall malicious: el hinge del paper"),
      grid: baseGrid,
      xAxis: { type: "value", max: 1, splitLine },
      yAxis: { type: "category", data: ["M3 grafo", "M2 texto", "M1 tabular"], axisLine },
      series: [{
        type: "bar",
        data: [
          { value: m.m3?.per_class["malicious"]?.recall ?? 0, itemStyle: { color: "#3aa88f" } },
          { value: m.m2?.per_class["malicious"]?.recall ?? 0, itemStyle: { color: "#6aa8ff" } },
          { value: m.per_class["malicious"]?.recall ?? 0, itemStyle: { color: "#d64545" } },
        ],
        label: { show: true, position: "right", formatter: fmt, color: "#e8edf2" },
        itemStyle: { borderRadius: [0, 4, 4, 0] },
      }],
    };
    return opt;
  }, [m]);
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <div ref={ref} style={{ height: 220 }} />
      <p className="mt-1 text-xs text-mut">M1 ≈ 0: el tabular no ve payload ni cadena. M2 0.97 / M3 0.96 lo rescatan. Esta es la justificación de la cascada.</p>
    </section>
  );
}

export function PerClassF1({ m }: { m: ModelMetrics }) {
  const ref = useChart(() => {
    const cls = ["benign", "suspicious", "malicious"];
    const opt: Opt = {
      backgroundColor: "transparent",
      title: title("F1 por clase y modelo (trade-off)"),
      grid: baseGrid,
      tooltip: { trigger: "axis" },
      legend: { bottom: 0, textStyle: { color: "#8a96a6", fontSize: 11 } },
      xAxis: { type: "category", data: cls, axisLine },
      yAxis: { type: "value", max: 1, splitLine },
      series: [
        { name: "M1", type: "bar", data: cls.map((c) => m.per_class[c]?.f1 ?? 0), itemStyle: { color: "#d99a2b" } },
        { name: "M2", type: "bar", data: cls.map((c) => m.m2?.per_class[c]?.f1 ?? 0), itemStyle: { color: "#6aa8ff" } },
        { name: "M3", type: "bar", data: cls.map((c) => m.m3?.per_class[c]?.f1 ?? 0), itemStyle: { color: "#3aa88f" } },
      ],
    };
    return opt;
  }, [m]);
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <div ref={ref} style={{ height: 260 }} />
      <p className="mt-1 text-xs text-mut">M1 gana suspicious (0.79); M2/M3 ganan malicious (~0.87) y pierden suspicious (~0.25-0.29). Especialistas vs generalista.</p>
    </section>
  );
}

export function PrAucMal({ m }: { m: ModelMetrics }) {
  const ref = useChart(() => {
    const fmt = (p: { value?: unknown }) => Number(p.value).toFixed(3);
    const opt: Opt = {
      backgroundColor: "transparent",
      title: title("PR-AUC malicious (ranking bajo IR 245:1)"),
      grid: baseGrid,
      xAxis: { type: "value", max: 1, splitLine },
      yAxis: { type: "category", data: ["M3 grafo", "M2 texto", "M1 tabular"], axisLine },
      series: [{
        type: "bar",
        data: [
          { value: m.m3?.per_class["malicious"]?.pr_auc ?? 0, itemStyle: { color: "#3aa88f" } },
          { value: m.m2?.per_class["malicious"]?.pr_auc ?? 0, itemStyle: { color: "#6aa8ff" } },
          { value: m.per_class["malicious"]?.pr_auc ?? 0, itemStyle: { color: "#d99a2b" } },
        ],
        label: { show: true, position: "right", formatter: fmt, color: "#e8edf2" },
        itemStyle: { borderRadius: [0, 4, 4, 0] },
      }],
    };
    return opt;
  }, [m]);
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <div ref={ref} style={{ height: 220 }} />
      <p className="mt-1 text-xs text-mut">PR-AUC, no accuracy: con IR 245:1 el accuracy es vacuo (94% con siempre-benign).</p>
    </section>
  );
}

// Matriz de confusión M1 medida (test temporal 28,212, row-normalized).
// Fuente: reports/eda/resumen_eda.md — benign [1,0,0], suspicious [0,0.9602,0.0398], malicious [0,0.9955,0.0045].
const CM = [
  [1.0, 0.0, 0.0],
  [0.0, 0.9602, 0.0398],
  [0.0, 0.9955, 0.0045],
];
const CM_LABELS = ["benign", "suspicious", "malicious"];

export function ConfusionM1() {
  const ref = useChart(() => {
    const data: Array<[number, number, number]> = [];
    CM.forEach((row, i) => row.forEach((v, j) => data.push([j, i, v])));
    const opt: Opt = {
      backgroundColor: "transparent",
      title: title("M1: matriz de confusión (filas = real)"),
      grid: { left: 8, right: 16, top: 40, bottom: 32, containLabel: true },
      xAxis: { type: "category", data: CM_LABELS, splitArea: { show: true }, axisLine },
      yAxis: { type: "category", data: CM_LABELS, splitArea: { show: true }, axisLine },
      visualMap: { min: 0, max: 1, calculable: true, orient: "horizontal", left: "center", bottom: 0, textStyle: { color: "#8a96a6" }, inRange: { color: ["#121923", "#d64545"] } },
      series: [{
        type: "heatmap",
        data,
        label: { show: true, color: "#e8edf2", fontSize: 12, formatter: (p) => Number(p.value[2]).toFixed(2) },
        emphasis: { itemStyle: { shadowBlur: 8 } },
      }],
    };
    return opt;
  }, []);
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <div ref={ref} style={{ height: 300 }} />
      <p className="mt-1 text-xs text-mut">Malicious colapsa a suspicious (0.9955). El tabular confunde lo raro con lo casi-raro: de ahí M2 (texto) y M3 (cadena).</p>
    </section>
  );
}

export function M4bCard({ m }: { m: ModelMetrics }) {
  if (!m.m4b) return null;
  return (
    <section className="rounded-md border border-line bg-panel p-4">
      <h3 className="font-semibold">M4b ATT&CK por técnica (XGBoost ×6) — no desplegado</h3>
      <dl className="mono mt-2 grid grid-cols-2 gap-1 text-xs text-txt/90">
        <dt className="text-mut">micro-F1 / macro-F1</dt><dd>{m.m4b.micro_f1} / {m.m4b.macro_f1}</dd>
        <dt className="text-mut">hamming / subset-acc</dt><dd>{m.m4b.hamming} / {m.m4b.subset_acc}</dd>
        <dt className="text-mut">train / test (threat)</dt><dd>{m.m4b.n_train.toLocaleString()} / {m.m4b.n_test.toLocaleString()}</dd>
        <dt className="text-mut">labels</dt><dd>{m.m4b.labels.join(", ")}</dd>
      </dl>
      <p className="mt-2 text-xs text-mut">T1190 F1 1.00 (trivial) · T1041/T1567 F1 0.07 (ni lineal ni XGB separan a nivel evento) · ver notebooks/m4b.</p>
    </section>
  );
}
