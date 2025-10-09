import pandas as pd
import numpy as np
import streamlit as st

def get_departement_code(codgeo):
    codgeo = str(codgeo)
    if codgeo.startswith("2A") or codgeo.startswith("2B"):
        return codgeo[:2]
    else:
        return codgeo[:2]

@st.cache_data
def load_and_clean_data(DATA_PATH):
    try:
        df = pd.read_csv(DATA_PATH, sep=';', dtype={'CODGEO': str, 'LIBGEO': str}, low_memory=False)
        df['CODGEO'] = df['CODGEO'].astype(str)
        df.columns = df.columns.str.strip()
        df['DATE_ARRETE'] = pd.to_datetime(df['DATE_ARRETE'])
        df['ANNEE'] = df['DATE_ARRETE'].dt.year
        df['MOIS'] = df['DATE_ARRETE'].dt.to_period('M')
        df = df.dropna(subset=['LIBGEO', 'DATE_ARRETE'])
        numeric_cols = ['NB_VP_RECHARGEABLES_EL', 'NB_VP_RECHARGEABLES_GAZ', 'NB_VP']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df['NB_RECHARGEABLES_TOTAL'] = df['NB_VP_RECHARGEABLES_EL'] + df['NB_VP_RECHARGEABLES_GAZ']
        df['PART_ELECTRIQUE'] = np.where(
            df['NB_VP'] > 0,
            df['NB_RECHARGEABLES_TOTAL'] / df['NB_VP'] * 100,
            0
        )
        df['DEPARTEMENT'] = df['CODGEO'].apply(get_departement_code)
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return None