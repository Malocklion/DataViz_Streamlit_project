# app.py
import os
import numpy as np
import pandas as pd
import streamlit as st

from utils.io import load_and_clean_data
from sections.intro import render_intro
from sections.analysis import render_analysis
from sections.insights import render_insights
from sections.implications import render_implications
from sections.data_methods import render_data_methods

# --------------------------
# Configuration
# --------------------------
st.set_page_config(
    page_title="Transition Énergétique Automobile - France",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------
# CSS
# --------------------------
st.markdown(
    """
<style>
:root{
  --primary: #22c55e; --primary-600:#16a34a;
  --bg:#0b1220; --surface:#0f172a;
  --border: rgba(148,163,184,.18);
  --muted:#9aa4b2; --text:#e6e8eb;
}
html, body, [data-testid="stAppViewContainer"]{ background: var(--bg); }
* { font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial; }

.main-header { font-size: 2.2rem; color: var(--text); text-align: center; margin: 0 0 1rem 0; }
.section-header { color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: .35rem; margin-top: 1rem; }

/* Tabs pills */
.stTabs [role="tablist"]{ gap:.5rem; border:0; margin:.25rem 0 1rem; }
.stTabs [role="tab"]{
  padding:.5rem 1rem; border-radius:999px; border:1px solid var(--border);
  background:var(--surface); color:var(--text); opacity:.9; transition:all .15s ease;
}
.stTabs [role="tab"]:hover{ opacity:1; border-color:rgba(255,255,255,.28); }
.stTabs [role="tab"][aria-selected="true"]{
  color:#fff; opacity:1; background:linear-gradient(180deg, rgba(34,197,94,.18), rgba(34,197,94,.06));
  border-color:rgba(34,197,94,.55); box-shadow:0 0 0 2px rgba(34,197,94,.18) inset;
}
.stTabs [role="tablist"]::after{ display:none; }

/* Metrics cards */
[data-testid="stMetric"]{
  background:var(--surface); border:1px solid var(--border);
  border-radius:10px; padding:10px 14px;
}
[data-testid="stMetric"] [data-testid="stMetricLabel"]{ color:var(--muted)!important; font-weight:600; }
[data-testid="stMetric"] [data-testid="stMetricValue"]{ color:#fff!important; font-weight:700; }

/* Sidebar */
section[data-testid="stSidebar"]{ background:#0a0f1a!important; border-right:1px solid var(--border); }

a, .markdown-text-container a { color: var(--primary); }
.small { font-size:.9rem; color:var(--muted); }
</style>
""",
    unsafe_allow_html=True,
)

# --------------------------
# Titre
# --------------------------
st.markdown(
    '<h1 class="main-header">🚗⚡ La Transition Énergétique Automobile en France</h1>',
    unsafe_allow_html=True,
)

# --------------------------
# Données (avec cache)
# --------------------------
DATA_PATH = os.path.join("data", "voitures-par-commune-par-energie.csv")

@st.cache_data(show_spinner=False)
def get_data(path: str) -> pd.DataFrame:
    return load_and_clean_data(path)

try:
    df = get_data(DATA_PATH)
except Exception as e:
    st.error(
        f"❌ Impossible de charger les données ({e}). "
        "Vérifiez le fichier dans le dossier data/."
    )
    st.stop()

if df is None or df.empty:
    st.error("❌ Impossible de charger les données. Vérifiez le fichier dans le dossier data/.")
    st.stop()

# --------------------------
# Filtres (sidebar)
# --------------------------
st.sidebar.markdown("## 🎛️ Filtres")

# Trimestre unique
quarters_available = sorted(df["TRIMESTRE"].unique())
quarter_label_map = {q: f"T{int(q.quarter)} {int(q.year)}" for q in quarters_available}
quarter_labels = [quarter_label_map[q] for q in quarters_available]
selected_quarter_label = st.sidebar.selectbox(
    "📅 Trimestre d'analyse",
    options=quarter_labels,
    index=len(quarter_labels) - 1,
    help="Analyse détaillée = trimestre choisi; les vues temporelles restent historiques.",
)
label_to_period = {v: k for k, v in quarter_label_map.items()}
selected_period = label_to_period[selected_quarter_label]

# Départements
departements = sorted(df["DEPARTEMENT"].unique())
departements_display = ["Tous"] + departements
selected_departements = st.sidebar.multiselect(
    "🗺️ Départements (codes INSEE)",
    options=departements_display,
    default=departements_display[0],
    help="Choisis un ou plusieurs départements. 'Tous' = France entière.",
)

# DOM-TOM
exclude_domtom = st.sidebar.toggle(
    "Exclure DOM-TOM (971, 972, 973, 974, 976, ...)", value=False
)
domtom = {"971", "972", "973", "974", "976", "975", "977", "978", "984", "986", "987", "988"}
if "Tous" in selected_departements:
    filtered_departements = [
        d for d in departements if (not exclude_domtom or d not in domtom)
    ]
else:
    filtered_departements = [
        d for d in selected_departements if (not exclude_domtom or d not in domtom)
    ]

# Seuil de parc minimal
min_vehicles = st.sidebar.slider(
    "🚗 Taille minimale du parc (VP)",
    min_value=0,
    max_value=int(df["NB_VP"].max()),
    value=100,
    step=50,
    help="Filtre les micro-communes pour améliorer la lisibilité.",
)

# --------------------------
# Périmètre courant + T-1 (calculs globaux)
# --------------------------
df_current = df[
    (df["TRIMESTRE"] == selected_period)
    & (df["DEPARTEMENT"].isin(filtered_departements))
    & (df["NB_VP"] >= min_vehicles)
].copy()
df_current = df_current[
    (df_current["PART_ELECTRIQUE"] >= 0) & (df_current["PART_ELECTRIQUE"] <= 100)
]

prev_period = selected_period - 1
df_prev = df[
    (df["TRIMESTRE"] == prev_period)
    & (df["DEPARTEMENT"].isin(filtered_departements))
    & (df["NB_VP"] >= min_vehicles)
].copy()

total_vp = int(df_current["NB_VP"].sum()) if not df_current.empty else 0
total_ev = (
    int(df_current["NB_RECHARGEABLES_TOTAL"].sum()) if not df_current.empty else 0
)
weighted_rate = (total_ev / total_vp * 100) if total_vp > 0 else 0.0
communes_count = int(df_current["LIBGEO"].nunique()) if not df_current.empty else 0

prev_total_vp = int(df_prev["NB_VP"].sum()) if not df_prev.empty else 0
prev_total_ev = (
    int(df_prev["NB_RECHARGEABLES_TOTAL"].sum()) if not df_prev.empty else 0
)
prev_rate = (
    (prev_total_ev / prev_total_vp * 100) if prev_total_vp > 0 else np.nan
)
delta_pp_value = None if np.isnan(prev_rate) else (weighted_rate - prev_rate)

# --------------------------
# KPI globaux (photo du trimestre)
# --------------------------
st.markdown(
    '<h2 class="section-header">📊 Indicateurs clés (photo du trimestre)</h2>',
    unsafe_allow_html=True,
)
if df_current.empty:
    st.info("Aucune donnée pour ce périmètre. Modifiez les filtres.")
else:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "🚗 Parc total (VP)",
            f"{total_vp:,}",
            delta=(f"{(total_vp - prev_total_vp):+,}" if prev_total_vp else None),
        )
    with c2:
        st.metric(
            "⚡ Véhicules électriques/rechargeables",
            f"{total_ev:,}",
            delta=(f"{(total_ev - prev_total_ev):+,}" if prev_total_ev else None),
        )
    with c3:
        st.metric(
            "📈 Taux d'adoption pondéré",
            f"{weighted_rate:.2f}%",
            delta=(f"{delta_pp_value:+.2f} %" if delta_pp_value is not None else None),
        )
    with c4:
        prev_communes = int(df_prev["LIBGEO"].nunique()) if not df_prev.empty else 0
        st.metric(
            "🏘️ Communes analysées",
            f"{communes_count:,}",
            delta=(f"{(communes_count - prev_communes):+,}" if prev_communes else None),
        )

# --------------------------
# Onglets narratifs
# --------------------------
tab_problem, tab_analysis, tab_insights, tab_implications, tab_data = st.tabs(
    ["🧭 Problem", "🧪 Analysis", "💡 Insights", "🎯 Implications", "📚 Data & Methods"]
)

with tab_problem:
    render_intro()

with tab_analysis:
    render_analysis(
        df=df,
        df_current=df_current,
        df_prev=df_prev,
        quarter_labels=quarter_labels,
        label_to_period=label_to_period,
        filtered_departements=filtered_departements,
        min_vehicles=min_vehicles,
    )

with tab_insights:
    render_insights(
        df_current=df_current,
        df_prev=df_prev,
        filtered_departements=filtered_departements,
        min_vehicles=min_vehicles,
    )

with tab_implications:
    render_implications(
        df_current=df_current,
        df_prev=df_prev,
        weighted_rate=weighted_rate,
        delta_pp_value=delta_pp_value,
    )

with tab_data:
    render_data_methods(
        df=df,
        df_current=df_current,
        selected_quarter_label=selected_quarter_label,
    )
