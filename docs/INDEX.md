# Index documentaire — ConsultAI 360

Cette documentation décrit une **mission de conseil simulée** pour NexaRetail. Les données commerciales sont synthétiques, l'expérience de prédiction utilise le jeu public distinct DataCo et les gains financiers sont des hypothèses.

## Cadrage métier

1. [Contexte métier](01_contexte_metier.md)
2. [Diagnostic métier](02_diagnostic_metier.md)
3. [Processus métier](03_processus_metier.md)
4. [Dictionnaire des indicateurs](04_dictionnaire_indicateurs.md)
5. [Périmètre du projet](05_perimetre_projet.md)
6. [Charte de projet](06_charte_projet.md)

## Réalisation et restitution

7. [Problématique de prédiction](07_problematique_prediction.md)
8. [Rapport final de prédiction](08_rapport_final_prediction.md)
9. [Documentation de l'API](09_documentation_api.md)
10. [Rapport Power BI](10_rapport_power_bi.md)
11. [Validation et reproductibilité](11_validation_reproductibilite.md)
12. [Rapport final de conseil](12_rapport_final_conseil.md)

## Références complémentaires

- [Feuille de route](feuille_de_route.md)
- [Schéma relationnel initial](modele_donnees/01_schema_relationnel.md)
- [Organisation technique et dépendances de chemins](guides/organisation_technique.md)
- [Installation de l'assistant IA — guide historique](guides/installation_assistant_ia.md)
- [Ancienne proposition d'API — archive](archives/09_ancienne_proposition_api.md)
- [Guide dbt](../dbt_nexaretail/README.md)
- [Guide Docker](../docker/README.md)
- [Présentation générale du dépôt](../README.md)

## Convention de classement

Les documents métier et de synthèse sont regroupés dans `docs/`. Les guides spécifiques sont dans `docs/guides/`, les archives dans `docs/archives/` et les fichiers produits par les traitements dans `reports/`. Les fichiers `README.md` techniques restent dans les sous-projets concernés.

Les scripts, les définitions dbt, les modèles Power BI et les chemins de données ne sont pas renommés sans contrôle des dépendances.
