import re
import sys
from pathlib import Path

# Permet l'import de la configuration si exécuté de façon isolée
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.logger import get_logger

logger = get_logger("Process.extract")

"""
Module Process / Extraction & Transformation :
Parse les lignes de logs auth brutes avec les expressions régulières (re)
pour extraire les champs structurés : date, heure, service, type d'événement, utilisateur ciblé et IP.
Enregistre les logs et erreurs éventuelles dans l'application log.
"""

# Pattern global pour l'en-tête standard des logs Linux syslog/auth
LOG_HEADER_PATTERN = re.compile(
    r'^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}))\s+'
    r'(?P<host>\S+)\s+(?P<service>[a-zA-Z0-9_\-]+)(?:\[\d+\])?:\s+(?P<message>.*)$'
)

# Pattern pour extraire les adresses IPv4
IP_PATTERN = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

# Patterns spécifiques pour les types d'événements et les utilisateurs
FAILED_USER_PATTERN = re.compile(r'Failed password for (?:invalid user )?(\S+)', re.IGNORECASE)
INVALID_USER_PATTERN = re.compile(r'Invalid user (\S+)', re.IGNORECASE)
ACCEPTED_USER_PATTERN = re.compile(r'Accepted \S+ for (\S+)', re.IGNORECASE)
SESSION_USER_PATTERN = re.compile(r'session (?:opened|closed) for user (\S+)', re.IGNORECASE)


def extract_from_row(row):
    """
    Parse une seule ligne de log auth et retourne un dictionnaire structuré,
    ou None si la ligne ne correspond pas au format attendu.
    Gère et journalise les erreurs potentielles d'extraction.
    """
    if not isinstance(row, str):
        logger.warning(f"Ligne de type invalide recue : {type(row)}")
        return None

    row = row.strip()
    if not row:
        return None

    try:
        match = LOG_HEADER_PATTERN.match(row)
        if not match:
            # Ligne non conforme au format syslog Linux
            return None

        data = match.groupdict()
        message = data["message"]

        # Catégorisation de l'événement et extraction du compte ciblé
        event_type = "Other"
        user = None

        if "Failed password" in message:
            event_type = "Failed Password"
            u_match = FAILED_USER_PATTERN.search(message)
            if u_match:
                user = u_match.group(1)
        elif "Invalid user" in message:
            event_type = "Invalid User"
            u_match = INVALID_USER_PATTERN.search(message)
            if u_match:
                user = u_match.group(1)
        elif "Accepted" in message:
            event_type = "Accepted Login"
            u_match = ACCEPTED_USER_PATTERN.search(message)
            if u_match:
                user = u_match.group(1)
        elif "session opened" in message:
            event_type = "Session Opened"
            u_match = SESSION_USER_PATTERN.search(message)
            if u_match:
                user = u_match.group(1).split("(")[0]
        elif "session closed" in message:
            event_type = "Session Closed"
            u_match = SESSION_USER_PATTERN.search(message)
            if u_match:
                user = u_match.group(1).split("(")[0]
        elif "Connection closed" in message:
            event_type = "Connection Closed"

        # Extraction des adresses IP (en ignorant les adresses locales de loopback)
        found_ips = [ip for ip in IP_PATTERN.findall(message) if not ip.startswith("127.")]
        ip = found_ips[0] if found_ips else None

        return {
            "month": data["month"],
            "day": int(data["day"]),
            "time": data["time"],
            "hour": int(data["hour"]),
            "host": data["host"],
            "service": data["service"],
            "event_type": event_type,
            "user": user,
            "ip": ip,
            "message": message
        }
    except ValueError as e:
        logger.error(f"Erreur de conversion de type lors du parsing : {e} (Ligne: {row[:80]})")
        return None
    except Exception as e:
        logger.error(f"Erreur inattendue de regex/transformation : {e} (Ligne: {row[:80]})")
        return None


def extract_all(rows):
    """
    Transforme une collection de lignes de logs brutes en une liste d'enregistrements structurés.
    Journalise le début, la progression et les totaux.
    """
    if not rows:
        logger.warning("Aucune ligne fournie pour l'extraction.")
        return []

    logger.info(f"Debut de l'extraction Regex sur {len(rows):,} lignes...")
    transformed = []
    ignored_count = 0

    for row in rows:
        parsed = extract_from_row(row)
        if parsed:
            transformed.append(parsed)
        else:
            ignored_count += 1

    logger.info(
        f"Fin de l'extraction : {len(transformed):,} enregistrements valides extraits, "
        f"{ignored_count:,} lignes non reconnues ou vides."
    )
    return transformed


if __name__ == "__main__":
    test_line = "May 24 00:28:00 ns sshd[1351222]: Failed password for invalid user test from 45.156.87.204 port 41740 ssh2"
    result = extract_from_row(test_line)
    print("Test unitaire extract_from_row :")
    for k, v in result.items():
        print(f"  {k}: {v}")
