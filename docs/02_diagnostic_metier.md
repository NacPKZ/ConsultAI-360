# 02 : Diagnostic métier : Du symptôme à la décision

<div align="center">

**CONSULTAI 360 | DOSSIER DE CONSEIL**

[Accueil du projet](../README.md) | [Sommaire documentaire](INDEX.md) | [Application Streamlit](https://consultai-360.streamlit.app/)

</div>


> **CONSULTAI 360 / DIAGNOSTIC INITIAL**  
> **Nature :** hypothèses métier d'une entreprise fictive, confrontées aux observations du projet | **Règle :** ne pas transformer une simulation en incident réellement subi.

[← Contexte](01_contexte_metier.md) | [Index](INDEX.md) | [Processus →](03_processus_metier.md)

## Plan d'investigation pour un diagnostic en entreprise

Le diagnostic présenté plus haut serait approfondi par des entretiens, un échantillonnage des données et une revue des contrôles existants.

| Séquence | Investigation | Livrable de décision |
|:--|:--|:--|
| **A. Écouter** | Entretiens avec responsables métier et utilisateurs | Carte des irritants et décisions affectées |
| **B. Mesurer** | Profils de données, taux de nulls, contrôles de clés | Registre des anomalies avec périmètre |
| **C. Réconcilier** | Comparaison de plusieurs calculs d'un même indicateur | Définition commune et exceptions |
| **D. Prioriser** | Impact métier, coût, urgence, dépendances | Backlog classé et propriétaires |
| **E. Tester** | Pilote ciblé avec mesure avant/après | Décision documentée de poursuite |

### Exemple de fiche d'incident qualité

| Champ | Exemple illustratif |
|:--|:--|
| Identifiant | DQ-REF-001 |
| Objet | Commande sans client attribuable |
| Impact | Segmentation commerciale incomplète |
| Détection | Anti-jointure entre commandes et référentiel clients |
| Traitement | Préserver la commande, exposer « Inconnu », rechercher la source fiable |
| Validation | Contrôle du nombre de lignes et des montants avant/après |
| Décision | Correction uniquement avec preuve d'identité |

*Cette fiche est un modèle de méthode, pas un ticket issu d'un système de production.*

---
## Synthèse de direction

Le risque majeur pour NexaRetail n'est pas uniquement la présence d'erreurs : c'est **l'illusion de précision** produite par des indicateurs qui masquent les données non attribuables. Le diagnostic recommande de traiter d'abord la confiance dans les données, ensuite leur exploitation analytique, puis les expérimentations IA et leur valeur économique.

| Enjeu | Risque métier | Réponse | Priorité logique |
|:--|:--|:--|:--|
| Qualité des données | KPI incomplets ou mal attribués | Contrôles Python/SQL/dbt | **P1 : Fondation** |
| Reporting fragmenté | Versions contradictoires d'un indicateur | DW et Power BI | **P2 : Pilotage** |
| Logistique | Retards difficiles à qualifier | Analyse des expéditions | **P2 : Pilotage** |
| Analyse commerciale | Décisions sur des périmètres incomplets | Mesures contextualisées | **P2 : Pilotage** |
| IA sans gouvernance | Recommandations non justifiées | Assistant contrôlé, pilote et ROI | **P3 : Expérimentation** |



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

**Suite du dossier :** [Cartographie des processus](03_processus_metier.md) | [Dictionnaire des KPI](04_dictionnaire_indicateurs.md) | [Rapport final de conseil](12_rapport_final_conseil.md)



## Comment lire un diagnostic

```mermaid
flowchart TD
 A["Observation : anomalie détectée"] --> B["Hypothèse de cause"]
 B --> C["Contrôle ciblé"]
 C --> D{"Cause confirmée ?"}
 D -->|Oui| E["Correction et mesure d'impact"]
 D -->|Non| F["Nouvelle hypothèse"]
 F --> C
```

<details><summary><strong>Exemple de distinction entre constat et hypothèse</strong></summary>

Un taux de valeurs manquantes est mesurable. Une mauvaise synchronisation entre systèmes peut l'expliquer, mais cette cause doit être testée. Dans le cas NexaRetail, l'organisation est fictive : aucune enquête terrain n'a confirmé une cause organisationnelle.

</details>

---

[Chapitre précédent](01_contexte_metier.md) | [Sommaire](INDEX.md) | [Chapitre suivant](03_processus_metier.md)
