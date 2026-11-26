# Console Streamlit : parcours et fonctionnement

La console présente un dossier d’analyse NexaRetail en quatre rubriques. Les scénarios **faible**, **moyen** et **critique** sont sélectionnés une seule fois, dans la barre latérale.

| Rubrique | Usage |
|---|---|
| Synthèse | Quatre indicateurs, effet du scénario sur la couverture des montants, actions proposées et note exportable |
| Diagnostic opérationnel | Qualité des montants, comparaison CA renseigné / montant hypothétique et ponctualité des livraisons |
| Traçabilité des données | Source réellement utilisée, populations, contrôles et export JSON |
| Assistant IA | Questions métier, suivi du contexte, sources repliées et export de l’échange |

Les anciens écrans Atelier, Observatoire, Investigation, Laboratoire et Porte de décision ont été regroupés. Le journal d’investigation, les tableaux de comparaison répétés et le dictionnaire des indicateurs ont été retirés de l’interface. Le dictionnaire documentaire du projet reste disponible dans le dépôt.

## Démarrage en démonstration

Depuis la racine du dépôt :

```bash
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Le mode démonstration est sélectionné par défaut. Il ne nécessite ni PostgreSQL ni Ollama. Sur le serveur public, `CONSULTAI_DEMO_MODE=true` empêche toute recherche de modèle local.

Les valeurs de démonstration sont des références figées. La référence conserve les volumes et le panier moyen arrondi : le CA est donc **reconstitué**, et non présenté comme une somme exacte extraite de PostgreSQL. Le montant hypothétique des commandes sans montant est identifié séparément et n’est jamais une perte mesurée.

## Connexion PostgreSQL

Configurer `ASSISTANT_DATABASE_URL` dans l’environnement du processus, avec un rôle en lecture seule, puis désactiver « Mode démonstration ». Les fonctions `overview()` et `delivery()` de `src/assistant/kpi.py` utilisent des requêtes paramétrées et une transaction en lecture seule. Le cache dure cinq minutes.

Sans connexion configurée, ou en cas d’échec, l’application conserve le choix du visiteur, signale le repli et identifie les valeurs comme une référence de démonstration. Aucune exception de connexion n’est affichée au visiteur. Une erreur sur un scénario entraîne le repli de l’ensemble des scénarios afin d’éviter de mélanger les sources.

## Assistant : calculs et modèle local

`src/assistant/copilot.py` reconnaît les questions sur le CA, les montants, le panier, les retards, les scénarios, les hypothèses et les sources. Il fournit les résultats des outils Python. Les commandes et les livraisons conservent leurs dénominateurs distincts.

Un modèle local **Ollama** peut compléter la reconnaissance des demandes qui ne sont pas comprises par le routeur déterministe. Le modèle configuré par `CONSULTAI_OLLAMA_MODEL` (par défaut `llama3.2:1b`) doit déjà être installé. `OLLAMA_HOST` accepte seulement une adresse locale. La sortie du modèle est une intention appartenant à une liste autorisée ; elle ne contient ni chiffres à afficher ni SQL à exécuter. En cas d’erreur, l’assistant demande une précision et les outils déterministes restent disponibles.

Chaque scénario et chaque source disposent d’un historique séparé. Une question nommant explicitement un autre scénario est traitée sur ce scénario et signalée dans la réponse. « Nouvel échange » efface les messages et les hypothèses de la conversation active. Les agrégats disponibles ne permettent pas d’inventer un magasin, un transporteur responsable ou une cause.

Le module historique `src/assistant/llm.py` conserve son mécanisme de commentaire pour les usages locaux antérieurs ; ce n’est pas le moteur de rédaction de la nouvelle console.

## Validation

```bash
python -m pip install -r requirements.txt -r requirements-api.txt
python -m pytest -q
```

Les tests couvrent les fonctions existantes, la validation des populations, le CA PostgreSQL distinct du CA reconstitué, les simulations, les limites de l’assistant, le suivi de scénario et les parcours Streamlit. Ils ne constituent pas un test d’intégration sur une base PostgreSQL de production ou un modèle Ollama réel.
