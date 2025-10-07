# utils.py
import pandas as pd
from datetime import datetime

path = 'data/voitures-par-commune-par-energie.csv'

DATE_COL = 'DATE_ARRETE'




def load_data(path=None, url=None):
    """Charger le CSV localement (path) ou depuis une URL (url)."""
    try:
        if path:
            # Essayer différents séparateurs et encodages
            try:
                df = pd.read_csv(path, dtype={"CODGEO": str}, sep=';', encoding='utf-8')
            except:
                try:
                    df = pd.read_csv(path, dtype={"CODGEO": str}, sep=',', encoding='utf-8')
                except:
                    df = pd.read_csv(path, dtype={"CODGEO": str}, sep=';', encoding='latin-1')
        elif url:
            # Même logique pour l'URL
            try:
                df = pd.read_csv(url, dtype={"CODGEO": str}, sep=';', encoding='utf-8')
            except:
                df = pd.read_csv(url, dtype={"CODGEO": str}, sep=',', encoding='utf-8')
        else:
            raise ValueError("Fournir path ou url")
        
        return df
    except Exception as e:
        raise Exception(f"Impossible de lire le fichier: {str(e)}")


def clean_df(df):
    df = df.copy()
    # CODGEO en str, padding si besoin
    df['CODGEO'] = df['CODGEO'].astype(str).str.zfill(5)

    # DATE_ARRETE -> datetime (essayer plusieurs formats)
    try:
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors='coerce')
    except Exception:
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors='coerce')

    # colonnes numériques
    for col in ['NB_VP_RECHARGEABLES_EL', 'NB_VP_RECHARGEABLES_GAZ', 'NB_VP']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # créer métrique totale rechargeables
    df['NB_RECHARGEABLES'] = df['NB_VP_RECHARGEABLES_EL'] + df['NB_VP_RECHARGEABLES_GAZ']

    # part rechargeable
    df['SHARE_RECH'] = df.apply(lambda r: r['NB_RECHARGEABLES']/r['NB_VP'] if r['NB_VP']>0 else 0, axis=1)

    # extraire année/mois
    df['ANNEE'] = df[DATE_COL].dt.year
    # Utiliser truncate au lieu de to_period pour éviter les problèmes JSON
    df['MOIS'] = df[DATE_COL].dt.to_period('M').dt.start_time

    return df




def aggregate_by_level(df, level='commune'):
    """Aggregations utiles : par commune (CODGEO), par département, par année"""
    df = df.copy()
    if level=='departement':
        df['DEP'] = df['CODGEO'].str[:2]
        grp = df.groupby(['DEP','ANNEE']).agg({'NB_VP':'sum','NB_RECHARGEABLES':'sum'}).reset_index()
        grp['SHARE'] = grp['NB_RECHARGEABLES']/grp['NB_VP']
        return grp
    elif level=='commune':
        grp = df.groupby(['CODGEO','LIBGEO','ANNEE']).agg({'NB_VP':'sum','NB_RECHARGEABLES':'sum'}).reset_index()
        grp['SHARE'] = grp['NB_RECHARGEABLES']/grp['NB_VP']
        return grp
    else:
        raise ValueError('level doit être commune ou departement')