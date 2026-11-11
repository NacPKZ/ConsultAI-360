# Installation de l'assistant IA — guide historique (étape 8.3)

Ce document conserve la procédure d'installation suivie pendant l'étape 8.3. **Ne pas recopier les fichiers déjà présents dans le dépôt.** Vérifier l'environnement actuel avant toute modification.

1. Vérifier que `.env` et `.env.*` sont exclus par `.gitignore` et que les éventuels fichiers d'exemple ne contiennent aucun secret.
2. Configurer localement les variables d'environnement requises par l'assistant. Ne jamais publier `.env`. Ne pas présumer que le fichier `.env.assistant.example` existe dans la version courante.
3. Si le rôle PostgreSQL lecture seule n'existe pas encore, utiliser les instructions suivantes avec un administrateur. **Ne pas recréer un rôle déjà existant** :

```sql
CREATE ROLE assistant_ro LOGIN PASSWORD 'REMPLACER_PAR_MOT_DE_PASSE_FORT';
GRANT CONNECT ON DATABASE nexaretail_db TO assistant_ro;
GRANT USAGE ON SCHEMA dw TO assistant_ro;
GRANT SELECT ON dw.fact_orders, dw.fact_shipments TO assistant_ro;
```

Si le rôle existe déjà, ne pas réexécuter CREATE ROLE. Vérifier les permissions avec un administrateur.

4. Dans VS Code, terminal PowerShell à la racine :

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-assistant.txt
.\.venv\Scripts\python.exe -m pytest tests/test_assistant_kpi.py -q
.\.venv\Scripts\python.exe -m src.assistant.check_connection
```

Les tests unitaires doivent réussir sans connexion DB. Le contrôle de connexion affiche deux dictionnaires calculés sur la base locale; les chiffres ne sont pas connus à l'avance.

Note : `fact_shipments` doit exister et être chargé. La requête logistique calcule le retard à partir des dates, sans supposer que `is_late` est à jour.

Ne pas commiter de secrets. Vérifier `git status` dans VS Code avant commit.
