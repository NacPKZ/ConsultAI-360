# ConsultAI 360 — NexaRetail | Data Quality, Analytics & AI Consulting

> **Projet de conseil Data & IA — cas d'étude sur données synthétiques.** Conception d'une chaîne analytique PostgreSQL, simulation de dégradations de données, mesure de leur impact sur les KPI et préparation de recommandations business.

**État :** phases de génération/scénarios et SQL/Data Warehouse réalisées ; autres volets (BI, ML, NLP, IA, ROI) à documenter selon leur avancement effectif.  
**Technologies mises en œuvre :** Python 3.12, PostgreSQL, SQL, DBeaver, VS Code, Git/GitHub.  
**Périmètre :** NexaRetail, entreprise fictive ; aucune conclusion ne porte sur une entreprise réelle.

## Livrables et rapports

> **Rapport disponible :** [**01 — Data Engineering, Data Quality & Business Analytics (PDF)**](rapports/01_Rapport_Data_Engineering_Analytics.pdf)  
> Architecture PostgreSQL RAW → CLEAN → DW, audit de qualité, analyse de l'impact des anomalies sur les indicateurs métier, validation SQL et recommandations.

| Livrable | Statut | Accès |
|---|---|---|
| **01 — Data Engineering, Data Quality & Business Analytics** | Disponible | [Consulter le rapport PDF](rapports/01_Rapport_Data_Engineering_Analytics.pdf) |
| 02 — Business Intelligence & Data Visualisation | À venir | — |
| 03 — Machine Learning & évaluation | À venir | — |
| 04 — Synthèse finale de conseil Data & IA | À venir | — |

Les livrables sont centralisés dans le dossier [`rapports/`](rapports/). Les analyses et les scripts restent accessibles dans les dossiers techniques du dépôt.

## Résumé exécutif

Le chiffre d'affaires de référence sur les **120 000 commandes originales** est de **72 056 406,60 €**. Les variantes dégradées, à volume de commandes constant, produisent des montants inférieurs :

| Jeu | Commandes | CA des commandes | Écart à l'original | Écart % |
|---|---:|---:|---:|---:|
| ORIGINAL | 120 000 | 72 056 406,60 € | — | — |
| LOW | 120 000 | 71 327 494,22 € | −728 912,38 € | −1,01 % |
| MEDIUM | 120 000 | 68 448 127,94 € | −3 608 278,66 € | −5,01 % |
| CRITICAL | 120 000 | 64 901 512,00 € | −7 154 894,60 € | −9,93 % |

**Interprétation :** le scénario CRITICAL sous-estime le **CA mesuré** de 7,15 M€ ; ce n'est **pas** une perte de trésorerie ou de chiffre d'affaires réellement subie. Les scénarios représentent des dégradations simulées, et non une estimation statistique d'un risque réel.

## Architecture et volumes

```text
Données NexaRetail originales (synthétiques)
            |
            v
Injection d'anomalies -> LOW / MEDIUM / CRITICAL
            |
            v
PostgreSQL raw (4 107 649 lignes, original compris)
            |
            v
Contrôles et préparation -> clean (3 019 182 lignes)
            |
            v
Data Warehouse dimensionnel (dw)
  dim_customers / dim_products / dim_stores / dim_dates
  fact_orders / fact_sales / fact_payments
            |
            v
KPI SQL, analyse d'impact, contrôle de qualité
            |
            v
Exploitation BI / recommandations (travaux ultérieurs)
```

- **RAW :** 1 006 394 lignes ORIGINAL ; 1 011 524 LOW ; 1 032 042 MEDIUM ; 1 057 689 CRITICAL.
- **CLEAN :** 1 006 394 lignes par scénario, soit 3 019 182.
- **DW :** 360 000 commandes, 818 859 lignes de vente, 376 503 paiements, 730 dates, 360 003 membres clients, 24 003 produits et 108 magasins.
- Les jointures respectent le champ `scenario` pour ne jamais croiser les variantes.

## Qualité des données : anomalies préservées et mesurées

| Indicateur | LOW | MEDIUM | CRITICAL | Total |
|---|---:|---:|---:|---:|
| Commandes avec client inconnu | 1 200 | 6 000 | 12 000 | 19 200 |
| Lignes avec produit inconnu | 2 730 | 13 648 | 27 295 | 43 673 |
| Paiements sans commande correspondante | 1 255 | 6 275 | 12 550 | 20 080 |
| Commandes sans date | 1 200 | 6 000 | 12 000 | 19 200 |

Les **82 953** anomalies de référence correspondent à des **lignes affectées dans trois tables distinctes**, pas nécessairement à 82 953 transactions uniques. Les dates manquantes sont un autre indicateur et ne doivent pas être ajoutées sans vérifier les recouvrements.

Dans CRITICAL, les paiements non rattachables représentent **6 459 898,61 €** et le CA non attribuable à un client connu **6 478 206,85 €**. Ce sont des **montants non attribuables**, pas des pertes économiques constatées.

### Choix de gouvernance

- Conserver les lignes transactionnelles même lorsque des références sont invalides.
- Utiliser un membre technique **« Inconnu » par scénario** dans les dimensions clients, produits et magasins.
- Préserver `order_key IS NULL` pour les paiements non rattachables ; ne pas inventer de commande.
- Conserver les montants commandes, lignes de vente et paiements dans **des faits distincts**, car leurs granularités diffèrent.
- Documenter les écarts entre `SUM(order_total)` et `SUM(line_total)` ; ne pas les présenter comme équivalents.
- La piste de restauration depuis les sources originales a été **explorée mais différée** : le schéma `recovered` est expérimental, sans correction appliquée. En entreprise, une restauration exige une source de vérité vérifiée et une piste d'audit.

