
# ConsultAI 360 — API FastAPI

## Objectif
Exposer des KPI calculés par Python et PostgreSQL
sans dépendre de l'interface Streamlit.

## Endpoints
- GET /health : état de l'API
- GET /scenarios : scénarios disponibles
- GET /kpis/{scenario} : indicateurs du scénario

## Modes
- CONSULTAI_DEMO_MODE=true : données de référence
- CONSULTAI_DEMO_MODE=false : données PostgreSQL

## Sécurité
- API en lecture seule
- Aucun SQL généré par le LLM
- Pas de secrets dans le dépôt
- Réponse 503 en cas de données indisponibles

## Validation
Tests unitaires en mode démonstration et
tests PostgreSQL avec fonctions simulées.

## Limites
L'API locale n'est pas déployée publiquement.
Les tests simulés ne remplacent pas les tests
d'intégration sur PostgreSQL réel.
