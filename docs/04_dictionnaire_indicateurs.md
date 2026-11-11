# 04 · Dictionnaire des indicateurs — Référentiel KPI

> **CONSULTAI 360 / CONTRAT DE MESURE**  
> **Version :** référentiel enrichi · **Périmètre :** NexaRetail synthétique, expérience ML DataCo indépendante, ROI hypothétique.

[← Processus](03_processus_metier.md) · [Index](INDEX.md) · [Périmètre →](05_perimetre_projet.md)

---

## Principe fondamental

> **Un KPI = une définition + une source + une granularité + un dénominateur + des filtres + une règle de gestion des données manquantes.**

Le dictionnaire initial proposait des indicateurs métier génériques. Cette version distingue **définition cible**, **mesure réellement disponible** et **indicateur à ne pas afficher sans données suffisantes**. Les formules ci-dessous sont des règles métier ; elles ne prétendent pas reproduire mot pour mot toutes les mesures DAX.

## 1. Règles transversales

| Dimension de contrôle | Règle |
|:--|:--|
| **Scénario** | Ne jamais joindre ORIGINAL, LOW, MEDIUM et CRITICAL sans clé de scénario |
| **Grain** | Distinguer commande, ligne de vente, paiement, expédition, réclamation |
| **Montants** | Ne pas assimiler montant de commande, montant de ligne et encaissement |
| **Valeurs nulles** | Afficher complétude et exclusions ; ne pas remplacer silencieusement par zéro |
| **Dates** | Préciser la date utilisée : commande, expédition, livraison |
| **Ratios** | Protéger la division par zéro et définir la population éligible |
| **Comparaison** | Vérifier même période, même scénario et même périmètre |
| **Gouvernance** | Versionner la définition si la règle change |

## 2. Ventes et finance

| KPI | Définition opérationnelle | Grain / vigilance |
|:--|:--|:--|
| **Nombre de commandes** | `COUNT(DISTINCT order_id)` sur le périmètre défini | Commande ; statut et scénario à préciser |
| **CA mesuré des commandes** | Somme des montants de commande **renseignés** | Commande ; ne pas qualifier automatiquement de CA net |
| **Panier moyen mesuré** | CA des commandes renseignées ÷ nombre de commandes avec montant renseigné | Éviter de diviser par toutes les commandes si certaines n'ont pas de montant |
| **Part online** | Commandes du canal en ligne ÷ commandes avec canal évaluable | Définir si part en **nombre** ou en **montant** |
| **CA par magasin** | Somme du montant selon la règle d'attribution magasin | Inclure/mesurer les non attribuables |
| **Complétude du montant** | Commandes avec montant ÷ commandes contrôlées | Accompagne tout CA affecté par des nulls |
| **CA net** | Ventes − remises − remboursements selon règles validées | **Indicateur cible** : ne pas l'assimiler au CA mesuré sans rapprochement |
| **Marge brute** | CA net − coût des produits vendus | **Conditionnel** à la disponibilité de coûts fiables |

### Exemple de lecture documentée — scénario MEDIUM

| Mesure | Valeur | Signification |
|:--|--:|:--|
| Commandes | **120 000** | Volume du scénario |
| Montants renseignés | **114 000** | 95 % de complétude |
| Montants manquants | **6 000** | 5 % de non-complétude |
| CA mesuré | **68 448 127,94 €** | Somme des montants connus |
| Panier moyen sur montants renseignés | **600,42 €** | 68 448 127,94 ÷ 114 000, arrondi |

> [!CAUTION]
> Un **montant manquant dans la donnée** n'est pas une vente perdue. Les résultats d'autres vues Power BI peuvent utiliser des granularités ou définitions différentes ; tout rapprochement doit préciser la mesure comparée.

## 3. Logistique

| KPI | Formule / règle | Population |
|:--|:--|:--|
| **Expéditions** | Nombre d'enregistrements d'expédition selon identifiant retenu | Expéditions |
| **Expéditions évaluables** | Expéditions disposant des informations nécessaires à la règle de retard | Sous-ensemble évaluable |
| **Retards** | Nombre d'expéditions évaluables dont la livraison réelle dépasse la date prévue | Évaluables |
| **Taux de retard** | Retards ÷ expéditions évaluables × 100 | **Ne pas utiliser toutes les commandes** |
| **Taux à temps** | Livraisons à temps ÷ expéditions évaluables × 100 | Même règle d'éligibilité |
| **Couverture logistique** | Expéditions évaluables ÷ expéditions totales × 100 | Toutes les expéditions |
| **Délai moyen** | Moyenne des durées calculables selon les dates définies | Exclure explicitement les dates non exploitables |
| **Délai de préparation** | Fin de préparation − validation | **Conditionnel** aux horodatages disponibles |

