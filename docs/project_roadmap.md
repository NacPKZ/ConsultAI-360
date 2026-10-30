# ConsultAI 360 : Roadmap du projet

**Entreprise :** NexaRetail (fictive)

**Mission :** Transformation Data & Intelligence Artificielle

**Durée prévisionnelle :** 180 heures

**Nature du document :** Feuille de route de référence

## 1. Présentation du projet

ConsultAI 360 simule une mission complète de conseil en transformation Data & IA pour NexaRetail, une entreprise fictive française spécialisée dans le commerce omnicanal.

Le projet couvre l'ensemble du cycle de valorisation des données : génération, contrôle qualité, stockage, transformation, analyse, prédiction et exploitation par l'intelligence artificielle.

Il comprend également une évaluation financière et des recommandations stratégiques.

## 2. Organisation générale

| Phase | Activité | Durée estimée |
|---|---|---:|
| 1 | Cadrage métier | 6 h |
| 2 | Génération des données synthétiques | 10 h |
| 3 | Injection d'anomalies et Excel | 10 h |
| 4 | PostgreSQL et qualité des données | 15 h |
| 5 | Data Warehouse et dbt | 15 h |
| 6 | Power BI | 18 h |
| 7 | Machine Learning | 17 h |
| 8 | Assistant IA et Streamlit | 24 h |
| 9 | Analyse financière et ROI | 14 h |
| 10 | Stratégie de transformation | 8 h |
| 11 | Tests et documentation | 21 h |
| 12 | Rapport, présentation et GitHub | 22 h |
| **Total** | | **180 h** |

## 3. Phase 1 — Cadrage métier

**Objectif :** définir les besoins de NexaRetail et les limites de la mission.

**Travaux prévus :**
1. Présentation de NexaRetail.
2. Diagnostic des problématiques métier.
3. Cartographie des processus.
4. Définition des KPI.
5. Définition du périmètre.
6. Validation du cadrage.

**Livrables :** documents de cadrage, diagnostic métier, dictionnaire des KPI et charte de projet.

## 4. Phase 2 — Génération des données synthétiques

**Objectif :** construire un environnement de données réaliste et reproductible.

**Travaux prévus :**
1. Définition du schéma relationnel.
2. Développement des scripts Python.
3. Génération des clients, magasins, produits et employés.
4. Génération des commandes et paiements.
5. Génération des livraisons et réclamations.
6. Vérification des relations entre les tables.
7. Contrôle de la cohérence initiale.
8. Documentation des règles de génération.

**Livrables :** jeux de données synthétiques, scripts Python et documentation technique.

## 5. Phase 3 — Injection d'anomalies et Excel

**Objectif :** simuler des problèmes de qualité des données et établir un diagnostic initial.

**Travaux prévus :**
1. Définition des catégories d'anomalies.
2. Injection contrôlée d'erreurs.
3. Conservation d'une référence des anomalies injectées.
4. Exploration et contrôles dans Excel.
5. Mesure de la qualité initiale.
6. Documentation des anomalies.

**Livrables :** données corrompues, registre des anomalies et rapport de diagnostic.

## 6. Phase 4 — PostgreSQL et qualité des données

**Objectif :** centraliser, contrôler et fiabiliser les données.

**Travaux prévus :**
1. Création de la base PostgreSQL.
2. Importation des données.
3. Développement des contrôles SQL.
4. Détection des anomalies.
5. Application des règles de nettoyage.
6. Évaluation de la précision et du rappel.
7. Vérification des résultats.

**Livrables :** base PostgreSQL, scripts SQL et rapport de qualité.

## 7. Phase 5 — Data Warehouse et dbt

**Objectif :** structurer les données pour les analyses décisionnelles.

**Travaux prévus :**
1. Définition du modèle dimensionnel.
2. Création des tables de faits et dimensions.
3. Développement des transformations dbt.
4. Implémentation des tests.
5. Documentation des modèles.
6. Validation des indicateurs.

**Livrables :** Data Warehouse, projet dbt et documentation du modèle.

## 8. Phase 6 — Power BI

**Objectif :** développer un environnement de pilotage interactif.

