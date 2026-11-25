# Refonte de la console

La version de référence avant intervention est `8c58792`. Les sources manufacturées NexaRetail, le SQL, les modèles dbt, le rapport Power BI, l’expérimentation DataCo et l’API sont maintenus dans leurs emplacements historiques.

| Priorité | Points revus | Résultat |
|---|---|---|
| Haute | Navigation à huit entrées, ateliers recoupés, contrôle de scénario difficile à localiser, premier écran trop descriptif, en-tête mobile rogné | Cinq espaces, scénario visible, démo facultative, marge et grille mobile |
| Haute | Reconstruction du CA à partir d’un panier arrondi, Original absent, écart ambigu, dénominateurs implicites, confusion entre exposition et pertes | Reprise des CA exacts du rapport SQL, Original en comparaison, définitions et résultats séparés des hypothèses |
| Haute | Assistant public assimilable à un modèle, questions courtes incomprises, heure non traitée, historique dispersé, erreurs du modèle | Mode publié explicite, tests sur formulations, heure de Paris, dialogue réinitialisable, repli analytique |
| Moyenne | Radar, graphiques redondants, sélecteurs CSS fragiles, score de santé trop central, paramètres avancés trop visibles | Barres et tableau de comparaison, styles limités, simulation en section dépliable |
| Moyenne | Doctrine de publication dispersée, exports à plusieurs endroits, source du chiffre difficile à retrouver | Recommandations avec éléments de preuve, seuils et deux exports, dictionnaire des KPI accessible |

## Contrôles

Le CA moyen de 68 448 127,94 €, les 6 000 montants absents sur 120 000, le panier connu de 600,42 € et les 10 333 retards sur 70 005 livraisons sont vérifiés en mode démonstration. Le CA Original est issu du [rapport de conseil](12_rapport_final_conseil.md). Les champs Original absents de la référence de la console sont affichés comme indisponibles.

La sensibilité conserve 20 000 tirages log-normaux reproductibles. Les quantiles P5 et P95 décrivent la simulation conditionnelle au panier moyen inconnu. Les chiffres des données synthétiques restent vérifiables via le JSON et les résultats connus.

Le test du moteur et de l’API utilise les fixtures existantes. PostgreSQL et Ollama requièrent un service configuré sur la machine qui les exécute. La console publique fournit les agrégats de référence et l’assistant analytique en français.
