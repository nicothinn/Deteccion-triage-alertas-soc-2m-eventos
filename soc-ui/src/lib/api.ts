// ponytail: un wrapper fetch, sin axios
export const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export type Label = "benign" | "suspicious" | "malicious";

export interface SocEvent {
  artifact_id: string;
  timestamp: number;
  message_type: string;
  stream_name: string;
  pipeline: string;
  product_name: string;
  vendor_name: string;
  src_ip: string;
  dst_ip: string;
  action: string;
  severity: string;
  protocol: string;
  label_binary: Label;
  attack_techniques: string;
  attack_tactics: string;
  message_sanitized: string;
  org_id: string;
  incident_ids: string;
}

export interface Stats {
  total: number; benign: number; suspicious: number; malicious: number;
  top_types: Record<string, number>; top_orgs: Record<string, number>;
  top_tech: Record<string, number>; window: string;
  severity: Record<string, number>; disposition: Record<string, number>;
  top_products: Record<string, number>; top_vendors: Record<string, number>;
  graph: { nodes: number; edges: number; incidents: number; edge_types: Record<string, number> };
}

export interface ClassMetrics { precision: number; recall: number; f1: number; support: number; pr_auc: number }
export interface ModelMetrics {
  model: string; f1_macro: number; per_class: Record<string, ClassMetrics>;
  n_train: number; n_test: number;
  config: { n_estimators: number; learning_rate: number; num_leaves: number; class_weight: string; split: string; sample_n: number };
  note?: string;
  m2?: { model: string; encoder: string; f1_macro: number; recall_mal_at_1fpr: number;
         per_class: Record<string, ClassMetrics>; n_train: number; n_test: number } | null;
  m3?: { model: string; f1_macro: number; recall_mal_at_1fpr: number;
         per_class: Record<string, ClassMetrics>; n_train: number; n_test: number } | null;
}

export interface ExplainFeat { feature: string; importance: number; value: number; active: boolean }
export interface ExplainResp { label: string; proba: Record<string, number>; model: string; top_features: ExplainFeat[] }

export interface Vecindario {
  node: string; n_edges: number;
  nodes: { id: string; type: string; signal_count: number; suspicion: number; org: string }[];
  edges: { src: string; dst: string; type: string }[];
}

export interface ScoreResp {
  label: string; proba: Record<string, number>;
  techniques: string[]; tactics: string[]; model: string; triage: string;
  m2?: { label: string; proba: Record<string, number>; model: string } | null;
}

export interface IncidentResp {
  incident_id: string; n: number;
  events: Record<string, unknown>[];
  report: { mo_name: string; suspicion_score: number; report_source: string; report_text: string } | null;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${r.status} ${path}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => get<{ ok: boolean; model: string; loaded: boolean }>("/health"),
  stats: () => get<Stats>("/stats"),
  queue: (label = "all", limit = 60) => get<SocEvent[]>(`/queue?label=${label}&limit=${limit}`),
  incident: (id: string) => get<IncidentResp>(`/incident/${id}`),
  modelMetrics: () => get<ModelMetrics>("/model/metrics"),
  vecindario: (node: string, tipos = "", limit = 150) =>
    get<Vecindario>(`/graph/vecindario?node=${encodeURIComponent(node)}&tipos=${tipos}&limit=${limit}`),
  explain: async (e: SocEvent): Promise<ExplainResp> => {
    const r = await fetch(`${API}/explain`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_type: e.message_type || "firewall_action",
        stream_name: e.stream_name || "syslog",
        product_name: e.product_name || "",
        vendor_name: e.vendor_name || "",
        pipeline: e.pipeline || "syslog",
        org_id: e.org_id || "ORG-0004",
        action: e.action || "",
        severity: e.severity || "",
        protocol: e.protocol || "",
        message: (e.message_sanitized || "").slice(0, 2000),
      }),
    });
    if (!r.ok) throw new Error(`explain ${r.status}`);
    return r.json() as Promise<ExplainResp>;
  },
  feedback: async (artifact_id: string, decision: string, note = "") => {    const r = await fetch(`${API}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artifact_id, decision, note }),
    });
    if (!r.ok) throw new Error(`feedback ${r.status}`);
    return r.json() as Promise<{ ok: boolean; n: number }>;
  },
  score: async (e: SocEvent): Promise<ScoreResp> => {
    const r = await fetch(`${API}/score`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message_type: e.message_type || "firewall_action",
        stream_name: e.stream_name || "syslog",
        product_name: e.product_name || "",
        vendor_name: e.vendor_name || "",
        pipeline: e.pipeline || "syslog",
        org_id: e.org_id || "ORG-0004",
        action: e.action || "",
        severity: e.severity || "",
        protocol: e.protocol || "",
        message: (e.message_sanitized || "").slice(0, 2000),
      }),
    });
    if (!r.ok) throw new Error(`score ${r.status}`);
    return r.json() as Promise<ScoreResp>;
  },
  scoreGraph: async (artifact_id: string): Promise<ScoreResp & { n_vecinos: number }> => {
    const r = await fetch(`${API}/score_graph`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ artifact_id }),
    });
    if (!r.ok) throw new Error(`score_graph ${r.status}`);
    return r.json();
  },
};

export function parseIncidentIds(raw: string): string[] {
  try {
    const v = JSON.parse(raw);
    return Array.isArray(v) ? v : [];
  } catch {
    return [];
  }
}

export const SEVC = { malicious: "#d64545", suspicious: "#d99a2b", benign: "#3aa88f" } as const;