**Exemple documenté MEDIUM :** 70 567 expéditions ; 70 005 évaluables ; 10 333 en retard ; **14,76 %** de retard (arrondi). Les 562 non évaluables ne doivent pas être classées comme ponctuelles.

## 4. Qualité des données

| KPI | Formule | Attention |
|:--|:--|:--|
| **Complétude** | Valeurs présentes ÷ valeurs attendues × 100 | Définir champs et population |
| **Taux de doublons** | Enregistrements identifiés comme doublons ÷ enregistrements contrôlés × 100 | Préciser clé et définition du doublon |
| **Taux de références invalides** | Lignes dont la référence n'existe pas ÷ lignes contrôlées × 100 | Une même transaction peut comporter plusieurs anomalies |
| **Taux d'anomalies** | Éléments anormaux ÷ éléments contrôlés × 100 | **Ne pas mélanger cellules et lignes** |
| **Précision de détection** | VP ÷ (VP + FP) | Nécessite une vérité terrain |
| **Rappel de détection** | VP ÷ (VP + FN) | Nécessite une vérité terrain |
| **F1-score** | 2 × précision × rappel ÷ (précision + rappel) | Éviter toute confusion avec le F1 du ML |

Les **82 953 anomalies de référence** mentionnées dans le README sont des lignes affectées dans plusieurs tables, **pas 82 953 commandes distinctes**.

## 5. Machine Learning — DataCo uniquement

| Indicateur | Sens | Valeur finale documentée |
|:--|:--|--:|
| **ROC AUC** | Capacité globale de classement des scores | **76,05 %** |
| **Rappel** | Part des retards réels détectés | **77,66 %** |
| **Précision** | Part des alertes positives correspondant à des retards | **65,88 %** |
| **F1-score** | Équilibre précision/rappel | **71,29 %** |
| **Seuil de classification** | Seuil retenu pour convertir le score en alerte | **0,40** |

Les métriques proviennent de l'[évaluation finale DataCo](08_rapport_final_prediction.md). Elles **ne mesurent pas** les performances d'un modèle déployé chez NexaRetail. Une AUC n'est pas une exactitude.

## 6. Assistant IA et pilotage

| KPI / critère | Règle | Statut |
|:--|:--|:--|
| Conformité d'une réponse | Respect des sections et des garde-fous définis | Contrôle applicatif |
| Exactitude factuelle | Faits corrects ÷ faits évalués | À mesurer sur un protocole explicitement documenté |
| Temps de reporting | Temps entre demande et restitution | À instrumenter pour démontrer un gain |
| Gain de temps | Temps de référence − temps après changement | **Hypothèse** tant qu'aucun pilote n'est mesuré |
| Coût d'exploitation | Charges opérationnelles incluses dans le modèle | Définir horizon et exclusions |

**Règle de sécurité analytique :** les chiffres sont produits par SQL/Python ; le modèle génératif **commente**, sans inventer de nouveaux KPI.

## 7. ROI — interprétation financière

`ROI = (bénéfices estimés − coûts retenus) / coûts retenus × 100`, pour un horizon et un périmètre de coûts **explicitement identiques**.

| Scénario | ROI hypothétique documenté | Lecture |
|:--|--:|:--|
| Prudent | **36,5 %** | Hypothèses conservatrices |
| Central | **110 %** | Hypothèses intermédiaires |
| Optimiste | **194 %** | Hypothèses favorables |

> [!WARNING]
> Ces ROI ne sont **ni des gains observés ni une promesse financière**. Le périmètre du modèle comporte des exclusions documentées, notamment certains coûts récurrents et éléments fiscaux. Se reporter au [rapport de conseil](12_rapport_final_conseil.md) avant toute réutilisation.

## 8. Fiche de validation d'un nouvel indicateur

Avant publication, renseigner : **nom**, **question métier**, **formule**, **table source**, **grain**, **filtres**, **population éligible**, **traitement des nulls**, **propriétaire métier**, **contrôle de rapprochement**, **limites** et **date de version**.

## 9. Références

[Rapport Power BI](10_rapport_power_bi.md) · [Évaluation ML](08_rapport_final_prediction.md) · [Validation et reproductibilité](11_validation_reproductibilite.md) · [Rapport final](12_rapport_final_conseil.md)

---

**Suite :** [05 · Périmètre](05_perimetre_projet.md) · [06 · Charte de projet](06_charte_projet.md)
