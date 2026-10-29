# NexaRetail : Cartographie des processus métier

**Projet :** ConsultAI 360

**Entreprise :** NexaRetail

**Document :** Analyse des processus opérationnels

## 1. Objectif

Cette cartographie vise à représenter les principales étapes du parcours d'une commande chez NexaRetail.

Elle permet d'identifier les départements impliqués, les données produites et les risques opérationnels susceptibles d'affecter la performance de l'entreprise.

## 2. Processus de gestion des commandes

Le processus étudié comprend six étapes principales.

### 2.1. Création de la commande

Le client sélectionne des produits sur la plateforme e-commerce ou effectue un achat en magasin.

Le système enregistre les informations relatives à la commande.

**Données :** identifiant client, identifiant commande, produits, quantités, prix et date.

### 2.2. Validation du paiement

Le système vérifie le paiement associé à la commande.

Un paiement accepté permet de poursuivre le traitement. Un paiement refusé nécessite un traitement spécifique.

**Données :** montant, moyen de paiement, date et statut.

### 2.3. Préparation de la commande

Les équipes concernées organisent la préparation des produits commandés.

Cette étape comprend la vérification des articles et leur préparation pour l'expédition.

**Données :** produits, quantités, statut de préparation et dates.

### 2.4. Expédition et transport

La commande est confiée à un transporteur chargé de son acheminement.

Les informations de suivi permettent de contrôler son avancement.

**Données :** transporteur, date d'expédition, date prévue de livraison et statut.

### 2.5. Livraison

La commande est remise au client.

L'entreprise peut comparer la date réelle de livraison à la date initialement prévue.

**Données :** date de livraison réelle, délai de livraison et retard éventuel.

### 2.6. Service après-vente

En cas de problème, le client peut contacter le service client.

Les réclamations peuvent concerner les retards, les produits ou les paiements.

**Données :** identifiant de réclamation, motif, date de création, statut et date de résolution.

## 3. Départements impliqués

| Processus | Département principal | Données produites |
|---|---|---|
| Création de commande | Commercial | Commandes, produits |
| Validation du paiement | Finance | Paiements |
| Préparation | Logistique | Statuts, dates |
| Expédition | Logistique | Transporteurs, expéditions |
| Livraison | Logistique | Délais, retards |
| Réclamations | Service client | Tickets, résolutions |

## 4. Risques opérationnels

Plusieurs risques peuvent affecter le processus :

- Commandes enregistrées avec des informations incorrectes.
- Paiements présentant des incohérences.
- Retards dans la préparation des commandes.
- Difficultés de suivi des expéditions.
- Livraisons réalisées après la date prévue.
- Réclamations non résolues dans les délais attendus.

Ces risques constituent des hypothèses qui seront étudiées lors des analyses de données.

## 5. Opportunités d'amélioration

L'exploitation des données pourrait permettre :

1. D'automatiser certains contrôles de qualité.
2. De centraliser les informations commerciales et logistiques.
3. De suivre les délais de livraison dans Power BI.
4. D'identifier les facteurs associés aux retards.
5. D'améliorer le suivi des réclamations.
6. De faciliter l'interprétation des indicateurs grâce à un assistant IA.

## 6. Conclusion

La cartographie met en évidence les interactions entre les activités commerciales, financières, logistiques et le service client.

Elle constitue une base pour définir les indicateurs de performance, structurer les données et identifier les processus pouvant bénéficier des solutions développées dans ConsultAI 360.
