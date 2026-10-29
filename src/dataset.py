# ponytail: carga local parquet, sin re-descargar
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"

def load_signals(sample_n=None):
    df = pd.read_parquet(DATA / "signals" / "signals.parquet")
    return df.sample(sample_n, random_state=42) if sample_n else df

def load_incidents():
    return pd.read_parquet(DATA / "signals" / "incident_signals.parquet")

def load_graph():
    nodes = pd.read_parquet(DATA / "graph" / "nodes.parquet")
    edges = pd.read_parquet(DATA / "graph" / "edges-00000.parquet")
    return nodes, edges

def load_reports():
    return pd.read_parquet(DATA / "graph" / "attack_reports.parquet")
