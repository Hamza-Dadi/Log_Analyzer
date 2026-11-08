# Log Analyzer - Pipeline d'Analyse de Logs

Hamza Dadi - 3ème Année Ingénierie Logicielle

## Présentation du Projet

Sur les serveurs Linux, toutes les tentatives de connexion et d'authentification sont enregistrées au fur et à mesure dans un fichier appelé `auth.log`. Quand un serveur est connecté à Internet, il reçoit en permanence des attaques de robots ou de pirates qui essaient de deviner les mots de passe.

Ce projet a pour but de créer un **pipeline de données complet en Python** pour analyser ces logs :
1. Lire automatiquement plus de **65 000 lignes de logs**, qu'elles soient dans des fichiers texte normaux ou dans des archives compressées `.gz`.
2. Extraire les informations utiles de chaque ligne (la date, l'heure, le nom d'utilisateur visé, l'adresse IP et le résultat de la tentative) grâce aux **expressions régulières (Regex)**.
3. Trouver le pays et la ville de chaque adresse IP attaquante en utilisant l'API **IPinfo**, avec un système de cache pour ne pas gaspiller les requêtes gratuites.
4. Enregistrer toutes les données propres dans une base de données **PostgreSQL** pour pouvoir faire des calculs et des tris très rapides avec le langage SQL.
5. Tracer tout ce qui se passe et enregistrer toutes les erreurs possibles dans un fichier journal **`app.log`**.
6. Afficher un **dashboard interactif avec Matplotlib** en mode sombre (fond noir), qui montre directement à l'écran les drapeaux des pays et les 3 graphiques demandés par Mr Lahmer.

---

## Organisation des Fichiers

Le projet est découpé en plusieurs dossiers, chacun ayant un rôle précis :

- **`Data/`** : Contient les fichiers de logs réels du serveur (`auth.log.1`, `auth.log.2`, `auth.log.3.gz`, `auth.log.4.gz`). Les fichiers terminés par `.gz` sont compressés pour prendre moins de place sur le disque.
- **`Ingestion/`** : 
  - `raw.py` : Ouvre et lit tous les fichiers du dossier `Data/`. Il sait décompresser directement les fichiers `.gz` en mémoire sans avoir besoin de les extraire sur le disque, et rassemble toutes les lignes dans une grande liste.
- **`Process/`** :
  - `exctract_transform.py` : Analyse chaque ligne de texte avec des expressions régulières pour séparer les champs (mois, jour, heure, nom de l'utilisateur, adresse IP, et type d'événement : mot de passe échoué, faux utilisateur, connexion réussie...).
  - `geolocation.py` : Interroge l'API IPinfo pour trouver le pays de chaque adresse IP. Il garde les résultats dans `ip_cache.json` pour ne pas redemander deux fois la même adresse et accélérer le programme.
- **`Storage/`** :
  - `database.py` : Gère la connexion avec la base de données PostgreSQL via la bibliothèque `psycopg2`. Il insère les 65 000 lignes dans la table et exécute les requêtes SQL d'analyse.
  - `schema_postgres.sql` : Contient le code SQL pour créer la table `security_logs` et les index qui rendent les recherches instantanées.
  - `main.py` : Enchaîne toutes les étapes du projet et crée deux fichiers récapitulatifs : un tableau `logs_clean.csv` et un fichier de chiffres clés `stats_summary.json`.
  - `flags/` : Dossier qui stocke les images des drapeaux de chaque pays en format PNG pour les afficher sur les graphiques.
- **`Serving/`** :
  - `visualizer.py` : Construit la fenêtre graphique avec Matplotlib en mode sombre, place les drapeaux des pays à côté des barres et affiche les 3 graphiques demandés.
- **`config/`** :
  - `logger.py` : Configure le système de logs de l'application qui écrit automatiquement dans `app.log`.
- **`main.py`** : Le fichier principal qu'il suffit d'exécuter pour lancer tout le pipeline d'un coup.

---

## Base de Données (PostgreSQL)

### Pourquoi utiliser une base de données ?
Parcourir un fichier texte de 65 000 lignes pour compter combien d'attaques viennent de chaque pays prendrait beaucoup de temps. En insérant les données dans **PostgreSQL**, on peut poser des questions directes avec le langage SQL (par exemple : *"donne-moi les 8 pays avec le plus d'échecs"*). La base répond en quelques millisecondes grâce à des **index** placés sur les colonnes importantes (le pays, l'adresse IP, l'utilisateur et le type d'événement).

### Paramètres de connexion
Le script utilise la bibliothèque officielle `psycopg2`. Par défaut, il utilise les réglages standards d'une installation locale de PostgreSQL :
- **Serveur (Hôte)** : `localhost` (la machine sur laquelle tourne le programme)
- **Port** : `5432` (le port standard officiel de PostgreSQL)
- **Base de données** : `security_logs`
- **Utilisateur** : `postgres` (l'utilisateur principal créé par défaut par PostgreSQL)
- **Mot de passe** : `postgres`

Si vos identifiants sont différents, vous pouvez les modifier facilement grâce à des variables d'environnement (`PG_HOST`, `PG_PORT`, `PG_DB`, `PG_USER`, `PG_PASSWORD`) sans avoir à modifier le code Python.

*Note pratique :* Si le serveur PostgreSQL n'est pas allumé sur votre ordinateur au moment du test, le programme le détecte, l'écrit dans `app.log` et utilise automatiquement les statistiques sauvegardées dans `stats_summary.json` pour que la fenêtre graphique s'affiche quand même sans planter.

---

## Journalisation des Erreurs (`app.log`)

Comme vu en cours avec le module `logging`, le projet ne laisse aucune erreur silencieuse et n'affiche pas de messages d'erreur compliqués à l'utilisateur :
- Tout est consigné dans le fichier **`app.log`**.
- La configuration utilise un **`RotatingFileHandler`** : le fichier a une taille maximale (2 Mo). Quand il est plein, il crée une archive automatique pour ne jamais saturer le disque.
- Le format de chaque ligne respecte la consigne du cours :  
  `date et heure | niveau de gravité | nom du module | message explicatif`
- Tous les modules (`Ingestion`, `Process`, `Storage`, `Serving`) utilisent des blocs `try / except` pour attraper les problèmes (fichier absent, coupure réseau vers l'API, base de données inaccessible) et les enregistrer avec le niveau adapté (`INFO`, `WARNING` ou `ERROR`).

---

## Dashboard Demandé par Mr Lahmer

Le visualiseur ouvre une fenêtre graphique interactive Matplotlib en thème sombre (fond noir `#0d1117`, reposant pour les yeux) avec les **3 graphiques demandés par Mr Lahmer** :

1. **Nombre de tentatives échouées par pays** :
   - Un graphique en barres horizontales rouges montrant d'où viennent les attaques.
   - Affiche le nom complet du pays, le nombre d'attaques et le vrai drapeau du pays en image PNG.
   - On remarque que les deux plus gros attaquants sont la Roumanie (2 561 attaques) et les Pays-Bas (2 149 attaques), suivis par le Vietnam, la Finlande et la Pologne.

2. **Nombre de tentatives réussies par user** :
   - Un graphique en barres vertes montrant les accès légitimes sur la machine.
   - On y voit les connexions réussies par l'administrateur `adminesisa` (en SSH) et les ouvertures de sessions du compte `root`.

3. **Tentatives échouées avec invalid user** :
   - Un graphique en barres orange qui liste les faux noms d'utilisateurs les plus souvent testés par les pirates pour essayer d'entrer.
   - Les comptes les plus attaqués sont `admin` (407 fois), `esisa` (193 fois), `ubuntu` (144 fois), puis `user`, `test`, `support`, `dev` et `solana`.

Un 4ème panneau affiche un résumé global avec les chiffres totaux (total des lignes, total des attaques, pays n°1, statut du système).

---

## Comment Exécuter le Projet

Pour lancer le pipeline complet :

```bash
python main.py
```

Le programme va :
1. Charger les 65 565 lignes de logs depuis le dossier `Data/`.
2. Découper les lignes et récupérer les pays des adresses IP.
3. Se connecter à PostgreSQL pour préparer les données.
4. Noter chaque action dans `app.log`.
5. Ouvrir la fenêtre interactive avec les graphiques et les drapeaux.
