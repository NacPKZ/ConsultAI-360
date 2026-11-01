# Docker - ConsultAI 360

## Architecture
PostgreSQL 18 et dbt 1.11.0 avec Docker Compose.
Base : nexaretail_db | Port : 5433 | Profil : dbt_nexaretail

## Demarrage
Definir DOCKER_POSTGRES_PASSWORD dans PowerShell.
docker compose up -d postgres
docker compose build dbt
docker compose run --rm dbt debug

## Donnees
Importer les schemas raw et clean avant d'executer dbt.
Les sauvegardes PostgreSQL restent locales et sont exclues de Git.

## Pipeline
docker compose run --rm dbt build

## Resultats
16 modeles, 37 tests, 53 PASS, 0 erreur.

## Arret
docker compose down
Cette commande conserve les donnees PostgreSQL.
