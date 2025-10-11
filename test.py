import os
import json
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import load_and_clean_data  # uses: https://github.com/... -> in workspace: utils.py

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
st.markdown("""
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
.stTabs [role="tablist"]{ gap: .5rem; border: 0; margin: .25rem 0 1rem; }
.stTabs [role="tab"]{ padding: .5rem 1rem; border-radius: 999px; border: 1px solid var(--border); background: var(--surface); color: var(--text); opacity: .9; transition: all .15s ease; }
.stTabs [role="tab"]:hover{ opacity: 1; border-color: rgba(255,255,255,.28); }
.stTabs [role="tab"][aria-selected="true"]{ color:#fff; opacity: 1; background: linear-gradient(180deg, rgba(34,197,94,.18), rgba(34,197,94,.06)); border-color: rgba(34,197,94,.55); box-shadow: 0 0 0 2px rgba(34,197,94,.18) inset; }
.stTabs [role="tablist"]::after{ display:none; }
[data-testid="stMetric"]{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; }
[data-testid="stMetric"] [data-testid="stMetricLabel"]{ color: var(--muted) !important; font-weight: 600; }
[data-testid="stMetric"] [data-testid="stMetricValue"]{ color: #ffffff !important; font-weight: 700; }
section[data-testid="stSidebar"]{ background: #0a0f1a !important; border-right: 1px solid var(--border); }
a, .markdown-text-container a { color: var(--primary); }
.small { font-size: .9rem; color: var(--muted); }
blockquote { border-left: 4px solid var(--primary); padding: .5rem .75rem; background: rgba(34,197,94,.06); border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# --------------------------
# Helpers & cache
# --------------------------
@st.cache_data(ttl=3600)
def load_departements_geojson():
    local_path = os.path.join("data", "departements.geojson")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback (rare)
    url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()

@st.cache_data(ttl=3600)
def make_quarter_label(p):
    return f"T{int(p.quarter)} {int(p.year)}"

@st.cache_data(ttl=3600)
def aggregate_regional(df_in):
    g = df_in.groupby(['TRIMESTRE','DEPARTEMENT'], as_index=False).agg(
        NB_VP=('NB_VP','sum'),
        NB_RECHARGEABLES_TOTAL=('NB_RECHARGEABLES_TOTAL','sum')
    )
    g['PART_ELECTRIQUE'] = np.where(g['NB_VP']>0, g['NB_RECHARGEABLES_TOTAL']/g['NB_VP']*100, 0)
    g['LABEL'] = g['TRIMESTRE'].apply(make_quarter_label)
    return g

def dep_filter_list(departements, selected, exclude_domtom):
    domtom = {"971","972","973","974","976","975","977","978","984","986","987","988"}
    if "Tous" in selected:
        return [d for d in departements if (not exclude_domtom or d not in domtom)]
    return [d for d in selected if (not exclude_domtom or d not in domtom)]


# --------------------------
# Data
# --------------------------
st.markdown('<h1 class="main-header">🚗⚡ La Transition Énergétique Automobile en France</h1>', unsafe_allow_html=True)

DATA_PATH = os.path.join("data", "voitures-par-commune-par-energie.csv")
df = load_and_clean_data(DATA_PATH)
if df is None or df.empty:
    st.error("❌ Impossible de charger les données. Vérifiez le fichier dans data/.")
    st.stop()

# --------------------------
# Sidebar — audience & filters (UX)
# --------------------------
st.sidebar.markdown("## 🎯 Audience & contexte")
st.sidebar.markdown("- Décideurs publics, DREAL, opérateurs d’infrastructures, collectivités.")
st.sidebar.markdown("- Objectif: suivre l’adoption VE et prioriser l’action.")

st.sidebar.markdown("## 🎛️ Filtres")
quarters_available = sorted(df['TRIMESTRE'].unique())
quarter_labels = [make_quarter_label(q) for q in quarters_available]
label_to_period = {make_quarter_label(q): q for q in quarters_available}
selected_quarter_label = st.sidebar.selectbox(
    "📅 Trimestre d'analyse",
    options=quarter_labels,
    index=len(quarter_labels) - 1,
    help="Analyse détaillée au trimestre choisi; les vues temporelles restent historiques."
)
selected_period = label_to_period[selected_quarter_label]

departements = sorted(df['DEPARTEMENT'].unique())
departements_display = ["Tous"] + departements
selected_departements = st.sidebar.multiselect(
    "🗺️ Départements (codes INSEE)",
    options=departements_display,
    default=departements_display[0],
    help="Sélectionne un ou plusieurs départements. 'Tous' = France entière."
)
exclude_domtom = st.sidebar.toggle("Exclure DOM‑TOM (971, 972, 973, 974, 976, ...)", value=False)
filtered_departements = dep_filter_list(departements, selected_departements, exclude_domtom)

min_vehicles = st.sidebar.slider(
    "🚗 Taille minimale du parc (VP)",
    min_value=0, max_value=int(df['NB_VP'].max()), value=100, step=50,
    help="Filtre les micro‑communes pour améliorer la lisibilité."
)

# --------------------------
# Current perimeter
# --------------------------
df_current = df[
    (df['TRIMESTRE'] == selected_period) &
    (df['DEPARTEMENT'].isin(filtered_departements)) &
    (df['NB_VP'] >= min_vehicles)
].copy()
df_current = df_current[(df_current['PART_ELECTRIQUE'] >= 0) & (df_current['PART_ELECTRIQUE'] <= 100)]

# KPIs + previous quarter
total_vp = int(df_current['NB_VP'].sum())
total_ev = int(df_current['NB_RECHARGEABLES_TOTAL'].sum())
weighted_rate = (total_ev / total_vp * 100) if total_vp > 0 else 0.0
communes_count = int(df_current['LIBGEO'].nunique())

prev_period = selected_period - 1
df_prev = df[
    (df['TRIMESTRE'] == prev_period) &
    (df['DEPARTEMENT'].isin(filtered_departements)) &
    (df['NB_VP'] >= min_vehicles)
]
prev_total_vp = int(df_prev['NB_VP'].sum()) if not df_prev.empty else 0
prev_total_ev = int(df_prev['NB_RECHARGEABLES_TOTAL'].sum()) if not df_prev.empty else 0
prev_rate = (prev_total_ev / prev_total_vp * 100) if prev_total_vp > 0 else np.nan
delta_pp = None if np.isnan(prev_rate) else (weighted_rate - prev_rate)

# --------------------------
# Narrative tabs
# --------------------------
tab_problem, tab_analysis, tab_insights, tab_implications, tab_appendix = st.tabs(
    ["1) Problème", "2) Analyse", "3) Insights", "4) Implications", "Annexes"]
)

# ============ 1) PROBLEM ============
with tab_problem:
    st.markdown('<h2 class="section-header">Problème</h2>', unsafe_allow_html=True)
    st.markdown("""
- Comment évolue l’adoption des véhicules électriques (VE) en France ?
- Où se situent les disparités territoriales et quelles priorités d’action en découlent ?
- Quels territoires contribuent le plus à la croissance récente du parc électrique ?
""")
    st.markdown("Hypothèse de mesure: le taux d’adoption par territoire est défini par $\\text{Taux} = \\frac{EV}{VP} \\times 100$.")
    st.info("Ce tableau de bord raconte: l’état actuel, l’évolution temporelle, les contrastes territoriaux et leurs implications opérationnelles.")

    st.markdown('<h2 class="section-header">Indicateurs clés (périmètre courant)</h2>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🚗 Parc total (VP)", f"{total_vp:,}",
                  delta=(f"{(total_vp - prev_total_vp):+,}" if prev_total_vp else None))
    with c2:
        st.metric("⚡ Véhicules électriques/rechargeables", f"{total_ev:,}",
                  delta=(f"{(total_ev - prev_total_ev):+,}" if prev_total_ev else None))
    with c3:
        st.metric("📈 Taux d'adoption pondéré", f"{weighted_rate:.2f}%",
                  delta=(f"{delta_pp:+.2f} pp" if delta_pp is not None else None))
    with c4:
        st.metric("🏘️ Communes analysées", f"{communes_count:,}")

    st.caption("Question: Quel est l’état actuel, et s’améliore‑t‑il par rapport au trimestre précédent ?")

# ============ 2) ANALYSIS ============
with tab_analysis:
    st.markdown('<h2 class="section-header">Analyse</h2>', unsafe_allow_html=True)
    st.markdown("> On examine l’évolution spatio‑temporelle et l’historique pour comprendre le rythme d’adoption.")

    # Evolution map (animated)
    geojson = load_departements_geojson()
    df_hist_dept = df[(df['DEPARTEMENT'].isin(filtered_departements)) & (df['NB_VP'] >= min_vehicles)].copy()
    regional_hist = aggregate_regional(df_hist_dept)

    st.subheader("🗺️ Carte de France — évolution dans le temps")
    colA, colB = st.columns([2,1])
    with colA:
        map_metric = st.radio(
            "Métrique de couleur", ["Taux d'adoption (%)", "Véhicules électriques (nombre)"],
            horizontal=True, key="map_metric_story"
        )
    with colB:
        animate = st.toggle("Animer par trimestre", value=True, help="Active l’animation par trimestre")

    if regional_hist.empty:
        st.info("Pas de données suffisantes pour la carte temporelle.")
    else:
        map_color_col = 'PART_ELECTRIQUE' if map_metric.startswith("Taux") else 'NB_RECHARGEABLES_TOTAL'
        plot_data = regional_hist.copy()
        if not animate:
            plot_data = plot_data[plot_data['TRIMESTRE'] == selected_period].copy()

        fig_map = px.choropleth_mapbox(
            plot_data,
            geojson=geojson,
            locations='DEPARTEMENT',
            featureidkey="properties.code",
            color=map_color_col,
            color_continuous_scale="Viridis" if map_color_col=='PART_ELECTRIQUE' else "Blues",
            mapbox_style="carto-positron",
            zoom=4.5, center={"lat": 46.6, "lon": 2.5},
            hover_data={'NB_VP':':,', 'NB_RECHARGEABLES_TOTAL':':,', 'PART_ELECTRIQUE':':.2f', 'LABEL':True},
            labels={'PART_ELECTRIQUE': 'Taux (%)', 'NB_RECHARGEABLES_TOTAL': "VE (nbre)"},
            animation_frame=('LABEL' if animate else None),
            title=("Évolution spatiale du parc électrique" if animate else f"Carte — {map_metric} ({selected_quarter_label})")
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=620)
        st.plotly_chart(fig_map, use_container_width=True)

    st.caption("Question: Où et quand la progression est‑elle la plus forte ? La diffusion est‑elle homogène ?")

    # Trends — time series (all filtered deps)
    st.subheader("📈 Évolution trimestrielle (périmètre départemental courant)")
    if df_hist_dept.empty:
        st.info("Pas assez de données pour tracer l'évolution.")
    else:
        temporal = df_hist_dept.groupby('TRIMESTRE', as_index=False).agg(
            NB_VP=('NB_VP','sum'),
            NB_RECHARGEABLES_TOTAL=('NB_RECHARGEABLES_TOTAL','sum')
        )
        temporal['PART_ELECTRIQUE'] = np.where(
            temporal['NB_VP']>0,
            temporal['NB_RECHARGEABLES_TOTAL']/temporal['NB_VP']*100, 0
        )
        temporal = temporal.sort_values('TRIMESTRE').copy()
        temporal['LABEL'] = temporal['TRIMESTRE'].apply(make_quarter_label)

        fig_trends = make_subplots(rows=2, cols=1,
                                   subplot_titles=("Parc total vs Véhicules électriques", "Taux d'adoption (%)"),
                                   specs=[[{}],[{}]])
        fig_trends.add_trace(go.Scatter(x=temporal['LABEL'], y=temporal['NB_VP'], name="Parc total (VP)",
                                        mode='lines+markers', line=dict(color='#1f77b4')), row=1, col=1)
        fig_trends.add_trace(go.Scatter(x=temporal['LABEL'], y=temporal['NB_RECHARGEABLES_TOTAL'], name="Véhicules électriques",
                                        mode='lines+markers', line=dict(color='#2ca02c')), row=1, col=1)
        fig_trends.add_trace(go.Scatter(x=temporal['LABEL'], y=temporal['PART_ELECTRIQUE'], name="Taux adoption (%)",
                                        mode='lines+markers', line=dict(color='#ff7f0e', width=3)), row=2, col=1)
        fig_trends.update_yaxes(title_text="Nombre (veh.)", row=1, col=1)
        fig_trends.update_yaxes(title_text="%", row=2, col=1)
        fig_trends.update_layout(height=580, showlegend=True, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_trends, use_container_width=True)

    # Growth (delta) map QoQ
    st.subheader("🚀 Croissance trimestrielle par département (pp)")
    df_curr_dep = df_current.groupby('DEPARTEMENT', as_index=False).agg(
        EV=('NB_RECHARGEABLES_TOTAL','sum'),
        VP=('NB_VP','sum')
    )
    df_curr_dep['TAUX'] = np.where(df_curr_dep['VP']>0, df_curr_dep['EV']/df_curr_dep['VP']*100, 0)
    df_prev_dep = df_prev.groupby('DEPARTEMENT', as_index=False).agg(
        EV_PREV=('NB_RECHARGEABLES_TOTAL','sum'),
        VP_PREV=('NB_VP','sum')
    )
    if not df_prev_dep.empty and not df_curr_dep.empty:
        growth = df_curr_dep.merge(df_prev_dep, on='DEPARTEMENT', how='left')
        rate_prev = np.where(growth['VP_PREV']>0, growth['EV_PREV']/growth['VP_PREV']*100, np.nan)
        growth['DELTA_PP'] = growth['TAUX'] - rate_prev
        fig_delta = px.choropleth_mapbox(
            growth, geojson=geojson, locations='DEPARTEMENT', featureidkey="properties.code",
            color='DELTA_PP', color_continuous_scale="RdYlGn", range_color=[-2, 2],
            mapbox_style="carto-positron", zoom=4.5, center={"lat": 46.6, "lon": 2.5},
            labels={'DELTA_PP':"Δ taux (pp) vs T-1"}, title="Variation trimestrielle du taux d’adoption (pp)"
        )
        fig_delta.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=520)
        st.plotly_chart(fig_delta, use_container_width=True)
        st.caption("Question: Quels départements tirent la croissance ce trimestre ?")
    else:
        st.info("Trimestre précédent indisponible pour la carte de croissance.")

# ============ 3) INSIGHTS ============
with tab_insights:
    st.markdown('<h2 class="section-header">Insights</h2>', unsafe_allow_html=True)
    st.markdown("> Faits saillants et réponses aux questions utilisateur.")
    # Leaders/laggards, concentration, contributors
    dept_summary = df_current.groupby('DEPARTEMENT', as_index=False).agg(
        EV=('NB_RECHARGEABLES_TOTAL','sum'),
        VP=('NB_VP','sum')
    )
    if not dept_summary.empty:
        dept_summary['TAUX'] = np.where(dept_summary['VP']>0, dept_summary['EV']/dept_summary['VP']*100, 0)
        lead = dept_summary.sort_values('TAUX', ascending=False).head(1)
        lag = dept_summary.sort_values('TAUX', ascending=True).head(1)
        top10_share = (dept_summary.sort_values('EV', ascending=False).head(10)['EV'].sum() /
                       max(1, dept_summary['EV'].sum())) * 100
    else:
        lead, lag, top10_share = None, None, 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Taux d’adoption (pondéré)", f"{weighted_rate:.2f}%",
                  delta=(f"{delta_pp:+.2f} pp" if delta_pp is not None else None),
                  help="Pondéré par le parc total")
    with c2:
        if lead is not None and not lead.empty:
            st.metric("Département leader (taux)", f"{lead.iloc[0]['DEPARTEMENT']}",
                      delta=f"{lead.iloc[0]['TAUX']:.2f}%")
        else:
            st.metric("Département leader (taux)", "—")
    with c3:
        st.metric("Concentration Top 10 (VE)", f"{top10_share:.1f}%",
                  help="Part du parc VE concentrée dans 10 départements")

    st.markdown("#### Qui contribue le plus à la hausse ce trimestre ?")
    contrib = None
    if not df_prev.empty:
        curr_dep = df_current.groupby('DEPARTEMENT', as_index=False)['NB_RECHARGEABLES_TOTAL'].sum().rename(columns={'NB_RECHARGEABLES_TOTAL':'EV'})
        prev_dep = df_prev.groupby('DEPARTEMENT', as_index=False)['NB_RECHARGEABLES_TOTAL'].sum().rename(columns={'NB_RECHARGEABLES_TOTAL':'EV_PREV'})
        contrib = curr_dep.merge(prev_dep, on='DEPARTEMENT', how='left').fillna({'EV_PREV':0})
        contrib['DELTA_EV'] = contrib['EV'] - contrib['EV_PREV']
        top_contrib = contrib.sort_values('DELTA_EV', ascending=False).head(12)
        fig_contrib = px.bar(top_contrib, x='DELTA_EV', y='DEPARTEMENT', orientation='h',
                             labels={'DELTA_EV':'Δ VE (nbre)', 'DEPARTEMENT':'Département'},
                             title="Top contributeurs à la hausse des VE (T vs T‑1)",
                             color_discrete_sequence=['#22c55e'])
        fig_contrib.update_layout(height=520, margin=dict(l=10,r=10,t=60,b=10))
        st.plotly_chart(fig_contrib, use_container_width=True)
    else:
        st.info("Trimestre précédent indisponible pour l’analyse des contributeurs.")

    st.markdown("#### Distribution et disparités (trimestre sélectionné)")
    colA, colB = st.columns(2)
    with colA:
        communes_rates = df_current.groupby('LIBGEO', as_index=False)['PART_ELECTRIQUE'].mean()
        if communes_rates.empty:
            st.info("Pas de données pour afficher la distribution.")
        else:
            fig_hist = px.histogram(
                communes_rates, x='PART_ELECTRIQUE', nbins=40, histnorm='percent',
                labels={'PART_ELECTRIQUE':"Taux d'adoption (%)"},
                title="Répartition des communes par taux d'adoption"
            )
            fig_hist.update_xaxes(ticksuffix="%", tickformat=".0f")
            fig_hist.update_yaxes(title_text="Part des communes (%)")
            fig_hist.add_vline(x=float(communes_rates['PART_ELECTRIQUE'].median()),
                               line_dash='dash', line_color='orange', annotation_text='Médiane', annotation_position="top")
            fig_hist.add_vline(x=float(communes_rates['PART_ELECTRIQUE'].mean()),
                               line_dash='dot', line_color='cyan', annotation_text='Moyenne', annotation_position="top")
            st.plotly_chart(fig_hist, use_container_width=True)
    with colB:
        dept_agg = df_current.groupby('DEPARTEMENT', as_index=False).agg(PARC=('NB_VP','sum'))
        top_dept = dept_agg.sort_values('PARC', ascending=False)['DEPARTEMENT'].head(12).tolist()
        communes_dept = (df_current[df_current['DEPARTEMENT'].isin(top_dept)]
                         .groupby(['DEPARTEMENT','LIBGEO'], as_index=False)['PART_ELECTRIQUE'].mean())
        if communes_dept.empty:
            st.info("Pas assez de données pour la variabilité par département.")
        else:
            fig_box = px.box(communes_dept, x='DEPARTEMENT', y='PART_ELECTRIQUE',
                             labels={'DEPARTEMENT':'Département', 'PART_ELECTRIQUE':"Taux d'adoption (%)"},
                             points=False, title="Dispersion des taux par département (top parc)")
            fig_box.update_yaxes(ticksuffix="%", tickformat=".0f")
            st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("#### En bref — ce qu’il faut retenir")
    bullets = [
        f"Taux pondéré actuel: {weighted_rate:.2f}%.",
        f"Variation vs T‑1: {(f'{delta_pp:+.2f} pp' if delta_pp is not None else 'n.d.')}.",
        f"Concentration: top‑10 départements = {top10_share:.1f}% du parc VE.",
    ]
    if lead is not None and not lead.empty and lag is not None and not lag.empty:
        bullets.append(f"Écart territorial: leader {lead.iloc[0]['DEPARTEMENT']} ({lead.iloc[0]['TAUX']:.2f}%) vs laggard {lag.iloc[0]['DEPARTEMENT']} ({lag.iloc[0]['TAUX']:.2f}%).")
    st.markdown("\n".join([f"- {b}" for b in bullets]))

# ============ 4) IMPLICATIONS ============
with tab_implications:
    st.markdown('<h2 class="section-header">Implications</h2>', unsafe_allow_html=True)
    st.markdown("> Traduction opérationnelle des constats.")
    # Simple rules-of-thumb based on insights
    recos = []
    if delta_pp is not None and delta_pp > 0:
        recos.append("Poursuivre l’effort: l’adoption progresse; renforcer les leviers qui fonctionnent (prime, ZFE, maillage IRVE).")
    else:
        recos.append("Relancer la dynamique: accélérer les incitations ciblées et lever les freins (infrastructures, information).")
    if total_ev > 0 and total_vp > 0 and weighted_rate < 10:
        recos.append("Priorité infrastructures: déploiement accéléré de bornes dans les zones à faible taux mais fort parc VP.")
    if total_ev > 0 and 'contrib' in locals() and contrib is not None and not contrib.empty:
        recos.append("Suivre les contributeurs: concentrer les efforts sur les départements à fort potentiel d’augmentation.")
    recos.append("Mesure continue: suivre trimestriellement les taux et la distribution pour détecter élargissement/resserrement des écarts.")
    st.markdown("\n".join([f"- {r}" for r in recos]))

    st.markdown("Bloc note:")
    st.markdown("""
- Audiences: décideurs publics, opérateurs d’IRVE, collectivités.
- Takeaways: carte d’évolution, top contributeurs, dispersion des taux.
- Prochaines étapes: ciblage territorial, expérimentation locale, évaluation d’impact.
""")

# ============ ANNEXES (méthodes, téléchargement) ============
with tab_appendix:
    st.markdown('<h2 class="section-header">Données & Méthodes</h2>', unsafe_allow_html=True)
    st.markdown("- Source: Data.gouv — voitures particulières par commune et type de recharge (trimestriel)")
    st.markdown("- Pipeline: ingestion → nettoyage → dérivations (ANNEE, TRIMESTRE, DEPARTEMENT) → filtrage → agrégations.")
    st.markdown("Hypothèses:")
    st.markdown("""
- Exclusion des libellés non communaux (Forains, ND, Non identifié).
- Taux d’adoption $= \\frac{EV}{VP} \\times 100$ borné à $[0, 100]$.
- Agrégations: moyenne du taux au niveau commune; sommes EV/VP au niveau commune/département.
""")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"- Lignes: {len(df):,}")
        st.write(f"- Communes uniques: {df['LIBGEO'].nunique():,}")
        st.write(f"- Période: {df['DATE_ARRETE'].min().strftime('%Y-%m-%d')} → {df['DATE_ARRETE'].max().strftime('%Y-%m-%d')}")
        st.write(f"- Années: {df['ANNEE'].min()}–{df['ANNEE'].max()} ({df['ANNEE'].nunique()} au total)")
    with col2:
        issues = []
        if df.isnull().sum().sum() > 0:
            issues.append("Valeurs manquantes présentes.")
        if (df['NB_RECHARGEABLES_TOTAL'] > df['NB_VP']).any():
            issues.append("Incohérences: rechargeables > total (lignes isolées).")
        if issues:
            for i in issues: st.warning(i)
        else:
            st.success("✅ Aucun problème critique détecté.")

    st.markdown("### 📥 Télécharger les données filtrées (trimestre sélectionné)")
    export_suffix = selected_quarter_label.replace(" ", "_")
    csv = df_current.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Télécharger CSV",
        data=csv,
        file_name=f"vehicules_electriques_{export_suffix}.csv",
        mime="text/csv"
    )