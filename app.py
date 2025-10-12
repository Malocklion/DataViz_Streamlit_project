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
""", unsafe_allow_html=True)

# --------------------------
# Titre
# --------------------------
st.markdown('<h1 class="main-header">🚗⚡ La Transition Énergétique Automobile en France</h1>', unsafe_allow_html=True)

# --------------------------
# Données
# --------------------------
DATA_PATH = os.path.join("data", "voitures-par-commune-par-energie.csv")
df = load_and_clean_data(DATA_PATH)
if df is None or df.empty:
    st.error("❌ Impossible de charger les données. Vérifiez le fichier dans le dossier data/.")
    st.stop()

# --------------------------
# Filtres (sidebar)
# --------------------------
st.sidebar.markdown("## 🎛️ Filtres")

# Trimestre unique
quarters_available = sorted(df['TRIMESTRE'].unique())
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
departements = sorted(df['DEPARTEMENT'].unique())
departements_display = ["Tous"] + departements
selected_departements = st.sidebar.multiselect(
    "🗺️ Départements (codes INSEE)",
    options=departements_display,
    default=departements_display[0],
    help="Choisis un ou plusieurs départements. 'Tous' = France entière."
)

# DOM-TOM
exclude_domtom = st.sidebar.toggle("Exclure DOM‑TOM (971, 972, 973, 974, 976, ...)", value=False)
domtom = {"971","972","973","974","976","975","977","978","984","986","987","988"}
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
# Périmètre courant + T-1 (calculs globaux)
# --------------------------
df_current = df[
    (df['TRIMESTRE'] == selected_period) &
    (df['DEPARTEMENT'].isin(filtered_departements)) &
    (df['NB_VP'] >= min_vehicles)
].copy()
df_current = df_current[(df_current['PART_ELECTRIQUE'] >= 0) & (df_current['PART_ELECTRIQUE'] <= 100)]

prev_period = selected_period - 1
df_prev = df[
    (df['TRIMESTRE'] == prev_period) &
    (df['DEPARTEMENT'].isin(filtered_departements)) &
    (df['NB_VP'] >= min_vehicles)
].copy()

total_vp = int(df_current['NB_VP'].sum()) if not df_current.empty else 0
total_ev = int(df_current['NB_RECHARGEABLES_TOTAL'].sum()) if not df_current.empty else 0
weighted_rate = (total_ev / total_vp * 100) if total_vp > 0 else 0.0
communes_count = int(df_current['LIBGEO'].nunique()) if not df_current.empty else 0

prev_total_vp = int(df_prev['NB_VP'].sum()) if not df_prev.empty else 0
prev_total_ev = int(df_prev['NB_RECHARGEABLES_TOTAL'].sum()) if not df_prev.empty else 0
prev_rate = (prev_total_ev / prev_total_vp * 100) if prev_total_vp > 0 else np.nan
delta_pp_value = None if np.isnan(prev_rate) else (weighted_rate - prev_rate)

# --------------------------
# KPI globaux (photo du trimestre)
# --------------------------
st.markdown('<h2 class="section-header">📊 Indicateurs clés (photo du trimestre)</h2>', unsafe_allow_html=True)
if df_current.empty:
    st.info("Aucune donnée pour ce périmètre. Modifiez les filtres.")
else:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🚗 Parc total (VP)", f"{total_vp:,}",
                  delta=(f"{(total_vp - prev_total_vp):+,}" if prev_total_vp else None))
    with c2:
        st.metric("⚡ Véhicules électriques/rechargeables", f"{total_ev:,}",
                  delta=(f"{(total_ev - prev_total_ev):+,}" if prev_total_ev else None))
    with c3:
        st.metric("📈 Taux d'adoption pondéré", f"{weighted_rate:.2f}%",
                  delta=(f"{delta_pp_value:+.2f} %" if delta_pp_value is not None else None))
    with c4:
        prev_communes = int(df_prev['LIBGEO'].nunique()) if not df_prev.empty else 0
        st.metric("🏘️ Communes analysées", f"{communes_count:,}",
                  delta=(f"{(communes_count - prev_communes):+,}" if prev_communes else None))

# --------------------------
# Onglets narratifs
# --------------------------
tab_problem, tab_analysis, tab_insights, tab_implications, tab_data = st.tabs(
    ["🧭 Problem", "🧪 Analysis", "💡 Insights", "🎯 Implications", "📚 Data & Methods"]
)

# ============ 1) PROBLEM ============
with tab_problem:
    st.markdown("## Contexte")
    st.markdown("La transition écologique du secteur automobile est un enjeu majeur en France, où le transport représente près de 30 % des émissions de gaz à effet de serre. Depuis plusieurs années, les politiques publiques encouragent l’adoption de véhicules à faibles émissions, notamment électriques et hybrides, à travers des bonus écologiques, la mise en place de zones à faibles émissions (ZFE) et des investissements dans les infrastructures de recharge. Cependant, la vitesse d’adoption de ces véhicules n’est pas homogène : elle varie fortement selon les territoires, le niveau de revenu moyen, ou encore la densité des bornes de recharge.")
    
    st.markdown("## Problème")
    st.markdown("- Comment la transition vers les véhicules électriques se traduit-elle à l’échelle territoriale en France, et quelles disparités révèle-t-elle entre les communes ?")
    
    st.markdown("## Enjeux actuels")
    st.markdown("""
