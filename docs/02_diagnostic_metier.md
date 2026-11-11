# 02 · Diagnostic métier — Du symptôme à la décision

> **CONSULTAI 360 / DIAGNOSTIC INITIAL**  
> **Nature :** hypothèses métier d'une entreprise fictive, confrontées aux observations du projet · **Règle :** ne pas transformer une simulation en incident réellement subi.

[← Contexte](01_contexte_metier.md) · [Index](INDEX.md) · [Processus →](03_processus_metier.md)

---

## Synthèse de direction

Le risque majeur pour NexaRetail n'est pas uniquement la présence d'erreurs : c'est **l'illusion de précision** produite par des indicateurs qui masquent les données non attribuables. Le diagnostic recommande de traiter d'abord la confiance dans les données, ensuite leur exploitation analytique, puis les expérimentations IA et leur valeur économique.

| Enjeu | Risque métier | Réponse | Priorité logique |
|:--|:--|:--|:--|
| Qualité des données | KPI incomplets ou mal attribués | Contrôles Python/SQL/dbt | **P1 — Fondation** |
| Reporting fragmenté | Versions contradictoires d'un indicateur | DW et Power BI | **P2 — Pilotage** |
| Logistique | Retards difficiles à qualifier | Analyse des expéditions | **P2 — Pilotage** |
| Analyse commerciale | Décisions sur des périmètres incomplets | Mesures contextualisées | **P2 — Pilotage** |
| IA sans gouvernance | Recommandations non justifiées | Assistant contrôlé, pilote et ROI | **P3 — Expérimentation** |

> [!NOTE]
> Les problèmes organisationnels décrits ici sont des **hypothèses de cadrage**. Les anomalies chiffrées proviennent, elles, des jeux de données synthétiques générés dans le projet.

## 1. Hypothèses et mécanismes de risque

### DQ-01 · Qualité des données

**Symptômes envisagés :** identifiants absents, références invalides, dates manquantes, doublons et incohérences.

**Mécanisme :** si une commande n'est plus associable à son client, le montant peut rester présent dans le total global tout en disparaissant d'une analyse par segment client. La différence n'est pas nécessairement une perte commerciale ; c'est une **perte de capacité d'attribution**.

**Contrôles proposés :** complétude par champ, intégrité référentielle, volumes par scénario, montants non attribuables, conservation des lignes et journalisation des anomalies.

**Critère de décision :** publier chaque KPI avec son périmètre, sa couverture et ses exclusions.

### BI-02 · Reporting fragmenté

**Symptômes envisagés :** multiples fichiers Excel, extractions ponctuelles, définitions concurrentes.

