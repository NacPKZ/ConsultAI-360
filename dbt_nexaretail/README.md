# Transformations dbt — ConsultAI 360

Ce sous-projet dbt organise les transformations analytiques de NexaRetail, de la préparation des données aux modèles destinés aux analyses et tableaux de bord.

## Organisation

- `models/staging/` : préparation et standardisation des données sources.
- `models/intermediate/` : transformations intermédiaires.
- `models/marts/` : tables analytiques pour les usages métier.
- `tests/` : tests SQL spécifiques.
- `macros/`, `seeds/`, `snapshots/` et `analyses/` : répertoires conventionnels de dbt, certains réservés à de futurs usages.
- `dbt_project.yml` : configuration du projet.

## Prérequis

PostgreSQL doit être accessible et les schémas sources nécessaires doivent déjà exister. La configuration de connexion se trouve dans `docker/dbt/profiles.yml` à la racine du dépôt. Le mot de passe est fourni par la variable d'environnement `DBT_POSTGRES_PASSWORD`, jamais dans Git.

## Commandes de contrôle

Le profil versionné dans `docker/dbt/profiles.yml` utilise l'hôte `postgres`, résolu dans le réseau Docker. Il **n'est pas directement adapté à une exécution dbt sur Windows** sans profil local distinct.

Depuis la racine du dépôt, avec Docker disponible et `DOCKER_POSTGRES_PASSWORD` défini :

```powershell
docker compose up -d postgres
docker compose build dbt
docker compose run --rm dbt debug
docker compose run --rm dbt build
```

Le service dbt est associé au profil Compose `tools` ; ces commandes explicites ciblent ce service. Les schémas `raw` et `clean` doivent être importés avant `dbt build`.

Ces commandes sont des indications de reproduction, **pas une affirmation qu'elles ont été relancées pendant le nettoyage**. Voir également [le guide Docker](../docker/README.md).

## Validation et limites

Le bilan historique consigne 16 modèles et 37 tests dbt (53 validations réussies lors des exécutions documentées). Il ne garantit pas une reconstruction intégrale dans un nouvel environnement. Voir [le bilan de validation](../docs/11_validation_reproductibilite.md) et [la feuille de route](../docs/feuille_de_route.md).

Les répertoires `target/`, `logs/` et `dbt_packages/` sont des artefacts locaux à exclure du versionnement.
