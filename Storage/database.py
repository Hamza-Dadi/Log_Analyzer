import os
import sys
import json
from pathlib import Path
from collections import Counter
import psycopg2
from psycopg2 import extras

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.logger import get_logger

logger = get_logger("Storage.database")

"""
Module Database (Storage) :
Gere la persistance relationnelle des logs de securite dans une base de donnees PostgreSQL.
Utilise exclusivement la bibliotheque psycopg2.
Cree la table 'security_logs' et les index B-Tree pour optimiser les requetes analytiques.
Journalise toutes les operations et erreurs de base de donnees dans app.log.
"""


class PostgresDatabase:
    """Gestionnaire de base de donnees relationnelle PostgreSQL pour les logs."""

    def __init__(self, host=None, port=None, dbname=None, user=None, password=None):
        self.host = host or os.getenv("PG_HOST", "localhost")
        self.port = int(port or os.getenv("PG_PORT", 5432))
        self.dbname = dbname or os.getenv("PG_DB", "security_logs")
        self.user = user or os.getenv("PG_USER", "postgres")
        self.password = password or os.getenv("PG_PASSWORD", "postgres")
        self.engine_name = "postgresql"
        self.is_connected = False
        self._check_and_init()

    def get_connection(self):
        """Ouvre et retourne une connexion PostgreSQL."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
            connect_timeout=3
        )

    def _check_and_init(self):
        """Verifie la connexion et initialise la structure de la table."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS security_logs (
                            id SERIAL PRIMARY KEY,
                            month VARCHAR(10),
                            day INTEGER,
                            time VARCHAR(20),
                            hour INTEGER,
                            service VARCHAR(50),
                            event_type VARCHAR(50),
                            username VARCHAR(100),
                            ip_address VARCHAR(50),
                            country VARCHAR(10),
                            city VARCHAR(100),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE INDEX IF NOT EXISTS idx_security_country ON security_logs(country);
                        CREATE INDEX IF NOT EXISTS idx_security_ip ON security_logs(ip_address);
                        CREATE INDEX IF NOT EXISTS idx_security_event ON security_logs(event_type);
                        CREATE INDEX IF NOT EXISTS idx_security_hour ON security_logs(hour);
                        CREATE INDEX IF NOT EXISTS idx_security_user ON security_logs(username);
                    """)
                conn.commit()
            self.is_connected = True
            logger.info(f"Connexion PostgreSQL reussie. Schema et index initialises sur {self.dbname} ({self.host}:{self.port}).")
        except psycopg2.OperationalError as e:
            self.is_connected = False
            logger.warning(
                f"Serveur PostgreSQL non joignable sur {self.host}:{self.port} ({e}). "
                "Mode hors-ligne actif (utilisation des donnees pre-calculees)."
            )
        except Exception as e:
            self.is_connected = False
            logger.error(f"Erreur d'initialisation PostgreSQL : {e}")

    def insert_records(self, records, ip_locations=None, clear_first=True):
        """
        Insere en lot (batch) les enregistrements structurés dans PostgreSQL via execute_values.
        """
        if not self.is_connected:
            logger.warning("Insertion PostgreSQL ignoree : serveur PostgreSQL non connecte.")
            return

        ip_locations = ip_locations or {}
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    if clear_first:
                        cur.execute("TRUNCATE TABLE security_logs RESTART IDENTITY;")
                        logger.debug("Table PostgreSQL 'security_logs' purgee.")

                    batch_data = []
                    for r in records:
                        ip = r.get("ip") or ""
                        loc = ip_locations.get(ip, {}) if ip else {}
                        batch_data.append((
                            r.get("month", ""),
                            r.get("day", 0),
                            r.get("time", ""),
                            r.get("hour", 0),
                            r.get("service", ""),
                            r.get("event_type", ""),
                            r.get("user") or "",
                            ip,
                            loc.get("country", ""),
                            loc.get("city", "")
                        ))

                    query = """
                        INSERT INTO security_logs (
                            month, day, time, hour, service, event_type, username, ip_address, country, city
                        ) VALUES %s
                    """
                    extras.execute_values(cur, query, batch_data, page_size=2000)
                conn.commit()
            logger.info(f"Succes : {len(records):,} enregistrements inseres dans PostgreSQL.")
        except Exception as e:
            logger.error(f"Erreur lors de l'insertion dans PostgreSQL : {e}")

    # ─────────────────────────────────────────────────────────────
    # Requêtes Spécifiques au Dashboard demandé par le Professeur
    # ─────────────────────────────────────────────────────────────

    def query_failed_by_country(self, limit=8):
        """Métrique 1 : Nombre de tentatives échouées par pays."""
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT country, COUNT(*) as cnt
                            FROM security_logs
                            WHERE event_type IN ('Failed Password', 'Invalid User')
                              AND country IS NOT NULL AND country != '' AND country != 'Inconnu'
                            GROUP BY country
                            ORDER BY cnt DESC
                            LIMIT %s;
                        """, (limit,))
                        results = cur.fetchall()
                        logger.debug(f"query_failed_by_country executee avec succes ({len(results)} pays).")
                        return results
            except Exception as e:
                logger.error(f"Erreur query_failed_by_country PostgreSQL : {e}")

        # Secours via le resume statistique si PostgreSQL est hors-ligne
        return self._load_fallback_summary().get("failed_by_country", [])[:limit]

    def query_successful_by_user(self):
        """Métrique 2 : Nombre de tentatives réussies par utilisateur."""
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT username, COUNT(*) as cnt
                            FROM security_logs
                            WHERE event_type IN ('Accepted Login', 'Session Opened')
                              AND username IS NOT NULL AND username != ''
                            GROUP BY username
                            ORDER BY cnt DESC;
                        """)
                        results = cur.fetchall()
                        logger.debug(f"query_successful_by_user executee avec succes ({len(results)} users).")
                        return results
            except Exception as e:
                logger.error(f"Erreur query_successful_by_user PostgreSQL : {e}")

        return self._load_fallback_summary().get("successful_by_user", [])

    def query_failed_invalid_users(self, limit=8):
        """Métrique 3 : Tentatives échouées avec utilisateur invalide."""
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT username, COUNT(*) as cnt
                            FROM security_logs
                            WHERE event_type = 'Invalid User'
                              AND username IS NOT NULL AND username != ''
                            GROUP BY username
                            ORDER BY cnt DESC
                            LIMIT %s;
                        """, (limit,))
                        results = cur.fetchall()
                        logger.debug(f"query_failed_invalid_users executee avec succes ({len(results)} faux users).")
                        return results
            except Exception as e:
                logger.error(f"Erreur query_failed_invalid_users PostgreSQL : {e}")

        return self._load_fallback_summary().get("failed_invalid_users", [])[:limit]

    def query_top_countries(self, limit=10):
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT country, COUNT(*) as cnt
                            FROM security_logs
                            WHERE country IS NOT NULL AND country != '' AND country != 'Inconnu'
                            GROUP BY country
                            ORDER BY cnt DESC
                            LIMIT %s;
                        """, (limit,))
                        return Counter(dict(cur.fetchall()))
            except Exception as e:
                logger.error(f"Erreur query_top_countries PostgreSQL : {e}")
        return Counter(dict(self._load_fallback_summary().get("top_10_countries", [])))

    def query_event_counts(self):
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT event_type, COUNT(*) as cnt
                            FROM security_logs
                            WHERE event_type IS NOT NULL AND event_type != ''
                            GROUP BY event_type
                            ORDER BY cnt DESC;
                        """)
                        return Counter(dict(cur.fetchall()))
            except Exception as e:
                logger.error(f"Erreur query_event_counts PostgreSQL : {e}")
        return Counter(self._load_fallback_summary().get("events_summary", {}))

    def query_top_ips(self, limit=10):
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT ip_address, COUNT(*) as cnt
                            FROM security_logs
                            WHERE ip_address IS NOT NULL AND ip_address != ''
                            GROUP BY ip_address
                            ORDER BY cnt DESC
                            LIMIT %s;
                        """, (limit,))
                        return Counter(dict(cur.fetchall()))
            except Exception as e:
                logger.error(f"Erreur query_top_ips PostgreSQL : {e}")
        return Counter(dict(self._load_fallback_summary().get("top_10_ips", [])))

    def query_hourly_activity(self):
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            SELECT hour, COUNT(*) as cnt
                            FROM security_logs
                            GROUP BY hour
                            ORDER BY hour ASC;
                        """)
                        return Counter(dict(cur.fetchall()))
            except Exception as e:
                logger.error(f"Erreur query_hourly_activity PostgreSQL : {e}")
        return Counter()

    def get_total_count(self):
        if self.is_connected:
            try:
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT COUNT(*) FROM security_logs;")
                        row = cur.fetchone()
                        return row[0] if row else 0
            except Exception as e:
                logger.error(f"Erreur get_total_count PostgreSQL : {e}")
        return self._load_fallback_summary().get("total_in_db", 65565)

    def _load_fallback_summary(self):
        """Charge le résumé JSON pré-calculé si PostgreSQL n'est pas actif."""
        summary_file = ROOT_DIR / "Storage" / "stats_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}


# Alias pour compatibilité
LogDatabase = PostgresDatabase


if __name__ == "__main__":
    db = LogDatabase()
    print(f"Base de donnees active : {db.engine_name}")
    print(f"Statut connexion PostgreSQL : {'Connecte' if db.is_connected else 'Hors-ligne'}")
    print("Tentatives echouees par pays :", db.query_failed_by_country(5))
    print("Tentatives reussies par user :", db.query_successful_by_user())
    print("Tentatives echouees invalid users :", db.query_failed_invalid_users(5))
