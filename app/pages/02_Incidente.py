"""Incidente: cadena de ataque + reporte. Pagina 2."""
# ponytail: graphviz nativo, sin pyvis/networkx
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
CSS = """<style>.stApp{background:#0F141B;}
section[data-testid="stSidebar"]{background:#121923;border-right:1px solid #263242;}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;}
.status{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:#8A96A6;
border:1px solid #263242;background:#121923;padding:8px 12px;border-radius:6px;}
table{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;}
</style>"""


@st.cache_data
def incident_ids(n=40):
    df = pd.read_parquet(
        ROOT / "data" / "signals" / "signals.parquet",
        columns=["artifact_id", "incident_ids", "label_binary", "timestamp"],
    )
    m = df[df.label_binary == "malicious"]
    ids: dict[str, int] = {}
    for v in m["incident_ids"].head(20000):
        try:
            for i in json.loads(v):
                ids[i] = ids.get(i, 0) + 1
        except Exception:
            continue
    return sorted(ids, key=ids.get, reverse=True)[:n]


@st.cache_data
def load_incident(inc):
    sig = pd.read_parquet(ROOT / "data" / "signals" / "signals.parquet")
    mask = sig["incident_ids"].str.contains(inc, na=False)
    ev = sig[mask].copy()
    ev["ts"] = pd.to_datetime(ev["timestamp"], unit="s", utc=True)
    ev = ev.sort_values("timestamp")
    rep = pd.read_parquet(ROOT / "data" / "graph" / "attack_reports.parquet")
    r = rep[rep.incident_id == inc]
    return ev, (r.iloc[0].to_dict() if len(r) else None)


st.set_page_config(page_title="Incidente — Precinct6 SOC", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

ids = incident_ids()
inc = st.selectbox("Incidente", ids, format_func=lambda x: x[:8])
ev, rep = load_incident(inc)

st.markdown(f"<div class='status'>INCIDENTE <b class='mono'>{inc}</b> &nbsp;·&nbsp; {len(ev)} eventos &nbsp;·&nbsp; "
            f"{ev['label_binary'].value_counts().to_dict()}</div>", unsafe_allow_html=True)

chain = ev.head(8)
dots = ["digraph { rankdir=LR; bgcolor=transparent; node [shape=box style=rounded fontname=monospace fontsize=10];"]
for _, r in chain.iterrows():
    a = (str(r['src_ip'] or ' Zugang')[:18]).replace('"', '')
    b = (str(r['dst_ip'] or str(r['message_type']))[:18]).replace('"', '')
    lbl = f"{r['message_type']}\\n{r['action']}".replace('"', '')
    col = "#D64545" if r["label_binary"] == "malicious" else ("#D99A2B" if r["label_binary"] == "suspicious" else "#3AA88F")
    dots.append(f'"{a}" -> "{b}" [label="{lbl}" color="{col}" fontcolor="#DCE4ED"];')
dots.append("}")
st.subheader("Cadena de ataque (orden temporal)")
st.graphviz_chart("\n".join(dots))

c1, c2 = st.columns([1, 1])
with c1:
    st.subheader("Línea de tiempo")
    tl = ev[["ts", "message_type", "action", "src_ip", "label_binary"]].copy()
    tl["ts"] = tl["ts"].dt.strftime("%m-%d %H:%M:%S")
    st.dataframe(tl, use_container_width=True, hide_index=True, height=320)
with c2:
    st.subheader("Reporte del incidente")
    if rep:
        st.markdown(f"**{rep['mo_name']}** · suspicion {rep['suspicion_score']} · fuente {rep['report_source']}")
        st.write(str(rep["report_text"])[:2500])
    else:
        st.info("Sin reporte asociado.")
    st.subheader("Indicadores")
    iocs = ev[["src_ip", "dst_ip", "username", "message_type"]].drop_duplicates().head(20)
    st.dataframe(iocs, use_container_width=True, hide_index=True, height=220)
