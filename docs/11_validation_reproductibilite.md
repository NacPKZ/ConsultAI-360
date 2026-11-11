# 11 : Registre de validation et reproductibilité

<div align="center">

**CONSULTAI 360 | DOSSIER DE CONSEIL**

[Accueil du projet](../README.md) | [Sommaire documentaire](INDEX.md) | [Application Streamlit](https://consultai-360.streamlit.app/)

</div>


Date du bilan : 10 novembre 2026.

## Périmètre et méthode
Cette étape consolide les contrôles déjà réalisés. Elle ne réexécute pas les traitements métier, l'entraînement ML, les transformations SQL/dbt ou les applications déjà vérifiées lors des étapes précédentes.

Trois niveaux de preuve sont distingués :
- **Exécuté le 10/11/2026** : résultat de commande communiqué pendant l'étape 11.
- **Historique documenté** : résultat déclaré dans les livrables des étapes précédentes, non rejoué pendant l'étape 11.
- **Non vérifié dans cette étape** : aucun résultat nouveau permettant d'attester le fonctionnement courant.

## Matrice de validation

| Domaine | Preuve | Statut | Limite |
|---|---|---|---|
| Environnement Python | Python 3.12.10 ; pytest 9.2.0 ; environnement virtuel actif | Exécuté le 10/11/2026 | Environnement Windows local |
| Tests Python / API / assistant | `python -m pytest -q tests` : **31 passed in 2.87s** | Exécuté le 10/11/2026 | Les tests API avec fonctions PostgreSQL simulées ne prouvent pas une connexion réelle |
| Git | Branche `main`, commit initial `e5c89ac`, `git status --short` vide | Observé le 10/11/2026 | État antérieur à l'ajout de ce bilan |
| dbt | README : 16 modèles, 37 tests, 11 sources ; dernier `dbt build` **53/53 PASS** | Historique documenté | Non rejoué pendant l'étape 11 |
| Contrôles SQL / DW | README : contrôles de volumes, sommes, scénarios et tests finaux PASS | Historique documenté | Non rejoués pendant l'étape 11 |
| API | `docs/09_documentation_api.md` ; tests de routes et de données simulées | Tests Python exécutés ; documentation historique | Intégration réelle PostgreSQL non attestée par ces tests |
| Streamlit, Ollama, Docker | Fonctionnement précédemment testé, confirmé par le porteur du projet | Validation antérieure déclarée | Aucun test courant supplémentaire, conformément au périmètre de l'étape |
| Power BI | `docs/10_rapport_power_bi.md` : architecture à sept pages et contrôles antérieurs | Historique documenté | Pas de vérification visuelle ou de recalcul DAX pendant l'étape 11 |
| ML DataCo | `docs/08_rapport_final_prediction.md` : évaluation finale du Random Forest | Historique documenté | Pas de réentraînement ni de réévaluation pendant l'étape 11 |
| Reproductibilité | Instructions partielles dans README et documents spécialisés | Documentée partiellement | Reconstruction complète sur machine vierge non démontrée |

## Incident Docker observé pendant l'audit
La commande `docker compose ps` a d'abord échoué faute de variable `DOCKER_POSTGRES_PASSWORD` dans la configuration disponible pour Compose. Un second diagnostic a indiqué que le moteur Docker Desktop était inaccessible à ce moment-là. Le fichier `.env` existait, sans que son contenu soit divulgué.

Ces constats **ne prouvent ni une corruption de la base ni un défaut des transformations dbt**. Aucune modification des secrets, des volumes ou des services n'a été entreprise. Le porteur du projet a confirmé avoir déjà validé ces composants et a choisi de ne pas répéter ces tests.

## Points de vigilance méthodologiques
1. **NexaRetail** : entreprise fictive, données synthétiques ; les écarts de CA mesurés entre scénarios ne sont pas des pertes financières réelles.
2. **DataCo** : dataset public distinct, cible de risque de retard d'expédition ; performances non transférables automatiquement à NexaRetail.
3. **Random Forest** : le seuil 0,40 est une règle de décision choisie sur validation, non un optimum économique démontré.
4. **Exports ML** : la provenance des exports d'analyse de seuil et d'évaluation finale doit être réconciliée avant toute affirmation d'identité parfaite des métriques.
5. **ROI** : scénarios financiers hypothétiques, sans gains réalisés ni causalité démontrée.
6. **Reproductibilité** : le fonctionnement local antérieur ne prouve pas qu'un tiers peut tout reconstruire depuis un dépôt vierge.

## Décision de clôture
Les tests Python existants sont validés (**31/31**). Les autres composants sont retenus sur la base des preuves historiques et des validations précédentes, **sans nouvelle certification technique**. L'étape 11 peut être clôturée en tant que **consolidation documentaire des preuves existantes**, avec les réserves ci-dessus. Aucun nouveau test ou refactoring n'est nécessaire pour cette clôture limitée.

## Références internes
- `README.md`
- `docs/08_rapport_final_prediction.md`
- `docs/09_documentation_api.md`
- `docs/10_rapport_power_bi.md`
- `tests/`
- `dbt_nexaretail/tests/`

---

## Annexe : Guide technique et reproductibilité

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
| Rapport ML final | `docs/08_rapport_final_prediction.md` |
| Documentation API | `docs/09_documentation_api.md` |
| Documentation Power BI | `docs/10_rapport_power_bi.md` |
| Bilan des validations | ce document |

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
Cette documentation **consolide** le travail existant ; elle ne certifie pas une reconstruction complète depuis zéro. Voir ce document pour les preuves, réserves et résultats.

---

## Application hébergée et limites de la preuve

**URL fournie pour la démonstration :** [ConsultAI 360 sur Streamlit](https://consultai-360.streamlit.app/).

La présence de cette URL est une information de publication communiquée par le porteur du projet. Elle ne démontre **ni une disponibilité permanente, ni une connexion PostgreSQL de production, ni l'exposition de l'API FastAPI**. L'état actuel du site n'a pas pu être établi par cette revue.

## Matrice de lecture pour un évaluateur

| Niveau de preuve | Exemple | Ce que l'on peut conclure |
|---|---|---|
| **Test exécuté** | 31 tests Python réussis le 10/11/2026 | Les cas couverts ont passé dans cet environnement |
| **Résultat historique** | 53/53 PASS dbt | Un build antérieur a été déclaré réussi |
| **Livrable documenté** | Sept pages Power BI | Une structure et des indicateurs sont décrits |
| **Lien de démonstration** | Application Streamlit | Une adresse publique a été fournie |
| **Non démontré** | Reconstruction complète depuis zéro | Aucune garantie de reproductibilité intégrale |

### Protocole minimal pour une future revue externe

1. Relever le commit et les versions logicielles.
2. Identifier les fichiers de données effectivement accessibles.
3. Vérifier la connexion à une base de test et les droits de lecture.
4. Exécuter les tests pertinents en conservant les journaux.
5. Comparer les résultats SQL, Power BI et les exports ML sur des périmètres identiques.
6. Documenter les écarts, les limites et les corrections nécessaires.

Ce protocole **n'a pas été exécuté** dans le cadre de cette mise à jour des textes.


---

## Ce que cette partie m'a appris

> [!NOTE]
> **Notion clé : Test unitaire et test d'intégration**
> Un test avec une base simulée peut valider une fonction, mais pas la connectivité réelle, les droits d'accès ou les performances de PostgreSQL.

> [!TIP]
> **Exercice pratique**
> Classer les preuves par environnement, date, composant et niveau de test.

> [!WARNING]
> **Erreur à éviter**
> Présenter 31 tests Python réussis comme une certification de toute l'architecture.

> [!IMPORTANT]
> **À retenir pour un entretien**
> Chaque preuve doit être accompagnée de son périmètre.

### Passer de la théorie à la pratique

| En situation professionnelle | Réflexe recommandé |
|---|---|
| Avant de développer | Clarifier la question métier et les données disponibles |
| Pendant l'analyse | Vérifier les hypothèses, les granularités et les exclusions |
| Avant de présenter | Distinguer résultats mesurés, simulations et limites |
| Après la restitution | Documenter les décisions, les actions et les contrôles à poursuivre |

### Navigation dans le dossier

[Chapitre précédent](10_rapport_power_bi.md) | **11 / 12 : Validation et reproductibilité** | [Chapitre suivant](12_rapport_final_conseil.md)

[Retour au sommaire documentaire](INDEX.md)
