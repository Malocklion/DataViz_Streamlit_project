import streamlit as st
import pandas as pd
import plotly.express as px
import pydeck as pdk
import sys
import os

# Ajouter le répertoire courant au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import load_data, clean_df, aggregate_by_level  # Import des fonctions depuis utils.py

# Configuration de la page
st.set_page_config(page_title="Dashboard Véhicules Rechargeables", layout="wide")
st.title("Dashboard Véhicules Rechargeables par Commune")

# Initialiser les données par défaut
@st.cache_data
def get_default_data():
    """Créer des données par défaut pour l'initialisation"""
    test_data = pd.DataFrame({
        'CODGEO': ['75001', '75002', '75003', '69001', '13001', '31001', '59001'],
        'LIBGEO': ['Paris 1er', 'Paris 2e', 'Paris 3e', 'Lyon 1er', 'Marseille 1er', 'Toulouse Centre', 'Lille Centre'],
        'DATE_ARRETE': ['2023-12-31', '2023-12-31', '2023-12-31', '2023-12-31', '2023-12-31', '2023-12-31', '2023-12-31'],
        'NB_VP': [1000, 1500, 800, 1200, 900, 1100, 950],
        'NB_VP_RECHARGEABLES_EL': [100, 200, 80, 150, 90, 120, 95],
        'NB_VP_RECHARGEABLES_GAZ': [50, 75, 40, 60, 45, 55, 48]
    })
    return clean_df(test_data)

# Charger les données par défaut si aucune donnée n'est en session
if 'df' not in st.session_state:
    st.session_state['df'] = get_default_data()

# Sidebar
st.sidebar.header('Chargement des données')
st.sidebar.info("📊 Données d'exemple chargées par défaut")

upload = st.sidebar.file_uploader('Uploader votre CSV', type=['csv'])
use_sample = st.sidebar.checkbox('Charger depuis URL', value=False)
url_input = st.sidebar.text_input('URL CSV (si activé)', '')

if st.sidebar.button("Recharger données d'exemple"):
    st.session_state['df'] = get_default_data()
    st.sidebar.success("Données d'exemple rechargées !")

@st.cache_data
def get_df(upload, url_input, use_sample):
    try:
        if upload is not None:
            df = load_data(path=upload)
        elif use_sample and url_input:
            df = load_data(url=url_input)
        else:
            return None
        return clean_df(df)
    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
        return None

# Charger nouvelles données si fournies
new_df = get_df(upload, url_input, use_sample)
if new_df is not None:
    st.session_state['df'] = new_df
    st.sidebar.success("Nouvelles données chargées !")

# Utiliser les données de la session
df = st.session_state['df']

# Quick checks
st.sidebar.markdown("---")
st.sidebar.markdown("### Informations sur les données")
st.sidebar.markdown(f"**Lignes:** {df.shape[0]}")
st.sidebar.markdown(f"**Colonnes:** {df.shape[1]}")
st.sidebar.markdown(f"**Date min:** {df['DATE_ARRETE'].min()}")
st.sidebar.markdown(f"**Date max:** {df['DATE_ARRETE'].max()}")

# Filters
years = sorted(df['ANNEE'].dropna().unique())
selected_year = st.sidebar.selectbox('Année', options=years, index=len(years)-1)

df_year = df[df['ANNEE']==selected_year]

# KPIs
col1, col2, col3 = st.columns(3)
with col1:
    total_vp = int(df_year['NB_VP'].sum())
    st.metric('Total VP (année)', f"{total_vp:,}")
with col2:
    total_rech = int(df_year['NB_RECHARGEABLES'].sum())
    st.metric('Total VP rechargeables', f"{total_rech:,}")
with col3:
    share = total_rech/total_vp if total_vp>0 else 0
    st.metric('Part rechargeable', f"{share:.1%}")

# Time series
st.header('📈 Évolution temporelle')
series = df.groupby('MOIS').agg({'NB_VP':'sum','NB_RECHARGEABLES':'sum'}).reset_index()
series['SHARE'] = series['NB_RECHARGEABLES']/series['NB_VP']

# Convertir Period en string pour éviter l'erreur JSON
series['MOIS_STR'] = series['MOIS'].astype(str)

fig_ts = px.line(series, x='MOIS_STR', y='SHARE', title='Part des VP rechargeables (par mois)')
fig_ts.update_xaxes(title_text="Mois")
st.plotly_chart(fig_ts, use_container_width=True)

# Top communes
st.header('🏆 Top communes (part rechargeable)')
agg_comm = aggregate_by_level(df, level='commune')
agg_comm_y = agg_comm[agg_comm['ANNEE']==selected_year]
top_by_abs = agg_comm_y.sort_values('NB_RECHARGEABLES', ascending=False).head(10)
fig_bar = px.bar(top_by_abs, x='NB_RECHARGEABLES', y='LIBGEO', orientation='h', 
                 title='Top 10 communes par nombre de VP rechargeables')
st.plotly_chart(fig_bar, use_container_width=True)

# Scatter: parc vs share
st.header('🔍 Corrélation taille du parc vs part rechargeable')
fig_sc = px.scatter(agg_comm_y, x='NB_VP', y='SHARE', hover_data=['LIBGEO'], 
                    title='NB_VP vs Part rechargeable (communes)')
st.plotly_chart(fig_sc, use_container_width=True)

# Afficher les données brutes
if st.sidebar.checkbox("Afficher les données brutes"):
    st.header('📋 Données brutes')
    st.dataframe(df)

# Map section (optionnelle)
st.header('🗺️ Carte (optionnelle)')
st.markdown('Pour afficher une carte, uploadez un fichier `commune_coords.csv` avec `CODGEO,lat,lon`.')

coords_upload = st.file_uploader('Uploader commune_coords.csv (optionnel)', type=['csv'])
if coords_upload is not None:
    coords = pd.read_csv(coords_upload, dtype={'CODGEO':str})
    coords['CODGEO'] = coords['CODGEO'].str.zfill(5)
    merged = agg_comm_y.merge(coords[['CODGEO','lat','lon']], on='CODGEO', how='left')
    merged = merged.dropna(subset=['lat', 'lon'])
    
    if not merged.empty:
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=pdk.ViewState(
                latitude=merged['lat'].mean(),
                longitude=merged['lon'].mean(),
                zoom=6,
                pitch=0,
            ),
            layers=[
                pdk.Layer(
                    'ScatterplotLayer',
                    data=merged,
                    get_position='[lon, lat]',
                    get_color='[200, 30, 0, 160]',
                    get_radius=200,
                ),
            ],
        ))