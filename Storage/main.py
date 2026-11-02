import sys
import csv
import json
from pathlib import Path
from collections import Counter

# Ajout du dossier racine Log_Analyzer au path pour permettre l'exécution directe
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.logger import get_logger
from Ingestion import raw
from Process import exctract_transform
from Process import geolocation
from Storage.database import LogDatabase
from Serving import visualizer

logger = get_logger("Storage.main")

"""
Point d'entrée principal du pipeline de données de sécurité :
1. Ingestion : lecture robuste des logs bruts (fichiers texte et archives gzip)
2. Process : extraction Regex et enrichissement avec l'API IPinfo (pays, ville)
3. Storage : insertion relationnelle dans PostgreSQL + exports CSV et JSON
4. Serving : affichage interactif direct des 3 graphiques demandés par le professeur
Journalisation complète de l'exécution et des erreurs dans app.log.
"""


def run_pipeline(data_path="./Data", max_ips_to_query=50, launch_visualizer=True):
    logger.info("Demarrage complet du pipeline Log Analyzer...")
    print("=" * 65)
    print("      LOG ANALYZER - PIPELINE DE SECURITE & STATISTIQUES ")
    print("=" * 65)

    try:
        # 1. Ingestion
        print("\n[1/4] Ingestion des fichiers de logs...")
        raw_rows = raw.toRows(data_path)
        print(f"      -> {len(raw_rows):,} lignes de logs lues depuis '{data_path}'.")

        if not raw_rows:
            logger.warning("Aucune donnee brute trouvee lors de l'ingestion.")

        # 2. Process / Extraction Regex
        print("\n[2/4] Extraction et structuration Regex...")
        records = exctract_transform.extract_all(raw_rows)
        print(f"      -> {len(records):,} enregistrements structures avec succes.")

        # Comptage des adresses IP uniques
        ip_counts_raw = Counter(r["ip"] for r in records if r.get("ip"))
        print(f"      -> {len(ip_counts_raw)} adresses IP uniques identifiees.")

        # 3. Process / Géolocalisation avec l'API IPinfo
        print(f"\n[3/4] Geolocalisation via l'API IPinfo (Top {max_ips_to_query} IPs)...")
        top_ips = [ip for ip, _ in ip_counts_raw.most_common(max_ips_to_query)]
        ip_locations = geolocation.get_locations_bulk(top_ips)

        # 4. Storage / Persistance Relationnelle (PostgreSQL) & Fichiers
        print("\n[4/4] Persistance des donnees dans le dossier Storage...")
        storage_dir = ROOT_DIR / "Storage"
        storage_dir.mkdir(exist_ok=True)

        # 4.1 Insertion dans la base de donnees relationnelle PostgreSQL
        db = LogDatabase()
        print("      -> Moteur de base de donnees : PostgreSQL (table 'security_logs')")
        if db.is_connected:
            print("      -> Insertion des enregistrements dans PostgreSQL...")
            db.insert_records(records, ip_locations=ip_locations, clear_first=True)
            db_total = db.get_total_count()
            print(f"      -> [OK] {db_total:,} lignes enregistrees dans PostgreSQL.")
        else:
            print("      -> [INFO] Serveur PostgreSQL non demarre en local (mode hors-ligne actif).")
            db_total = db.get_total_count()

        # 4.2 Récupération des 3 métriques exactes demandées par le professeur
        failed_by_country = db.query_failed_by_country(limit=8)
        successful_by_user = db.query_successful_by_user()
        failed_invalid_users = db.query_failed_invalid_users(limit=8)

        # Métriques complémentaires
        country_counts = db.query_top_countries(limit=10)
        event_counts = db.query_event_counts()
        ip_counts = db.query_top_ips(limit=10)
        hourly_counts = db.query_hourly_activity()

        # 4.3 Export CSV des logs nettoyés et enrichis
        csv_file = storage_dir / "logs_clean.csv"
        try:
            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                fieldnames = ["month", "day", "time", "hour", "service", "event_type", "user", "ip", "country", "city"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in records:
                    ip = r.get("ip") or ""
                    loc = ip_locations.get(ip, {}) if ip else {}
                    writer.writerow({
                        "month": r.get("month", ""),
                        "day": r.get("day", 0),
                        "time": r.get("time", ""),
                        "hour": r.get("hour", 0),
                        "service": r.get("service", ""),
                        "event_type": r.get("event_type", ""),
                        "user": r.get("user") or "",
                        "ip": ip,
                        "country": loc.get("country", ""),
                        "city": loc.get("city", "")
                    })
            logger.info(f"Fichier CSV genere avec succes : {csv_file.name}")
            print(f"      -> Fichier CSV genere : {csv_file.name}")
        except Exception as e:
            logger.error(f"Erreur lors de l'export CSV : {e}")

        # 4.4 Export JSON du résumé statistique
        summary_file = storage_dir / "stats_summary.json"
        try:
            summary_data = {
                "total_lines": len(raw_rows),
                "total_in_db": db_total,
                "unique_ips": len(ip_counts_raw),
                "failed_by_country": failed_by_country,
                "successful_by_user": successful_by_user,
                "failed_invalid_users": failed_invalid_users,
                "events_summary": dict(event_counts),
                "top_10_ips": ip_counts.most_common(10),
                "top_10_countries": country_counts.most_common(10)
            }
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Resume JSON exporte avec succes : {summary_file.name}")
            print(f"      -> Resume statistique enregistre : {summary_file.name}")
        except Exception as e:
            logger.error(f"Erreur lors de l'export JSON : {e}")

        # Résumé console
        print("\n" + "=" * 65)
        print("                    RESUME DES RESULTATS (SQL)")
        print("=" * 65)
        print(f"  * Total des logs en base PostgreSQL : {db_total:,}")
        print(f"  * Tentatives echouees           : {event_counts.get('Failed Password', 0) + event_counts.get('Invalid User', 0):,}")
        print(f"  * Connexions reussies (Accepted): {event_counts.get('Accepted Login', 0):,}")
        print("-" * 65)
        print("  [1. Nombre tentatives echouees par pays (SQL)] :")
        for c, cnt in failed_by_country[:5]:
            print(f"    - {c:<6} : {cnt:>6,} echecs")
        print("-" * 65)
        print("  [2. Nombre tentatives reussies par user (SQL)] :")
        for u, cnt in successful_by_user:
            print(f"    - {u:<12} : {cnt:>6,} reussites")
        print("-" * 65)
        print("  [3. Tentatives echouees avec invalid user (SQL)] :")
        for u, cnt in failed_invalid_users[:5]:
            print(f"    - {u:<12} : {cnt:>6,} tentatives")
        print("=" * 65)

        logger.info("Pipeline termine avec succes.")

        # 5. Serving / Lancement de l'affichage interactif à l'écran
        if launch_visualizer:
            stats = {
                "failed_by_country": failed_by_country,
                "successful_by_user": successful_by_user,
                "failed_invalid_users": failed_invalid_users,
                "countries": country_counts,
                "events": event_counts,
                "ips": ip_counts,
                "hourly": hourly_counts,
                "ip_locations": ip_locations
            }
            visualizer.show_dashboard(stats)

    except Exception as e:
        logger.critical(f"Erreur critique lors de l'execution du pipeline : {e}", exc_info=True)
        print(f"[!] Erreur critique : {e}")
        raise


if __name__ == "__main__":
    run_pipeline()
