# sections/intro.py
import streamlit as st

def render_intro():
    st.markdown("## Contexte")
    st.markdown(
        """
La transition écologique du secteur automobile est un enjeu majeur en France, 
où le transport représente près de 30 % des émissions de gaz à effet de serre. 
Depuis plusieurs années, les politiques publiques encouragent l’adoption de véhicules 
à faibles émissions, notamment électriques et hybrides, à travers des bonus écologiques, 
la mise en place de zones à faibles émissions (ZFE) et des investissements 
dans les infrastructures de recharge.

Cependant, la vitesse d’adoption de ces véhicules n’est pas homogène : 
elle varie fortement selon les territoires, le niveau de revenu moyen, 
ou encore la densité des bornes de recharge.
"""
    )

    st.markdown("## Problème")
    st.markdown(
        "- Comment la transition vers les véhicules électriques se traduit-elle à l’échelle territoriale en France, "
        "et quelles disparités révèle-t-elle entre les communes ?"
    )

    st.markdown("## Enjeux actuels")
    st.markdown(
        """
La décarbonation du transport routier s’inscrit dans la trajectoire européenne visant à mettre fin 
aux ventes de véhicules thermiques neufs d’ici 2035. Réduire rapidement les émissions de gaz à effet 
de serre et les polluants locaux, notamment dans les zones denses, constitue un enjeu à la fois 
sanitaire et climatique. Si l’adoption du véhicule électrique progresse, elle demeure très contrastée 
selon les territoires et les profils d’usagers.

Au-delà de la dimension environnementale, la question de l’équité territoriale est essentielle : 
il s’agit d’éviter un décrochage durable des zones rurales et périurbaines face aux grandes métropoles. 
Le déploiement des infrastructures de recharge (IRVE), la capacité du réseau électrique, 
les distances parcourues, le pouvoir d’achat et l’accompagnement aux nouveaux usages 
(information, médiation, services) sont autant de leviers déterminants.

Enfin, le pilotage public doit viser une allocation optimale des ressources : identifier les territoires 
à fort parc automobile mais à faible taux d’électrification, articuler les investissements IRVE et les 
zones à faibles émissions (ZFE) avec les dispositifs d’aide, et assurer un suivi régulier de la dynamique 
territoriale pour ajuster les politiques en temps réel.  

👉 Ce tableau de bord a précisément pour ambition d’éclairer ces décisions stratégiques.
"""
    )