La décarbonation du transport routier s’inscrit dans la trajectoire européenne visant à mettre fin aux ventes de véhicules thermiques neufs d’ici 2035. Réduire rapidement les émissions de gaz à effet de serre et les polluants locaux, notamment dans les zones denses, constitue un enjeu à la fois sanitaire et climatique. Si l’adoption du véhicule électrique progresse, elle demeure très contrastée selon les territoires et les profils d’usagers.

Au-delà de la dimension environnementale, la question de l’équité territoriale est essentielle : il s’agit d’éviter un décrochage durable des zones rurales et périurbaines face aux grandes métropoles. Le déploiement des infrastructures de recharge (IRVE), la capacité du réseau électrique, les distances parcourues, le pouvoir d’achat et l’accompagnement aux nouveaux usages (information, médiation, services) sont autant de leviers déterminants.

Enfin, le pilotage public doit viser une allocation optimale des ressources : identifier les territoires à fort parc automobile mais à faible taux d’électrification, articuler les investissements IRVE et les zones à faibles émissions (ZFE) avec les dispositifs d’aide, et assurer un suivi régulier de la dynamique territoriale pour ajuster les politiques en temps réel.  
Ce tableau de bord a précisément pour ambition d’éclairer ces décisions stratégiques.
""")


# ============ 2) ANALYSIS ============
with tab_analysis:
    st.markdown("## Analyse")
    st.caption("On examine la répartition spatiale et l’évolution temporelle pour comprendre le rythme d’adoption.")

    # --- Carte par département (photo du trimestre)
    st.markdown("### 🗺️ Carte par département")
    map_metric = st.radio(
        "Métrique de couleur",
        options=["Taux d'adoption (%)", "Véhicules électriques (nombre)"],
        index=0, horizontal=True, key="map_metric_radio",
        help="Couleur = taux (%) ou nombre de véhicules électriques."
    )
    map_color_col = 'PART_ELECTRIQUE' if map_metric.startswith("Taux") else 'NB_RECHARGEABLES_TOTAL'

    # Slider de trimestre pour la carte uniquement
    map_quarter_label = st.select_slider(
        "Trimestre de la carte",
        options=quarter_labels,
        value=selected_quarter_label,
        help="Glisse pour changer le trimestre affiché sur la carte."
    )
    map_period = label_to_period[map_quarter_label]

    # Données de la carte basées sur le trimestre du slider
    df_map = df[
        (df['TRIMESTRE'] == map_period) &
        (df['DEPARTEMENT'].isin(filtered_departements)) &
        (df['NB_VP'] >= min_vehicles)
    ].copy()

    regional = df_map.groupby('DEPARTEMENT', as_index=False).agg(
         NB_VP=('NB_VP','sum'),
         NB_RECHARGEABLES_TOTAL=('NB_RECHARGEABLES_TOTAL','sum')
     )
    regional['PART_ELECTRIQUE'] = np.where(
        regional['NB_VP']>0, regional['NB_RECHARGEABLES_TOTAL']/regional['NB_VP']*100, 0
    )

    with st.spinner("Chargement de la carte..."):
        geojson_url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
        response = requests.get(geojson_url, timeout=20)
        departements_geojson = response.json()

    if regional.empty:
        st.info("Pas de données pour afficher la carte avec les filtres courants.")
    else:
        fig_map = px.choropleth_mapbox(
            regional, geojson=departements_geojson, locations='DEPARTEMENT', featureidkey="properties.code",
            color=map_color_col, color_continuous_scale="Viridis" if map_color_col=='PART_ELECTRIQUE' else "Blues",
            labels={'PART_ELECTRIQUE':'Taux adoption (%)', 'NB_RECHARGEABLES_TOTAL':"Véhicules électriques"},
            mapbox_style="carto-positron", zoom=4.5, center={"lat":46.6,"lon":2.5},
            title=f"Carte — {map_metric} ({map_quarter_label})"
        )
        fig_map.update_layout(margin={"r":0,"t":40,"l":0,"b":0}, height=700)
        st.plotly_chart(fig_map, use_container_width=True)

        # Paragraphe de lecture (hausse + concentration urbaine)
        rate_map = (regional['NB_RECHARGEABLES_TOTAL'].sum() / regional['NB_VP'].sum() * 100) if regional['NB_VP'].sum() > 0 else 0.0
        df_map_prev = df[
            (df['TRIMESTRE'] == (map_period - 1)) &
            (df['DEPARTEMENT'].isin(filtered_departements)) &
            (df['NB_VP'] >= min_vehicles)
        ]
        if not df_map_prev.empty:
            prev_ev = df_map_prev['NB_RECHARGEABLES_TOTAL'].sum()
            prev_vp = df_map_prev['NB_VP'].sum()
            prev_rate_map = (prev_ev / prev_vp * 100) if prev_vp > 0 else np.nan
            delta_map_pp = None if np.isnan(prev_rate_map) else (rate_map - prev_rate_map)
        else:
            delta_map_pp = None

        top10_share_map = (
            regional.nlargest(10, 'NB_RECHARGEABLES_TOTAL')['NB_RECHARGEABLES_TOTAL'].sum()
            / max(1, regional['NB_RECHARGEABLES_TOTAL'].sum())
        ) * 100

        st.markdown(
            "Bien que le taux d’adoption progresse trimestre après trimestre"
            + f", il reste très concentré: les 10 départements les plus dotés regroupent ~{top10_share_map:.1f}% du parc électrique observé. "
              "Globalement, cette tendance est surtout menée par les grandes métropoles."
        )
    st.caption("Question: Où sont les niveaux d’adoption les plus élevés/faibles ?")

    # --- Séries temporelles (historique des départements filtrés)
    st.markdown("### 📈 Évolution trimestrielle")
    df_hist = df[(df['DEPARTEMENT'].isin(filtered_departements)) & (df['NB_VP'] >= min_vehicles)].copy()
    if df_hist.empty:
        st.info("Pas assez de données pour tracer l'évolution.")
    else:
        temporal = df_hist.groupby('TRIMESTRE', as_index=False).agg(
            NB_VP=('NB_VP','sum'),
            NB_RECHARGEABLES_TOTAL=('NB_RECHARGEABLES_TOTAL','sum')
        )
        temporal['PART_ELECTRIQUE'] = np.where(
            temporal['NB_VP']>0, temporal['NB_RECHARGEABLES_TOTAL']/temporal['NB_VP']*100, 0
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

        # Paragraphe de lecture (analyse début → fin)
        if len(temporal) >= 2:
            start_label = str(temporal['LABEL'].iloc[0])
            end_label   = str(temporal['LABEL'].iloc[-1])

            rate_start = float(temporal['PART_ELECTRIQUE'].iloc[0])
            rate_end   = float(temporal['PART_ELECTRIQUE'].iloc[-1])
            delta_rate_pp = rate_end - rate_start

            ev_start = float(temporal['NB_RECHARGEABLES_TOTAL'].iloc[0])
            ev_end   = float(temporal['NB_RECHARGEABLES_TOTAL'].iloc[-1])
            vp_start = float(temporal['NB_VP'].iloc[0])
            vp_end   = float(temporal['NB_VP'].iloc[-1])

            ev_abs   = ev_end - ev_start
            vp_abs   = vp_end - vp_start
            ev_pct   = (ev_end/ev_start - 1)*100 if ev_start > 0 else np.nan
            vp_pct   = (vp_end/vp_start - 1)*100 if vp_start > 0 else np.nan

            n_quarters = max(1, len(temporal) - 1)
            n_years = n_quarters / 4.0
            ev_cagr = (((ev_end/ev_start)**(1/n_years) - 1)*100) if (ev_start > 0 and n_years > 0) else np.nan

            st.markdown(
                f"Du {start_label} au {end_label}, le taux d’adoption passe de {rate_start:.2f}% à {rate_end:.2f}% "
                f". Le nombre de véhicules électriques progresse de "
                f"{ev_abs:+,.0f}, soit {'' if np.isnan(ev_pct) else f'{ev_pct:+.1f}%'}"
                f". Sur la même période, le parc total évolue de {vp_abs:+,.0f}"
            f"{'' if np.isnan(vp_pct) else f' ({vp_pct:+.1f}%)'}. "
                f" En clair un progression est visible  sur toute la période, avec un gain cumulé de {delta_rate_pp:.2f} %."
            )
        else:
            st.markdown("Série trop courte pour une analyse début → fin.")
    st.caption("Question: La dynamique s’accélère‑t‑elle ou se tasse‑t‑elle ?")

    # --- Variations T vs T‑1 (communes)
    st.markdown("### 🚀 Variations trimestrielles (Top hausses / baisses)")
    df_prev_sel = df_prev.copy()
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
            st.caption("Communes avec la plus forte hausse du taux (Δ % vs T‑1).")
            fig_up = px.bar(up, x='DELTA_PP', y='LIBGEO', orientation='h',
                            labels={'DELTA_PP':'Variation (%)', 'LIBGEO':'Commune'},
                            title='Top 10 hausses (%) vs T-1',
                            color_discrete_sequence=['#2ca02c'])
            fig_up.update_xaxes(tickformat=".2f")
            st.plotly_chart(fig_up, use_container_width=True)
        with c2:
            st.caption("Communes avec la plus forte baisse du taux (Δ % vs T‑1).")
            fig_down = px.bar(down, x='DELTA_PP', y='LIBGEO', orientation='h',
                              labels={'DELTA_PP':'Variation (%)', 'LIBGEO':'Commune'},
                              title='Top 10 baisses (%) vs T-1',
                              color_discrete_sequence=['#e45756'])
            fig_down.update_xaxes(tickformat=".2f")
            st.plotly_chart(fig_down, use_container_width=True)

# ============ 3) INSIGHTS ============
with tab_insights:
    st.markdown("## Insights")
    st.caption("On répond: qui est en tête/en retard et quelles communes expliquent les écarts ?")

    # --- Top/Bottom communes
    st.markdown("### 🏆 Top / 📉 Bottom des communes")
    st.caption("Comparer Top et Bottom avec la même métrique pour évaluer la dispersion.")
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

    # --- Focus communes d’un département
    st.markdown("### 🌳 Communes d’un département")
    st.caption("Choisis un département filtré pour détailler ses communes (barres classées).")
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
            # Uniquement barres classées (treemap retiré)
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

# ============ 4) IMPLICATIONS ============
with tab_implications:
    st.markdown("## Implications")
    st.caption("Traduction opérationnelle des constats — où agir, avec quoi et pourquoi.")

    # Synthèse narrative (paragraphes)
    # Résumés départementaux pour les comparaisons
    _dept = df_current.groupby('DEPARTEMENT', as_index=False).agg(
        EV=('NB_RECHARGEABLES_TOTAL', 'sum'),
        VP=('NB_VP', 'sum')
    )
    if not _dept.empty:
        _dept['TAUX'] = np.where(_dept['VP'] > 0, _dept['EV']/_dept['VP']*100, 0)
        _lead = _dept.sort_values('TAUX', ascending=False).head(1)
        _lag  = _dept.sort_values('TAUX', ascending=True).head(1)
        _top10_share = (_dept.sort_values('EV', ascending=False).head(10)['EV'].sum() /
                        max(1, _dept['EV'].sum())) * 100
    else:
        _lead = _lag = pd.DataFrame()
        _top10_share = 0.0

    # Paragraphe 1 — dynamique générale
    if delta_pp_value is None:
        p1 = f"Le taux d’adoption des véhicules électriques s’établit à {weighted_rate:.2f}% sur le périmètre sélectionné. Cette photographie renseigne le niveau atteint ce trimestre, sans comparaison directe au trimestre précédent."
    elif delta_pp_value > 0:
        p1 = f"Le taux d’adoption s’établit à {weighted_rate:.2f}% et progresse de {delta_pp_value:+.2f} point(s) de pourcentage par rapport au trimestre précédent. La dynamique est positive mais exige d’être entretenue pour se diffuser au‑delà des territoires déjà moteurs."
    else:
        p1 = f"Le taux d’adoption s’établit à {weighted_rate:.2f}% et recule de {delta_pp_value:+.2f} point(s) de pourcentage vs T‑1. Cette inflexion invite à un diagnostic des freins locaux et à un renforcement ciblé des leviers."

    # Paragraphe 2 — disparités territoriales
    if not _lead.empty and not _lag.empty:
        p2 = (
            f"Les disparités territoriales demeurent marquées : le département le plus avancé "
            f"({_lead.iloc[0]['DEPARTEMENT']}) atteint {_lead.iloc[0]['TAUX']:.2f}%, tandis que le moins avancé "
            f"({_lag.iloc[0]['DEPARTEMENT']}) reste à {_lag.iloc[0]['TAUX']:.2f}%. Par ailleurs, près de "
            f"{_top10_share:.1f}% du parc électrique observé se concentre dans les dix départements les plus dotés, "
            f"ce qui confirme un effet de polarisation autour des grands pôles urbains."
        )
    else:
        p2 = "La répartition territoriale ne permet pas d’identifier clairement des leaders et des retardataires aux filtres actuels. La concentration du parc reste néanmoins à surveiller."

    # Paragraphe 3 — implications opérationnelles
    p3 = (
        "En pratique, il convient de prioriser les départements combinant un parc de véhicules particuliers élevé et un taux d’adoption encore faible — ils offrent le meilleur potentiel d’impact à court terme. "
        "Dans les territoires déjà avancéess, l’enjeu est plutôt de consolider la dynamique (qualité de service des bornes, disponibilité, tarification) tandis que les zones en décélération appellent une action corrective rapide. "
        "Un suivi trimestriel des écarts permettra d’ajuster l’allocation des moyens et de diffuser les bonnes pratiques des départements leaders."
    )

    st.markdown(f"{p1}\n\n{p2}\n\n{p3}")

    # --- Priorisation territoriale (graphique rétabli) ---
    dept_curr = df_current.groupby('DEPARTEMENT', as_index=False).agg(
        VP=('NB_VP','sum'),
        EV=('NB_RECHARGEABLES_TOTAL','sum')
    )
    if not dept_curr.empty:
        dept_curr['TAUX'] = np.where(dept_curr['VP'] > 0, dept_curr['EV']/dept_curr['VP']*100, 0)
        dept_prev = df_prev.groupby('DEPARTEMENT', as_index=False).agg(
            VP_PREV=('NB_VP','sum'),
            EV_PREV=('NB_RECHARGEABLES_TOTAL','sum')
        )
        if not dept_prev.empty:
            dept_prev['TAUX_PREV'] = np.where(dept_prev['VP_PREV'] > 0, dept_prev['EV_PREV']/dept_prev['VP_PREV']*100, np.nan)
        prio = dept_curr.merge(
            dept_prev[['DEPARTEMENT','TAUX_PREV']] if not dept_prev.empty else dept_curr[['DEPARTEMENT']],
            on='DEPARTEMENT', how='left'
        )
        prio['DELTA_PP'] = prio['TAUX'] - prio['TAUX_PREV']

        median_rate = float(prio['TAUX'].median())
        p75_vp = float(prio['VP'].quantile(0.75))

        st.markdown("### 📌 Priorisation territoriale (où agir en premier ?)")
        st.caption("Matrice: fort parc (haut) × faible taux (gauche). Couleur = Δ % vs T‑1; taille = VE.")
        fig_mat = px.scatter(
            prio, x='TAUX', y='VP', size='EV', color='DELTA_PP',
            color_continuous_scale='RdYlGn', hover_name='DEPARTEMENT',
            hover_data={'TAUX':':.2f', 'VP':':,', 'EV':':,', 'DELTA_PP':':+.2f'},
            labels={'TAUX':"Taux d'adoption (%)", 'VP':"Parc total (VP)", 'EV':'VE', 'DELTA_PP':'Δ %'},
            title="Priorisation IRVE — Parc vs Taux (départements filtrés)"
        )
        fig_mat.add_vline(x=median_rate, line_dash='dash', line_color='orange')
        fig_mat.add_hline(y=p75_vp, line_dash='dash', line_color='orange')
        fig_mat.update_layout(height=520, margin=dict(l=10, r=10, t=60, b=10))
        st.plotly_chart(fig_mat, use_container_width=True)

        # Paragraphe d’interprétation
        top_targets = prio[(prio['TAUX'] <= median_rate) & (prio['VP'] >= p75_vp)].copy()
        top_targets = top_targets.sort_values(['VP','TAUX'], ascending=[False, True]).head(5)
        if not top_targets.empty:
            names = ", ".join(top_targets['DEPARTEMENT'].astype(str).tolist())
            st.markdown(
                f"Lecture: les départements à adresser en priorité sont {names}. "
                "Ils cumulent un parc élevé et un taux sous la médiane; une intensification des IRVE et de l’accompagnement y devrait produire le plus d’impact immédiat."
            )
        else:
            st.markdown("Avec les filtres actuels, aucun département ne ressort nettement comme priorité forte.")

# ============ 5) DATA & METHODS ============
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

