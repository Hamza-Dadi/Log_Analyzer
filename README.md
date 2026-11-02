# 🛡️ Log Analyzer - Projet Python (ESISA 3ème Année)

Système complet d'ingestion, d'extraction Regex, d'enrichissement par géolocalisation IP, de **persistance en base de données relationnelle SQLite** et de visualisation graphique interactive des journaux d'authentification Linux (`auth.log`).

Projet réalisé dans le cadre du module Python — École Supérieure d'Ingénierie en Sciences Appliquées (**ESISA**).

---

## 🏗️ Architecture du Projet

Le projet respecte scrupuleusement la séparation en couches d'un pipeline de données industriel :

```text
Log_Analyzer/
│
├── Data/                   # Données sources (auth.log.1, auth.log.2, auth.log.3.gz, auth.log.4.gz)
│
├── Ingestion/              # Couche 1 : Ingestion des flux de logs
│   ├── __init__.py
│   └── raw.py              # Lecture des fichiers texte et des archives compressées .gz
│
├── Process/                # Couche 2 : Traitement et enrichissement
│   ├── __init__.py
│   ├── exctract_transform.py # Extraction par expressions régulières (re)
│   └── geolocation.py      # Interrogation de l'API IPinfo avec token personnel & cache local
│
├── Storage/                # Couche 3 : Persistance & Base de données
│   ├── __init__.py
│   ├── database.py         # Gestionnaire de base de données relationnelle SQLite (table & index)
│   ├── main.py             # Orchestrateur central du pipeline
│   ├── logs_clean.csv      # Export tabulaire des logs enrichis
│   ├── stats_summary.json  # Métriques et compteurs agrégés
│   ├── ip_cache.json       # Cache persistant des coordonnées IPinfo
│   └── flags/              # Cache des drapeaux PNG de chaque pays
│
├── Serving/                # Couche 4 : Restitution et affichage interactif
│   ├── __init__.py
│   └── visualizer.py       # Affichage interactif direct des graphiques Matplotlib à l'écran (Dark Mode + Flags)
│
├── main.py                 # Point d'entrée principal à la racine
├── pyproject.toml          # Configuration de l'environnement uv
└── README.md               # Documentation du projet
```

---

## ⚙️ Modules et Bibliothèques Utilisés

Le projet n'utilise que les bibliothèques autorisées en cours :
* **`re`** : Extraction structurée des dates, daemons (`sshd`, `CRON`), événements (`Failed password`, `Invalid user`, `Accepted`) et adresses IP.
* **`sqlite3`** : Modélisation relationnelle, indexation et requêtes d'agrégation SQL (`GROUP BY`, `ORDER BY`, `COUNT`).
* **`gzip` & `os` / `pathlib`** : Lecture des archives compressées de rotation de logs.
* **`requests`** : Connexion à l'API [ipinfo.io](https://ipinfo.io/) pour la géolocalisation des attaquants.
* **`concurrent.futures`** : Requêtes multithreadées pour accélérer la résolution des adresses IP.
* **`matplotlib`** : Affichage graphique interactif à l'écran en mode sombre (TkAgg).
* **`csv` & `json`** : Stockage persistant et cache.

---

## 🗄️ Modélisation de la Base de Données (SQLite)

Le module `Storage/database.py` gère automatiquement la table `security_logs` :

```sql
CREATE TABLE IF NOT EXISTS security_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT,
    day INTEGER,
    time TEXT,
    hour INTEGER,
    service TEXT,
    event_type TEXT,
    username TEXT,
    ip_address TEXT,
    country TEXT,
    city TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour accélérer les requêtes d'analyse
CREATE INDEX IF NOT EXISTS idx_country ON security_logs(country);
CREATE INDEX IF NOT EXISTS idx_ip ON security_logs(ip_address);
CREATE INDEX IF NOT EXISTS idx_event ON security_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_hour ON security_logs(hour);
```

### Pourquoi une base de données relationnelle ?
1. **Performance des requêtes analytiques** : les requêtes SQL avec `GROUP BY country` ou `GROUP BY hour` sont exécutées en quelques millisecondes grâce aux index B-Tree.
2. **Intégrité et transactions ACID** : garantit l'intégrité des 65 000 enregistrements insérés en lot (`executemany`).
3. **Persistance robuste** : permet d'interroger la base sans devoir re-parser les fichiers bruts à chaque fois.

---

## 🚀 Installation & Exécution

### 1. Prérequis
Python 3.10+ avec les dépendances installées :
```bash
pip install matplotlib requests
# ou avec uv :
uv sync
```

### 2. Lancement du Pipeline
Exécutez simplement la commande à la racine du projet :
```bash
.\.venv\Scripts\python.exe main.py
# ou
python main.py
```

Le programme insère les données dans la base SQLite, affiche le résumé console, puis **ouvre automatiquement la fenêtre interactive Matplotlib (Dark Mode avec drapeaux)** sur votre écran.

---

## 📊 Tableau de Bord Graphique Interactif (Dark Mode)

La fenêtre interactive regroupe simultanément :

1. **Top 8 des Pays d'Origine des Attaques** : Diagramme en barres horizontales avec **drapeaux réels en PNG**.
2. **Répartition des Événements** : Donut / Camembert de la proportion des événements de sécurité.
3. **Top 8 des Adresses IP Attaquantes** : Classement des adresses IP les plus agressives avec mention de leur pays.
4. **Distribution Horaire des Attaques (00h - 23h)** : Courbe temporelle d'activité montrant la fréquence des attaques selon l'heure.

---

## 📈 Résultats Observés sur le Jeu de Données (Extraits par SQL)

* **Total de logs en base de données** : **65 565** enregistrements
* **Tentatives d'accès bloquées (Failed password)** : **10 962**
* **Comptes utilisateurs inexistants (Invalid user)** : **3 166**
* **Connexions réussies (Accepted login)** : **734**
* **Comptes les plus ciblés par force brute** : `root` (11 971 tentatives), `admin` (761), `esisa` (396), `support` (375).
* **Principaux pays d'origine détectés** : Roumanie (`RO`), Pays-Bas (`NL`), Vietnam (`VN`), Finlande (`FI`), Lituanie (`LT`).
