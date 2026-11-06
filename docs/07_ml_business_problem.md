# Étape 7 : Prédiction du risque de retard d'expédition

## 1. Contexte métier

Les retards d'expédition peuvent entraîner des coûts opérationnels, une dégradation de l'expérience client et une augmentation des réclamations.

L'objectif est d'identifier suffisamment tôt les commandes présentant un risque élevé de retard pour permettre aux équipes logistiques de prioriser leurs interventions.

## 2. Objectif Machine Learning

Développer un modèle de classification binaire permettant d'estimer la probabilité de retard d'expédition.

**Variable cible :** `Late_delivery_risk`

- 0 : absence de retard selon la définition du dataset
- 1 : retard selon la définition du dataset

## 3. Source

Dataset public : DataCo Smart Supply Chain for Big Data Analysis.

Ce dataset est indépendant des données synthétiques NexaRetail utilisées dans les étapes précédentes.

## 4. Moment de prédiction

La prédiction doit utiliser uniquement les informations disponibles au moment de la commande.

Les informations connues après l'expédition ou après la constatation du retard seront exclues.

## 5. Méthodologie

1. Audit de la qualité et de la structure du dataset.
2. Identification des doublons et du grain des données.
3. Vérification de la variable cible.
4. Recherche des risques de fuite de données.
5. Séparation chronologique des données.
6. Construction d'une baseline.
7. Entraînement de modèles de classification.
8. Évaluation avec ROC-AUC, PR-AUC, précision, rappel, F1 et matrice de confusion.
9. Analyse des facteurs prédictifs.
10. Suivi des expériences avec MLflow.

## 6. Critères de réussite

- Pipeline reproductible.
- Absence de fuite de données identifiée dans les variables retenues.
- Performance comparée à une baseline.
- Évaluation sur des données chronologiquement postérieures à l'entraînement.
- Interprétation métier des résultats.
- Limites et hypothèses documentées.

## 7. Limites

Le dataset ne contient pas de véritable date de livraison finale permettant de mesurer directement le retard du dernier kilomètre.

Les performances du modèle ne démontreront donc pas, à elles seules, sa capacité à prédire les retards de livraison chez NexaRetail.

Les recommandations opérationnelles et les éventuels gains financiers seront présentés comme des simulations, sauf preuve empirique contraire.
