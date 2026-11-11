<div align="center">

# CONSULTAI 360

### From Data Quality to Business Decisions

**Mission de conseil Data, Analytics & Intelligence Artificielle**

**NexaRetail : cas d'étude de transformation data pour une entreprise omnicanale fictive**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![dbt](https://img.shields.io/badge/dbt-Core-FF694B?style=for-the-badge&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![Power BI](https://img.shields.io/badge/Power_BI-DAX-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)

[**Application interactive**](https://consultai-360.streamlit.app/) | [**Rapport final de conseil**](docs/12_rapport_final_conseil.md) | [**Documentation complète**](docs/INDEX.md) | [**Rapport Data Engineering (PDF)**](rapports/01_Rapport_Data_Engineering_Analytics.pdf)

*Novembre 2026 | Projet de portfolio | Données synthétiques et expériences indépendantes*

</div>

---

## Le projet en 30 secondes

**Comment une entreprise peut-elle prendre de bonnes décisions lorsque ses données sont incomplètes, incohérentes ou difficilement exploitables ?**

ConsultAI 360 reproduit une mission de conseil Data et IA de bout en bout pour **NexaRetail**, un distributeur omnicanal fictif. Le projet part de données transactionnelles générées en Python, introduit des anomalies contrôlées, mesure leur impact dans PostgreSQL, construit une couche analytique avec dbt, puis restitue les résultats dans Power BI et une application Streamlit.

En parallèle, une expérimentation de Machine Learning sur le dataset public **DataCo** étudie la prédiction du risque de retard logistique. Une analyse financière simulée complète le diagnostic et débouche sur une proposition de **pilote de 90 jours**.

> **Positionnement :** démonstration de méthode, de compétences et de raisonnement consultant. NexaRetail n'est pas un client réel. Les résultats DataCo ne sont pas des prédictions sur NexaRetail, et les ROI présentés ne sont pas des gains réalisés.

### Les repères essentiels

|  | Indicateur | Portée |
|:--|--:|:--|
| **Données métier** | 10 tables sources | NexaRetail synthétique |
| **Scénarios** | 4 | ORIGINAL, LOW, MEDIUM, CRITICAL |
| **Volume RAW total** | 4 107 649 lignes | Somme des quatre scénarios |
| **Commandes de référence** | 120 000 | Scénario ORIGINAL |
| **Transformation dbt** | 16 modèles et 37 tests | Dernier build historique : 53/53 PASS |
| **Reporting** | 7 pages | Power BI |
| **Tests Python** | 31 réussis | Exécution documentée du 10/11/2026 |
| **Prédiction** | ROC-AUC 0,7605 | Random Forest évalué sur DataCo |

## Explorer la démonstration

<div align="center">

### [Ouvrir ConsultAI 360 sur Streamlit](https://consultai-360.streamlit.app/)

**Application de démonstration interactive**

[Documentation de l'interface et de l'API](docs/09_documentation_api.md) | [Guide d'installation de l'assistant](docs/guides/installation_assistant_ia.md)

</div>

L'application s'inscrit dans la logique du projet : rendre les indicateurs consultables et fournir une interprétation encadrée. Les fonctions métier calculent les chiffres ; le modèle de langage intervient dans la rédaction de commentaires, avec contrôle du format et mécanisme de repli.

L'adresse publique a été communiquée pour le projet. Sa disponibilité permanente et les connexions de production ne sont pas certifiées par la documentation GitHub.

## Technologies, outils et logiciels

### Stack technique

| Domaine | Technologies | Utilisation dans ConsultAI 360 |
|---|---|---|
| **Programmation et simulation** | Python 3.12, pandas, NumPy | Génération, audit, transformations, calculs et automatisation |
| **Base de données** | PostgreSQL 18, SQL, psycopg | Stockage, contrôle qualité, modèle dimensionnel et requêtes KPI |
| **Data Engineering** | dbt Core, dbt-postgres | Staging, transformations intermédiaires, marts et tests |
| **Business Intelligence** | Microsoft Power BI, Power Query, DAX | Modélisation, mesures, tableaux de bord et analyse des scénarios |
| **Machine Learning** | scikit-learn, Random Forest | Classification du risque de retard et comparaison de modèles |
| **Expérimentation ML** | MLflow, analyses de seuils et explicabilité | Traçabilité et analyse des expérimentations documentées |
| **Application web** | Streamlit, Plotly | Interface de démonstration et visualisation interactive |
| **API** | FastAPI, Pydantic | Routes HTTP locales, validation et consultation de KPI |
| **IA générative locale** | Ollama, Llama 3.2 | Commentaires métier contrôlés sur des résultats déterministes |
| **Qualité logicielle** | pytest | Tests unitaires et tests de comportement |
| **Environnement** | Docker, Docker Compose | Configuration PostgreSQL et dbt conteneurisée |
| **Versionnement** | Git, GitHub | Historique, organisation du code et documentation |

### Environnement de travail

| Logiciel | Rôle |
|---|---|
| **Visual Studio Code** | Développement Python, SQL, fichiers de configuration et Git |
| **DBeaver** | Exploration et administration de la base PostgreSQL |
| **Power BI Desktop** | Construction et mise en forme du rapport décisionnel |
| **Microsoft Excel** | Contrôles exploratoires et travail sur les données tabulaires |
| **PowerShell / terminal Windows** | Exécution des scripts, tests et commandes de maintenance |
| **Docker Desktop** | Gestion du moteur Docker local |

Les outils cités n'ont pas tous le même niveau de preuve : certains sont au cœur des traitements vérifiés, d'autres interviennent dans la préparation, l'exploration ou une configuration technique documentée.

## Architecture de la mission

~~~mermaid
flowchart TB
  subgraph N["NexaRetail : données synthétiques"]
    A["Python : génération de 10 tables"] --> B["ORIGINAL / LOW / MEDIUM / CRITICAL"]
    B --> C["PostgreSQL RAW"]
    C --> D["CLEAN : qualification et contrôles"]
    D --> E["DW : dimensions et tables de faits"]
    E --> F["dbt : staging, intermediate, marts"]
    E --> G["KPI SQL et fonctions métier"]
  end
  F --> H["Power BI : 7 pages"]
  G --> I["Streamlit et API locale"]
  I --> J["Ollama : commentaires encadrés"]
  subgraph M["Expérimentation ML indépendante"]
    K["DataCo : données publiques"] --> L["Préparation par commande"]
    L --> P["Baseline / Random Forest"]
    P --> Q["Évaluation et seuil de décision"]
  end
  H --> R["Diagnostic et recommandations"]
  J --> R
  Q --> R
  R --> S["Scénarios ROI et pilote de 90 jours"]
~~~

**Trois périmètres distincts :** NexaRetail fournit les données métier synthétiques, DataCo fournit la population de l'expérience prédictive, et le ROI utilise des hypothèses financières. Leur réunion dans une présentation ne signifie pas qu'ils proviennent d'une même base de données.

[Schéma relationnel détaillé](docs/modele_donnees/01_schema_relationnel.md) | [Organisation technique](docs/guides/organisation_technique.md) | [Feuille de route](docs/feuille_de_route.md)

## 01. Business understanding : comprendre NexaRetail

NexaRetail simule un réseau de distribution omnicanal avec **35 magasins**, **120 000 clients**, **8 000 produits** et **450 employés** dans son scénario de référence.

La mission répond à quatre questions :

1. **Fiabilité :** quelles anomalies perturbent les mesures commerciales et logistiques ?
2. **Pilotage :** comment construire des KPI comparables et interprétables ?
3. **Anticipation :** quelles conditions rendent un modèle de risque logistique exploitable ?
4. **Décision :** quelles initiatives méritent un investissement ou un pilote ?

Le cadrage comprend un diagnostic, une cartographie des processus, un dictionnaire d'indicateurs, une définition du périmètre et une charte de projet.

[Contexte métier](docs/01_contexte_metier.md) | [Diagnostic](docs/02_diagnostic_metier.md) | [Processus](docs/03_processus_metier.md) | [Dictionnaire KPI](docs/04_dictionnaire_indicateurs.md)

## 02. Data generation : quatre scénarios pour tester la robustesse

Les données sont générées artificiellement pour représenter commandes, lignes d'articles, paiements, livraisons, stocks et réclamations. Trois variantes dégradées permettent de tester les contrôles et la résistance des analyses.

| Scénario | Lignes RAW | Fonction |
|---|---:|---|
| **ORIGINAL** | 1 006 394 | Référence synthétique |
| **LOW** | 1 011 524 | Dégradation limitée |
| **MEDIUM** | 1 032 042 | Dégradation intermédiaire |
| **CRITICAL** | 1 057 689 | Dégradation plus importante |
| **TOTAL** | **4 107 649** | Lignes cumulées des dix tables |

Les anomalies incluent notamment des références client ou produit invalides, des paiements non rattachables et des dates manquantes. Leur présence est volontaire : supprimer systématiquement les lignes anormales ferait disparaître une partie du problème à mesurer.

### Exemples de contrôles qualité

| Contrôle | LOW | MEDIUM | CRITICAL |
|---|---:|---:|---:|
| Commandes avec client inconnu | 1 200 | 6 000 | 12 000 |
| Lignes avec produit inconnu | 2 730 | 13 648 | 27 295 |
| Paiements non rattachables | 1 255 | 6 275 | 12 550 |
| Commandes sans date | 1 200 | 6 000 | 12 000 |

Ces comptages concernent des **types d'anomalies et des grains différents**. Ils ne doivent pas être additionnés sans contrôler les recouvrements.

[Diagnostic complet](docs/02_diagnostic_metier.md) | [Schéma et cardinalités](docs/modele_donnees/01_schema_relationnel.md)

## 03. Data Engineering : PostgreSQL, qualité et Data Warehouse

Le parcours de données distingue trois couches :

| Couche | Fonction | Principe |
|---|---|---|
| **RAW** | Conserver les entrées et les scénarios | Traçabilité des données initiales et dégradées |
| **CLEAN** | Typer, contrôler et qualifier | Une donnée contrôlée n'est pas forcément corrigée |
| **DW** | Fournir des faits et dimensions analytiques | Granularités et jointures explicites |

Le modèle dimensionnel sépare les **commandes**, les **lignes de vente**, les **paiements** et les **expéditions**. Cette séparation évite de multiplier artificiellement les montants lorsqu'une commande possède plusieurs articles ou plusieurs opérations associées.

Les membres techniques « Inconnu » permettent de conserver des transactions dont certaines références sont dégradées. Les paiements sans commande identifiable ne sont pas associés arbitrairement à une commande inventée.

### Un résultat métier important : le chiffre d'affaires mesuré

| Scénario | Commandes de référence | CA mesuré | Écart vs ORIGINAL |
|---|---:|---:|---:|
| ORIGINAL | 120 000 | 72 056 406,60 € | Référence |
| LOW | 120 000 | 71 327 494,22 € | -1,01 % |
| MEDIUM | 120 000 | 68 448 127,94 € | -5,01 % |
| CRITICAL | 120 000 | 64 901 512,00 € | -9,93 % |

~~~mermaid
xychart-beta
    title "CA mesuré selon le scénario (millions EUR)"
    x-axis ["ORIGINAL", "LOW", "MEDIUM", "CRITICAL"]
    y-axis "Millions EUR" 0 --> 80
    bar [72.06, 71.33, 68.45, 64.90]
~~~

Dans CRITICAL, le CA mesuré est inférieur de **7 154 894,60 €** à la référence. Il s'agit d'une **sous-estimation de l'indicateur liée à la dégradation des données**, pas d'une perte de ventes ou de trésorerie réellement observée.

[Définitions et limites des KPI](docs/04_dictionnaire_indicateurs.md) | [Rapport Data Engineering en PDF](rapports/01_Rapport_Data_Engineering_Analytics.pdf)

## 04. Analytics Engineering : dbt et tests

Le projet dbt organise les transformations selon trois niveaux :

~~~mermaid
flowchart LR
 A["Sources PostgreSQL"] --> B["Staging : vues"]
 B --> C["Intermediate : vues"]
 C --> D["Marts : tables"]
 D --> E["Analyses et contrôles"]
~~~

Les deux marts métier documentés sont :

- **mart_data_quality_summary** : mesure des anomalies et de leur fréquence par scénario.
- **mart_revenue_impact** : comparaison du CA mesuré avec la référence synthétique.

**Bilan historique : 16 modèles, 37 tests, 11 sources déclarées et 53/53 éléments réussis lors du dernier `dbt build` documenté.** Ce résultat ne signifie pas que 53 tests indépendants ont été exécutés, ni qu'une reconstruction Docker complète vient d'être validée.

[Guide des transformations dbt](dbt_nexaretail/README.md) | [Guide Docker](docker/README.md) | [Registre des preuves](docs/11_validation_reproductibilite.md)

## 05. Business Intelligence : sept pages Power BI

Le rapport adopte une identité visuelle **bleu marine, doré et fond clair**. Chaque page répond à une question métier et distingue les données mesurées des hypothèses.

| Page | Thème | Décision éclairée |
|---|---|---|
| **01** | Vue générale | Suivre les indicateurs clés |
| **02** | Performance commerciale | Comparer magasins et canaux |
| **03** | Performance logistique | Analyser les livraisons évaluables et les retards |
| **04** | Qualité des données | Identifier les anomalies et les exclusions |
| **05** | Analyse IA et prédictions | Présenter les résultats du modèle **DataCo** |
| **06** | Impact financier et ROI | Comparer trois hypothèses de valeur |
| **07** | Recommandations stratégiques | Prioriser les actions et préparer le pilote |

Les pages 1 à 4 concernent les données synthétiques NexaRetail. La page 5 restitue l'expérience ML sur DataCo. Les pages 6 et 7 utilisent notamment des hypothèses financières et une proposition de transformation.

Le projet mobilise **Power Query**, la modélisation relationnelle, les **mesures DAX**, les filtres, les visuels de comparaison, la navigation et la conception d'un rapport décisionnel.

[Documentation détaillée du dashboard](docs/10_rapport_power_bi.md)

## 06. Machine Learning : prédire le risque de retard

L'expérience prédictive utilise **DataCo Supply Chain**, une source publique distincte de NexaRetail. L'objectif est d'estimer le risque de livraison tardive sans employer des informations qui ne seraient connues qu'après l'expédition.

| Élément | Valeur documentée |
|---|---:|
| Lignes d'articles dans la source | 180 519 |
| Commandes distinctes | 65 752 |
| Train | 46 026 commandes |
| Validation | 9 863 commandes |
| Test | 9 863 commandes |
| Cible | `Late_delivery_risk` |

Le protocole prévoit une séparation par commande, la prévention des fuites de données, une baseline, un Random Forest et une analyse des compromis entre fausses alertes et retards non détectés.

### Résultats d'évaluation documentés

| Métrique | Baseline | Random Forest |
|---|---:|---:|
| ROC-AUC | 0,729 | **0,7605** |
| PR-AUC | 0,750 | **0,819** |
| Précision | **0,802** | 0,6588 |
| Rappel | 0,587 | **0,7766** |
| F1 | 0,678 | **0,7129** |
| Faux négatifs | 2 242 | **1 213** |
| Faux positifs | **787** | 2 184 |

**Seuil de décision retenu pour le Random Forest : 0,40.**

Le modèle améliore le rappel et le F1 dans l'évaluation rapportée, mais génère davantage de fausses alertes. Le meilleur choix dépendrait du coût opérationnel de chaque type d'erreur.

Les performances sont **propres à DataCo**. Elles ne constituent ni une validation sur NexaRetail ni la preuve d'une baisse réelle des retards.

[Problématique et protocole](docs/07_problematique_prediction.md) | [Rapport ML et limites](docs/08_rapport_final_prediction.md)

## 07. Assistant IA et API : interpréter sans inventer les chiffres

L'assistant suit une séparation stricte des responsabilités :

~~~mermaid
flowchart LR
 A["Question métier"] --> B["Fonction KPI autorisée"]
 B --> C["PostgreSQL en lecture seule"]
 C --> D["Résultat calculé"]
 D --> E["Commentaire Ollama"]
 E --> F["Contrôle de conformité"]
 F --> G["Réponse ou repli déterministe"]
~~~

- **Calcul :** fonctions Python et requêtes SQL paramétrées.
- **Accès aux données :** rôle PostgreSQL à privilèges limités et transaction en lecture seule.
- **Interprétation :** commentaires générés par un modèle Ollama local.
- **Contrôle :** validation de structure, restrictions sur les chiffres générés et réponse de repli.
- **Interface :** Streamlit.
- **API locale :** FastAPI, avec routes `/health`, `/scenarios` et `/kpis/{scenario}`.

Le LLM **ne génère pas de SQL à exécuter librement**. Le mode démonstration de l'API et l'accès à une base réelle sont deux contextes différents ; le fonctionnement public d'une API de production n'est pas revendiqué.

[Application Streamlit](https://consultai-360.streamlit.app/) | [Documentation API](docs/09_documentation_api.md) | [Installation et sécurité](docs/guides/installation_assistant_ia.md)

## 08. Analyse financière : trois scénarios de ROI

Le modèle financier explore un investissement initial hypothétique de **50 000 €** et des gains annuels supposés.

| Scénario | Gains annuels supposés | Gain net calculé | ROI simulé |
|---|---:|---:|---:|
| Prudent | 68 250 € | 18 250 € | **36,5 %** |
| Central | 105 000 € | 55 000 € | **110 %** |
| Optimiste | 147 000 € | 97 000 € | **194 %** |

Ces calculs dépendent des hypothèses et du périmètre des coûts retenus. Ils **ne mesurent pas un ROI effectivement obtenu**, ne prouvent aucune causalité et ne remplacent pas un budget de production complet.

### Décision de conseil proposée

~~~mermaid
flowchart LR
 A["Fiabiliser les KPI"] --> B["Pilote de 90 jours"]
 B --> C["Mesurer coûts, usages et résultats"]
 C --> D{"Valeur démontrée ?"}
 D -->|Oui| E["Étudier une extension"]
 D -->|Non| F["Corriger ou arrêter"]
~~~

**Recommandation : GO pour un pilote instrumenté, NO-GO pour une industrialisation immédiate.**

[Rapport final de conseil](docs/12_rapport_final_conseil.md) | [Feuille de route](docs/feuille_de_route.md)

## Compétences démontrées

| Famille | Compétences mises en pratique |
|---|---|
| **Conseil Data et stratégie** | Cadrage, diagnostic, définition du périmètre, priorisation, scénarios ROI, recommandation |
| **Business Analysis** | Cartographie des processus, besoins métier, définition et interprétation des KPI |
| **Data Quality** | Profilage, complétude, intégrité référentielle, anomalies, règles de contrôle, traçabilité |
| **Data Engineering** | Génération de données, modélisation relationnelle, pipelines SQL, architecture RAW/CLEAN/DW |
| **Analytics Engineering** | Modélisation dimensionnelle, transformations dbt, marts, tests et lineage |
| **Business Intelligence** | Power Query, DAX, datavisualisation, navigation, reporting décisionnel |
| **Machine Learning** | Préparation, split, prévention des fuites, classification, évaluation, seuils et explicabilité |
| **IA appliquée** | Intégration d'un LLM local, séparation calcul/interprétation, garde-fous, fallback |
| **Développement** | Python, API FastAPI, Streamlit, tests automatisés, configuration |
| **Documentation et qualité** | Git, GitHub, preuves de validation, procédures, limites et reproductibilité |

### Livrables accessibles

| Livrable | Accès |
|---|---|
| **Rapport Data Engineering, Data Quality & Analytics** | [Rapport PDF](rapports/01_Rapport_Data_Engineering_Analytics.pdf) |
| **Dashboard Power BI** | [Rapport de conception et d'analyse](docs/10_rapport_power_bi.md) |
| **Expérimentation Machine Learning** | [Rapport d'évaluation](docs/08_rapport_final_prediction.md) |
| **Application Streamlit** | [Démonstration interactive](https://consultai-360.streamlit.app/) |
| **API FastAPI** | [Documentation et routes](docs/09_documentation_api.md) |
| **Rapport final de conseil** | [Synthèse, ROI et recommandations](docs/12_rapport_final_conseil.md) |
| **Documentation complète** | [Index des 12 chapitres et guides](docs/INDEX.md) |
| **Plan initial et bilan d'évolution** | [Feuille de route](docs/feuille_de_route.md) |
| **Registre de validation** | [Tests et limites](docs/11_validation_reproductibilite.md) |

## Organisation du dépôt

~~~text
ConsultAI-360/
├── api/                    # API FastAPI locale
├── app.py                  # Interface Streamlit
├── data/                   # Données locales selon disponibilité
├── dbt_nexaretail/         # Modèles, tests et configuration dbt
├── docker/                 # Profil de connexion dbt Docker
├── docs/                   # 12 chapitres, guides, index et archives
├── rapports/               # Rapport PDF conservé
├── reports/                # Sorties et artefacts analytiques
├── sql/                    # Scripts PostgreSQL numérotés
├── src/
│   ├── assistant/          # Fonctions KPI et règles IA
│   └── ml/                 # Préparation et évaluation DataCo
├── tests/                  # Tests Python
├── compose.yaml            # Configuration Docker Compose
├── Dockerfile.dbt          # Image d'exécution dbt
└── README.md
~~~

Cette arborescence est une **vue fonctionnelle simplifiée**. D'autres fichiers, dossiers techniques et artefacts peuvent être présents.

[Guide de l'organisation technique](docs/guides/organisation_technique.md) | [Schéma relationnel](docs/modele_donnees/01_schema_relationnel.md)

## Installer le projet en local : PostgreSQL, dbt et Streamlit

Cette section s'adresse à une personne qui **clone le dépôt et veut faire fonctionner le projet sur son propre ordinateur**, notamment connecter PostgreSQL à dbt et à l'assistant IA. Les commandes ci-dessous sont prévues pour **Windows et PowerShell**, depuis la racine du dépôt.

**À savoir avant de commencer :** cloner le dépôt récupère le code et les configurations, mais **ne récupère pas automatiquement les données de ta base PostgreSQL personnelle**. Le serveur peut donc démarrer correctement tout en contenant une base vide. Il faut ensuite générer ou importer les données NexaRetail, puis construire les tables analytiques.

### Étape 1 : récupérer le dépôt et installer les outils

Prérequis : **Git**, **Python**, **Docker Desktop** (moteur démarré) et, pour consulter la base, **DBeaver** ou un autre client PostgreSQL. **Power BI Desktop** et **Ollama** sont facultatifs pour la seule connexion PostgreSQL.

~~~powershell
git clone https://github.com/NacPKZ/ConsultAI-360.git
cd ConsultAI-360

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
~~~

Si PowerShell bloque l'activation de l'environnement virtuel, utiliser directement `.\.venv\Scripts\python.exe` pour exécuter Python, sans modifier les règles de sécurité de Windows.

### Étape 2 : lancer PostgreSQL avec Docker

Le fichier `compose.yaml` définit une base PostgreSQL 18 nommée `nexaretail_db`. **Choisir son propre mot de passe**, puis le transmettre à Docker dans la session PowerShell :

~~~powershell
$env:DOCKER_POSTGRES_PASSWORD = Read-Host "Mot de passe PostgreSQL"

docker compose up -d postgres
docker compose ps
~~~

Pour confirmer que PostgreSQL répond :

~~~powershell
docker compose exec postgres pg_isready -U postgres -d nexaretail_db
~~~

Résultat attendu : le serveur indique qu'il accepte les connexions. **Cela ne signifie pas encore que les tables NexaRetail sont présentes.**

### Étape 3 : connecter DBeaver à PostgreSQL

Créer une nouvelle connexion **PostgreSQL** avec les paramètres suivants :

| Paramètre DBeaver | Valeur |
|---|---|
| Hôte | `127.0.0.1` |
| Port | `5433` |
| Base de données | `nexaretail_db` |
| Utilisateur | `postgres` |
| Mot de passe | Celui choisi à l'étape 2 |

Cliquer sur **Tester la connexion**. Si DBeaver propose de télécharger le pilote PostgreSQL, accepter.

**Pourquoi 5433 et non 5432 ?** Le conteneur écoute sur `5432` en interne, mais `compose.yaml` expose le port **5433 sur ton ordinateur**. À l'intérieur du réseau Docker, dbt utilise `postgres:5432`. Ces deux adresses ne sont pas interchangeables.

### Étape 4 : créer et alimenter les tables NexaRetail

La base créée par Docker est initialement vide. Pour obtenir les mêmes analyses, il faut disposer des **dix tables sources** et respecter l'ordre des traitements :

1. Préparer ou générer les données synthétiques des quatre scénarios.
2. Exécuter les scripts d'import dans le schéma **RAW**.
3. Appliquer les contrôles et traitements **CLEAN**.
4. Construire les dimensions et tables de faits **DW**.
5. Vérifier les volumes, les clés, les scénarios et les KPI avant de lancer dbt.

Les scripts sont classés dans [`sql/`](sql/) et leur organisation est détaillée dans le [guide technique](docs/guides/organisation_technique.md). Les chemins d'import, les données disponibles et les dépendances doivent être adaptés à l'ordinateur utilisé.

**Point bloquant possible :** si les CSV ou autres données d'entrée nécessaires ne sont pas fournis dans le dépôt, il faut les régénérer à partir des scripts disponibles ou obtenir les fichiers attendus. **Ne pas considérer une base vide comme un échec de connexion.**

### Étape 5 : connecter dbt à cette même base

Le profil `docker/dbt/profiles.yml` utilise déjà :

- Hôte : `postgres`
- Port : `5432`
- Base : `nexaretail_db`
- Mot de passe : variable `DBT_POSTGRES_PASSWORD`, alimentée par Compose à partir de `DOCKER_POSTGRES_PASSWORD`

Dans **la même session PowerShell** que l'étape 2 :

~~~powershell
docker compose build dbt
docker compose --profile tools run --rm dbt debug
docker compose --profile tools run --rm dbt build
~~~

**`dbt debug`** vérifie la configuration et la connexion. **`dbt build`** exécute les modèles et tests, mais peut échouer si les schémas et tables sources ne sont pas encore chargés. Les 53 éléments réussis rapportés dans la documentation sont un **résultat historique**, pas une garantie sur une nouvelle installation.

### Étape 6 : connecter l'assistant IA à PostgreSQL

Le code de l'assistant lit la variable d'environnement **`ASSISTANT_DATABASE_URL`**. Il interroge notamment `dw.fact_orders` et `dw.fact_shipments`. Pour limiter les risques, créer un utilisateur PostgreSQL **en lecture seule** une fois le DW disponible.

Depuis DBeaver, avec le compte administrateur, exécuter en remplaçant le mot de passe d'exemple :

~~~sql
CREATE ROLE assistant_ro LOGIN PASSWORD 'CHOISIR_UN_MOT_DE_PASSE_DISTINCT';
GRANT CONNECT ON DATABASE nexaretail_db TO assistant_ro;
GRANT USAGE ON SCHEMA dw TO assistant_ro;
GRANT SELECT ON dw.fact_orders, dw.fact_shipments TO assistant_ro;
~~~

Ne pas recréer le rôle s'il existe déjà. Ne pas utiliser le compte administrateur dans une application exposée au public.

Créer ensuite un fichier local **`.env`**, exclu de Git, à la racine du dépôt :

~~~dotenv
ASSISTANT_DATABASE_URL=postgresql://assistant_ro:VOTRE_MOT_DE_PASSE@127.0.0.1:5433/nexaretail_db
~~~

Si le mot de passe contient des caractères spéciaux, les encoder correctement dans l'URL. **Ne jamais publier ce fichier, un vrai mot de passe ou une capture qui le montre.**

Installer les dépendances de l'assistant et tester sa connexion :

~~~powershell
python -m pip install -r requirements-assistant.txt
python -m src.assistant.check_connection
~~~

Le contrôle affiche des KPI issus de la base locale. Si une table `dw` manque, il faut d'abord terminer l'étape 4, et non modifier arbitrairement le code Python.

### Étape 7 : démarrer Streamlit et, si nécessaire, Ollama

~~~powershell
streamlit run app.py
~~~

L'application locale est normalement accessible sur **http://localhost:8501**. Certaines fonctionnalités peuvent nécessiter des dépendances ou une configuration supplémentaires.

Pour les commentaires générés localement, installer et démarrer **Ollama**, puis télécharger le modèle utilisé dans le projet :

~~~powershell
ollama pull llama3.2:1b
~~~

La présence d'Ollama n'est pas nécessaire pour simplement vérifier que PostgreSQL répond. L'application publique [ConsultAI 360](https://consultai-360.streamlit.app/) est une démonstration distincte de cet environnement local.

### Problèmes fréquents

| Symptôme | Cause probable | Vérification utile |
|---|---|---|
| `DOCKER_POSTGRES_PASSWORD` manquant | Variable non définie dans cette session | Refaire l'étape 2 dans le terminal actif |
| Docker ne démarre pas | Docker Desktop ou son moteur est arrêté | Démarrer Docker Desktop, puis `docker compose ps` |
| DBeaver refuse la connexion | Mauvais port, mot de passe ou conteneur arrêté | Utiliser `127.0.0.1:5433`, vérifier `docker compose ps` |
| `dbt debug` échoue | Profil, réseau Docker ou authentification | Vérifier `docker/dbt/profiles.yml` et la variable |
| `dbt build` signale une source absente | Données RAW/CLEAN non importées | Terminer l'étape 4 |
| `ASSISTANT_DATABASE_URL manquant` | Fichier `.env` absent ou non chargé | Vérifier le fichier local et le lancement via `check_connection` |
| `relation dw.fact_orders does not exist` | Data Warehouse non construit | Exécuter les scripts DW |
| Streamlit affiche des KPI vides | Base vide ou scénario non chargé | Vérifier les données dans DBeaver |

Pour arrêter sans effacer volontairement le volume de données :

~~~powershell
docker compose down
~~~

**Attention :** `docker compose down -v` supprime les volumes associés et peut détruire la base PostgreSQL locale.

### Ce qui est reproductible, et ce qui reste à vérifier

Le dépôt fournit **une procédure de démarrage et des composants documentés**, mais **l'installation intégrale sur un ordinateur neuf n'a pas encore été testée de bout en bout**. Les scripts d'import, les données requises, les secrets et certaines dépendances doivent être vérifiés avant de promettre un résultat identique. Les tests Python et dbt déjà publiés restent des preuves **historiques**.

[Guide Docker détaillé](docker/README.md) | [Guide dbt](dbt_nexaretail/README.md) | [Installation de l'assistant](docs/guides/installation_assistant_ia.md) | [Validation et limites](docs/11_validation_reproductibilite.md)

## Documentation : choisir son parcours

| Profil | Parcours conseillé |
|---|---|
| **Recruteur ou jury** | [Rapport final](docs/12_rapport_final_conseil.md) puis [Power BI](docs/10_rapport_power_bi.md) |
| **Consultant / Business Analyst** | [Contexte](docs/01_contexte_metier.md), [diagnostic](docs/02_diagnostic_metier.md), [KPI](docs/04_dictionnaire_indicateurs.md) |
| **Data Engineer / Analytics Engineer** | [Schéma](docs/modele_donnees/01_schema_relationnel.md), [dbt](dbt_nexaretail/README.md), [validation](docs/11_validation_reproductibilite.md) |
| **Data Scientist** | [Problématique ML](docs/07_problematique_prediction.md), [rapport ML](docs/08_rapport_final_prediction.md) |
| **Développeur IA** | [API](docs/09_documentation_api.md), [assistant](docs/guides/installation_assistant_ia.md) |

Le **[centre de documentation](docs/INDEX.md)** regroupe les douze chapitres, les guides techniques, les archives et plusieurs parcours de lecture.

## Ce que le projet apporte

ConsultAI 360 ne se limite pas à entraîner un modèle ou à produire un dashboard. Il montre comment relier une anomalie de données à une mesure, une mesure à une décision, et une décision à un protocole de validation.

Le principe directeur est simple : **des calculs vérifiables, des limites explicites et des recommandations proportionnées aux preuves disponibles**.

---

<div align="center">

### CONSULTAI 360

**Data Quality | Analytics Engineering | Business Intelligence | Machine Learning | AI Applications | Data Strategy**

[Application Streamlit](https://consultai-360.streamlit.app/) | [Documentation](docs/INDEX.md) | [Rapport final](docs/12_rapport_final_conseil.md) | [Bilan de validation](docs/11_validation_reproductibilite.md)

*Portfolio technique et conseil, NexaRetail (entreprise fictive), novembre 2026.*

</div>
