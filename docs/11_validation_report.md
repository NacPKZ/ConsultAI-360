# ConsultAI 360 — Étape 11 : bilan de validation

Date du bilan : 10 novembre 2026.

## Périmètre et méthode
Cette étape consolide les contrôles déjà réalisés. Elle ne réexécute pas les traitements métier, l'entraînement ML, les transformations SQL/dbt ou les applications déjà vérifiées lors des étapes précédentes.

Trois niveaux de preuve sont distingués :
- **Exécuté le 10/11/2026** : résultat de commande communiqué pendant l'étape 11.
- **Historique documenté** : résultat déclaré dans les livrables des étapes précédentes, non rejoué pendant l'étape 11.
- **Non vérifié dans cette étape** : aucun résultat nouveau permettant d'attester le fonctionnement courant.

## Matrice de validation

| Domaine | Preuve | Statut | Limite |
|---|---|---|---|
| Environnement Python | Python 3.12.10 ; pytest 9.2.0 ; environnement virtuel actif | Exécuté le 10/11/2026 | Environnement Windows local |
| Tests Python / API / assistant | `python -m pytest -q tests` : **31 passed in 2.87s** | Exécuté le 10/11/2026 | Les tests API avec fonctions PostgreSQL simulées ne prouvent pas une connexion réelle |
| Git | Branche `main`, commit initial `e5c89ac`, `git status --short` vide | Observé le 10/11/2026 | État antérieur à l'ajout de ce bilan |
| dbt | README : 16 modèles, 37 tests, 11 sources ; dernier `dbt build` **53/53 PASS** | Historique documenté | Non rejoué pendant l'étape 11 |
| Contrôles SQL / DW | README : contrôles de volumes, sommes, scénarios et tests finaux PASS | Historique documenté | Non rejoués pendant l'étape 11 |
| API | `docs/09_api.md` ; tests de routes et de données simulées | Tests Python exécutés ; documentation historique | Intégration réelle PostgreSQL non attestée par ces tests |
| Streamlit, Ollama, Docker | Fonctionnement précédemment testé, confirmé par le porteur du projet | Validation antérieure déclarée | Aucun test courant supplémentaire, conformément au périmètre de l'étape |
| Power BI | `docs/10_powerbi_final.md` : architecture à sept pages et contrôles antérieurs | Historique documenté | Pas de vérification visuelle ou de recalcul DAX pendant l'étape 11 |
| ML DataCo | `docs/08_ml_final_report.md` : évaluation finale du Random Forest | Historique documenté | Pas de réentraînement ni de réévaluation pendant l'étape 11 |
| Reproductibilité | Instructions partielles dans README et documents spécialisés | Documentée partiellement | Reconstruction complète sur machine vierge non démontrée |

## Incident Docker observé pendant l'audit
La commande `docker compose ps` a d'abord échoué faute de variable `DOCKER_POSTGRES_PASSWORD` dans la configuration disponible pour Compose. Un second diagnostic a indiqué que le moteur Docker Desktop était inaccessible à ce moment-là. Le fichier `.env` existait, sans que son contenu soit divulgué.

Ces constats **ne prouvent ni une corruption de la base ni un défaut des transformations dbt**. Aucune modification des secrets, des volumes ou des services n'a été entreprise. Le porteur du projet a confirmé avoir déjà validé ces composants et a choisi de ne pas répéter ces tests.

## Points de vigilance méthodologiques
1. **NexaRetail** : entreprise fictive, données synthétiques ; les écarts de CA mesurés entre scénarios ne sont pas des pertes financières réelles.
2. **DataCo** : dataset public distinct, cible de risque de retard d'expédition ; performances non transférables automatiquement à NexaRetail.
3. **Random Forest** : le seuil 0,40 est une règle de décision choisie sur validation, non un optimum économique démontré.
4. **Exports ML** : la provenance des exports d'analyse de seuil et d'évaluation finale doit être réconciliée avant toute affirmation d'identité parfaite des métriques.
5. **ROI** : scénarios financiers hypothétiques, sans gains réalisés ni causalité démontrée.
6. **Reproductibilité** : le fonctionnement local antérieur ne prouve pas qu'un tiers peut tout reconstruire depuis un dépôt vierge.

## Décision de clôture
Les tests Python existants sont validés (**31/31**). Les autres composants sont retenus sur la base des preuves historiques et des validations précédentes, **sans nouvelle certification technique**. L'étape 11 peut être clôturée en tant que **consolidation documentaire des preuves existantes**, avec les réserves ci-dessus. Aucun nouveau test ou refactoring n'est nécessaire pour cette clôture limitée.

## Références internes
- `README.md`
- `docs/08_ml_final_report.md`
- `docs/09_api.md`
- `docs/10_powerbi_final.md`
- `tests/`
- `dbt_nexaretail/tests/`
