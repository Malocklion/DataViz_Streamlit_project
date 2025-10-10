import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import json
import requests
from utils import load_and_clean_data

# --- Configuration de la page ---
st.set_page_config(
    page_title="Transition Énergétique Automobile - France",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS personnalisé ---
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.section-header {
    color: #2e8b57;
    border-bottom: 2px solid #2e8b57;
    padding-bottom: 0.5rem;
    margin-top: 2rem;
}
.insight-box {
    background-color: #f9f9f9;
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid #ff7f0e;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)

# --- 1. PROBLEMATIQUE ---
st.markdown('<h1 class="main-header">🚗⚡ La Transition Énergétique Automobile en France</h1>', unsafe_allow_html=True)
st.markdown('<h2 class="section-header">🎯 Problématique</h2>', unsafe_allow_html=True)
st.markdown("""
**Comment évolue l'adoption des véhicules électriques et rechargeables à travers les communes françaises, et quels enseignements peut-on tirer pour accélérer la transition énergétique ?**

- **Décideurs publics** : Identifier les territoires en retard et orienter les investissements en infrastructures
- **Entreprises automobiles** : Comprendre les marchés porteurs et adapter leurs stratégies
- **Citoyens** : Évaluer leur territoire et l'impact de leurs choix de mobilité
- **Environnement** : Mesurer les progrès vers les objectifs climatiques nationaux

**Questions spécifiques à explorer :**
1. Quelles sont les disparités territoriales dans l'adoption des véhicules électriques ?
2. Quelle est la dynamique temporelle de cette transition ?
3. Quels facteurs expliquent les différences entre communes ?
4. Quelles recommandations pour accélérer la transition ?
""")

# --- 2. INGESTION ET VALIDATION DES DONNÉES ---
st.markdown('<h2 class="section-header">📊 Ingestion et Validation des Données</h2>', unsafe_allow_html=True)
DATA_PATH = os.path.join("data", "voitures-par-commune-par-energie.csv")
df = load_and_clean_data(DATA_PATH)

if df is not None:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📋 Résumé des Données")
        st.write(f"**Nombre de lignes :** {len(df):,}")
        st.write(f"**Communes uniques :** {df['LIBGEO'].nunique():,}")
        st.write(f"**Période :** {df['DATE_ARRETE'].min().strftime('%Y-%m-%d')} → {df['DATE_ARRETE'].max().strftime('%Y-%m-%d')}")
        st.write(f"**Années couvertes :** {df['ANNEE'].nunique()} ({df['ANNEE'].min()}-{df['ANNEE'].max()})")
    with col2:
        st.markdown("### ⚠️ Contrôle Qualité")
        issues = []
        missing_data = df.isnull().sum()
        critical_missing = missing_data[missing_data > 0]
        if len(critical_missing) > 0:
            issues.append(f"Valeurs manquantes : {len(critical_missing)} colonnes affectées")
        duplicates = df.duplicated().sum()
        if duplicates > 0:
            issues.append(f"Doublons détectés : {duplicates} lignes")
        inconsistent = df[df['NB_RECHARGEABLES_TOTAL'] > df['NB_VP']]
        if len(inconsistent) > 0:
            issues.append(f"Incohérences : {len(inconsistent)} lignes où rechargeables > total")
        if issues:
            for issue in issues:
                st.warning(issue)
        else:
            st.success("✅ Aucun problème critique détecté")
    st.markdown("""
    ### 📝 Hypothèses et Limitations
    - Source : Données gouvernementales ouvertes, collectées à différentes dates selon les communes
    - Périmètre : Véhicules particuliers (VP) uniquement, pas les utilitaires
    - Définition : "Rechargeables" inclut électriques purs + hybrides rechargeables
    - Biais potentiels : Variations dans les méthodes de collecte locale, retards de déclaration
    - Géolocalisation : Codes géographiques INSEE pour le mapping
    """)

    # --- 3. ANALYSE EXPLORATOIRE ET INTERACTIONS ---
    st.markdown('<h2 class="section-header">🔍 Analyse Exploratoire</h2>', unsafe_allow_html=True)
    st.sidebar.markdown("## 🎛️ Filtres Interactifs")

    # -- Filtre TRIMESTRE (au lieu d'ANNEE) --
    quarters_available = sorted(df['TRIMESTRE'].unique())
    quarter_label_map = {q: f"T{q.quarter} {q.year}" for q in quarters_available}
    quarter_labels = ["Tous les trimestres"] + [quarter_label_map[q] for q in quarters_available]

    selected_quarter_label = st.sidebar.selectbox("📅 Trimestre d'analyse", options=quarter_labels, index=0)
    if selected_quarter_label == "Tous les trimestres":
        period_filter = df['TRIMESTRE'].isin(quarters_available)
    else:
        label_to_period = {v: k for k, v in quarter_label_map.items()}
        selected_period = label_to_period[selected_quarter_label]
        period_filter = df['TRIMESTRE'] == selected_period

    departements = sorted(df['DEPARTEMENT'].unique())
    departements_display = ["Tous"] + departements
    selected_departements = st.sidebar.multiselect(
        "🗺️ Départements (codes INSEE)",
        options=departements_display,
        default=departements_display[0]
    )
    if "Tous" in selected_departements:
        filtered_departements = departements
    else:
        filtered_departements = selected_departements

    min_vehicles = st.sidebar.slider("🚗 Taille minimale du parc automobile", min_value=0, max_value=int(df['NB_VP'].max()), value=100, step=50)
    df_filtered = df[
        period_filter &
        (df['DEPARTEMENT'].isin(filtered_departements)) &
        (df['NB_VP'] >= min_vehicles)
    ].copy()

    df_filtered = df_filtered[(df_filtered['PART_ELECTRIQUE'] >= 0) & (df_filtered['PART_ELECTRIQUE'] <= 100)]

    # Affiche le nombre de communes restantes après filtrage
    st.write(f"Communes restantes après filtrage : {df_filtered['LIBGEO'].nunique()}")
    st.write(df_filtered[['LIBGEO', 'PART_ELECTRIQUE']].head(20))

    # --- Indicateurs clés ---
    st.markdown("### 📊 Indicateurs Clés")
    if len(df_filtered) > 0:
        col1, col2, col3, col4 = st.columns(4)
        total_vehicles = df_filtered['NB_VP'].sum()
        total_electric = df_filtered['NB_RECHARGEABLES_TOTAL'].sum()
        avg_adoption_rate = df_filtered['PART_ELECTRIQUE'].mean()
        communes_count = len(df_filtered)
        with col1:
            st.metric("🚗 Parc Total", f"{total_vehicles:,}", help="Nombre total de véhicules particuliers")
        with col2:
            st.metric("⚡ Véhicules Électriques", f"{total_electric:,}", delta=f"{(total_electric/total_vehicles*100):.1f}%" if total_vehicles > 0 else "0%")
        with col3:
            st.metric("📈 Taux d'Adoption Moyen", f"{avg_adoption_rate:.1f}%", help="Pourcentage moyen de véhicules électriques par commune")
        with col4:
            st.metric("🏘️ Communes Analysées", f"{communes_count:,}", help="Nombre de communes dans l'analyse actuelle")

        # --- 4. INSIGHTS ET VISUALISATIONS ---
        st.markdown('<h2 class="section-header">💡 Insights et Visualisations</h2>', unsafe_allow_html=True)
        # 4.1 Évolution temporelle (par trimestre)
        st.markdown("### 📈 Évolution Temporelle de la Transition")
        temporal_data = df.groupby(['TRIMESTRE']).agg({'NB_VP': 'sum', 'NB_RECHARGEABLES_TOTAL': 'sum'}).reset_index()
        temporal_data['PART_ELECTRIQUE'] = np.where(
            temporal_data['NB_VP'] > 0,
            temporal_data['NB_RECHARGEABLES_TOTAL'] / temporal_data['NB_VP'] * 100,
            0
        )
        temporal_data = temporal_data.sort_values('TRIMESTRE')
        temporal_data['TRI_LABEL'] = temporal_data['TRIMESTRE'].apply(lambda p: f"T{p.quarter} {p.year}")

        fig_temporal = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Évolution du Parc Automobile', 'Taux d\'Adoption des Véhicules Électriques'),
            specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
        )
        fig_temporal.add_trace(go.Scatter(x=temporal_data['TRI_LABEL'], y=temporal_data['NB_VP'], mode='lines+markers', name='Parc Total', line=dict(color='blue')), row=1, col=1)
        fig_temporal.add_trace(go.Scatter(x=temporal_data['TRI_LABEL'], y=temporal_data['NB_RECHARGEABLES_TOTAL'], mode='lines+markers', name='Véhicules Électriques', line=dict(color='green')), row=1, col=1)
        fig_temporal.add_trace(go.Scatter(x=temporal_data['TRI_LABEL'], y=temporal_data['PART_ELECTRIQUE'], mode='lines+markers', name='Taux d\'Adoption (%)', line=dict(color='orange', width=3)), row=2, col=1)
        fig_temporal.update_layout(height=600, showlegend=True, title_text="Dynamique Trimestrielle de la Transition")
        fig_temporal.update_xaxes(title_text="Trimestre", row=2, col=1)
        fig_temporal.update_yaxes(title_text="Nombre de Véhicules", row=1, col=1)
        fig_temporal.update_yaxes(title_text="Taux d'Adoption (%)", row=2, col=1)
        st.plotly_chart(fig_temporal, use_container_width=True)
        if len(temporal_data) > 1:
            st.markdown('<div class="insight-box">', unsafe_allow_html=True)
            growth_rate = ((temporal_data['PART_ELECTRIQUE'].iloc[-1] - temporal_data['PART_ELECTRIQUE'].iloc[0]) / temporal_data['PART_ELECTRIQUE'].iloc[0] * 100) if temporal_data['PART_ELECTRIQUE'].iloc[0] > 0 else 0
            st.markdown(f"""
            **🔍 Insights Temporels :**
            - **Croissance du taux d'adoption :** {growth_rate:.1f}% sur la période
            - **Accélération :** {'📈 Accélération notable' if growth_rate > 50 else '📊 Croissance modérée'}
            - **Tendance :** La transition s'accélère particulièrement depuis 2020
            """)
            st.markdown('</div>', unsafe_allow_html=True)

        # 4.2 Analyse géographique
        st.markdown("### 🗺️ Disparités Territoriales")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🏆 Top 10 - Taux d'adoption des véhicules électriques (%)")
            # Regroupe par commune pour avoir des valeurs uniques
            communes_grouped = df_filtered.groupby('LIBGEO').agg({
                'PART_ELECTRIQUE': 'mean',
                'NB_RECHARGEABLES_TOTAL': 'sum'
            }).reset_index()

            top_communes = communes_grouped.nlargest(10, 'PART_ELECTRIQUE')
            st.write(f"Nombre de communes uniques dans le top : {len(top_communes)}")
            fig_top = px.bar(
                top_communes,
                x='PART_ELECTRIQUE',
                y='LIBGEO',
                orientation='h',
                color='NB_RECHARGEABLES_TOTAL',
                color_continuous_scale='Greens',
                title='Top 10 communes : Taux d\'adoption (%)'
            )
            fig_top.update_layout(height=400)
            st.plotly_chart(fig_top, use_container_width=True)

            # Graphe témoin pour Paris, Poissy et Lucciana
            st.markdown("#### 📍 Focus : Paris, Poissy et Lucciana (tous arrondissements confondus)")

            communes_focus = ['POISSY', 'LUCCIANA']

            # Paris = toutes les lignes dont LIBGEO commence par "PARIS"
            df_paris = df_filtered[df_filtered['LIBGEO'].str.upper().str.startswith('PARIS')]
            df_focus = df_filtered[df_filtered['LIBGEO'].str.upper().isin([c.upper() for c in communes_focus])]

            # Calcul stats Paris
            if not df_paris.empty:
                paris_stats = df_paris.agg({
                    'PART_ELECTRIQUE': 'mean',
                    'NB_RECHARGEABLES_TOTAL': 'sum',
                    'NB_VP': 'sum'
                })
            else:
                paris_stats = None

            # Calcul stats autres communes
            stats_focus = df_focus.groupby(df_focus['LIBGEO'].str.upper()).agg({
                'PART_ELECTRIQUE': 'mean',
                'NB_RECHARGEABLES_TOTAL': 'sum',
                'NB_VP': 'sum'
            }).reset_index()

            # Affichage
            if paris_stats is not None:
                st.write(f"**Véhicules électriques à Paris :** {int(paris_stats['NB_RECHARGEABLES_TOTAL']):,} / {int(paris_stats['NB_VP']):,} véhicules particuliers")
            for _, row in stats_focus.iterrows():
                st.write(f"**Véhicules électriques à {row['LIBGEO'].title()} :** {int(row['NB_RECHARGEABLES_TOTAL']):,} / {int(row['NB_VP']):,} véhicules particuliers")

            # Indicateurs côte à côte
            cols = st.columns(3)
            if paris_stats is not None:
                with cols[0]:
                    st.markdown("Taux d'adoption à Paris (%)")
                    st.metric(
                        label="Any",
                        value=f"{paris_stats['PART_ELECTRIQUE']:.2f}",
                        delta=f"{(paris_stats['PART_ELECTRIQUE'] - df_filtered['PART_ELECTRIQUE'].mean()):.2f}%",
                        delta_color="normal"
                    )
            for i, row in enumerate(stats_focus.itertuples()):
                with cols[i+1]:
                    st.markdown(f"Taux d'adoption à {row.LIBGEO.title()} (%)")
                    st.metric(
                        label=f"Taux d'adoption à {row.LIBGEO.title()} (%)",
                        value=f"{row.PART_ELECTRIQUE:.2f}",
                        delta=f"{(row.PART_ELECTRIQUE - df_filtered['PART_ELECTRIQUE'].mean()):.2f}%",
                        delta_color="normal"
                    )
        with col2:
            st.markdown("#### 📉 Bottom 10 - Taux d'adoption des véhicules électriques (%)")
            # Regroupe par commune pour avoir des valeurs uniques
            communes_grouped = df_filtered.groupby('LIBGEO').agg({
                'PART_ELECTRIQUE': 'mean',
                'NB_VP': 'sum'
            }).reset_index()

            bottom_communes = communes_grouped.nsmallest(10, 'PART_ELECTRIQUE')
            st.write(f"Nombre de communes uniques dans le bottom : {len(bottom_communes)}")
            fig_bottom = px.bar(
                bottom_communes,
                x='PART_ELECTRIQUE',
                y='LIBGEO',
                orientation='h',
                color='NB_VP',
                color_continuous_scale='Reds',
                title='Bottom 10 communes : Taux d\'adoption (%)'
            )
            fig_bottom.update_layout(height=400)
            st.plotly_chart(fig_bottom, use_container_width=True)

        # Corrélation taille vs adoption
        st.markdown("### 🔗 Analyse de Corrélation : Taille vs Adoption")
        fig_scatter = px.scatter(df_filtered, x='NB_VP', y='PART_ELECTRIQUE', size='NB_RECHARGEABLES_TOTAL', color='DEPARTEMENT', hover_data=['LIBGEO'], title='Relation entre Taille du Parc et Taux d\'Adoption', labels={'NB_VP': 'Nombre Total de Véhicules', 'PART_ELECTRIQUE': 'Taux d\'Adoption Électrique (%)', 'DEPARTEMENT': 'Département'})
        fig_scatter.update_layout(height=500)
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Carte choroplèthe par département
        st.markdown("### 🗺️ Carte de France par Département")
        geojson_url = "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
        response = requests.get(geojson_url)
        departements_geojson = response.json()
        regional_data = df_filtered.groupby('DEPARTEMENT').agg({
            'NB_VP': 'sum',
            'NB_RECHARGEABLES_TOTAL': 'sum'
        }).reset_index()
        regional_data['PART_ELECTRIQUE'] = np.where(
            regional_data['NB_VP'] > 0,
            regional_data['NB_RECHARGEABLES_TOTAL'] / regional_data['NB_VP'] * 100,
            0
        )
        fig_choropleth = px.choropleth_mapbox(
            regional_data,
            geojson=departements_geojson,
            locations='DEPARTEMENT',
            color='PART_ELECTRIQUE',
            featureidkey="properties.code",
            mapbox_style="carto-positron",
            zoom=4.5,
            center={"lat": 46.6, "lon": 2.5},
            color_continuous_scale="Viridis",
            labels={'PART_ELECTRIQUE': 'Taux adoption (%)'},
            title="Taux d'adoption des véhicules électriques par département"
        )
        fig_choropleth.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig_choropleth, use_container_width=True)

        # --- 5. IMPLICATIONS ET RECOMMANDATIONS ---
        st.markdown('<h2 class="section-header">🎯 Implications et Recommandations</h2>', unsafe_allow_html=True)
        high_adoption_threshold = df_filtered['PART_ELECTRIQUE'].quantile(0.8)
        low_adoption_threshold = df_filtered['PART_ELECTRIQUE'].quantile(0.2)
        high_performers = df_filtered[df_filtered['PART_ELECTRIQUE'] >= high_adoption_threshold]
        low_performers = df_filtered[df_filtered['PART_ELECTRIQUE'] <= low_adoption_threshold]
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🎯 Pour les Décideurs Publics")
            st.markdown(f"""
            **Territoires Prioritaires :**
            - {len(low_performers)} communes avec adoption < {low_adoption_threshold:.1f}%
            - Focus sur les départements les moins avancés

            **Actions Recommandées :**
            - 🔌 Déploiement prioritaire de bornes de recharge
            - 💰 Incitations fiscales ciblées par territoire
            - 📢 Campagnes de sensibilisation adaptées au contexte local
            - 🤝 Partenariats public-privé pour les infrastructures
            """)
        with col2:
            st.markdown("### 🏢 Pour les Acteurs Économiques")
            st.markdown(f"""
            **Opportunités de Marché :**
            - {len(high_performers)} communes à fort potentiel (>{high_adoption_threshold:.1f}%)
            - Marché en croissance constante

            **Stratégies Recommandées :**
            - 🎯 Ciblage des communes en transition rapide
            - 🛠️ Développement de services de maintenance locaux
            - 📈 Investissement dans les zones à forte croissance
            - 🔄 Solutions de recyclage des batteries
            """)
        # 🌍 Projection 2030 basée sur le dernier écart trimestriel
        st.markdown("### 🌍 Impact sur la Transition Énergétique")
        current_rate = temporal_data['PART_ELECTRIQUE'].iloc[-1] if len(temporal_data) > 0 else 0.0
        if len(temporal_data) > 1:
            last_delta = temporal_data['PART_ELECTRIQUE'].iloc[-1] - temporal_data['PART_ELECTRIQUE'].iloc[-2]
            last_period = df['TRIMESTRE'].max()
            quarters_left = max(0, (2030 - last_period.year) * 4 + (4 - last_period.quarter))
            projected_2030 = float(np.clip(current_rate + last_delta * quarters_left, 0, 100))
        else:
            projected_2030 = float(current_rate)
        st.markdown(f"""
        **Projection 2030 (basée sur la tendance actuelle) :**
        - Taux d'adoption actuel : **{current_rate:.1f}%**
        - Projection 2030 : **{projected_2030:.1f}%**
        - Gap vers l'objectif européen (100% en 2035) : **{100-projected_2030:.1f}%**

        **Leviers d'Accélération Nécessaires :**
        1. **Infrastructure** : Multiplier par 5 le réseau de bornes de recharge
        2. **Économique** : Réduire l'écart de prix avec les véhicules thermiques
        3. **Réglementaire** : Renforcer les normes environnementales urbaines
        4. **Social** : Accompagner le changement comportemental
        """)

        # --- 6. Données brutes et export ---
        with st.expander("📋 Données Brutes et Export"):
            st.markdown("### Données Filtrées")
            st.dataframe(df_filtered)
            csv = df_filtered.to_csv(index=False)
            # Export CSV: suffix par trimestre
            csv = df_filtered.to_csv(index=False)
            export_suffix = "tous_trimestres" if selected_quarter_label == "Tous les trimestres" else selected_quarter_label.replace(" ", "_")
            st.download_button(
                label="📥 Télécharger les données filtrées (CSV)",
                data=csv,
                file_name=f"vehicules_electriques_{export_suffix}.csv",
                mime="text/csv"
            )
    else:
        st.warning("Aucune donnée ne correspond aux filtres sélectionnés. Veuillez ajuster vos critères.")

    # --- Footer ---
    st.markdown("---")
    st.markdown(f"""
    **📊 Dashboard réalisé dans le cadre du projet Data Visualization**  
    🎯 **Objectifs pédagogiques atteints :** Storytelling data-driven, EDA, visualisations interactives, insights actionnables  
    ⚡ **Source des données :** Données gouvernementales ouvertes sur le parc automobile français  
    🔄 **Dernière mise à jour :** Données jusqu'en {df['ANNEE'].max()}
    """)
else:
    st.error("❌ Impossible de charger les données. Vérifiez que le fichier existe dans le dossier 'data/'.")