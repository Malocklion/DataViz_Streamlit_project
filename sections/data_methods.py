# sections/data_methods.py
import pandas as pd
import streamlit as st


def render_data_methods(
    df: pd.DataFrame,
    df_current: pd.DataFrame,
    selected_quarter_label: str,
):
    st.markdown("### 📚 Source des données")
    st.markdown(
        "- Jeu: Voitures particulières immatriculées par commune et par type de recharge (trimestriel)\n"
        "- Portail: https://www.data.gouv.fr/datasets/voitures-particulieres-immatriculees-par-commune-et-par-type-de-recharge-jeu-de-donnees-aaadata/"
    )

    st.markdown("### 🧼 Nettoyage et hypothèses")
    st.markdown(
        """
- Exclusion des libellés non communaux (Forains, ND, Non identifié).
- Taux d’adoption = (EV/VP) × 100, borné à [0, 100].
- Agrégations: moyenne du taux par commune; sommes EV/VP par commune/département.
- Colonnes dérivées: ANNEE, TRIMESTRE, DEPARTEMENT.
        """
    )

    st.markdown("### 🧪 Résumé et contrôle qualité (ensemble complet)")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"- Lignes: {len(df):,}")
        st.write(f"- Communes uniques: {df['LIBGEO'].nunique():,}")
        st.write(
            f"- Période: {df['DATE_ARRETE'].min().strftime('%Y-%m-%d')} → "
            f"{df['DATE_ARRETE'].max().strftime('%Y-%m-%d')}"
        )
        st.write(
            f"- Années: {df['ANNEE'].min()}–{df['ANNEE'].max()} ({df['ANNEE'].nunique()} au total)"
        )
    with col2:
        issues = []
        if df.isnull().sum().sum() > 0:
            issues.append("Valeurs manquantes présentes.")
        if (df["NB_RECHARGEABLES_TOTAL"] > df["NB_VP"]).any():
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
        mime="text/csv",
    )

    st.markdown("### ⚠️ Limites & biais potentiels")
    st.info(
        "Les données reposent sur les immatriculations déclarées et peuvent ne pas capturer "
        "les véhicules radiés ou exportés. Les comportements d’usage (kilométrage, multi-motorisation) "
        "ne sont pas observés, ce qui limite l’interprétation en termes d’émissions effectives."
    )
