# Veille logements CROUS 🏠

Scraper qui surveille [trouverunlogement.lescrous.fr](https://trouverunlogement.lescrous.fr)
et t'envoie un **email** dès qu'un nouveau logement se libère dans ta zone,
grâce à **GitHub Actions** (aucun serveur à héberger, gratuit).

## Comment ça marche

1. Toutes les 15 minutes, GitHub Actions lance `scraper.py`.
2. Le script récupère la page de résultats de ta recherche (rendue côté serveur)
   et extrait les annonces (titre, prix, adresse, lien).
3. Il compare avec le dernier passage (`state.json`) : si une **nouvelle** annonce
   apparaît, il t'envoie un email récapitulatif.
4. L'état est re-committé dans le dépôt pour ne pas te notifier deux fois pour la
   même annonce (une annonce qui disparaît puis revient te re-notifie).

## Installation (5 minutes)

### 1. Créer le dépôt
Crée un dépôt GitHub (privé de préférence) et pousse ces fichiers dedans.

### 2. Définir ta recherche
Va sur https://trouverunlogement.lescrous.fr, applique tes filtres (ville, prix…)
sur la carte, puis **copie l'URL** de la page de résultats. Elle ressemble à :

```
https://trouverunlogement.lescrous.fr/tools/42/search?bounds=2.22_48.90_2.47_48.81
```

Dans ton dépôt GitHub : **Settings → Secrets and variables → Actions → Variables →
New repository variable** :

| Nom          | Valeur                                    |
|--------------|-------------------------------------------|
| `SEARCH_URL` | l'URL de recherche copiée ci-dessus       |

Pour surveiller **plusieurs villes**, mets plusieurs URLs dans `SEARCH_URL`,
une par ligne (ou séparées par des espaces).

### 3. Configurer l'email (Gmail)
Il faut un **mot de passe d'application** Gmail (pas ton mot de passe normal) :
1. Active la validation en 2 étapes sur ton compte Google.
2. Va sur https://myaccount.google.com/apppasswords et génère un mot de passe
   d'application (16 caractères).

Puis dans **Settings → Secrets and variables → Actions → Secrets → New repository
secret**, ajoute :

| Nom             | Valeur                                         |
|-----------------|------------------------------------------------|
| `MAIL_USERNAME` | ton adresse Gmail (`toi@gmail.com`)            |
| `MAIL_PASSWORD` | le mot de passe d'application (16 caractères)  |
| `MAIL_TO`       | la ou les adresses qui reçoivent les alertes   |

Pour prévenir plusieurs personnes, mets toutes les adresses dans `MAIL_TO`
séparées par des virgules : `moi@gmail.com,quelquun@exemple.fr`.

### 4. Activer et tester
- Onglet **Actions** → active les workflows si demandé.
- Lance-le à la main : **Veille logements CROUS → Run workflow** pour vérifier
  que tout marche (regarde les logs, et ta boîte mail).

## Tester en local

```bash
SEARCH_URL="https://trouverunlogement.lescrous.fr/tools/42/search?bounds=..." \
  STATE_FILE=/tmp/state.json python3 scraper.py
```

Aucune dépendance à installer : le script n'utilise que la bibliothèque standard Python.

## Bon à savoir

- **Pagination** : le site affiche 24 annonces par page. Pour une zone bien ciblée
  (une ville), les résultats tiennent sur une page — aucun souci. Pour une zone très
  large avec beaucoup d'offres, seules les 24 premières sont vues.
- **Fréquence** : `cron: "*/15 * * * *"`. Tu peux réduire à `*/5` (minimum GitHub),
  mais les crons GitHub sont parfois retardés de quelques minutes en cas de charge.
- **Crons désactivés** : GitHub désactive les workflows planifiés après 60 jours
  **sans activité** sur le dépôt. Les commits d'état réguliers gardent le dépôt actif.
- **Autre canal** que l'email (Telegram, Discord, issue GitHub) : facile à ajouter,
  demande-moi.
```
