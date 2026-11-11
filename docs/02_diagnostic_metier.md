# NexaRetail : Diagnostic métier initial

**Projet :** ConsultAI 360

**Mission :** Transformation Data & Intelligence artificielle

**Document :** Analyse des problématiques métier

## 1. Objectif du diagnostic

Ce diagnostic vise à identifier les principales difficultés rencontrées par NexaRetail dans la gestion et l'exploitation de ses données.

L'analyse permet de comprendre les conséquences potentielles de ces problèmes sur les performances de l'entreprise et de définir les axes prioritaires de transformation.

Les problèmes présentés constituent des hypothèses de départ qui seront étudiées à partir des données simulées.

## 2. Identification des problèmes métier

### 2.1. Qualité insuffisante des données

Les informations provenant des différents départements présentent des risques d'anomalies : doublons, valeurs manquantes, formats incorrects et incohérences métier.

**Conséquences :**
- Indicateurs de performance potentiellement erronés.
- Difficultés de consolidation des données.
- Temps supplémentaire consacré aux corrections.
- Risques de décisions fondées sur des informations incorrectes.

**Solution envisagée :** mise en place d'un pipeline automatisé de détection, de nettoyage et de contrôle des données.

### 2.2. Reporting fragmenté

Les équipes utilisent plusieurs fichiers Excel et systèmes de reporting indépendants.

Cette organisation complique la production d'une vision globale des performances.

**Conséquences :**
- Production manuelle de rapports.
- Risques d'incohérences entre départements.
- Difficultés d'accès aux indicateurs actualisés.
- Perte de temps dans les analyses.

**Solution envisagée :** centralisation des données dans un Data Warehouse et création de tableaux de bord Power BI.

### 2.3. Difficultés logistiques

NexaRetail souhaite mieux comprendre les facteurs associés aux retards de livraison.

**Conséquences :**
- Risques d'insatisfaction client.
- Augmentation potentielle des réclamations.
- Coûts opérationnels supplémentaires.
- Difficultés d'anticipation des incidents.

**Solution envisagée :** analyse des performances logistiques et expérimentation de modèles prédictifs.

### 2.4. Exploitation limitée des données commerciales

L'entreprise dispose d'informations sur les clients, les ventes et les produits, mais ne les exploite pas suffisamment pour orienter ses décisions.

**Conséquences :**
- Opportunités commerciales difficilement identifiables.
- Segmentation client limitée.
- Analyse incomplète des performances.
- Difficultés de priorisation des actions.

**Solution envisagée :** développement d'analyses commerciales et de tableaux de bord décisionnels.

### 2.5. Absence de stratégie IA structurée

La direction souhaite intégrer l'intelligence artificielle sans disposer d'une vision claire des cas d'usage prioritaires.

**Conséquences :**
- Risques d'investissements peu rentables.
- Difficultés d'évaluation des bénéfices.
- Manque de visibilité sur les risques techniques.
- Absence de feuille de route de déploiement.

**Solution envisagée :** création d'un assistant IA analytique et élaboration d'une stratégie de transformation accompagnée d'une analyse financière.

## 3. Synthèse du diagnostic

| Problématique | Département concerné | Solution envisagée |
|---|---|---|
| Qualité des données | Tous | Python, SQL |
| Reporting fragmenté | Finance, commercial | PostgreSQL, dbt, Power BI |
| Retards de livraison | Logistique | Data Analytics, Machine Learning |
| Exploitation commerciale limitée | Commercial, marketing | Power BI, analyse statistique |
| Absence de stratégie IA | Direction | IA générative, Streamlit, analyse ROI |

## 4. Priorités de transformation

Les initiatives sont organisées selon leurs dépendances techniques et métier.

**Priorité 1 : Fiabiliser les données**

Identifier les anomalies, définir les règles de qualité et mettre en place les processus de correction.

**Priorité 2 : Centraliser et analyser**

Construire une architecture analytique permettant de produire des indicateurs cohérents.

**Priorité 3 : Développer les capacités prédictives**

Expérimenter des méthodes de Machine Learning et évaluer leur pertinence.

**Priorité 4 : Intégrer l'intelligence artificielle**

Développer un assistant analytique et mesurer sa fiabilité.

**Priorité 5 : Évaluer la rentabilité**

Construire plusieurs scénarios financiers et proposer une stratégie de déploiement.

Cet ordre constitue une proposition initiale. La priorisation finale sera affinée à partir des résultats du projet.

## 5. Conclusion

Le diagnostic initial met en évidence cinq domaines d'amélioration potentiels : qualité des données, reporting, logistique, exploitation commerciale et stratégie IA.

La transformation de NexaRetail nécessitera une approche progressive, combinant fiabilisation des données, automatisation, analyse décisionnelle et expérimentation de solutions d'intelligence artificielle.

ConsultAI 360 vise à démontrer comment ces différentes composantes peuvent contribuer à une stratégie cohérente de transformation Data & IA.
