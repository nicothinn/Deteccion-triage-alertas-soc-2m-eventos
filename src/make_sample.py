"""Muestras compactas para hosts de 512MB (Render free).

uv run python src/make_sample.py
-> data/signals/signals_sample.parquet  (~20k filas, ~3MB)
-> data/graph/edges_sample.parquet      (~250k edges, ~8MB)

Medido: app + /queue + /incident ~= 240MB con este sample (512MB alcanza).
El parquet completo cuesta 4.9GB por request; por eso el sample.
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SIG, GRP = ROOT / "data" / "signals", ROOT / "data" / "graph"
# mismas columnas que app/main.py (QCOLS + event_time para /score_graph)
COLS = ["artifact_id", "timestamp", "message_type", "stream_name", "pipeline",
        "product_name", "vendor_name", "src_ip", "dst_ip", "src_host", "dst_host",
        "username", "matched_rules", "action", "severity", "protocol", "label_binary",
        "attack_techniques", "attack_tactics", "message_sanitized", "org_id",
        "incident_ids", "event_time"]


def signals(rows: int) -> int:
    df = pd.read_parquet(SIG / "signals.parquet", columns=COLS)
    mal = df[df["label_binary"] == "malicious"]
    rest = max(rows - len(mal), 0)
    sus = df[df["label_binary"] == "suspicious"].sample(n=rest // 2, random_state=42)
    ben = df[df["label_binary"] == "benign"].sample(n=rest - rest // 2, random_state=42)
    out = pd.concat([mal, sus, ben])
    assert len(out) == rows, "no hay suficientes filas para el tamano pedido"
    assert (out["label_binary"] == "malicious").sum() == len(mal), "se perdieron malicious"
    out.to_parquet(SIG / "signals_sample.parquet", index=False)
    return len(out)


def edges(max_rows: int, top_nodes: int) -> int:
    # ponytail: conserva vecindarios completos de los nodos mas conectados
    # (ahi viven los 5 nodos sugeridos por la UI); el resto se muestrea.
    e = pd.read_parquet(GRP / "edges-00000.parquet", columns=["src", "dst", "type"])
    hot = pd.concat([e["src"], e["dst"]]).value_counts().head(top_nodes).index
    s = e[e["src"].isin(hot) | e["dst"].isin(hot)]
    if len(s) > max_rows:
        s = s.sample(max_rows, random_state=42)
    s.to_parquet(GRP / "edges_sample.parquet", index=False)
    return len(s)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=20000)
    p.add_argument("--edges", type=int, default=250_000)
    p.add_argument("--nodes", type=int, default=800)
    a = p.parse_args()
    print(f"signals_sample.parquet {signals(a.rows):,} filas")
    print(f"edges_sample.parquet   {edges(a.edges, a.nodes):,} edges")
