# sections/implications.py
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from utils.viz import configure_fig


def render_implications(
    df_current: pd.DataFrame,
    df_prev: pd.DataFrame,
    weighted_rate: float,
    delta_pp_value: float | None,
):
    st.markdown("## Implications")
    st.caption("Traduction opérationnelle des constats — où agir, avec quoi et pourquoi.")

    # Résumés départementaux
    _dept = df_current.groupby("DEPARTEMENT", as_index=False).agg(
        EV=("NB_RECHARGEABLES_TOTAL", "sum"),
        VP=("NB_VP", "sum"),
    )
    if not _dept.empty:
        _dept["TAUX"] = np.where(_dept["VP"] > 0, _dept["EV"] / _dept["VP"] * 100, 0)
        _lead = _dept.sort_values("TAUX", ascending=False).head(1)
        _lag = _dept.sort_values("TAUX", ascending=True).head(1)
        _top10_share = (
            _dept.sort_values("EV", ascending=False).head(10)["EV"].sum()
            / max(1, _dept["EV"].sum())
        ) * 100
    else:
        _lead = _lag = pd.DataFrame()
        _top10_share = 0.0

    # Paragraphe 1 — dynamique générale
    if delta_pp_value is None:
        p1 = (
            f"Le taux d’adoption des véhicules électriques s’établit à {weighted_rate:.2f}% "
            "sur le périmètre sélectionné. Cette photographie renseigne le niveau atteint ce trimestre, "
            "sans comparaison directe au trimestre précédent."
        )
    elif delta_pp_value > 0:
        p1 = (
            f"Le taux d’adoption s’établit à {weighted_rate:.2f}% et progresse de "
            f"{delta_pp_value:+.2f} point(s) de pourcentage par rapport au trimestre précédent. "
            "La dynamique est positive mais exige d’être entretenue pour se diffuser au-delà "
            "des territoires déjà moteurs."
        )
    else:
        p1 = (
            f"Le taux d’adoption s’établit à {weighted_rate:.2f}% et recule de "
            f"{delta_pp_value:+.2f} point(s) de pourcentage vs T-1. "
            "Cette inflexion invite à un diagnostic des freins locaux et à un renforcement ciblé des leviers."
        )

    # Paragraphe 2 — disparités territoriales
    if not _lead.empty and not _lag.empty:
        p2 = (
            f"Les disparités territoriales demeurent marquées : le département le plus avancé "
            f"({_lead.iloc[0]['DEPARTEMENT']}) atteint {_lead.iloc[0]['TAUX']:.2f}%, tandis que le moins avancé "
            f"({_lag.iloc[0]['DEPARTEMENT']}) reste à {_lag.iloc[0]['TAUX']:.2f}%. Par ailleurs, près de "
            f"{_top10_share:.1f}% du parc électrique observé se concentre dans les dix départements les plus dotés, "
            "ce qui confirme un effet de polarisation autour des grands pôles urbains."
        )
    else:
        p2 = (
            "La répartition territoriale ne permet pas d’identifier clairement des leaders "
            "et des retardataires aux filtres actuels. La concentration du parc reste néanmoins à surveiller."
        )

    # Paragraphe 3 — implications opérationnelles
    p3 = (
        "En pratique, il convient de prioriser les départements combinant un parc de véhicules particuliers "
        "élevé et un taux d’adoption encore faible — ils offrent le meilleur potentiel d’impact à court terme. "
        "Dans les territoires déjà avancés, l’enjeu est plutôt de consolider la dynamique "
        "(qualité de service des bornes, disponibilité, tarification) tandis que les zones en décélération "
        "appellent une action corrective rapide. Un suivi trimestriel des écarts permettra d’ajuster "
        "l’allocation des moyens et de diffuser les bonnes pratiques des départements leaders."
    )

    st.markdown(f"{p1}\n\n{p2}\n\n{p3}")

    # --- Priorisation territoriale (graphique) ---
    dept_curr = df_current.groupby("DEPARTEMENT", as_index=False).agg(
        VP=("NB_VP", "sum"),
        EV=("NB_RECHARGEABLES_TOTAL", "sum"),
    )
    if dept_curr.empty:
        return

    dept_curr["TAUX"] = np.where(dept_curr["VP"] > 0, dept_curr["EV"] / dept_curr["VP"] * 100, 0)
    dept_prev = df_prev.groupby("DEPARTEMENT", as_index=False).agg(
        VP_PREV=("NB_VP", "sum"),
        EV_PREV=("NB_RECHARGEABLES_TOTAL", "sum"),
    )
    if not dept_prev.empty:
        dept_prev["TAUX_PREV"] = np.where(
            dept_prev["VP_PREV"] > 0,
            dept_prev["EV_PREV"] / dept_prev["VP_PREV"] * 100,
            np.nan,
        )

    prio = dept_curr.merge(
        dept_prev[["DEPARTEMENT", "TAUX_PREV"]] if not dept_prev.empty else dept_curr[["DEPARTEMENT"]],
        on="DEPARTEMENT",
        how="left",
    )
    prio["DELTA_PP"] = prio["TAUX"] - prio["TAUX_PREV"]

    median_rate = float(prio["TAUX"].median())
    p75_vp = float(prio["VP"].quantile(0.75))

    st.markdown("### 📌 Priorisation territoriale (où agir en premier ?)")
    st.caption("Matrice: fort parc (haut) × faible taux (gauche). Couleur = Δ % vs T-1; taille = VE.")
    fig_mat = px.scatter(
        prio,
        x="TAUX",
        y="VP",
        size="EV",
        color="DELTA_PP",
        color_continuous_scale="RdYlGn",
        hover_name="DEPARTEMENT",
        hover_data={"TAUX": ":.2f", "VP": ":,", "EV": ":,", "DELTA_PP": ":+.2f"},
        labels={
            "TAUX": "Taux d'adoption (%)",
            "VP": "Parc total (VP)",
            "EV": "VE",
            "DELTA_PP": "Δ %",
        },
        title="Priorisation IRVE — Parc vs Taux (départements filtrés)",
    )
    fig_mat.add_vline(x=median_rate, line_dash="dash", line_color="orange")
    fig_mat.add_hline(y=p75_vp, line_dash="dash", line_color="orange")
    configure_fig(fig_mat, height=520)
    st.plotly_chart(fig_mat, use_container_width=True)

    top_targets = prio[
        (prio["TAUX"] <= median_rate) & (prio["VP"] >= p75_vp)
    ].copy()
    top_targets = top_targets.sort_values(["VP", "TAUX"], ascending=[False, True]).head(5)
    if not top_targets.empty:
        names = ", ".join(top_targets["DEPARTEMENT"].astype(str).tolist())
        st.markdown(
            f"Lecture: les départements à adresser en priorité sont {names}. "
            "Ils cumulent un parc élevé et un taux sous la médiane; une intensification des IRVE et de "
            "l’accompagnement y devrait produire le plus d’impact immédiat."
        )
    else:
        st.markdown(
            "Avec les filtres actuels, aucun département ne ressort nettement comme priorité forte."
        )
