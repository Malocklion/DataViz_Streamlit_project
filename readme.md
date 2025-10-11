# Transition Énergétique Automobile — France (Streamlit)

## 1. Story
- Problème: Où et à quel rythme les véhicules électriques s’adoptent-ils en France ?
- Approche: Données trimestrielles publiques (Data.gouv), nettoyage, KPI pondérés, carte, classements, tendances.
- Résultats clés: 
  - Taux d’adoption pondéré actuel: X%.
  - Départements en tête: ..., en retard: ...
- Implications: Cibler infrastructures et incitations sur les zones à faible taux.

## 2. Données
- Source: Data.gouv — Voitures particulières immatriculées par commune et type de recharge.
- Période: trimestrielle, multiples années.
- Champs clefs: NB_VP, NB_VP_RECHARGEABLES_EL, NB_VP_RECHARGEABLES_GAZ, CODGEO, LIBGEO, DATE_ARRETE.
- Nettoyage:
  - Exclusion libellés non communaux (Forains, ND, Non identifié).
  - Taux = (EV/VP)*100, borné [0,100].
  - Ajout colonnes ANNEE, TRIMESTRE.
- Caveats: retards de mise à jour, couverture inégale.

## 3. Lancer l’app
```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

## 4. Structure
- app.py: interface Streamlit (onglets Story / Explore / Trends / Data).
- utils.py: chargement + nettoyage, cache.
- data/: (optionnel) dépôt CSV si hors-ligne, sinon lien officiel.

## 5. Interactions
- Filtres: trimestre, départements (avec option DOM‑TOM), taille minimale du parc.
- Explore: carte, Top/Bottom, drilldown communes (barres ou treemap).
- Trends: évolution trimestrielle, hausses/baisses, distributions, variabilité, Lorenz.
- Export: CSV des filtres courants.

## 6. Licence et attribution
- Données: voir licence sur la page Data.gouv.
- Code: MIT (par défaut) — ajuster si besoin.

## 7. Démo vidéo (2–4 min)
- Flow suggéré:
  1) Story (contexte, question, KPI).
  2) Explore (carte → Top/Bottom → commune focus).
  3) Trends (évolution trimestrielle, variations).
  4) Implications + export.