**Travaux prévus :**
1. Connexion aux données.
2. Construction du modèle Power BI.
3. Création des mesures DAX.
4. Développement de quatre pages :
   - Vue générale.
   - Performances commerciales.
   - Performance logistique.
   - Qualité des données.
5. Intégration des filtres et interactions.
6. Vérification des KPI.

**Livrables :** rapport Power BI interactif et dictionnaire des mesures.

## 9. Phase 7 — Machine Learning

**Objectif :** expérimenter une approche prédictive sur des données publiques adaptées.

**Travaux prévus :**
1. Sélection du dataset.
2. Analyse exploratoire.
3. Préparation des variables.
4. Définition d'un modèle de référence.
5. Entraînement de modèles prédictifs.
6. Comparaison des performances.
7. Interprétation des résultats.
8. Analyse des limites.

**Livrables :** notebooks, modèles évalués et rapport Machine Learning.

## 10. Phase 8 — Assistant IA et Streamlit

**Objectif :** développer une interface d'analyse assistée par IA.

**Travaux prévus :**
1. Conception de l'interface Streamlit.
2. Connexion aux résultats analytiques.
3. Intégration des KPI.
4. Développement de l'assistant IA.
5. Génération de diagnostics.
6. Formulation de recommandations.
7. Contrôle des réponses.
8. Évaluation sur un ensemble de questions de test.

**Livrables :** application Streamlit, assistant IA et rapport d'évaluation.

## 11. Phase 9 — Analyse financière et ROI

**Objectif :** estimer la valeur économique de la transformation.

**Travaux prévus :**
1. Identification des coûts.
2. Estimation des gains potentiels.
3. Construction de trois scénarios financiers.
4. Calcul du ROI.
5. Analyse de sensibilité.
6. Interprétation des résultats.

**Livrables :** modèle financier et rapport d'analyse du ROI.

## 12. Phase 10 — Stratégie de transformation

**Objectif :** formuler une stratégie Data & IA adaptée aux besoins de NexaRetail.

**Travaux prévus :**
1. Identification des initiatives prioritaires.
2. Évaluation de leur impact et de leur faisabilité.
3. Construction d'une matrice de priorisation.
4. Définition d'une feuille de route à 3, 6 et 12 mois.
5. Formulation des recommandations stratégiques.

**Livrables :** stratégie de transformation et plan d'action.

## 13. Phase 11 — Tests et documentation

**Objectif :** garantir la cohérence et la reproductibilité des résultats.

**Travaux prévus :**
1. Tests des scripts Python.
2. Vérification des transformations SQL.
3. Validation des modèles dbt.
4. Contrôle des KPI Power BI.
5. Évaluation des modèles prédictifs.
6. Tests de l'assistant IA.
7. Documentation technique.
8. Vérification de la reproductibilité.

**Livrables :** rapports de tests et documentation consolidée.

## 14. Phase 12 — Rapport et finalisation

**Objectif :** présenter les résultats sous une forme professionnelle.

**Travaux prévus :**
1. Rédaction du rapport final.
2. Présentation de la méthodologie.
3. Synthèse des résultats techniques.
4. Présentation de l'analyse financière.
5. Formulation des recommandations.
6. Préparation de la présentation.
7. Organisation du dépôt GitHub.
8. Vérification finale des livrables.

**Livrables :** rapport professionnel, présentation et dépôt GitHub documenté.

## 15. Principes méthodologiques

Le développement de ConsultAI 360 repose sur les principes suivants :

- Privilégier la qualité des résultats à la multiplication des fonctionnalités.
- Documenter les hypothèses et les décisions techniques.
- Séparer clairement les données synthétiques des données publiques.
- Vérifier les calculs avant leur interprétation par l'IA.
- Garantir la reproductibilité des analyses.
- Conserver un historique Git des développements.
- Relier les résultats techniques aux besoins métier.
- Distinguer les gains financiers simulés des résultats réellement observés.

## 16. Conclusion

Cette feuille de route constitue le cadre méthodologique de ConsultAI 360.

Elle définit les activités, les objectifs et les livrables des douze phases du projet.

Elle est destinée à rester un document de référence stable, indépendamment de l'avancement des travaux.
