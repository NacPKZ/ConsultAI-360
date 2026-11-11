# 01 : NexaRetail : Contexte et ambition de transformation

<div align="center">

**CONSULTAI 360 | DOSSIER DE CONSEIL**

[Accueil du projet](../README.md) | [Sommaire documentaire](INDEX.md) | [Application Streamlit](https://consultai-360.streamlit.app/)

</div>


> **CONSULTAI 360 / DOSSIER DE CADRAGE**  
> **Statut :** contexte métier fictif et hypothèses initiales, enrichis par les réalisations documentées | **Secteur :** distribution omnicanale | **Périmètre :** étude de cas, aucune entreprise cliente réelle.

[← Index documentaire](INDEX.md) | [Diagnostic →](02_diagnostic_metier.md) | [Rapport final](12_rapport_final_conseil.md)

## Regard consultant : ce que la direction doit retenir

La modernisation analytique ne commence pas par le choix d'un outil. Elle commence par un **accord sur la signification des données**. Une direction peut disposer de tableaux très soignés et prendre de mauvaises décisions si les montants non attribuables ou les exclusions sont invisibles.

### Trois décisions structurantes

| Décision | Option à éviter | Option retenue dans l'étude |
|:--|:--|:--|
| Traitement des anomalies | Supprimer toute ligne imparfaite | Préserver les événements et qualifier leur fiabilité |
| Développement de l'IA | Confier les calculs au modèle génératif | Séparer calcul déterministe et commentaire |
| Passage à l'échelle | Généraliser sur la base d'une démonstration | Préparer un pilote limité, mesurable et réversible |

### Questions ouvertes pour une mission réelle

- Quelles sources sont juridiquement et opérationnellement reconnues comme référentielles ?
- Qui arbitre un désaccord entre Finance, Commerce et Logistique sur la définition d'un KPI ?
- Quel niveau de couverture est acceptable pour décider, selon le risque associé ?
- Quels usages de l'IA justifient une intervention humaine systématique ?

Ces questions ne peuvent pas être résolues par les données synthétiques seules.

---
## L'essentiel en 30 secondes

NexaRetail est une **entreprise française fictive de distribution omnicanale**. Sa problématique n'est pas seulement de produire davantage de tableaux de bord : elle doit rendre ses données **traçables, comparables et utilisables pour décider**, tout en évitant de confondre expérimentation IA et déploiement industriel.

| Repère de simulation | Valeur de référence | Lecture |
|:--|--:|:--|
| Magasins | **35** | Réseau physique fictif |
| Clients | **120 000** | Population synthétique |
| Collaborateurs | **450** | Effectif fictif |
| Produits | **8 000** | Catalogue simulé |
| Commandes originales | **120 000** | Volume effectivement documenté dans le jeu ORIGINAL |
| Horizon de données | **24 mois** | Hypothèse de cadrage |
| Canaux | **Magasin + e-commerce** | Commerce omnicanal |

> [!IMPORTANT]
> Ces valeurs décrivent un **univers de simulation**. Elles ne représentent ni des données d'entreprise réelle, ni des observations de marché. La fourchette de 100 000 à 150 000 commandes figurait dans le cadrage initial ; le jeu ORIGINAL documenté contient 120 000 commandes.

## 1. La situation métier

Le parcours d'achat traverse plusieurs fonctions : catalogue, vente, paiement, préparation, livraison et service après-vente. Chaque étape produit des données utiles, mais leur interprétation devient fragile lorsque les identifiants, les dates, les montants ou les règles de calcul divergent.

Trois questions structurent la mission :

1. **Peut-on faire confiance aux chiffres ?** Une vente peut exister sans être attribuable à un client connu ; un paiement peut être enregistré sans commande rattachable.
2. **Peut-on expliquer les performances ?** Les ventes, la logistique et les réclamations doivent être analysées à la bonne granularité, avec des définitions communes.
3. **Peut-on investir rationnellement dans la Data et l'IA ?** Les cas d'usage doivent être évalués selon leur valeur potentielle, leurs dépendances et leurs risques.

### Les équipes concernées

| Fonction | Décision à éclairer | Données pertinentes | Risque si l'information est dégradée |
|:--|:--|:--|:--|
| Direction générale | Prioriser les investissements | KPI consolidés, scénarios ROI | Arbitrages fondés sur des chiffres non comparables |
| Finance | Suivre le revenu mesuré | Commandes, paiements, remises | Confusion entre montant manquant et perte économique |
| Commercial | Comparer les canaux et magasins | Ventes, produits, clients | Mauvaise attribution des performances |
| Marketing | Comprendre les segments | Clients, commandes | Analyses biaisées par les identifiants absents |
| Logistique | Suivre les livraisons | Expéditions, dates, modes | Retards mal dénombrés ou non évaluables |
| Service client | Qualifier les irritants | Réclamations, commandes | Difficulté à relier les incidents aux parcours |

## 2. Cinq enjeux de transformation

### 01 : Qualité et gouvernance des données

Les données simulées sont dégradées volontairement selon des scénarios **ORIGINAL, LOW, MEDIUM et CRITICAL**. L'objectif est de mesurer l'effet d'erreurs observables, sans effacer artificiellement les transactions problématiques.

**Décision de conception :** distinguer une donnée *techniquement exploitable* d'une donnée *métier complète*. Une ligne sans référence valide reste visible et son absence d'attribution doit être mesurée.

### 02 : Reporting fragmenté

Le contexte initial suppose des extractions et fichiers Excel dispersés. La réponse proposée consiste à établir une chaîne **PostgreSQL → transformations et contrôles → Data Warehouse → Power BI**, avec des définitions de KPI explicites.

### 03 : Performance logistique

Le pilotage doit distinguer les livraisons **à temps**, **en retard** et **non évaluables**. Le dénominateur d'un taux de retard est aussi important que le numérateur ; une date absente ne doit pas être traitée silencieusement comme une livraison ponctuelle.

### 04 : Exploitation analytique

Le modèle décisionnel vise à rapprocher performances commerciales, qualité de données et indicateurs opérationnels sans confondre les granularités **commande**, **ligne de vente**, **paiement** et **expédition**.

### 05 : IA et allocation du capital

Un assistant peut expliquer des KPI calculés, mais ne doit pas inventer les résultats. Une expérience de prédiction peut démontrer une méthode sans prouver sa transférabilité à NexaRetail. Enfin, un ROI modélisé reste **hypothétique** tant qu'un pilote n'a pas mesuré les gains.

## 3. La mission ConsultAI 360

> **Question directrice**  
> Comment transformer un environnement de données imparfait en un système d'aide à la décision **fiable, explicable et économiquement défendable**, sans surpromettre les capacités de l'IA ?

| Axe | Travail réalisé ou documenté | Preuve à consulter |
|:--|:--|:--|
| Data Quality | Simulation, anomalies, contrôles et impacts | [Diagnostic](02_diagnostic_metier.md) |
| Data Engineering | PostgreSQL, schémas RAW/CLEAN/DW, dbt | [README technique dbt](../dbt_nexaretail/README.md) |
| Business Intelligence | Dashboard Power BI à **7 pages** | [Rapport BI](10_rapport_power_bi.md) |
| Data Science | Risque de retard sur le **dataset public DataCo** | [Évaluation ML](08_rapport_final_prediction.md) |
| IA analytique | Application Streamlit et assistant à calculs contrôlés | [Périmètre](05_perimetre_projet.md) |
| Conseil | Scénarios ROI et recommandations de transformation | [Rapport final](12_rapport_final_conseil.md) |

## 4. Deux univers de données : une séparation indispensable

```text
NEXARETAIL (synthétique)                 DATACO (public, indépendant)
Clients | ventes | paiements            Données logistiques DataCo
Livraisons | stocks | réclamations       |
        |                                v
        v                           Expérience de prédiction
PostgreSQL / dbt / Power BI               |
        |                                v
        v                           Évaluation hors NexaRetail
KPI métier / assistant / ROI
```

**Aucun score ML DataCo ne doit être présenté comme une prédiction validée sur les commandes NexaRetail.** Les avis textuels publics éventuellement explorés constituent également un corpus indépendant.

## 5. Ce que signifie « réussir »

La réussite de cette étude de cas repose sur cinq exigences : **définitions stables**, **calculs vérifiables**, **anomalies visibles**, **limites explicites** et **recommandations actionnables**. Elle ne suppose ni plateforme de production ni déploiement chez un client.

### Points de vigilance

- Les écarts de chiffre d'affaires entre scénarios décrivent une **sous-estimation de l'indicateur mesuré**, pas des ventes effectivement perdues.
- Les validations SQL, dbt, Python, Power BI et Docker n'ont pas toutes été exécutées à la même date ; voir le [bilan de reproductibilité](11_validation_reproductibilite.md).
- Les scénarios financiers sont des **hypothèses de décision**, non des économies constatées.
- L'IA formule des interprétations sous contraintes ; les KPI proviennent de calculs déterministes.

---

**À suivre :** [02 | Diagnostic métier](02_diagnostic_metier.md) | [03 | Cartographie des processus](03_processus_metier.md) | [04 | Dictionnaire des KPI](04_dictionnaire_indicateurs.md)


---

## Ce que cette partie m'a appris

> [!NOTE]
> **Notion clé : Donnée disponible et donnée exploitable**
> Une donnée peut être présente dans une table sans être utilisable pour toutes les analyses. Une commande dont le client est inconnu reste comptabilisable dans le volume global, mais ne peut pas être attribuée correctement à un segment client.

> [!TIP]
> **Exercice pratique**
> Comparer un KPI global avec sa ventilation par client, puis expliquer l'écart.

> [!WARNING]
> **Erreur à éviter**
> Interpréter un montant non attribuable comme une perte de chiffre d'affaires.

> [!IMPORTANT]
> **À retenir pour un entretien**
> La qualité dépend de la décision à prendre, pas uniquement du nombre de champs remplis.

### Passer de la théorie à la pratique

| En situation professionnelle | Réflexe recommandé |
|---|---|
| Avant de développer | Clarifier la question métier et les données disponibles |
| Pendant l'analyse | Vérifier les hypothèses, les granularités et les exclusions |
| Avant de présenter | Distinguer résultats mesurés, simulations et limites |
| Après la restitution | Documenter les décisions, les actions et les contrôles à poursuivre |

### Navigation dans le dossier

[Sommaire](INDEX.md) | **01 / 12 : Contexte métier** | [Suivant : 02 Diagnostic métier](02_diagnostic_metier.md)

[Retour au sommaire documentaire](INDEX.md)
