# Environnement Docker — ConsultAI 360

Ce dossier contient la configuration de connexion dbt utilisée avec Docker Compose. Le fichier `compose.yaml` et le fichier `Dockerfile.dbt` restent à la racine du dépôt, conformément aux chemins actuels du projet.

## Composants documentés

- PostgreSQL 18, base `nexaretail_db`, port hôte 5433 dans la configuration historique.
- dbt Core et adaptateur PostgreSQL.
- Profil dbt : `docker/dbt/profiles.yml`.

## Prérequis

Docker Desktop doit être démarré et le moteur Docker disponible. Définir la variable d'environnement `DOCKER_POSTGRES_PASSWORD` dans la session PowerShell avant le démarrage. Les secrets ne doivent pas être ajoutés à Git.

## Commandes de référence

À lancer **depuis la racine du dépôt**, uniquement si Docker est disponible et que les variables requises sont configurées :

```powershell
docker compose up -d postgres
docker compose build dbt
docker compose run --rm dbt debug
```

Les schémas sources `raw` et `clean` doivent être importés avant la construction des modèles. Les sauvegardes PostgreSQL restent locales.

Pour construire et tester les modèles :

```powershell
docker compose run --rm dbt build
```

Pour arrêter les conteneurs sans supprimer explicitement les volumes :

```powershell
docker compose down
```

## État de validation

Le bilan historique mentionne 16 modèles, 37 tests et 53 contrôles réussis. **Ces résultats ne constituent pas une validation de Docker à la date de ce nettoyage.** L'étape 11 a notamment documenté une variable d'environnement absente et un moteur Docker indisponible. Aucune réexécution Docker n'est nécessaire pour la réorganisation documentaire.

Voir [le bilan de validation](../docs/11_validation_reproductibilite.md) et [le guide dbt](../dbt_nexaretail/README.md).
