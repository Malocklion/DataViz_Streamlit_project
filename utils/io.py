# utils/io.py
import re
import unicodedata
import pandas as pd
import numpy as np
import streamlit as st

def get_departement_code(codgeo):
    codgeo = str(codgeo)
    if codgeo.startswith("2A") or codgeo.startswith("2B"):
        return codgeo[:2]
    else:
        return codgeo[:2]

def _strip_accents_upper(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.upper()

# Expressions à exclure (après normalisation sans accents, en MAJUSCULE)
BANNED_REGEX = re.compile(
    r"^(?:"
    r"FORAIN(?:S)?|"
    r"NON[\s\-]*IDENTIFI(?:E|EE)(?:S)?|"
    r"NON[\s\-]*DEFINI(?:E)?(?:S)?|"
    r"NON[\s\-]*RENSEIGNE(?:E)?(?:S)?|"
    r"INCONNU(?:S)?|"
    r"SANS[\s\-]*LIBELLE(?:S)?|"
    r"SANS[\s\-]*OBJET|"
    r"PARIS[\s\-]*ND|"
    r"ND"
    r")$"
)

def load_and_clean_data(DATA_PATH: str):
    """
    Charge et nettoie le fichier data/voitures-par-commune-par-energie.csv

    Colonnes attendues (selon data.gouv.fr):
    - codgeo_commune, libelle_commune, date_arrete
    - nb_vp_rechargeables_el, nb_vp_rechargeables_hybrides_rechargeables, nb_vp

    Étapes:
    1. Lecture et parsing des dates
    2. Conversion numérique (NB_VP > 0 obligatoire)
    3. Calcul indicateurs (NB_RECHARGEABLES_TOTAL, PART_ELECTRIQUE)
    4. Nettoyage des valeurs aberrantes:
       - NB_VP > 0 (sinon pas de base de calcul)
       - NB_RECHARGEABLES_TOTAL <= NB_VP (cohérence)
       - PART_ELECTRIQUE entre 0 et 100%
       - Suppression outliers extrêmes (> 99.5e percentile)
    5. Exclusion libellés invalides (Forains, ND, etc.)
    """
    try:
        # Lecture
        df = pd.read_csv(
            DATA_PATH,
            sep=';',
            dtype={'codgeo_commune': str, 'libelle_commune': str},
            low_memory=False
        )
        # Normalisation colonnes (minuscule -> MAJUSCULE uniforme)
        df.columns = df.columns.str.strip().str.upper()

        # Renommage pour compatibilité avec le code existant
        rename_map = {
            'CODGEO_COMMUNE': 'CODGEO',
            'LIBELLE_COMMUNE': 'LIBGEO',
            'DATE_ARRETE': 'DATE_ARRETE',
            'NB_VP_RECHARGEABLES_EL': 'NB_VP_RECHARGEABLES_EL',
            'NB_VP_RECHARGEABLES_HYBRIDES_RECHARGEABLES': 'NB_VP_RECHARGEABLES_GAZ',  # approximation
            'NB_VP': 'NB_VP'
        }
        df = df.rename(columns=rename_map)
        df['CODGEO'] = df['CODGEO'].astype(str)

        # Dates -> trimestre
        df['DATE_ARRETE'] = pd.to_datetime(df['DATE_ARRETE'], errors='coerce')
        df = df.dropna(subset=['DATE_ARRETE', 'LIBGEO'])
        df['ANNEE'] = df['DATE_ARRETE'].dt.year
        df['TRIMESTRE'] = df['DATE_ARRETE'].dt.to_period('Q')

        # Colonnes numériques
        num_cols = ['NB_VP_RECHARGEABLES_EL', 'NB_VP_RECHARGEABLES_GAZ', 'NB_VP']
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            else:
                df[c] = 0

        # 1) Exclusion des lignes avec parc VP nul ou négatif (pas de base de calcul)
        df = df[df['NB_VP'] > 0].copy()

        # 2) Calcul indicateurs
        df['NB_RECHARGEABLES_TOTAL'] = (
            df['NB_VP_RECHARGEABLES_EL'] + df['NB_VP_RECHARGEABLES_GAZ']
        )
        df['PART_ELECTRIQUE'] = np.where(
            df['NB_VP'] > 0,
            df['NB_RECHARGEABLES_TOTAL'] / df['NB_VP'] * 100,
            0
        )

        # 3) Nettoyage des incohérences: EV > VP impossible
        df = df[df['NB_RECHARGEABLES_TOTAL'] <= df['NB_VP']].copy()

        # 4) Taux entre 0 et 100%
        df = df[(df['PART_ELECTRIQUE'] >= 0) & (df['PART_ELECTRIQUE'] <= 100)].copy()

        # 5) Suppression outliers extrêmes (au‑delà du 99.5e percentile)
        if len(df) > 0:
            p995 = df['PART_ELECTRIQUE'].quantile(0.995)
            df = df[df['PART_ELECTRIQUE'] <= p995].copy()

        # Département
        df['DEPARTEMENT'] = df['CODGEO'].apply(get_departement_code)

        # Nettoyage des libellés communes
        df['LIBGEO'] = df['LIBGEO'].astype(str).str.strip()
        df['LIBGEO_NORM'] = df['LIBGEO'].apply(_strip_accents_upper)

        # Exclusions: vides / NA / Forains / ND / etc.
        mask_valid = (
            df['LIBGEO_NORM'].str.len() > 0
        ) & (
            ~df['LIBGEO_NORM'].isin(['NA', 'NAN', 'NONE'])
        ) & (
            ~df['LIBGEO_NORM'].str.fullmatch(BANNED_REGEX)
        )

        df = df[mask_valid].drop(columns=['LIBGEO_NORM']).copy()

        return df

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return None
