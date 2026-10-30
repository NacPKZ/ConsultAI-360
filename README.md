## Choix méthodologiques — Données textuelles

### Architecture à deux sources

ConsultAI 360 distingue deux sources de données indépendantes :

**1. NexaRetail — Données transactionnelles synthétiques**

Les données de clients, commandes, produits, paiements, livraisons, stocks et réclamations sont générées artificiellement.

Elles permettent de simuler un environnement d'entreprise cohérent, de contrôler la qualité des données et d'évaluer l'impact des anomalies sur les indicateurs métier.

**2. Corpus d'avis clients — Données textuelles réelles**

Le corpus `SetFit/amazon_reviews_multi_fr` constitue une source indépendante destinée aux futures analyses NLP : extraction de thèmes, analyse des sentiments, regroupement sémantique et synthèse automatique.

Ces avis ne proviennent pas de NexaRetail et ne sont pas associés à ses clients ou à ses commandes.

### Expérimentation abandonnée : enrichissement des réclamations

Trois versions d'un processus d'enrichissement ont été expérimentées :

| Version | Textes associés | Couverture |
|---|---:|---:|
| V1 | 3 580 | 40,28 % |
| V2 | 1 644 | 18,50 % |
| V2.1 | 902 | 10,15 % |

Les contrôles ont révélé des incohérences entre certains avis réels et les produits des commandes synthétiques.

L'ajout de règles de filtrage a réduit les associations problématiques détectables, mais n'a pas permis de garantir leur cohérence sémantique.

**Décision : abandonner cette association artificielle et conserver les deux sources séparées.**

Les scripts et rapports statistiques sont conservés afin de documenter les expérimentations, leurs limites et les raisons de ce changement d'architecture.

### Conséquences pour la suite

- Les 8 888 réclamations NexaRetail conservent leur structure synthétique d'origine.
- Les avis réels ne sont pas utilisés pour simuler des messages authentiques des clients NexaRetail.
- Les anomalies de la phase 3 seront injectées uniquement dans des copies des données synthétiques.
- Le corpus textuel pourra être exploité indépendamment lors de la phase NLP.
- Les textes réels ne seront pas publiés dans le dépôt avant vérification des droits de redistribution.
- Toute classification supervisée devra tenir compte des biais d'étiquetage et être évaluée sur des données annotées indépendamment.

Cette démarche illustre une décision de gouvernance des données : privilégier la traçabilité et la validité méthodologique plutôt qu'une couverture artificiellement élevée.
