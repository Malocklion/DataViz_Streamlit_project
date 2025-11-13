# sections/insights.py
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from utils.viz import configure_fig


def render_insights(
    df_current: pd.DataFrame,
    df_prev: pd.DataFrame,
    filtered_departements: list[str],
    min_vehicles: int,
):
    st.markdown("## Insights")
    st.caption(
        "On répond: qui est en tête/en retard et quelles communes expliquent les écarts ?"
    )

    # --- Top/Bottom communes
    st.markdown("### Top / Bottom des communes au niveau National")
    st.caption("Comparer Top et Bottom avec la même métrique pour évaluer la dispersion.")
    c1, c2 = st.columns([1, 1])
    with c1:
        metric_choice = st.radio(
            "Métrique de classement",
            options=["Taux d'adoption (%)", "Véhicules électriques (nombre)"],
            index=0,
            key="rank_metric_radio",
            help="Taux (%) = part électrique; Nombre = volume de véhicules électriques",
        )
    with c2:
        top_n = st.slider(
            "Nombre de communes",
            min_value=5,
            max_value=30,
            value=10,
            step=5,
            key="rank_topn",
        )

    communes_grouped = df_current.groupby("LIBGEO", as_index=False).agg(
        TAUX=("PART_ELECTRIQUE", "mean"),
        NB_RECHARGEABLES_TOTAL=("NB_RECHARGEABLES_TOTAL", "sum"),
        NB_VP=("NB_VP", "sum"),
    )
    sort_col = "TAUX" if metric_choice.startswith("Taux") else "NB_RECHARGEABLES_TOTAL"

    colL, colR = st.columns(2)
    with colL:
        st.markdown("#### Top")
        top_communes = communes_grouped.nlargest(top_n, sort_col)
        fig_top = px.bar(
            top_communes,
            x=("TAUX" if sort_col == "TAUX" else "NB_RECHARGEABLES_TOTAL"),
            y="LIBGEO",
            orientation="h",
            color="NB_RECHARGEABLES_TOTAL",
            color_continuous_scale="Greens",
            labels={
                "TAUX": "Taux d'adoption (%)",
                "NB_RECHARGEABLES_TOTAL": "Véhicules électriques",
                "LIBGEO": "Commune",
            },
            title=f"Top {top_n} — {metric_choice}",
        )
        if sort_col == "TAUX":
            fig_top.update_xaxes(
                tickformat=".2f", ticksuffix="%", title_text="Taux d'adoption (%)"
            )
            fig_top.update_traces(
                text=top_communes["TAUX"].map(lambda v: f"{v:.2f}%"),
                textposition="outside",
                cliponaxis=False,
            )
        else:
            fig_top.update_xaxes(title_text="Véhicules électriques (nombre)")
            fig_top.update_traces(
                text=top_communes["NB_RECHARGEABLES_TOTAL"].map(
                    lambda v: f"{int(v):,}"
                ),
                textposition="outside",
                cliponaxis=False,
            )
        configure_fig(fig_top, height=420)
        st.plotly_chart(fig_top, use_container_width=True)

    with colR:
        st.markdown("#### Bottom")
        if sort_col == "TAUX":
            bottom_pos = communes_grouped[communes_grouped["TAUX"] > 0].nsmallest(
                top_n, "TAUX"
            )
            if len(bottom_pos) < top_n:
                needed = top_n - len(bottom_pos)
                zeros = communes_grouped[communes_grouped["TAUX"] == 0].nlargest(
                    needed, "NB_VP"
                )
                bottom_communes = pd.concat([bottom_pos, zeros], ignore_index=True)
            else:
                bottom_communes = bottom_pos
            x_col = "TAUX"
        else:
            bottom_communes = communes_grouped.nsmallest(
                top_n, "NB_RECHARGEABLES_TOTAL"
            )
            x_col = "NB_RECHARGEABLES_TOTAL"

        bottom_communes = bottom_communes.sort_values(x_col, ascending=True)
        fig_bottom = px.bar(
            bottom_communes,
            x=x_col,
            y="LIBGEO",
            orientation="h",
            color="NB_VP",
            color_continuous_scale="Reds",
            labels={
                "TAUX": "Taux d'adoption (%)",
                "NB_RECHARGEABLES_TOTAL": "Véhicules électriques",
                "NB_VP": "Parc total",
                "LIBGEO": "Commune",
            },
            title=f"Bottom {top_n} — {metric_choice}",
        )
        if x_col == "TAUX":
            max_x = float(bottom_communes["TAUX"].max() or 0)
            pad = max(0.05, max_x * 0.25)
            fig_bottom.update_xaxes(
                range=[0, max_x + pad],
                tickformat=".2f",
                ticksuffix="%",
                title_text="Taux d'adoption (%)",
            )
            fig_bottom.update_traces(
                text=bottom_communes["TAUX"].map(lambda v: f"{v:.2f}%"),
                textposition="outside",
                cliponaxis=False,
            )
        else:
            fig_bottom.update_xaxes(title_text="Véhicules électriques (nombre)")
            fig_bottom.update_traces(
                text=bottom_communes["NB_RECHARGEABLES_TOTAL"].map(
                    lambda v: f"{int(v):,}"
                ),
                textposition="outside",
                cliponaxis=False,
            )
        configure_fig(fig_bottom, height=420)
        st.plotly_chart(fig_bottom, use_container_width=True)


    # --- Focus communes d’un département
    st.markdown("### Communes d’un département")
    st.caption(
        "Choisis un département filtré pour détailler ses communes (barres classées)."
    )
    eligible_depts = filtered_departements
    if not eligible_depts:
        st.info("Aucun département disponible avec les filtres courants.")
        return

    if len(eligible_depts) == 1:
        selected_dept = eligible_depts[0]
    else:
        selected_dept = st.selectbox(
            "Choisissez un département",
            options=eligible_depts,
            key="dept_for_communes_view",
        )

    communes_dept = (
        df_current[df_current["DEPARTEMENT"] == selected_dept]
        .groupby("LIBGEO", as_index=False)
        .agg(
            EV=("NB_RECHARGEABLES_TOTAL", "sum"),
            PARC=("NB_VP", "sum"),
            TAUX=("PART_ELECTRIQUE", "mean"),
        )
    )

    if communes_dept.empty:
        st.warning(f"Aucune commune à afficher pour le département {selected_dept}.")
        return

    colA, colB = st.columns(2)
    with colA:
        sort_metric = st.selectbox(
            "Trier par",
            ["Taux d'adoption (%)", "Véhicules électriques (nombre)"],
            index=0,
            key="communes_sort_metric",
        )
    with colB:
        top_n_communes = st.slider(
            "Nombre de communes",
            5,
            min(50, len(communes_dept)),
            min(20, len(communes_dept)),
            5,
            key="communes_topn",
        )

    if sort_metric.startswith("Taux"):
        data_plot = communes_dept.sort_values("TAUX", ascending=False).head(
            top_n_communes
        )
        x_col = "TAUX"
    else:
        data_plot = communes_dept.sort_values("EV", ascending=False).head(
            top_n_communes
        )
        x_col = "EV"

    fig_bar = px.bar(
        data_plot,
        x=x_col,
        y="LIBGEO",
        orientation="h",
        color="TAUX",
        color_continuous_scale="RdYlGn",
        labels={
            "LIBGEO": "Commune",
            "TAUX": "Taux d'adoption (%)",
            "EV": "Véhicules électriques",
        },
        title=f"Département {selected_dept} — {sort_metric} (top {top_n_communes})",
    )
    if x_col == "TAUX":
        fig_bar.update_xaxes(
            tickformat=".2f", ticksuffix="%", title_text="Taux d'adoption (%)"
        )
        fig_bar.update_traces(
            text=data_plot["TAUX"].map(lambda v: f"{v:.2f}%"),
            textposition="outside",
            cliponaxis=False,
        )
    else:
        fig_bar.update_xaxes(title_text="Véhicules électriques (nombre)")
        fig_bar.update_traces(
            text=data_plot["EV"].map(lambda v: f"{int(v):,}"),
            textposition="outside",
            cliponaxis=False,
        )
    configure_fig(fig_bar, height=650)
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption(
        "Le nombre de communes disponibles à l'affichage dépend des données fournies par data.gouv.fr "
        "pour chaque trimestre. Certaines communes peuvent être absentes ou incomplètes en raison de "
        "données manquantes ou de valeurs anomalement basses ou élevées selon les années."
    )
    st.markdown(
        f"Cette vue détaillée des communes du département {selected_dept} révèle des disparités significatives dans l'adoption des véhicules électriques. "
        "Certaines communes affichent des taux d'adoption élevés, indiquant une transition plus rapide vers des options de mobilité durable. "
        "En revanche, d'autres communes restent en retrait, ce qui pourrait être attribué à divers facteurs tels que l'infrastructure de recharge limitée, "
        "les préférences locales ou les contraintes économiques. Cette analyse souligne l'importance de cibler les efforts de sensibilisation et "
        "d'investissement dans les infrastructures pour accélérer l'adoption des véhicules électriques à l'échelle locale."
    )

