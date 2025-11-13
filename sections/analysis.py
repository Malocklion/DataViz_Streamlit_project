# sections/analysis.py
import requests
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.viz import configure_fig


def render_analysis(
    df: pd.DataFrame,
    df_current: pd.DataFrame,
    df_prev: pd.DataFrame,
    quarter_labels: list[str],
    label_to_period: dict,
    filtered_departements: list[str],
    min_vehicles: int,
):
    st.markdown("## Analyse")
    st.caption(
        "On examine la répartition spatiale et l’évolution temporelle pour comprendre le rythme d’adoption."
    )

    # --- Carte par département (photo du trimestre)
    st.markdown("### Carte par département")
    map_metric = st.radio(
        "Métrique de couleur",
        options=["Taux d'adoption (%)", "Véhicules électriques (nombre)"],
        index=0,
        horizontal=True,
        key="map_metric_radio",
        help="Couleur = taux (%) ou nombre de véhicules électriques.",
    )
    map_color_col = (
        "PART_ELECTRIQUE" if map_metric.startswith("Taux") else "NB_RECHARGEABLES_TOTAL"
    )

    # Slider de trimestre pour la carte uniquement
    map_quarter_label = st.select_slider(
        "Trimestre de la carte",
        options=quarter_labels,
        value=quarter_labels[-1],
        help="Glisse pour changer le trimestre affiché sur la carte.",
    )
    map_period = label_to_period[map_quarter_label]

    # Données de la carte basées sur le trimestre du slider
    df_map = df[
        (df["TRIMESTRE"] == map_period)
        & (df["DEPARTEMENT"].isin(filtered_departements))
        & (df["NB_VP"] >= min_vehicles)
    ].copy()

    regional = df_map.groupby("DEPARTEMENT", as_index=False).agg(
        NB_VP=("NB_VP", "sum"),
        NB_RECHARGEABLES_TOTAL=("NB_RECHARGEABLES_TOTAL", "sum"),
    )
    regional["PART_ELECTRIQUE"] = np.where(
        regional["NB_VP"] > 0,
        regional["NB_RECHARGEABLES_TOTAL"] / regional["NB_VP"] * 100,
        0,
    )

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
            locations="DEPARTEMENT",
            featureidkey="properties.code",
            color=map_color_col,
            color_continuous_scale="Viridis"
            if map_color_col == "PART_ELECTRIQUE"
            else "Blues",
            labels={
                "PART_ELECTRIQUE": "Taux adoption (%)",
                "NB_RECHARGEABLES_TOTAL": "Véhicules électriques",
            },
            mapbox_style="carto-positron",
            zoom=4.5,
            center={"lat": 46.6, "lon": 2.5},
            title=f"Carte — {map_metric} ({map_quarter_label})",
        )
        configure_fig(fig_map, height=700)
        st.plotly_chart(fig_map, use_container_width=True)

        # Paragraphe de lecture
        rate_map = (
            regional["NB_RECHARGEABLES_TOTAL"].sum()
            / regional["NB_VP"].sum()
            * 100
            if regional["NB_VP"].sum() > 0
            else 0.0
        )
        df_map_prev = df[
            (df["TRIMESTRE"] == (map_period - 1))
            & (df["DEPARTEMENT"].isin(filtered_departements))
            & (df["NB_VP"] >= min_vehicles)
        ]
        if not df_map_prev.empty:
            prev_ev = df_map_prev["NB_RECHARGEABLES_TOTAL"].sum()
            prev_vp = df_map_prev["NB_VP"].sum()
            prev_rate_map = (prev_ev / prev_vp * 100) if prev_vp > 0 else np.nan
            delta_map_pp = (
                None if np.isnan(prev_rate_map) else (rate_map - prev_rate_map)
            )
        else:
            delta_map_pp = None

        top10_share_map = (
            regional.nlargest(10, "NB_RECHARGEABLES_TOTAL")[
                "NB_RECHARGEABLES_TOTAL"
            ].sum()
            / max(1, regional["NB_RECHARGEABLES_TOTAL"].sum())
        ) * 100

        st.markdown(
            "Bien que le taux d’adoption progresse trimestre après trimestre"
            + f", il reste très concentré: les 10 départements les plus dotés regroupent ~{top10_share_map:.1f}% du parc électrique observé. "
            "Globalement, cette tendance est surtout menée par les grandes métropoles. Cela souligne des disparités territoriales marquées dans l’adoption des véhicules électriques. Il faudrait approfondir l’analyse à l’échelle communale pour mieux comprendre ces dynamiques."
        )
    st.caption("Question: Où sont les niveaux d’adoption les plus élevés/faibles ?")

    # --- Séries temporelles (historique des départements filtrés)
    st.markdown("### 📈 Évolution trimestrielle")
    df_hist = df[
        (df["DEPARTEMENT"].isin(filtered_departements)) & (df["NB_VP"] >= min_vehicles)
    ].copy()
    if df_hist.empty:
        st.info("Pas assez de données pour tracer l'évolution.")
    else:
        temporal = df_hist.groupby("TRIMESTRE", as_index=False).agg(
            NB_VP=("NB_VP", "sum"),
            NB_RECHARGEABLES_TOTAL=("NB_RECHARGEABLES_TOTAL", "sum"),
        )
        temporal["PART_ELECTRIQUE"] = np.where(
            temporal["NB_VP"] > 0,
            temporal["NB_RECHARGEABLES_TOTAL"] / temporal["NB_VP"] * 100,
            0,
        )
        temporal = temporal.sort_values("TRIMESTRE").copy()
        temporal["LABEL"] = temporal["TRIMESTRE"].apply(
            lambda p: f"T{int(p.quarter)} {int(p.year)}"
        )

        fig_trends = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=(
                "Parc total vs Véhicules électriques",
                "Taux d'adoption (%)",
            ),
            specs=[[{}], [{}]],
        )
        fig_trends.add_trace(
            go.Scatter(
                x=temporal["LABEL"],
                y=temporal["NB_VP"],
                name="Parc total (VP)",
                mode="lines+markers",
                line=dict(color="#1f77b4"),
            ),
            row=1,
            col=1,
        )
        fig_trends.add_trace(
            go.Scatter(
                x=temporal["LABEL"],
                y=temporal["NB_RECHARGEABLES_TOTAL"],
                name="Véhicules électriques",
                mode="lines+markers",
                line=dict(color="#2ca02c"),
            ),
            row=1,
            col=1,
        )
        fig_trends.add_trace(
            go.Scatter(
                x=temporal["LABEL"],
                y=temporal["PART_ELECTRIQUE"],
                name="Taux adoption (%)",
                mode="lines+markers",
                line=dict(color="#ff7f0e", width=3),
            ),
            row=2,
            col=1,
        )
        fig_trends.update_yaxes(title_text="Nombre (veh.)", row=1, col=1)
        fig_trends.update_yaxes(title_text="%", row=2, col=1)
        configure_fig(fig_trends, height=600)
        st.plotly_chart(fig_trends, use_container_width=True)

        # Paragraphe de lecture (analyse début → fin)
        if len(temporal) >= 2:
            start_label = str(temporal["LABEL"].iloc[0])
            end_label = str(temporal["LABEL"].iloc[-1])

            rate_start = float(temporal["PART_ELECTRIQUE"].iloc[0])
            rate_end = float(temporal["PART_ELECTRIQUE"].iloc[-1])
            delta_rate_pp = rate_end - rate_start

            ev_start = float(temporal["NB_RECHARGEABLES_TOTAL"].iloc[0])
            ev_end = float(temporal["NB_RECHARGEABLES_TOTAL"].iloc[-1])
            vp_start = float(temporal["NB_VP"].iloc[0])
            vp_end = float(temporal["NB_VP"].iloc[-1])

            ev_abs = ev_end - ev_start
            vp_abs = vp_end - vp_start
            ev_pct = (ev_end / ev_start - 1) * 100 if ev_start > 0 else np.nan
            vp_pct = (vp_end / vp_start - 1) * 100 if vp_start > 0 else np.nan

            n_quarters = max(1, len(temporal) - 1)
            n_years = n_quarters / 4.0
            ev_cagr = (
                ((ev_end / ev_start) ** (1 / n_years) - 1) * 100
                if (ev_start > 0 and n_years > 0)
                else np.nan
            )

            st.markdown(
                f"Du {start_label} au {end_label}, le taux d'adoption passe de {rate_start:.2f}% à {rate_end:.2f}% "
                f"(+{delta_rate_pp:.2f} pp). Le nombre de véhicules électriques progresse de {ev_abs:+,.0f}"
                f"{'' if np.isnan(ev_pct) else f' ({ev_pct:+.1f}%)'}, tandis que le parc total évolue de {vp_abs:+,.0f}"
                f"{'' if np.isnan(vp_pct) else f' ({vp_pct:+.1f}%)'}. En clair, une progression continue est visible sur toute la période."
            )
            
            # Observation spécifique : baisse du parc total 2024-2025 (extraire année depuis TRIMESTRE)
            temporal['ANNEE'] = temporal['TRIMESTRE'].apply(lambda p: p.year)
            recent = temporal[temporal['ANNEE'] >= 2024]
            if len(recent) >= 2:
                vp_2024_start = recent.iloc[0]['NB_VP']
                vp_recent_end = recent.iloc[-1]['NB_VP']
                vp_delta_recent = vp_recent_end - vp_2024_start
                if vp_delta_recent < 0:
                    st.markdown(
                        f"**Observation clé** : depuis 2024, le parc total recule ({vp_delta_recent:+,.0f} véhicules). "
                        f"Ce phénomène peut refléter une transition vers d'autres modes de transport (vélo, transports en commun, autopartage) "
                        f"ou une évolution des usages (multi-motorisation en baisse, télétravail). "
                        f"Même si le parc baisse, le nombre de véhicules électriques continue de progresser, "
                        f"ce qui explique l'accélération du taux d'adoption."
                    )
        else:
            st.markdown("Série trop courte pour une analyse début → fin.")
    st.caption("Question: La dynamique s’accélère-t-elle ou se tasse-t-elle ?")

    # --- Variations T vs T-1 (communes)
    st.markdown("###  Variations trimestrielles (Top hausses / baisses)")
    df_prev_sel = df_prev.copy()
    curr_communes = df_current.groupby("LIBGEO", as_index=False).agg(
        TAUX=("PART_ELECTRIQUE", "mean")
    )
    prev_communes = df_prev_sel.groupby("LIBGEO", as_index=False).agg(
        TAUX_PREV=("PART_ELECTRIQUE", "mean")
    )
    delta = curr_communes.merge(prev_communes, on="LIBGEO", how="left").dropna(
        subset=["TAUX_PREV"]
    )

    if delta.empty:
        st.info("Pas de trimestre précédent disponible pour comparer.")
    else:
        delta["DELTA_PP"] = delta["TAUX"] - delta["TAUX_PREV"]
        up = delta.sort_values("DELTA_PP", ascending=False).head(10)
        down = delta.sort_values("DELTA_PP", ascending=True).head(10)

        c1, c2 = st.columns(2)
        with c1:
            st.caption("Communes avec la plus forte hausse du taux (Δ % vs T-1).")
            fig_up = px.bar(
                up,
                x="DELTA_PP",
                y="LIBGEO",
                orientation="h",
                labels={"DELTA_PP": "Variation (%)", "LIBGEO": "Commune"},
                title="Top 10 hausses (%) vs T-1",
                color_discrete_sequence=["#2ca02c"],
            )
            fig_up.update_xaxes(tickformat=".2f")
            configure_fig(fig_up, height=420)
            st.plotly_chart(fig_up, use_container_width=True)
        with c2:
            st.caption("Communes avec la plus forte baisse du taux (Δ % vs T-1).")
            fig_down = px.bar(
                down,
                x="DELTA_PP",
                y="LIBGEO",
                orientation="h",
                labels={"DELTA_PP": "Variation (%)", "LIBGEO": "Commune"},
                title="Top 10 baisses (%) vs T-1",
                color_discrete_sequence=["#e45756"],
            )
            fig_down.update_xaxes(tickformat=".2f")
            configure_fig(fig_down, height=420)
            st.plotly_chart(fig_down, use_container_width=True)
        
        st.markdown(
                f"Ces variations trimestrielles mettent en lumière des dynamiques locales significatives. On voit que certaines communes connaissent des hausses notables du taux d’adoption, suggérant une adoption accélérée des véhicules électriques. En revanche, d’autres communes affichent des baisses, ce qui pourrait indiquer des défis spécifiques ou des ralentissements dans la transition. Ces disparités soulignent l’importance d’une analyse fine à l’échelle communale pour comprendre les facteurs sous-jacents influençant l’adoption des véhicules électriques. Bien que ce soit principalement les grandes villes qui mènent la transition, certaines petites communes montrent également des progrès remarquables, notamment du à la taille de leurs parc automobiles moins important que celui des villes."
            )
