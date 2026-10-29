"""Precinct6 SOC — cola de triage. Corre: uv run streamlit run app/streamlit_app.py"""
# ponytail: consola densa, sin hero ni cards SaaS; st nativo + graphviz, sin deps nuevas
import datetime
import json
import pickle
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
CSS = """<style>
/* ponytail: tema acero SOC, plano, mono para valores maquina */
.stApp {background:#0F141B;}
section[data-testid="stSidebar"] {background:#121923; border-right:1px solid #263242;}
h1, h2, h3 {letter-spacing:-0.02em;}
.mono {font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;}
.status {font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12px; color:#8A96A6;
  border:1px solid #263242; background:#121923; padding:8px 12px; border-radius:6px;}
.sev {display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:8px;}
.stButton>button[kind="primary"]{width:100%; padding:0.7rem; font-weight:700; border-radius:6px;}
.stDataFrame {border:1px solid #263242; border-radius:6px;}
[data-testid="stMetric"] {border:1px solid #263242; background:#121923; border-radius:6px; padding:10px 12px;}
</style>"""

DOT = {"malicious": "#D64545", "suspicious": "#D99A2B", "benign": "#3AA88F"}


@st.cache_resource
def get_model():
    pkl = ROOT / "models" / "m1.pkl"
    if pkl.exists():
        with open(pkl, "rb") as f:
            return pickle.load(f)
    return None


@st.cache_data
def queue(n=4000):
    df = pd.read_parquet(
        ROOT / "data" / "signals" / "signals.parquet",
        columns=["artifact_id", "timestamp", "message_type", "src_ip", "dst_ip",
                 "action", "severity", "label_binary", "attack_techniques",
                 "message_sanitized", "org_id"],
    )
    mal = df[df.label_binary == "malicious"]
    sus = df[df.label_binary == "suspicious"].sample(min(len(df[df.label_binary == "suspicious"]), n // 2), random_state=7)
    ben = df[df.label_binary == "benign"].sample(min(len(df[df.label_binary == "benign"]), n // 4), random_state=7)
    q = pd.concat([mal, sus, ben]).copy()
    q["ts"] = pd.to_datetime(q["timestamp"], unit="s", utc=True)
    return q.sort_values("timestamp", ascending=False).reset_index(drop=True)


st.set_page_config(page_title="Precinct6 SOC — cola", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

d = get_model()
st.markdown(
    f"<div class='status'>PRECINCT6 SOC &nbsp;·&nbsp; ventana 26 jul – 01 ago 2024 &nbsp;·&nbsp; "
    f"2,011,674 eventos &nbsp;·&nbsp; modelo <b>{'m1-tabar-v1' if d else 'stub'}</b> &nbsp;·&nbsp; "
    f"F1-macro 0.60 &nbsp;·&nbsp; IR 245:1</div>",
    unsafe_allow_html=True,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Maliciosos", "7,728", "0.38% del total")
m2.metric("Sospechosos", "106,793", "5.3%")
m3.metric("Técnica top", "T1190", "Exploit public-facing app")
m4.metric("Modelo", "m1-tabar-v1" if d else "stub", "tabular LightGBM")

q = queue()
left, right = st.columns([1.15, 1])

with left:
    st.subheader("Cola por riesgo")
    st.caption("Maliciosos primero, luego sospechosos recientes. Elige uno para puntuarlo a la derecha.")
    view = q[["label_binary", "ts", "message_type", "src_ip", "action"]].head(60)
    st.dataframe(view, height=420, use_container_width=True, hide_index=True)
    ids = q["artifact_id"].head(60).tolist()
    pick = st.selectbox("Inspeccionar", ids, format_func=lambda a: a[:8])
    row0 = q[q.artifact_id == pick].iloc[0]

with right:
    st.subheader("Puntuar evento")
    with st.form("score"):
        c1, c2 = st.columns(2)
        with c1:
            mt = st.text_input("message_type", str(row0["message_type"]))
            stream = st.text_input("stream_name", "cisco_asa")
            action = st.text_input("action", str(row0["action"]))
            sev = st.text_input("severity", str(row0["severity"]))
        with c2:
            prod = st.text_input("product_name", "ASA Firewall")
            vend = st.text_input("vendor", "Cisco")
            proto = st.text_input("protocol", "")
            org = st.text_input("org_id", str(row0["org_id"]))
        msg = st.text_area("message_sanitized", str(row0["message_sanitized"])[:600], height=110)
        go = st.form_submit_button("Puntuar con M1", type="primary")

    if go:
        feat = pd.DataFrame([{
            "message_type": mt, "stream_name": stream, "product_name": prod,
            "vendor_name": vend, "pipeline": "syslog", "org_id": org, "action": action,
            "severity": sev, "protocol": proto, "hour": datetime.datetime.now().hour,
            "msg_len": len(msg), "lag_h": -1,
        }])
        if d:
            pipe = d["pipe"]
            pred = pipe.predict(feat)[0]
            proba = dict(zip(pipe.classes_, map(float, pipe.predict_proba(feat)[0])))
        else:
            pred, proba = "benign", {"benign": 1.0}
        dot = DOT.get(pred, "#3AA88F")
        st.markdown(f"<span class='sev' style='background:{dot}'></span><b class='mono'>{pred}</b>", unsafe_allow_html=True)
        st.bar_chart(pd.Series(proba))
        st.caption(f"Técnicas observadas: {row0['attack_techniques']} · M1 no usa texto, por eso M2 existe.")

st.divider()
g1, g2 = st.columns(2)
with g1:
    st.subheader("Volumen por tipo de mensaje")
    st.bar_chart(q["message_type"].value_counts().head(10))
with g2:
    st.subheader("Eventos por día")
    per_day = q.set_index(q["ts"].dt.date)["artifact_id"].resample("D").count()
    per_day.index = per_day.index.astype(str)
    st.line_chart(per_day)

st.caption("Páginas: Incidente (cadena de ataque + reporte) y Cobertura MITRE en el menú lateral.")
