# ConsultAI 360 — Étape 11 : guide technique et reproductibilité

## Objectif
Donner à un lecteur une carte du projet et des points de vérification **sans prétendre fournir un déploiement intégralement automatisé**. Les données sources et certaines sorties ML sont locales ; le dépôt seul ne garantit pas leur présence.

## Architecture fonctionnelle
1. **NexaRetail synthétique** : génération des données et scénarios ORIGINAL, LOW, MEDIUM, CRITICAL ; anomalies contrôlées.
2. **PostgreSQL** : schémas RAW, CLEAN, DW ; contrôles de cohérence et KPI.
3. **dbt** : modèles staging, intermediate, marts, tests de qualité et lineage.
4. **Power BI** : sept pages de pilotage commercial, logistique, qualité, ML, ROI et recommandations.
5. **DataCo ML** : pipeline distinct de prédiction du risque de retard d'expédition.
6. **FastAPI et Streamlit** : exposition et consultation de KPI ; règles métier ; assistant IA avec garde-fous.
7. **ROI** : simulations financières illustratives et recommandations de pilote, non résultats observés.

**Ne pas joindre implicitement NexaRetail, DataCo et simulations ROI : les populations, cibles et hypothèses diffèrent.**

## Où trouver les éléments

| Élément | Chemin |
|---|---|
| Vue d'ensemble et procédure SQL/dbt | `README.md` |
| Scripts SQL | `sql/` |
| Modèles et tests dbt | `dbt_nexaretail/` |
| Tests Python/API/assistant | `tests/` |
| Scripts ML | `src/ml/` |
| Assistant IA | `src/assistant/` |
| API | `api/` |
| Interface Streamlit | `app.py` |
| Rapport ML final | `docs/08_ml_final_report.md` |
| Documentation API | `docs/09_api.md` |
| Documentation Power BI | `docs/10_powerbi_final.md` |
| Bilan des validations | `docs/11_validation_report.md` |

## Contrôle léger déjà exécuté pendant l'étape 11
Depuis l'environnement virtuel Windows du projet :

```powershell
python --version
python -m pytest --version
python -m pytest --collect-only -q tests
python -m pytest -q tests
```

Résultat communiqué le 10 novembre 2026 : Python 3.12.10 ; pytest 9.2.0 ; 31 tests collectés et 31 réussis en 2,87 s.

Ces tests couvrent des comportements de l'API, les règles métier, le score de santé et les garde-fous de l'assistant. Ils ne constituent **pas** une preuve exhaustive de fonctionnement de PostgreSQL réel, Power BI ou Ollama.

## Prérequis à une reconstruction complète
- Python et les dépendances appropriées aux composants lancés.
- PostgreSQL opérationnel, schémas et données sources disponibles.
- Profil dbt et variables d'environnement configurés **localement**.
- Power BI Desktop et fichiers de rapport avec leurs sources accessibles.
- Fichiers DataCo autorisés et artefacts d'évaluation ML nécessaires.
- Ollama et modèle local si l'on souhaite tester la génération de commentaires IA.
- Docker Desktop uniquement pour le chemin d'exécution qui utilise Docker Compose.

Les fichiers `.env`, mots de passe, jeux de données sensibles et artefacts locaux ne doivent pas être publiés. Ne pas remplacer un mot de passe PostgreSQL existant sans connaître l'état des volumes.

## Ce qui n'est pas garanti par ce dépôt
- Installation « un clic » sur un nouvel ordinateur.
- Disponibilité des fichiers sources non versionnés.
- Réexécution exacte de toutes les expériences MLflow et de leurs exports locaux.
- Identité automatique entre exports ML d'analyse de seuil et d'évaluation finale.
- Recalcul de tous les KPI Power BI sans accès aux sources configurées.
- Déploiement public de l'API ou de l'assistant.

## Critères d'utilisation professionnelle
Avant une démonstration client ou une mise en production, exiger :
1. Une source de vérité, les droits d'accès et les définitions de KPI validés.
2. Une vérification des jointures, granularités et taux de couverture.
3. Un test d'intégration avec une vraie base et des données représentatives.
4. La traçabilité des modèles, seuils, splits et exports ML.
5. Des contrôles de sécurité et de non-divulgation des secrets.
6. Un pilote opérationnel pour mesurer l'effet réel des recommandations et du ROI.

## État de l'étape 11
Cette documentation **consolide** le travail existant ; elle ne certifie pas une reconstruction complète depuis zéro. Voir `docs/11_validation_report.md` pour les preuves, réserves et résultats.
