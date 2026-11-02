import sys
import csv
import json
from pathlib import Path
from collections import Counter

# Ajout du dossier racine Log_Analyzer au path pour permettre l'exécution directe
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Ingestion import raw
from Process import exctract_transform
from Process import geolocation
from Storage.database import LogDatabase
from Serving import visualizer

"""
Point d'entrée du pipeline de données :
1. Ingestion : lecture des logs bruts (auth.log.1, auth.log.2, etc.)
2. Process : extraction Regex et enrichissement avec l'API IPinfo
3. Storage : insertion relationnelle dans SQLite + exports CSV et JSON
4. Serving : affichage interactif direct des graphiques Matplotlib à l'écran
"""


def run_pipeline(data_path="./Data", max_ips_to_query=50, launch_visualizer=True):
    print("=" * 65)
    print("      LOG ANALYZER - PIPELINE DE SÉCURITÉ & STATISTIQUES (ESISA) ")
    print("=" * 65)

    # 1. Ingestion
    print("\n[1/4] Ingestion des fichiers de logs...")
    raw_rows = raw.toRows(data_path)
    print(f"      -> {len(raw_rows):,} lignes de logs lues depuis '{data_path}'.")

    # 2. Process / Extraction Regex
    print("\n[2/4] Extraction et structuration Regex...")
    records = exctract_transform.extract_all(raw_rows)
    print(f"      -> {len(records):,} enregistrements structurés avec succès.")

    # Comptage des adresses IP uniques
    ip_counts_raw = Counter(r["ip"] for r in records if r["ip"])
    print(f"      -> {len(ip_counts_raw)} adresses IP uniques identifiées.")

    # 3. Process / Géolocalisation avec l'API IPinfo
    print(f"\n[3/4] Géolocalisation via l'API IPinfo (Top {max_ips_to_query} IPs)...")
    top_ips = [ip for ip, _ in ip_counts_raw.most_common(max_ips_to_query)]
    ip_locations = geolocation.get_locations_bulk(top_ips)

    # 4. Storage / Persistance Relationnelle (SQLite) & Fichiers
    print("\n[4/4] Persistance des données dans le dossier Storage...")
    storage_dir = ROOT_DIR / "Storage"
    storage_dir.mkdir(exist_ok=True)

    # 4.1 Insertion dans la base de données relationnelle SQLite
    db = LogDatabase()
    print("      -> Insertion des 65,000+ enregistrements dans SQLite (security_logs.db)...")
    db.insert_records(records, ip_locations=ip_locations, clear_first=True)
    db_total = db.get_total_count()
    print(f"      -> [OK] {db_total:,} lignes enregistrées dans la table 'security_logs'.")

    # 4.2 Récupération des statistiques optimisées par requêtes SQL
    country_counts = db.query_top_countries(limit=10)
    event_counts = db.query_event_counts()
    ip_counts = db.query_top_ips(limit=10)
    hourly_counts = db.query_hourly_activity()
    top_users = db.query_top_users(limit=10)

    # 4.3 Export CSV des logs nettoyés et enrichis
    csv_file = storage_dir / "logs_clean.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["month", "day", "time", "hour", "service", "event_type", "user", "ip", "country", "city"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            ip = r.get("ip")
            loc = ip_locations.get(ip, {}) if ip else {}
            writer.writerow({
                "month": r.get("month"),
                "day": r.get("day"),
                "time": r.get("time"),
                "hour": r.get("hour"),
                "service": r.get("service"),
                "event_type": r.get("event_type"),
                "user": r.get("user") or "",
                "ip": ip or "",
                "country": loc.get("country", ""),
                "city": loc.get("city", "")
            })
    print(f"      -> Fichier CSV généré : {csv_file.name}")

    # 4.4 Export JSON du résumé statistique
    summary_file = storage_dir / "stats_summary.json"
    summary_data = {
        "total_lines": len(raw_rows),
        "total_in_db": db_total,
        "unique_ips": len(ip_counts_raw),
        "events_summary": dict(event_counts),
        "top_10_ips": ip_counts.most_common(10),
        "top_10_countries": country_counts.most_common(10),
        "top_10_targeted_users": top_users
    }
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    print(f"      -> Résumé statistique enregistré : {summary_file.name}")

    # Résumé console
    print("\n" + "=" * 65)
    print("                    RÉSUMÉ DES RÉSULTATS (SQL)")
    print("=" * 65)
    print(f"  * Total des logs en base SQLite : {db_total:,}")
    print(f"  * Tentatives de mot de passe KO : {event_counts.get('Failed Password', 0):,}")
    print(f"  * Utilisateurs invalides        : {event_counts.get('Invalid User', 0):,}")
    print(f"  * Connexions réussies (Accepted): {event_counts.get('Accepted Login', 0):,}")
    print("-" * 65)
    print("  [Top 5 des Pays Sources d'Attaques (SQL GROUP BY)] :")
    for c, cnt in country_counts.most_common(5):
        print(f"    - {c:<6} : {cnt:>6,} requêtes")
    print("-" * 65)
    print("  [Top 5 des Comptes Ciblés (SQL)] :")
    for u, cnt in top_users[:5]:
        print(f"    - {u:<12} : {cnt:>6,} tentatives")
    print("=" * 65)

    # 5. Serving / Lancement de l'affichage interactif à l'écran
    if launch_visualizer:
        print("\n[*] Ouverture de la fenêtre interactive des graphiques...")
        stats = {
            "countries": country_counts,
            "events": event_counts,
            "ips": ip_counts,
            "hourly": hourly_counts,
            "ip_locations": ip_locations
        }
        visualizer.show_dashboard(stats)


if __name__ == "__main__":
    run_pipeline()
