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

    - garde ta logique d'origine (CODGEO, LIBGEO, NB_VP_RECHARGEABLES_EL, etc.)
    - calcule NB_RECHARGEABLES_TOTAL et PART_ELECTRIQUE
    - nettoie les libellés (Forains, ND, Non identifié, etc.)
    """
    try:
        # Lecture
        df = pd.read_csv(
            DATA_PATH,
            sep=';',
            dtype={'CODGEO': str, 'LIBGEO': str},
            low_memory=False
        )
        df['CODGEO'] = df['CODGEO'].astype(str)
        df.columns = df.columns.str.strip()

        # Dates -> trimestre
        df['DATE_ARRETE'] = pd.to_datetime(df['DATE_ARRETE'], errors='coerce')
        df = df.dropna(subset=['DATE_ARRETE', 'LIBGEO'])
        df['ANNEE'] = df['DATE_ARRETE'].dt.year
        df['TRIMESTRE'] = df['DATE_ARRETE'].dt.to_period('Q')

        # Numériques
        num_cols = ['NB_VP_RECHARGEABLES_EL', 'NB_VP_RECHARGEABLES_GAZ', 'NB_VP']
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

        # Indicateurs
        df['NB_RECHARGEABLES_TOTAL'] = (
            df['NB_VP_RECHARGEABLES_EL'] + df['NB_VP_RECHARGEABLES_GAZ']
        )
        df['PART_ELECTRIQUE'] = np.where(
            df['NB_VP'] > 0,
            df['NB_RECHARGEABLES_TOTAL'] / df['NB_VP'] * 100,
            0
        )

        # Département
        df['DEPARTEMENT'] = df['CODGEO'].apply(get_departement_code)

        # Nettoyage des libellés communes
        df['LIBGEO'] = df['LIBGEO'].astype(str).str.strip()
        df['LIBGEO_NORM'] = df['LIBGEO'].apply(_strip_accents_upper)

        # Exclusions:
        # - vides / NA
        # - "ND", "PARIS ND", "FORAINS", "NON IDENTIFIE(E)", "NON RENSEIGNE(E)", "INCONNU", "SANS LIBELLE", etc.
        mask_valid = (
            df['LIBGEO_NORM'].str.len() > 0
        ) & (
            ~df['LIBGEO_NORM'].isin(['NA', 'NAN', 'NONE'])
        ) & (
            ~df['LIBGEO_NORM'].str.fullmatch(BANNED_REGEX)
        )

        df = df[mask_valid].drop(columns=['LIBGEO_NORM']).copy()

        # Garde des taux plausibles
        df = df[(df['PART_ELECTRIQUE'] >= 0) & (df['PART_ELECTRIQUE'] <= 100)]

        return df

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return None