**Mécanisme :** une même expression (« chiffre d'affaires ») peut désigner des sommes de commandes, de lignes de vente ou de paiements, pourtant non interchangeables.

**Réponse :** modèle dimensionnel, règles de jointure incluant le scénario, dictionnaire KPI, dashboard de pilotage.

**Critère de décision :** une mesure n'est publiable que si sa source, sa granularité et ses filtres sont explicites.

### LOG-03 · Livraison et qualité de service

**Symptômes envisagés :** retards, délais difficiles à expliquer, données de livraison incomplètes.

**Mécanisme :** calculer un taux de retard sur toutes les commandes, y compris celles sans date de livraison exploitable, peut masquer l'incertitude.

**Réponse :** suivre séparément **expéditions évaluables**, **retards** et **enregistrements non évaluables** ; comparer les modes de livraison sans conclure automatiquement à une causalité.

**Critère de décision :** ne pas confondre corrélation, prédiction et levier opérationnel démontré.

### COM-04 · Exploitation commerciale

**Symptômes envisagés :** faible visibilité consolidée sur les ventes, les canaux et les magasins.

**Mécanisme :** une variation de KPI peut provenir d'un changement réel d'activité, d'une donnée manquante ou d'un filtre différent.

**Réponse :** analyses par canal et magasin, comparaisons entre scénarios, rapprochements avec les montants de référence.

### IA-05 · Expérimentation sans gouvernance

**Symptômes envisagés :** attente de réponses automatiques, bénéfices difficiles à mesurer.

**Mécanisme :** un assistant génératif peut formuler un commentaire plausible mais faux ; un modèle entraîné sur DataCo ne constitue pas une preuve de performance sur NexaRetail.

**Réponse :** calculs réalisés par SQL/Python, assistant limité à l'interprétation, évaluation ML indépendante, scénarios financiers explicites et décision de pilote conditionnelle.

## 2. Éléments observés dans la simulation

| Observation documentée | Lecture correcte | Lecture à éviter |
|:--|:--|:--|
| 120 000 commandes dans ORIGINAL | Base de comparaison synthétique | Volume d'une entreprise réelle |
| CA ORIGINAL : **72 056 406,60 €** | Indicateur de référence simulé | Chiffre d'affaires audité |
| CA CRITICAL : **64 901 512,00 €** | Montant mesuré dans le scénario dégradé | Encaissements réels |
| Écart CRITICAL : **−7 154 894,60 €** | Sous-estimation simulée du CA mesuré | « 7,15 M€ de ventes perdues » |
| 19 200 commandes sans date, tous scénarios dégradés confondus | Risque de sous-couverture des analyses temporelles | Commandes inexistantes |

Ces valeurs sont reprises du [README de référence](../README.md). Le détail des transformations, scénarios et limites est présenté dans le [rapport final](12_rapport_final_conseil.md).

## 3. Diagnostic des causes : hypothèses à tester

| Domaine | Cause possible | Test ou preuve attendue | Responsable métier fictif |
|:--|:--|:--|:--|
| Référentiel | Identifiants incohérents | Anti-jointures et contrôles de clés | Data / Finance |
| Temporalité | Dates absentes ou invalides | Taux de couverture par période | Logistique |
| Consolidation | Définitions divergentes | Rapprochement SQL ↔ BI | Finance / Commercial |
| Explicabilité | Granularités mélangées | Vérification des tables de faits | Data |
| Adoption IA | Confiance excessive dans les réponses | Tests, garde-fous, revue humaine | Direction / Data |

> [!CAUTION]
> Les causes ci-dessus ne sont **pas établies par une enquête de terrain**. Elles constituent des pistes de diagnostic à vérifier dans une mission réelle.

## 4. Priorisation et dépendances

```text
P1  Fiabiliser les données et définir les KPI
             |
             v
P2  Consolider le DW et les analyses Power BI
             |
             v
P3  Tester des cas d'usage ML et IA sous contrôle
             |
             v
P4  Évaluer coûts, bénéfices et conditions du pilote
             |
             v
     Décision GO / NO-GO documentée
```

Cette séquence décrit une **dépendance de décision**, pas une preuve que chaque composant est industrialisé.

## 5. Questions qu'un consultant poserait au client

1. Quelle définition du chiffre d'affaires fait autorité : commande, facturation ou encaissement ?
2. Qui valide une correction de référence client ou produit ?
3. Quel pourcentage des expéditions possède des dates suffisamment fiables pour mesurer le retard ?
4. Quelles décisions commerciales changeraient réellement grâce au dashboard ?
5. Quels coûts et gains du pilote sont **mesurables**, et lesquels ne sont que supposés ?
6. Quel responsable métier approuve les recommandations formulées par l'IA ?

## 6. Conclusion et orientation

**Recommandation :** adopter une transformation progressive, avec une priorité donnée à la qualité et à la traçabilité, puis à la diffusion d'indicateurs communs. Les composants IA doivent rester soumis à des tests et à une validation humaine.

**Suite du dossier :** [Cartographie des processus](03_processus_metier.md) · [Dictionnaire des KPI](04_dictionnaire_indicateurs.md) · [Rapport final de conseil](12_rapport_final_conseil.md)
