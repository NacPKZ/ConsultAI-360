# Étape 8.3 — Installation

Copier les fichiers dans la racine du dépôt (fusionner `src`, `tests`, ne pas supprimer l'existant).

1. Ajouter `.env` et `.env.*` à `.gitignore`, en gardant l'exception `!.env.assistant.example`.
2. Copier `.env.assistant.example` vers `.env` et remplacer le mot de passe. Ne jamais commiter `.env`.
3. Créer un rôle PostgreSQL lecture seule dans DBeaver, avec les instructions ci-dessous (exécuter avec un administrateur) :

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
