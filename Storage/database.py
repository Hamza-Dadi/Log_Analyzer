import sqlite3
from pathlib import Path
from collections import Counter

"""
Module Database (Storage) :
Gère la persistance relationnelle des logs de sécurité dans une base de données SQLite.
Permet d'exécuter des requêtes SQL optimisées (indexation, agrégations, filtres rapides).
Utilise exclusivement le module standard sqlite3 de Python.
"""

DB_FILE = Path(__file__).resolve().parent / "security_logs.db"


class LogDatabase:
    """Gestionnaire de base de données relationnelle SQLite pour les logs."""

    def __init__(self, db_path=DB_FILE):
        self.db_path = Path(db_path)
        self.init_db()

    def get_connection(self):
        """Ouvre et retourne une connexion SQLite."""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialise le schéma de la table et les index de performance."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Création de la table principale
            cursor.execute("""
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
            """)

            # Création d'index pour accélérer les requêtes d'analyse et de reporting
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_country ON security_logs(country);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_ip ON security_logs(ip_address);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_event ON security_logs(event_type);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hour ON security_logs(hour);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON security_logs(username);")
            conn.commit()

    def insert_records(self, records, ip_locations=None, clear_first=True):
        """
        Insère en lot (batch) les enregistrements structurés dans la base SQLite.
        clear_first: si True, réinitialise la table pour éviter les doublons lors d'un ré-exécution.
        """
        ip_locations = ip_locations or {}

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if clear_first:
                cursor.execute("DELETE FROM security_logs;")

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

            cursor.executemany("""
                INSERT INTO security_logs (
                    month, day, time, hour, service, event_type, username, ip_address, country, city
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, batch_data)
            conn.commit()

    def query_top_countries(self, limit=10):
        """Retourne un Counter du Top des pays sources via une requête SQL GROUP BY."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT country, COUNT(*) as cnt
                FROM security_logs
                WHERE country IS NOT NULL AND country != '' AND country != 'Inconnu'
                GROUP BY country
                ORDER BY cnt DESC
                LIMIT ?;
            """, (limit,))
            return Counter(dict(cursor.fetchall()))

    def query_event_counts(self):
        """Retourne un Counter de la répartition des événements via SQL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT event_type, COUNT(*) as cnt
                FROM security_logs
                WHERE event_type IS NOT NULL AND event_type != ''
                GROUP BY event_type
                ORDER BY cnt DESC;
            """)
            return Counter(dict(cursor.fetchall()))

    def query_top_ips(self, limit=10):
        """Retourne un Counter du Top des adresses IP via SQL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ip_address, COUNT(*) as cnt
                FROM security_logs
                WHERE ip_address IS NOT NULL AND ip_address != ''
                GROUP BY ip_address
                ORDER BY cnt DESC
                LIMIT ?;
            """, (limit,))
            return Counter(dict(cursor.fetchall()))

    def query_hourly_activity(self):
        """Retourne un Counter de l'activité horaire via SQL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT hour, COUNT(*) as cnt
                FROM security_logs
                GROUP BY hour
                ORDER BY hour ASC;
            """)
            return Counter(dict(cursor.fetchall()))

    def query_top_users(self, limit=10):
        """Retourne les noms d'utilisateurs les plus ciblés."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, COUNT(*) as cnt
                FROM security_logs
                WHERE username IS NOT NULL AND username != ''
                GROUP BY username
                ORDER BY cnt DESC
                LIMIT ?;
            """, (limit,))
            return cursor.fetchall()

    def get_total_count(self):
        """Compte total d'enregistrements en base."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM security_logs;")
            row = cursor.fetchone()
            return row[0] if row else 0


if __name__ == "__main__":
    db = LogDatabase()
    print("Table SQLite initialisée avec succès :", db.db_path)
