"""Exploración inicial Precinct6 chica (streaming, sin bajar 2M filas)."""
# ponytail: streaming + sample 5k, baja completo solo si hace falta
from datasets import load_dataset

DATASET = "witfoo/precinct6-cybersecurity"

# 1. Ver subsets disponibles sin descargar todo
# subsets: signals, incident_signals, graph_nodes, graph_edges, attack_reports
for subset in ["signals", "attack_reports", "incident_signals"]:
    ds = load_dataset(DATASET, subset, split="train", streaming=True)
    row = next(iter(ds))
    print(f"\n=== {subset} ===")
    print("columnas:", list(row.keys()))
    print("ejemplo:", {k: str(v)[:200] for k, v in row.items()})

# 2. Sample pequeño a pandas para EDA
ds = load_dataset(DATASET, "signals", split="train", streaming=True)
sample = [r for _, r in zip(range(5000), ds)]
import pandas as pd
df = pd.DataFrame(sample)
print("\nshape sample:", df.shape)
print(df["label"].value_counts() if "label" in df else df.iloc[:, -5:].head())
df.to_csv("sample_signals_5k.csv", index=False)
print("guardado: sample_signals_5k.csv")
