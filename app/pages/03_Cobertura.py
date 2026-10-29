"""Cobertura MITRE + desbalance. Pagina 3."""
# ponytail: counts con pandas, bar_chart nativo
import pandas as pd
import streamlit as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = """<style>.stApp{background:#0F141B;}
section[data-testid="stSidebar"]{background:#121923;border-right:1px solid #263242;}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;}
.status{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;color:#8A96A6;
border:1px solid #263242;background:#121923;padding:8px 12px;border-radius:6px;}</style>"""


@st.cache_data
def cov():
    df = pd.read_parquet(
        ROOT / "data" / "signals" / "signals.parquet",
        columns=["attack_techniques", "attack_tactics", "label_binary", "severity", "timestamp"],
    )
    mal = df[df.label_binary == "malicious"]
    tech = mal["attack_techniques"].value_counts().head(12)
    tact = mal["attack_tactics"].value_counts().head(12)
    sev = df["severity"].replace("", "vacío").value_counts().head(8)
    df["day"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.date.astype(str)
    per = df.groupby(["day", "label_binary"]).size().unstack(fill_value=0)
    return tech, tact, sev, per


st.set_page_config(page_title="Cobertura MITRE — Precinct6 SOC", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)
tech, tact, sev, per = cov()

st.markdown("<div class='status'>COBERTURA ATT&amp;CK sobre 7,728 eventos maliciosos · el resto es ruido benigno 94.3%</div>",
            unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    st.subheader("Técnicas (ataque real)")
    st.bar_chart(tech)
    st.caption("T1190 domina: explotar app pública. M3-grafo debe conectar estos pasos entre hosts.")
with c2:
    st.subheader("Tácticas")
    st.bar_chart(tact)
    st.caption("TA0001 acceso inicial + TA0002 ejecución: perímetro, no insider.")

c3, c4 = st.columns(2)
with c3:
    st.subheader("Severidad global (el SOC vive aquí)")
    st.bar_chart(sev)
    st.caption("~49% sin severidad: el prepro de M1 la imputa como cadena vacía.")
with c4:
    st.subheader("Desbalance temporal")
    st.line_chart(per)
    st.caption("Benigno aplasta todo. Por eso el paper usa F1-macro y PR-AUC, nunca accuracy.")
