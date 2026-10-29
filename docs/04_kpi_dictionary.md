# NexaRetail : Dictionnaire des KPI

**Projet :** ConsultAI 360

**Entreprise :** NexaRetail

**Document :** Référentiel des indicateurs de performance

**Version :** 1.0 : Définitions initiales

## 1. Objectif

Ce document définit les principaux indicateurs utilisés pour évaluer les performances commerciales, financières, logistiques et opérationnelles de NexaRetail.

Il constitue un référentiel commun pour les analyses SQL, les tableaux de bord Power BI et l'assistant IA.

Les règles de calcul seront précisées et validées lors de la construction du modèle de données.

## 2. Indicateurs financiers et commerciaux

| Indicateur | Méthode de calcul | Objectif métier |
|---|---|---|
| Chiffre d'affaires net | Ventes − Remises − Remboursements | Mesurer les revenus commerciaux |
| Nombre de commandes | Nombre de commandes validées | Suivre l'activité |
| Panier moyen | CA net / Nombre de commandes | Mesurer la valeur moyenne des commandes |
| Marge brute | CA net − Coût des produits vendus | Évaluer la rentabilité commerciale |
| Taux de marge brute | Marge brute / CA net × 100 | Comparer la rentabilité |
| CA par magasin | Somme du CA attribué à chaque magasin | Comparer les performances |

## 3. Indicateurs logistiques

| Indicateur | Méthode de calcul | Objectif métier |
|---|---|---|
| Délai moyen de livraison | Moyenne des durées commande-livraison | Mesurer la rapidité |
| Taux de retard | Livraisons tardives / Livraisons effectuées × 100 | Identifier les problèmes de ponctualité |
| Taux de livraison à temps | Livraisons ponctuelles / Livraisons effectuées × 100 | Évaluer la qualité logistique |
| Délai moyen de préparation | Moyenne des durées validation-fin de préparation | Mesurer l'efficacité de préparation |
| Taux de réclamation | Commandes livrées avec réclamation / Commandes livrées × 100 | Suivre les incidents clients |

## 4. Indicateurs de qualité des données

| Indicateur | Méthode de calcul | Objectif métier |
|---|---|---|
| Taux de complétude | Valeurs présentes / Valeurs attendues × 100 | Mesurer les informations manquantes |
| Taux de doublons | Doublons / Enregistrements contrôlés × 100 | Détecter les duplications |
| Taux d'anomalies | Éléments anormaux / Éléments contrôlés × 100 | Mesurer la qualité initiale |
| Précision | VP / (VP + FP) | Évaluer la fiabilité des alertes |
| Rappel | VP / (VP + FN) | Mesurer la détection des anomalies |
| F1-score | 2 × Précision × Rappel / (Précision + Rappel) | Synthétiser les performances |

VP : vrais positifs.
FP : faux positifs.
FN : faux négatifs.

Les indicateurs de qualité seront calculés sur un périmètre explicitement défini : cellules, enregistrements ou anomalies.

## 5. Indicateurs Data & IA

| Indicateur | Méthode de calcul | Objectif métier |
|---|---|---|
| Temps de reporting | Durée de production d'un rapport | Mesurer l'efficacité |
| Gain de temps estimé | Temps initial − Temps après automatisation | Évaluer la productivité |
| Exactitude IA | Réponses factuelles correctes / Réponses factuelles évaluées × 100 | Mesurer la fiabilité |
| Coût d'exploitation | Somme des dépenses opérationnelles | Évaluer les charges |
| ROI estimé | (Bénéfices − Coûts) / Coûts × 100 | Évaluer la rentabilité |

## 6. Règles de gouvernance

Afin de garantir la cohérence des analyses :

1. Chaque KPI doit posséder une définition unique.
2. Les filtres et périodes d'analyse doivent être précisés.
3. Les données utilisées doivent être identifiables.
4. Les divisions par zéro doivent être traitées.
5. Les résultats SQL et Power BI doivent être cohérents.
6. Les hypothèses financières doivent être documentées.
7. Les indicateurs simulés ne doivent pas être présentés comme des résultats réels.

## 7. Conclusion

Ce dictionnaire constitue la première version du référentiel des KPI de NexaRetail.

Il sera enrichi lors de la génération des données, de la construction du Data Warehouse et du développement des tableaux de bord.

L'objectif est de garantir que chaque indicateur possède une définition compréhensible, une méthode de calcul reproductible et une utilité métier clairement identifiée.
