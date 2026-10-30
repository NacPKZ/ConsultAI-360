# NexaRetail : Schéma relationnel

**Projet :** ConsultAI 360

**Phase :** 2 : Génération des données synthétiques

**Version :** 1.0

## 1. Objectif

Ce document définit le modèle relationnel initial de NexaRetail.

L'objectif est de créer un ensemble de données synthétiques, cohérent et reproductible, permettant d'analyser les activités commerciales, financières et logistiques de l'entreprise.

Le modèle est original. Il s'inspire de mécanismes métier observés dans des datasets de commerce et de distribution, sans reprendre leurs enregistrements.

## 2. Tables et volumes prévisionnels

| Table | Clé primaire | Volume cible |
|---|---|---:|
| customers | customer_id | 120 000 |
| stores | store_id | 35 |
| employees | employee_id | 450 |
| products | product_id | 8 000 |
| orders | order_id | 120 000 |
| order_items | order_item_id | Variable |
| payments | payment_id | Variable |
| shipments | shipment_id | Variable |
| complaints | complaint_id | Variable |
| inventory | inventory_id | Variable |

## 3. Relations

| Table | Clé étrangère | Table référencée |
|---|---|---|
| orders | customer_id | customers |
| orders | store_id | stores |
| order_items | order_id | orders |
| order_items | product_id | products |
| payments | order_id | orders |
| shipments | order_id | orders |
| complaints | order_id | orders |
| employees | store_id | stores |
| inventory | store_id | stores |
| inventory | product_id | products |

Les clés étrangères `orders.store_id` et `employees.store_id` peuvent être nulles selon les règles métier.

## 4. Colonnes principales

### customers

| Colonne | Type | Description |
|---|---|---|
| customer_id | VARCHAR | Identifiant unique |
| first_name | VARCHAR | Prénom fictif |
| last_name | VARCHAR | Nom fictif |
| city | VARCHAR | Ville |
| region | VARCHAR | Région |
| registration_date | DATE | Date d'inscription |
| loyalty_tier | VARCHAR | Niveau de fidélité |

### stores

| Colonne | Type | Description |
|---|---|---|
| store_id | VARCHAR | Identifiant unique |
| store_name | VARCHAR | Nom du magasin |
| city | VARCHAR | Ville |
| region | VARCHAR | Région |
| opening_date | DATE | Date d'ouverture |
| store_size_m2 | INTEGER | Surface commerciale |

### employees

| Colonne | Type | Description |
|---|---|---|
| employee_id | VARCHAR | Identifiant unique |
| store_id | VARCHAR | Magasin d'affectation |
| department | VARCHAR | Département |
| job_title | VARCHAR | Poste |
| hire_date | DATE | Date d'embauche |

### products

| Colonne | Type | Description |
|---|---|---|
| product_id | VARCHAR | Identifiant unique |
| product_name | VARCHAR | Nom du produit |
| category | VARCHAR | Catégorie |
| subcategory | VARCHAR | Sous-catégorie |
| brand | VARCHAR | Marque fictive |
| base_price | DECIMAL | Prix de référence |
| unit_cost | DECIMAL | Coût unitaire |

### orders

| Colonne | Type | Description |
|---|---|---|
| order_id | VARCHAR | Identifiant unique |
| customer_id | VARCHAR | Client |
| store_id | VARCHAR | Magasin associé, si applicable |
| order_date | TIMESTAMP | Date de commande |
| sales_channel | VARCHAR | online / in_store |
| order_status | VARCHAR | Statut de la commande |
| order_total | DECIMAL | Montant de la commande |

### order_items

| Colonne | Type | Description |
|---|---|---|
| order_item_id | VARCHAR | Identifiant unique |
| order_id | VARCHAR | Commande |
| product_id | VARCHAR | Produit |
| quantity | INTEGER | Quantité |
| unit_price | DECIMAL | Prix au moment de l'achat |
| discount_amount | DECIMAL | Remise sur la ligne |
| line_total | DECIMAL | Total après remise |

### payments

| Colonne | Type | Description |
|---|---|---|
| payment_id | VARCHAR | Identifiant unique |
| order_id | VARCHAR | Commande |
| payment_date | TIMESTAMP | Date de l'opération |
| payment_method | VARCHAR | Moyen de paiement |
| payment_type | VARCHAR | payment / refund |
| payment_status | VARCHAR | Statut de l'opération |
| amount | DECIMAL | Montant de l'opération |

### shipments

| Colonne | Type | Description |
|---|---|---|
| shipment_id | VARCHAR | Identifiant unique |
| order_id | VARCHAR | Commande |
| shipping_date | TIMESTAMP | Date d'expédition |
| expected_delivery_date | TIMESTAMP | Date prévue |
| actual_delivery_date | TIMESTAMP | Date réelle |
| delivery_status | VARCHAR | Statut de livraison |
| carrier | VARCHAR | Transporteur fictif |
| shipping_cost | DECIMAL | Coût logistique estimé |

### complaints

| Colonne | Type | Description |
|---|---|---|
| complaint_id | VARCHAR | Identifiant unique |
| order_id | VARCHAR | Commande concernée |
| complaint_date | TIMESTAMP | Date de création |
| complaint_type | VARCHAR | Motif |
| complaint_status | VARCHAR | Statut |
| resolution_date | TIMESTAMP | Date de résolution |

### inventory

| Colonne | Type | Description |
|---|---|---|
| inventory_id | VARCHAR | Identifiant unique |
| store_id | VARCHAR | Magasin |
| product_id | VARCHAR | Produit |
| stock_quantity | INTEGER | Stock disponible |
| reorder_point | INTEGER | Seuil de réapprovisionnement |
| last_update | TIMESTAMP | Dernière actualisation |

## 5. Règles de cohérence

1. Les clés primaires sont uniques et non nulles.
2. Les clés étrangères non nulles référencent des enregistrements existants.
3. Chaque commande appartient à un client.
4. Chaque commande possède au moins une ligne.
5. Les quantités sont strictement positives.
6. Les prix et les coûts unitaires ne sont pas négatifs.
7. Les remises sont comprises entre zéro et le montant brut de la ligne.
8. Le total d'une ligne correspond à la quantité multipliée par le prix unitaire, moins la remise.
9. Le total d'une commande correspond à la somme de ses lignes.
10. Une commande annulée ne doit pas être considérée comme livrée.
11. Une commande physique ne nécessite pas obligatoirement d'expédition.
12. Une livraison réelle ne peut pas précéder l'expédition.
13. Une réclamation ne peut pas être résolue avant sa création.
14. Les stocks disponibles ne peuvent pas être négatifs.
15. Un couple magasin-produit apparaît au maximum une fois dans la table inventory.

## 6. Règles de simulation

La génération utilisera Python et une graine aléatoire fixe.

Les données représenteront notamment :

- Des comportements d'achat hétérogènes.
- Des produits de popularité variable.
- Des variations saisonnières.
- Des différences entre magasins.
- Des commandes en ligne et en magasin.
- Des délais logistiques variables.
- Des réclamations liées à différents incidents.

Les paramètres seront documentés afin de permettre la reproduction des résultats.

## 7. Qualité des données

La génération initiale devra produire un ensemble de données conforme aux règles métier retenues.

Les anomalies volontaires seront introduites séparément pendant la phase 3.

Cette séparation permettra de mesurer les anomalies injectées, leur détection et leur correction.

## 8. Limites

Les données sont entièrement synthétiques.

Les comportements simulés ne constituent pas des observations réelles sur NexaRetail.

Les analyses et recommandations qui en découleront devront être interprétées dans le cadre de cette simulation.
