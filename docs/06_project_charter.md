# CONSULTAI 360 : CHARTE DE PROJET

**Entreprise :** NexaRetail (fictive)

**Mission :** Transformation Data & Intelligence Artificielle

**Version :** 1.0

**Statut :** Cadrage initial : Validation simulée

## 1. Contexte

NexaRetail est une entreprise fictive française spécialisée dans le commerce omnicanal.

Elle dispose de 35 magasins, d'environ 120 000 clients, de 450 collaborateurs et d'un catalogue de 8 000 produits.

L'entreprise rencontre plusieurs difficultés liées à l'exploitation de ses données : informations de qualité variable, reporting fragmenté, visibilité limitée sur les opérations logistiques et absence de stratégie structurée en intelligence artificielle.

ConsultAI 360 propose une démarche de transformation visant à améliorer la fiabilité des données et leur utilisation dans les décisions métier.

## 2. Objectifs stratégiques

La mission poursuit cinq objectifs :

1. **Fiabiliser les données** grâce à des contrôles automatisés.
2. **Centraliser les informations** dans une architecture analytique cohérente.
3. **Améliorer le pilotage** avec des indicateurs et des tableaux de bord.
4. **Explorer les capacités prédictives** du Machine Learning.
5. **Évaluer les opportunités de l'IA** à travers un assistant et une analyse financière.

L'objectif final est de proposer des recommandations opérationnelles et stratégiques fondées sur des résultats vérifiables.

## 3. Périmètre fonctionnel

Le projet comprend quatre modules.

| Module | Finalité | Livrable |
|---|---|---|
| Data Quality Center | Détection et traitement des anomalies | Pipeline et rapport qualité |
| BI Center | Analyse des performances | Data Warehouse et Power BI |
| Predictive Analytics Center | Expérimentation prédictive | Modèles ML évalués |
| AI Consulting Center | Interprétation des KPI | Application Streamlit |

Ces modules seront complétés par une analyse du ROI, une stratégie de transformation et une documentation technique.

Le développement d'une plateforme e-commerce, d'une application mobile ou d'une infrastructure de production est exclu.

## 4. Architecture prévisionnelle

Le fonctionnement général reposera sur les étapes suivantes :

```text
Données synthétiques NexaRetail
              |
              v
    Contrôles qualité Python
              |
              v
          PostgreSQL
              |
              v
        Transformations dbt
              |
              v
         Data Warehouse
              |
       +------+------+
       |             |
       v             v
    Power BI      Streamlit
                     |
                     v
               Assistant IA
```

Le module Machine Learning utilisera un jeu de données public distinct.

Ses performances ne seront pas présentées comme une validation sur les données de NexaRetail.

## 5. Planification

Le budget de travail prévisionnel est de **180 heures**, réparties en 12 phases.

| Phase | Activité | Durée |
|---|---|---:|
| 1 | Cadrage métier | 6 h |
| 2 | Génération des données | 10 h |
| 3 | Injection d'anomalies et Excel | 10 h |
| 4 | PostgreSQL et qualité des données | 15 h |
| 5 | Data Warehouse et dbt | 15 h |
| 6 | Power BI | 18 h |
| 7 | Machine Learning | 17 h |
| 8 | Assistant IA et Streamlit | 24 h |
| 9 | Analyse du ROI | 14 h |
| 10 | Stratégie de transformation | 8 h |
| 11 | Tests et documentation | 21 h |
| 12 | Rapport, présentation et GitHub | 22 h |
| **Total** | | **180 h** |

Les durées constituent des estimations et pourront être ajustées selon les difficultés rencontrées.

## 6. Parties prenantes

Dans le cadre de cette simulation, les principales parties prenantes sont :

| Partie prenante | Responsabilité simulée |
|---|---|
| Direction générale | Définition des priorités stratégiques |
| Direction financière | Évaluation des coûts et du ROI |
| Direction commerciale | Analyse des ventes |
| Direction logistique | Suivi des livraisons |
| Service client | Analyse des réclamations |
| Consultant Data & IA | Conception, analyses et recommandations |

Le projet est réalisé individuellement. Les rôles métier correspondent à des interlocuteurs fictifs.

## 7. Principaux risques

| Risque | Impact potentiel | Mesure préventive |
|---|---|---|
| Données incohérentes | KPI incorrects | Tests de qualité |
| Périmètre trop large | Retards | Priorisation des fonctionnalités |
| Complexité technique | Blocages | Développement progressif |
| Résultats ML peu concluants | Faible valeur prédictive | Baselines et évaluation rigoureuse |
| Réponses IA incorrectes | Recommandations trompeuses | Calculs vérifiés et tests |
| Hypothèses ROI irréalistes | Conclusions financières fragiles | Scénarios et analyse de sensibilité |

## 8. Critères de validation

La mission sera considérée comme techniquement aboutie lorsque :

- Les données synthétiques seront reproductibles.
- Les anomalies injectées seront documentées et évaluées.
- Les transformations SQL et dbt seront testées.
- Les indicateurs Power BI seront cohérents avec les calculs de référence.
- Les modèles ML disposeront d'une évaluation reproductible.
- L'assistant IA aura été évalué sur au moins 20 questions.
- Les hypothèses du ROI seront explicites.
- Les recommandations seront reliées aux analyses réalisées.
- Le dépôt GitHub et les documents permettront de comprendre les résultats.

## 9. Décision de cadrage

**Décision simulée :** le périmètre initial de ConsultAI 360 est retenu comme référence pour le développement.

Toute modification majeure devra être évaluée selon son impact sur les objectifs, les délais et les livrables.

Cette décision correspond à une validation interne du projet pédagogique et non à une approbation par un client réel.

## 10. Conclusion

La phase de cadrage définit les objectifs, les limites, les livrables et les critères de réussite de ConsultAI 360.

Elle fournit un cadre de travail cohérent pour démarrer la génération des données et les développements techniques.

Les choix établis dans cette charte pourront être révisés si des contraintes techniques ou méthodologiques le justifient.