## Organisation des scripts

| Dossier | Fonction |
|---|---|
| `sql/01_setup/` | Préparation et génération de structure RAW |
| `sql/02_raw/` | Création/import des données RAW |
| `sql/03_clean/` | Audit, tables typées, import CLEAN et expérimentation RECOVERED |
| `sql/04_warehouse/` | Inspection, schéma dimensionnel, chargement dimensions/faits |
| `sql/05_analytics/` | KPI métier, comparaison des scénarios, référence ORIGINAL |
| `sql/06_optimization/` | Index, statistiques et `EXPLAIN (ANALYZE, BUFFERS)` |
| `sql/07_tests/` | Contrôles qualité, vérifications DW et tests finaux |

**Attention :** le dossier réel est `sql/04_warehouse/`, et non `sql/04_dw/`.

### Reproduire les travaux

1. Préparer PostgreSQL et la base `nexaretail_db`, avec les schémas `raw`, `clean`, `dw` et les dépendances Python nécessaires.
2. Disposer des fichiers sources et des variantes générées localement ; le dépôt seul ne garantit pas la présence des données ni leur droit de redistribution.
3. Exécuter les scripts dans l'ordre numérique, en adaptant les chemins, identifiants et paramètres de connexion à son environnement.
4. Contrôler les volumes RAW, puis charger les fichiers de `data/processed_v2/` dans CLEAN. **Ne pas réutiliser l'ancien traitement V1.**
5. Exécuter `sql/04_warehouse/02_create_dw_tables.sql`, puis `03_load_dimensions.sql` et `04_load_facts.sql`.
6. Exécuter les requêtes analytiques et les tests, notamment `sql/07_tests/05_final_dw_tests.sql`.

Les scripts ne constituent **pas** encore un pipeline de déploiement intégralement automatisé. Le script de copie `sql/03_clean/05_copy_clean_to_recovered.sql` a déjà été utilisé pour créer les tables expérimentales : **ne pas le relancer sans vérifier son comportement et l'état des tables**. Ne jamais publier mots de passe, fichiers sensibles ou jeux de données sans vérification des droits.

## Validation et performance

- **9/9** contrôles de volumes CLEAN → DW : PASS.
- **9/9** contrôles de sommes CLEAN → DW : PASS.
- **5/5** relations de scénarios : 0 mélange.
- **10/10** tests finaux automatisés : PASS, y compris les anomalies connues attendues.
- Trois plans `EXPLAIN ANALYZE` : **174,65 ms** (CA mensuel), **344,92 ms** (CA catégorie), **93,98 ms** (commandes CRITICAL datées).
- Ces mesures ont été faites **après** indexation ; **aucun gain avant/après n'est démontré**. Les `Parallel Seq Scan` et `Hash Join` sont cohérents avec des requêtes parcourant une grande part des données.

## Limites et prochaines étapes

- Les résultats sont propres à des données et corruptions **synthétiques**.
- Les anomalies de références et dates demeurent volontairement présentes ; CLEAN signifie ici **typé, contrôlé et exploitable**, non exempt d'erreurs.
- La dimension date ne couvre que les dates présentes ; 19 200 commandes sans date sont exclues des regroupements temporels classiques, mais conservées dans le CA global.
- Les tests de volumes ne suffisent pas à valider la justesse métier de chaque enregistrement.
- Les analyses par client, produit ou mois doivent afficher le taux de couverture et les lignes non attribuables.
- Les performances ne sont pas comparées à un benchmark préalable.
- À poursuivre : documentation métier des KPI, tableau de bord BI, analyses avancées, estimation de ROI et recommandations, selon la roadmap globale.

## Choix méthodologiques — Données textuelles

### Architecture à deux sources

**1. NexaRetail — données transactionnelles synthétiques.** Clients, commandes, produits, paiements, livraisons, stocks et réclamations sont générés artificiellement afin de tester la qualité et la robustesse des analyses.

**2. Corpus d'avis clients — données textuelles réelles.** `SetFit/amazon_reviews_multi_fr` est une source **indépendante**, destinée à de futures analyses NLP. Ces avis **ne proviennent pas de NexaRetail** et ne sont pas associés à ses clients ni à ses commandes.

### Expérimentation abandonnée : enrichissement des réclamations

| Version | Textes associés | Couverture |
|---|---:|---:|
| V1 | 3 580 | 40,28 % |
| V2 | 1 644 | 18,50 % |
| V2.1 | 902 | 10,15 % |

Des incohérences entre avis réels et produits synthétiques ont été détectées. Les filtres ont réduit les associations problématiques détectables sans garantir leur cohérence sémantique. **Décision : conserver les deux sources séparées**, plutôt que présenter des liens artificiels comme authentiques.

Les **8 888 réclamations** NexaRetail conservent leur structure synthétique. Les scripts d'expérimentation peuvent être conservés pour audit ; les avis réels ne doivent pas être redistribués sans vérification des droits. Toute classification supervisée doit tenir compte des biais d'étiquetage.

## Ce que démontre le projet

Un consultant Data/IA doit relier **architecture**, **contrôles**, **impact chiffré**, **limites** et **décisions**. ConsultAI 360 illustre cette démarche sur un environnement simulé, avec conservation des erreurs observables plutôt que correction arbitraire des données.

---
*Documentation mise à jour pour la clôture de la phase SQL / Data Warehouse — octobre 2026.*
