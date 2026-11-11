# Documentation de l'API FastAPI — ConsultAI 360

## Objectif

L'API locale expose des indicateurs de NexaRetail sans importer l'interface Streamlit. **Implémentation de référence :** `api/main.py`. L'ancien prototype de l'étape 9 est conservé uniquement dans `docs/archives/09_ancienne_proposition_api.md`.

## Points d'accès

| Méthode | Chemin | Réponse |
|---|---|---|
| GET | `/health` | `{"status": "ok"}` |
| GET | `/scenarios` | Liste des scénarios `low`, `medium`, `critical` |
| GET | `/kpis/{scenario}` | Indicateurs du scénario demandé |

Le nom de scénario est normalisé en minuscules. Un scénario inconnu renvoie HTTP 404.

## Modes de fonctionnement

- `CONSULTAI_DEMO_MODE=true` : réponses de démonstration, avec `scenario`, `orders`, `missing`, `missing_pct` et `source="demo"`.
- `CONSULTAI_DEMO_MODE=false` ou variable absente : lecture PostgreSQL via `src.assistant.kpi`, avec les indicateurs logistiques supplémentaires et `source="postgresql"`.

**Attention : le mode démonstration est désactivé par défaut dans le code actuel.** Sans connexion PostgreSQL disponible, `/kpis/{scenario}` peut répondre HTTP 503. La structure de réponse diffère entre les deux modes : aucun schéma Pydantic commun n'est déclaré dans l'implémentation actuelle.

## Sécurité et limites

- L'API ne génère pas de SQL à partir d'un modèle de langage.
- Les erreurs internes de lecture sont masquées derrière un message HTTP 503.
- Le code actuel intercepte largement les exceptions ; ce choix simplifie l'interface publique mais réduit le diagnostic côté appelant.
- Aucune authentification ni limitation de débit n'est implémentée dans `api/main.py` : ne pas présenter cette API comme prête pour une exposition publique.
- Les données de démonstration ne doivent pas être présentées comme des mesures issues de PostgreSQL.

## Validation

Les tests existants se trouvent notamment dans `tests/test_api_step9.py` et `tests/test_api_postgres_step9.py`. Le bilan consolidé de l'étape 11 est dans [la validation et reproductibilité](11_validation_reproductibilite.md). La mise à jour de ce document n'a pas réexécuté les tests.
