# NexaRetail : Définition du périmètre

**Projet :** ConsultAI 360

**Mission :** Transformation Data & Intelligence artificielle

**Document :** Project Scope : Version 1.0

## 1. Objectif du projet

ConsultAI 360 vise à concevoir une solution intégrée de traitement, d'analyse et d'exploitation des données pour NexaRetail, une entreprise fictive de commerce omnicanal.

Le projet simule une mission de conseil couvrant l'ensemble du cycle de valorisation des données, depuis leur génération jusqu'à la formulation de recommandations stratégiques.

La durée prévisionnelle de réalisation est fixée à 180 heures.

## 2. Fonctionnalités incluses

### 2.1. Data Quality Center

Ce module permettra de :

- Générer des données synthétiques cohérentes.
- Injecter volontairement des anomalies.
- Détecter les erreurs avec Python et SQL.
- Appliquer des règles de correction.
- Mesurer les performances du nettoyage.
- Documenter les anomalies et les corrections.

**Livrable :** pipeline de qualité des données accompagné d'un rapport d'évaluation.

### 2.2. Business Intelligence Center

Ce module comprendra :

- La centralisation des données dans PostgreSQL.
- La création d'un Data Warehouse.
- Les transformations et tests avec dbt.
- Le calcul des indicateurs de performance.
- La création d'un rapport Power BI interactif.

Le rapport comportera quatre pages consacrées aux performances générales, aux ventes, à la logistique et à la qualité des données.

**Livrable :** rapport Power BI et modèle analytique documenté.

### 2.3. Predictive Analytics Center

Ce module visera à :

- Sélectionner un jeu de données public adapté.
- Réaliser une analyse exploratoire.
- Préparer les variables.
- Comparer plusieurs modèles prédictifs.
- Évaluer leurs performances.
- Interpréter les résultats et leurs limites.

Les résultats issus du jeu de données public seront distingués des données simulées de NexaRetail.

**Livrable :** modèle de Machine Learning évalué et notebook documenté.

### 2.4. AI Consulting Center

Ce module permettra de :

- Développer une application Streamlit.
- Consulter les principaux KPI.
- Interroger un assistant IA.
- Générer des diagnostics à partir de résultats calculés.
- Proposer des recommandations métier.
- Tester la fiabilité des réponses.

Les calculs seront effectués par Python ou SQL. L'intelligence artificielle interviendra principalement dans l'interprétation des résultats.

**Livrable :** application interactive et rapport d'évaluation de l'assistant.

## 3. Analyse financière et stratégique

Le projet comprendra également :

- Une estimation des coûts de développement et d'exploitation.
- Une évaluation des bénéfices potentiels.
- Trois scénarios financiers.
- Une analyse de sensibilité.
- Une estimation du retour sur investissement.
- Une matrice de priorisation des initiatives.
- Une feuille de route de transformation à 3, 6 et 12 mois.

Les résultats financiers correspondront à des simulations et non à des gains réellement observés.

## 4. Éléments exclus du périmètre

Les fonctionnalités suivantes ne seront pas développées :

- Plateforme e-commerce opérationnelle.
- Système de paiement réel.
- Application mobile.
- Infrastructure cloud de production.
- Système complet de gestion des stocks.
- Déploiement dans une entreprise réelle.
- Entraînement d'un grand modèle de langage.
- Automatisation complète des décisions stratégiques.

Certaines technologies complémentaires, comme Docker, FastAPI ou MLflow, pourront être étudiées si le temps disponible le permet.

## 5. Contraintes du projet

Le projet devra respecter plusieurs contraintes :

**Temps :** budget prévisionnel de 180 heures.

**Données :** utilisation de données internes synthétiques et de données publiques documentées.

**Technologies :** priorité aux outils définis dans le cahier des charges.

**Qualité :** validation des résultats et reproductibilité des analyses.

**Documentation :** conservation des scripts, tests, hypothèses et décisions techniques.

**Confidentialité :** aucune donnée personnelle réelle ni clé API ne devra être publiée.

## 6. Critères de réussite

Le projet sera considéré comme abouti lorsque :

1. Les données synthétiques pourront être reproduites.
2. Les anomalies seront détectées et mesurées.
3. Le Data Warehouse sera fonctionnel.
4. Les KPI Power BI seront vérifiés.
5. Le modèle prédictif sera évalué.
6. L'assistant IA sera testé sur 20 questions.
7. Les scénarios financiers seront documentés.
8. Les recommandations seront justifiées.
9. Le dépôt GitHub permettra de comprendre et de reproduire les principales analyses.
10. Les livrables universitaires et professionnels seront finalisés.

## 7. Conclusion

Le périmètre retenu vise à concilier ambition technique, cohérence métier et faisabilité.

ConsultAI 360 doit démontrer une démarche complète de transformation Data & IA sans chercher à reproduire l'ensemble des systèmes informatiques d'une entreprise réelle.

La priorité sera accordée à la fiabilité des résultats, à la qualité des livrables et à la capacité de justifier les choix techniques et stratégiques.
