import os
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils import load_and_clean_data

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
/* --- Design tokens --- */
:root{
  --primary: #22c55e;         /* vert accent */
  --primary-600:#16a34a;
  --bg:#0b1220;               /* fond général (dark) */
  --surface:#0f172a;          /* cartes / onglets */
  --border: rgba(148,163,184,.18);
  --muted:#9aa4b2;
  --text:#e6e8eb;
}
html, body, [data-testid="stAppViewContainer"]{ background: var(--bg); }
* { font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial, "Noto Sans", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol"; }

/* --- Titres --- */
.main-header { font-size: 2.2rem; color: var(--text); text-align: center; margin: 0 0 1rem 0; }
.section-header { color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: .35rem; margin-top: 1rem; }

/* --- Onglets (pills) --- */
.stTabs [role="tablist"]{
  gap: .5rem; border: 0; margin: .25rem 0 1rem;
}
.stTabs [role="tab"]{
  padding: .5rem 1rem; border-radius: 999px;
  border: 1px solid var(--border); background: var(--surface);
  color: var(--text); opacity: .9; transition: all .15s ease;
}
.stTabs [role="tab"]:hover{ opacity: 1; border-color: rgba(255,255,255,.28); }
.stTabs [role="tab"][aria-selected="true"]{
  color:#fff; opacity: 1;
  background: linear-gradient(180deg, rgba(34,197,94,.18), rgba(34,197,94,.06));
  border-color: rgba(34,197,94,.55);
  box-shadow: 0 0 0 2px rgba(34,197,94,.18) inset;
}
/* retire le soulignement natif */
.stTabs [role="tablist"]::after{ display:none; }

/* --- KPI (st.metric) en cartes --- */
[data-testid="stMetric"]{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 14px;
}
[data-testid="stMetric"] [data-testid="stMetricLabel"]{
  color: var(--muted) !important; font-weight: 600;
}
[data-testid="stMetric"] [data-testid="stMetricValue"]{
  color: #ffffff !important; font-weight: 700;
}

/* --- Sidebar --- */
section[data-testid="stSidebar"]{
  background: #0a0f1a !important;
  border-right: 1px solid var(--border);
}

/* --- Liens & petits éléments --- */
a, .markdown-text-container a { color: var(--primary); }
.small { font-size: .9rem; color: var(--muted); }
</style>
""", unsafe_allow_html=True)

# --------------------------
# Chargement des données
# --------------------------
st.markdown('<h1 class="main-header">🚗⚡ La Transition Énergétique Automobile en France</h1>', unsafe_allow_html=True)

DATA_PATH = os.path.join("data", "voitures-par-commune-par-energie.csv")
df = load_and_clean_data(DATA_PATH)

if df is None or df.empty:
    st.error("❌ Impossible de charger les données. Vérifiez le fichier dans le dossier data/.")
    st.stop()

# --------------------------
# Filtres (sidebar)
# --------------------------
st.sidebar.markdown("## 🎛️ Filtres")

# Trimestre (un seul)
quarters_available = sorted(df['TRIMESTRE'].unique())
quarter_label_map = {q: f"T{int(q.quarter)} {int(q.year)}" for q in quarters_available}
quarter_labels = [quarter_label_map[q] for q in quarters_available]
selected_quarter_label = st.sidebar.selectbox(
    "📅 Trimestre d'analyse",
    options=quarter_labels,
    index=len(quarter_labels) - 1,
    help="Sélectionne un trimestre pour l'analyse courante (les tendances restent historiques).",
)
label_to_period = {v: k for k, v in quarter_label_map.items()}
selected_period = label_to_period[selected_quarter_label]

# Départements
departements = sorted(df['DEPARTEMENT'].unique())
departements_display = ["Tous"] + departements
selected_departements = st.sidebar.multiselect(
    "🗺️ Départements (codes INSEE)",
    options=departements_display,
    default=departements_display[0],
    help="Choisis un ou plusieurs départements. 'Tous' = France entière."
)

# Exclure DOM-TOM
exclude_domtom = st.sidebar.toggle(
    "Exclure DOM‑TOM (971, 972, 973, 974, 976, ...)",
    value=False
)
domtom = {"971", "972", "973", "974", "976", "975", "977", "978", "984", "986", "987", "988"}

if "Tous" in selected_departements:
    filtered_departements = [d for d in departements if (not exclude_domtom or d not in domtom)]
else:
    filtered_departements = [d for d in selected_departements if (not exclude_domtom or d not in domtom)]

# Seuil de parc minimal
min_vehicles = st.sidebar.slider(
    "🚗 Taille minimale du parc (VP)",
    min_value=0, max_value=int(df['NB_VP'].max()), value=100, step=50,
    help="Filtre les micro‑communes pour améliorer la lisibilité."
)

# --------------------------
# Données filtrées (périmètre courant)
# --------------------------
df_current = df[
    (df['TRIMESTRE'] == selected_period) &
    (df['DEPARTEMENT'].isin(filtered_departements)) &
    (df['NB_VP'] >= min_vehicles)
].copy()
df_current = df_current[(df_current['PART_ELECTRIQUE'] >= 0) & (df_current['PART_ELECTRIQUE'] <= 100)]

# --------------------------
# KPI globaux (périmètre courant)
# --------------------------
st.markdown('<h2 class="section-header">📊 Indicateurs Clés</h2>', unsafe_allow_html=True)

if df_current.empty:
    st.info("Aucune donnée pour ce périmètre. Modifiez les filtres.")
else:
    total_vp = int(df_current['NB_VP'].sum())
    total_ev = int(df_current['NB_RECHARGEABLES_TOTAL'].sum())
    weighted_rate = (total_ev / total_vp * 100) if total_vp > 0 else 0.0
    communes_count = int(df_current['LIBGEO'].nunique())

    # Trimestre précédent pour delta
    prev_period = selected_period - 1
    df_prev = df[
        (df['TRIMESTRE'] == prev_period) &
        (df['DEPARTEMENT'].isin(filtered_departements)) &
        (df['NB_VP'] >= min_vehicles)
    ]
    prev_total_vp = int(df_prev['NB_VP'].sum()) if not df_prev.empty else 0
    prev_total_ev = int(df_prev['NB_RECHARGEABLES_TOTAL'].sum()) if not df_prev.empty else 0
    prev_rate = (prev_total_ev / prev_total_vp * 100) if prev_total_vp > 0 else np.nan
    prev_communes = int(df_prev['LIBGEO'].nunique()) if not df_prev.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🚗 Parc total (VP)", f"{total_vp:,}",
                  delta=(f"{(total_vp - prev_total_vp):+,}" if prev_total_vp else None))
    with c2:
        st.metric("⚡ Véhicules électriques/rechargeables", f"{total_ev:,}",
                  delta=(f"{(total_ev - prev_total_ev):+,}" if prev_total_ev else None))
    with c3:
        delta_pp = None if np.isnan(prev_rate) else f"{(weighted_rate - prev_rate):+.2f} pp"
        st.metric("📈 Taux d'adoption pondéré", f"{weighted_rate:.2f}%", delta=delta_pp)
    with c4:
        st.metric("🏘️ Communes analysées", f"{communes_count:,}",
                  delta=(f"{(communes_count - prev_communes):+,}" if prev_communes else None))

# --------------------------
# Onglets
# --------------------------
tab_story, tab_explore, tab_trends, tab_data = st.tabs(
    ["🧭 Story", "🧪 Explore", "📈 Trends", "📚 Data & Methods"]
)

# ============ STORY ============
with tab_story:
    st.markdown("## Problème")
    st.markdown("- Comment évolue l’adoption des véhicules électriques en France et où sont les disparités territoriales ?")

    st.markdown("## Approche")
    st.markdown("- Données trimestrielles publiques (Data.gouv). Nettoyage, agrégations, indicateurs pondérés, visualisations interactives.")

    st.markdown("## Résultats clés")
    st.markdown(f"- Taux d’adoption pondéré (trimestre sélectionné): **{weighted_rate:.2f}%**")
    dept_summary = df_current.groupby('DEPARTEMENT', as_index=False).agg(EV=('NB_RECHARGEABLES_TOTAL','sum'),
                                                                         VP=('NB_VP','sum'))
    if not dept_summary.empty:
        dept_summary['TAUX'] = np.where(dept_summary['VP']>0, dept_summary['EV']/dept_summary['VP']*100, 0)
        top_depts = ", ".join(dept_summary.sort_values('TAUX', ascending=False).head(3)['DEPARTEMENT'])
        low_depts = ", ".join(dept_summary.sort_values('TAUX', ascending=True).head(3)['DEPARTEMENT'])
        st.markdown(f"- Départements en tête (taux): **{top_depts}**")
        st.markdown(f"- Départements en retard (taux): **{low_depts}**")

    st.markdown("## Implications")
    st.markdown("- Cibler en priorité les territoires à faible taux (infrastructures, incitations).")

    # === NEW: TL;DR et cartes d’insights ===
    st.markdown("### TL;DR — ce qu’il faut retenir ce trimestre")
    # Prépare quelques métriques narratives
    delta_pp = None if np.isnan(prev_rate) else (weighted_rate - prev_rate)
    dept_summary = df_current.groupby('DEPARTEMENT', as_index=False).agg(EV=('NB_RECHARGEABLES_TOTAL','sum'),
                                                                         VP=('NB_VP','sum'))
    if not dept_summary.empty:
        dept_summary['TAUX'] = np.where(dept_summary['VP']>0, dept_summary['EV']/dept_summary['VP']*100, 0)
        lead = dept_summary.sort_values('TAUX', ascending=False).head(1)
        lag  = dept_summary.sort_values('TAUX', ascending=True).head(1)
        top10_share = (dept_summary.sort_values('EV', ascending=False).head(10)['EV'].sum() /
                       max(1, dept_summary['EV'].sum())) * 100
    else:
        lead, lag, top10_share = None, None, 0

    colA, colB, colC = st.columns(3)
    with colA:
        if delta_pp is None:
            st.info("Évolution vs T-1 indisponible.")
        else:
            emoji = "🟢" if delta_pp >= 0 else "🔴"
            st.metric("Évolution du taux (pp vs T‑1)", f"{weighted_rate:.2f}%",
                      delta=f"{delta_pp:+.2f} pp", help="Différence de points de pourcentage vs trimestre précédent")
            st.caption(f"{emoji} Le taux progresse si delta > 0.")
    with colB:
        if lead is not None and not lead.empty:
            st.metric("Leader (taux)", f"{lead.iloc[0]['DEPARTEMENT']}",
                      delta=f"{lead.iloc[0]['TAUX']:.2f}%", help="Département au taux d’adoption le plus élevé")
        else:
            st.info("Leader indisponible.")
    with colC:
        st.metric("Concentration (Top 10 EV)", f"{top10_share:.1f}%",
                  help="Part des véhicules électriques concentrée dans les 10 départements les plus volumineux")

    st.markdown("— En bref:")
    bullets = [
        f"Taux pondéré actuel: {weighted_rate:.2f}%.",
        f"Communes couvertes: {communes_count:,}.",
        f"Volume EV: {total_ev:,} (parc total: {total_vp:,})."
    ]
    if delta_pp is not None:
        bullets.insert(1, f"Variation vs T-1: {delta_pp:+.2f} pp.")
    st.markdown("\n".join([f"- {b}" for b in bullets]))

# ============ EXPLORE ============
with tab_explore:
    st.caption("Vue instantanée du trimestre sélectionné: carte, classements et drill‑down par communes.")
    st.markdown("> Questions à explorer: Où sont les niveaux d’adoption les plus élevés/faibles ? Quelles communes tirent la moyenne vers le haut ou le bas ?")

    st.markdown("### 🗺️ Carte par département")

    # Choix métrique carte
    map_metric = st.radio(
        "Métrique de couleur",
        options=["Taux d'adoption (%)", "Véhicules électriques (nombre)"],
        index=0, horizontal=True, key="map_metric_radio",
        help="Couleur = taux (%) ou nombre de véhicules électriques."
    )
    map_color_col = 'PART_ELECTRIQUE' if map_metric.startswith("Taux") else 'NB_RECHARGEABLES_TOTAL'

    # Données agrégées département (période courante)
    regional = df_current.groupby('DEPARTEMENT', as_index=False).agg(
        NB_VP=('NB_VP','sum'),
        NB_RECHARGEABLES_TOTAL=('NB_RECHARGEABLES_TOTAL','sum')
    )
    regional['PART_ELECTRIQUE'] = np.where(
        regional['NB_VP']>0,
        regional['NB_RECHARGEABLES_TOTAL']/regional['NB_VP']*100,
        0
    )

    # Carte
    with st.spinner("Chargement de la carte..."):
        geojson_url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
        response = requests.get(geojson_url, timeout=20)
        departements_geojson = response.json()

    if regional.empty:
        st.info("Pas de données pour afficher la carte avec les filtres courants.")
    else:
        fig_map = px.choropleth_mapbox(
            regional,
            geojson=departements_geojson,
            locations='DEPARTEMENT',
            featureidkey="properties.code",
            color=map_color_col,
            color_continuous_scale="Viridis" if map_color_col=='PART_ELECTRIQUE' else "Blues",
            labels={'PART_ELECTRIQUE': 'Taux adoption (%)', 'NB_RECHARGEABLES_TOTAL': "Véhicules électriques"},
            mapbox_style="carto-positron",
            zoom=4.5, center={"lat": 46.6, "lon": 2.5},
            title=f"Carte — {map_metric}"
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=700)
        st.plotly_chart(fig_map, use_container_width=True)

    st.markdown("### 🏆 Top / 📉 Bottom des communes")
    st.caption("Astuce: compare le Top et le Bottom avec la même métrique pour voir la dispersion.")
    c1, c2 = st.columns([1,1])
    with c1:
        metric_choice = st.radio(
            "Métrique de classement",
            options=["Taux d'adoption (%)", "Véhicules électriques (nombre)"],
            index=0, key="rank_metric_radio",
            help="Taux (%) = part électrique; Nombre = volume de véhicules électriques"
        )
    with c2:
        top_n = st.slider("Nombre de communes", min_value=5, max_value=30, value=10, step=5, key="rank_topn")

    # Agrégation commune (période courante)
    communes_grouped = df_current.groupby('LIBGEO', as_index=False).agg(
        TAUX=('PART_ELECTRIQUE','mean'),
        NB_RECHARGEABLES_TOTAL=('NB_RECHARGEABLES_TOTAL','sum'),
        NB_VP=('NB_VP','sum')
    )
    sort_col = 'TAUX' if metric_choice.startswith("Taux") else 'NB_RECHARGEABLES_TOTAL'

    colL, colR = st.columns(2)
    with colL:
        st.markdown("#### 🏆 Top")
        top_communes = communes_grouped.nlargest(top_n, sort_col)
        fig_top = px.bar(
            top_communes,
            x=('TAUX' if sort_col=='TAUX' else 'NB_RECHARGEABLES_TOTAL'),
            y='LIBGEO', orientation='h',
            color='NB_RECHARGEABLES_TOTAL', color_continuous_scale='Greens',
            labels={'TAUX': "Taux d'adoption (%)", 'NB_RECHARGEABLES_TOTAL': "Véhicules électriques", 'LIBGEO': 'Commune'},
            title=f"Top {top_n} — {metric_choice}"
        )
        if sort_col=='TAUX':
            fig_top.update_xaxes(tickformat=".2f", ticksuffix="%", title_text="Taux d'adoption (%)")
            fig_top.update_traces(text=top_communes['TAUX'].map(lambda v: f"{v:.2f}%"), textposition="outside", cliponaxis=False)
        else:
            fig_top.update_xaxes(title_text="Véhicules électriques (nombre)")
            fig_top.update_traces(text=top_communes['NB_RECHARGEABLES_TOTAL'].map(lambda v: f"{int(v):,}"), textposition="outside", cliponaxis=False)
        fig_top.update_layout(height=420, margin=dict(l=10,r=10,t=60,b=10))
        st.plotly_chart(fig_top, use_container_width=True)

    with colR:
        st.markdown("#### 📉 Bottom")
        if sort_col == 'TAUX':
            bottom_pos = communes_grouped[communes_grouped['TAUX'] > 0].nsmallest(top_n, 'TAUX')
            if len(bottom_pos) < top_n:
                needed = top_n - len(bottom_pos)
                zeros = communes_grouped[communes_grouped['TAUX'] == 0].nlargest(needed, 'NB_VP')
                bottom_communes = pd.concat([bottom_pos, zeros], ignore_index=True)
            else:
                bottom_communes = bottom_pos
            x_col = 'TAUX'
        else:
            bottom_communes = communes_grouped.nsmallest(top_n, 'NB_RECHARGEABLES_TOTAL')
            x_col = 'NB_RECHARGEABLES_TOTAL'

        bottom_communes = bottom_communes.sort_values(x_col, ascending=True)
        fig_bottom = px.bar(
            bottom_communes, x=x_col, y='LIBGEO', orientation='h',
            color='NB_VP', color_continuous_scale='Reds',
            labels={'TAUX': "Taux d'adoption (%)", 'NB_RECHARGEABLES_TOTAL': "Véhicules électriques", 'NB_VP': 'Parc total', 'LIBGEO': 'Commune'},
            title=f"Bottom {top_n} — {metric_choice}"
        )
        if x_col == 'TAUX':
            max_x = float(bottom_communes['TAUX'].max() or 0)
            pad = max(0.05, max_x * 0.25)
            fig_bottom.update_xaxes(range=[0, max_x + pad], tickformat=".2f", ticksuffix="%", title_text="Taux d'adoption (%)")
            fig_bottom.update_traces(text=bottom_communes['TAUX'].map(lambda v: f"{v:.2f}%"), textposition="outside", cliponaxis=False)
        else:
            fig_bottom.update_xaxes(title_text="Véhicules électriques (nombre)")
            fig_bottom.update_traces(text=bottom_communes['NB_RECHARGEABLES_TOTAL'].map(lambda v: f"{int(v):,}"), textposition="outside", cliponaxis=False)
        fig_bottom.update_layout(height=420, margin=dict(l=10,r=10,t=60,b=10))
        st.plotly_chart(fig_bottom, use_container_width=True)

    st.markdown("### 🌳 Communes d’un département")
    st.caption("Choisis un département pour détailler ses communes (barres ou treemap).")
    eligible_depts = filtered_departements
    if not eligible_depts:
        st.info("Aucun département disponible avec les filtres courants.")
    else:
        if len(eligible_depts) == 1:
            selected_dept = eligible_depts[0]
        else:
            selected_dept = st.selectbox("Choisissez un département", options=eligible_depts, key="dept_for_communes_view")

        communes_dept = (
            df_current[df_current['DEPARTEMENT'] == selected_dept]
            .groupby('LIBGEO', as_index=False)
            .agg(EV=('NB_RECHARGEABLES_TOTAL','sum'),
                 PARC=('NB_VP','sum'),
                 TAUX=('PART_ELECTRIQUE','mean'))
        )

        if communes_dept.empty:
            st.warning(f"Aucune commune à afficher pour le département {selected_dept}.")
        else:
            viz_type = st.radio("Vue", ["Barres classées", "Treemap"], index=0, horizontal=True, key="communes_view_radio")
            if viz_type == "Barres classées":
                colA, colB = st.columns(2)
                with colA:
                    sort_metric = st.selectbox("Trier par", ["Taux d'adoption (%)", "Véhicules électriques (nombre)"], index=0, key="communes_sort_metric")
                with colB:
                    top_n_communes = st.slider("Nombre de communes", 5, min(50, len(communes_dept)), min(20, len(communes_dept)), 5, key="communes_topn")

                if sort_metric.startswith("Taux"):
                    data_plot = communes_dept.sort_values("TAUX", ascending=False).head(top_n_communes)
                    x_col = "TAUX"
                else:
                    data_plot = communes_dept.sort_values("EV", ascending=False).head(top_n_communes)
                    x_col = "EV"

                fig_bar = px.bar(
                    data_plot, x=x_col, y="LIBGEO", orientation="h",
                    color="TAUX", color_continuous_scale="RdYlGn",
                    labels={"LIBGEO":"Commune","TAUX":"Taux d'adoption (%)","EV":"Véhicules électriques"},
                    title=f"Département {selected_dept} — {sort_metric} (top {top_n_communes})"
                )
                if x_col == "TAUX":
                    fig_bar.update_xaxes(tickformat=".2f", ticksuffix="%", title_text="Taux d'adoption (%)")
                    fig_bar.update_traces(text=data_plot["TAUX"].map(lambda v: f"{v:.2f}%"), textposition="outside", cliponaxis=False)
                else:
                    fig_bar.update_xaxes(title_text="Véhicules électriques (nombre)")
                    fig_bar.update_traces(text=data_plot["EV"].map(lambda v: f"{int(v):,}"), textposition="outside", cliponaxis=False)
                fig_bar.update_layout(height=650, margin=dict(l=10, r=10, t=60, b=10))
                st.plotly_chart(fig_bar, use_container_width=True)

            else:
                vals = communes_dept["TAUX"].dropna().to_numpy()
                if vals.size >= 2:
                    q5, q95 = np.nanpercentile(vals, [5, 95])
                else:
                    q5 = float(communes_dept["TAUX"].min() if len(communes_dept) else 0.0)
                    q95 = float(communes_dept["TAUX"].max() if len(communes_dept) else 1.0)
                if q5 == q95:
                    q5, q95 = 0.0, max(1.0, float(q95))

                fig_communes = px.treemap(
                    communes_dept,
                    path=[px.Constant(f"Département {selected_dept}"), "LIBGEO"],
                    values="EV", color="TAUX",
                    color_continuous_scale="RdYlGn",
                    hover_data={"EV":":,", "PARC":":,", "TAUX":":.2f"},
                    title=None
                )
                fig_communes.update_coloraxes(
                    cmin=q5, cmax=q95,
                    colorbar=dict(title="Taux d'adoption (%)", tickformat=".2f")
                )
                fig_communes.update_traces(
                    hovertemplate="<b>%{label}</b><br>Taux: %{color:.2f}%<br>EV: %{value:,}<br>Parc: %{customdata[1]:,}<extra></extra>",
                    textinfo="label"
                )
                fig_communes.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=650)
                st.subheader(f"Département {selected_dept} — taille = EV, couleur = taux")
                st.plotly_chart(fig_communes, use_container_width=True)

# ============ TRENDS ============
with tab_trends:
    st.caption("Évolution dans le temps sur les départements filtrés + variations T vs T‑1 et distribution.")
    st.markdown("> Questions à explorer: Le taux accélère‑t‑il ? Quels territoires progressent le plus ce trimestre ? La distribution s’étale ou se resserre ?")
    st.markdown("### 📈 Évolution trimestrielle (périmètre départemental courant)")
    # Base historique sur les départements filtrés (pas de filtre sur le trimestre)
    df_hist = df[(df['DEPARTEMENT'].isin(filtered_departements)) & (df['NB_VP'] >= min_vehicles)].copy()
    if df_hist.empty:
        st.info("Pas assez de données pour tracer l'évolution.")
    else:
        temporal = df_hist.groupby('TRIMESTRE', as_index=False).agg(
            NB_VP=('NB_VP','sum'),
            NB_RECHARGEABLES_TOTAL=('NB_RECHARGEABLES_TOTAL','sum')
        )
        temporal['PART_ELECTRIQUE'] = np.where(
            temporal['NB_VP']>0,
            temporal['NB_RECHARGEABLES_TOTAL']/temporal['NB_VP']*100, 0
        )
        temporal = temporal.sort_values('TRIMESTRE').copy()
        temporal['LABEL'] = temporal['TRIMESTRE'].apply(lambda p: f"T{int(p.quarter)} {int(p.year)}")

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
        fig_trends.update_layout(height=600, showlegend=True, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_trends, use_container_width=True)

    st.markdown("### 🚀 Variations trimestrielles (Top hausses / baisses)")
    df_prev_sel = df[
        (df['TRIMESTRE'] == (selected_period - 1)) &
        (df['DEPARTEMENT'].isin(filtered_departements)) &
        (df['NB_VP'] >= min_vehicles)
    ].copy()
    curr_communes = df_current.groupby('LIBGEO', as_index=False).agg(TAUX=('PART_ELECTRIQUE','mean'))
    prev_communes = df_prev_sel.groupby('LIBGEO', as_index=False).agg(TAUX_PREV=('PART_ELECTRIQUE','mean'))
    delta = curr_communes.merge(prev_communes, on='LIBGEO', how='left').dropna(subset=['TAUX_PREV'])

    if delta.empty:
        st.info("Pas de trimestre précédent disponible pour comparer.")
    else:
        delta['DELTA_PP'] = delta['TAUX'] - delta['TAUX_PREV']
        up = delta.sort_values('DELTA_PP', ascending=False).head(10)
        down = delta.sort_values('DELTA_PP', ascending=True).head(10)

        c1, c2 = st.columns(2)
        with c1:
            fig_up = px.bar(up, x='DELTA_PP', y='LIBGEO', orientation='h',
                            labels={'DELTA_PP':'Variation (pp)', 'LIBGEO':'Commune'},
                            title='Top 10 hausses (pp vs T-1)',
                            color_discrete_sequence=['#2ca02c'])
            fig_up.update_xaxes(tickformat=".2f")
            st.plotly_chart(fig_up, use_container_width=True)
        with c2:
            fig_down = px.bar(down, x='DELTA_PP', y='LIBGEO', orientation='h',
                              labels={'DELTA_PP':'Variation (pp)', 'LIBGEO':'Commune'},
                              title='Top 10 baisses (pp vs T-1)',
                              color_discrete_sequence=['#e45756'])
            fig_down.update_xaxes(tickformat=".2f")
            st.plotly_chart(fig_down, use_container_width=True)

    st.markdown("### 📊 Distribution et variabilité (trimestre sélectionné)")
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
                             points=False, title="Distribution des taux par département (top parc)")
            fig_box.update_yaxes(ticksuffix="%", tickformat=".0f")
            st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("### 📐 Concentration du parc électrique (Lorenz)")
    ev_by_commune = df_current.groupby('LIBGEO', as_index=False)['NB_RECHARGEABLES_TOTAL'].sum()
    if ev_by_commune['NB_RECHARGEABLES_TOTAL'].sum() > 0:
        ev_sorted = ev_by_commune.sort_values('NB_RECHARGEABLES_TOTAL')
        ev_sorted['cum_communes'] = np.arange(1, len(ev_sorted)+1)/len(ev_sorted)
        ev_sorted['cum_ev'] = ev_sorted['NB_RECHARGEABLES_TOTAL'].cumsum()/ev_sorted['NB_RECHARGEABLES_TOTAL'].sum()
        fig_lorenz = go.Figure()
        fig_lorenz.add_trace(go.Scatter(x=ev_sorted['cum_communes'], y=ev_sorted['cum_ev'],
                                        mode='lines', name='Lorenz', line=dict(color='#1f77b4', width=3)))
        fig_lorenz.add_trace(go.Scatter(x=[0,1], y=[0,1], mode='lines', name='Égalité parfaite',
                                        line=dict(color='gray', dash='dash')))
        fig_lorenz.update_layout(
            xaxis_title="Part des communes", yaxis_title="Part cumulée des véhicules électriques",
            yaxis_tickformat=".0%", xaxis_tickformat=".0%", height=420, margin=dict(l=10,r=10,t=40,b=10)
        )
        st.plotly_chart(fig_lorenz, use_container_width=True)
    else:
        st.info("Aucune donnée EV pour tracer la courbe de Lorenz.")

# ============ DATA & METHODS ============
with tab_data:
    st.markdown("### 📚 Source des données")
    st.markdown("- Jeu: Voitures particulières immatriculées par commune et par type de recharge (trimestriel)")
    st.markdown("- Portail: https://www.data.gouv.fr/datasets/voitures-particulieres-immatriculees-par-commune-et-par-type-de-recharge-jeu-de-donnees-aaadata/")

    st.markdown("### 🧼 Nettoyage et hypothèses")
    st.markdown("""
- Exclusion des libellés non communaux (Forains, ND, Non identifié).
- Taux d’adoption = (EV/VP) × 100, borné à [0, 100].
- Agrégations: moyenne du taux par commune; sommes EV/VP par commune/département.
- Colonnes dérivées: ANNEE, TRIMESTRE, DEPARTEMENT.
    """)

    st.markdown("### 🧪 Résumé et contrôle qualité (ensemble complet)")
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
            for i in issues:
                st.warning(i)
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