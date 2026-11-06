import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

"""
Module de journalisation interne de l'application (Application Logging).
Utilise le format et les mécanismes de RotatingFileHandler vus en cours :
%(asctime)s|%(levelname)s|%(name)s|%(message)s
"""

LOG_FILE = Path(__file__).resolve().parent.parent / "app.log"

FORMATTER = logging.Formatter(
    fmt="%(asctime)s|%(levelname)s|%(name)s|%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour le module spécifié.
    Enregistre les messages INFO, WARNING et ERROR dans app.log.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Évite d'ajouter plusieurs fois les mêmes handlers
    if not logger.handlers:
        # 1. Handler fichier rotatif pour persister tous les événements et erreurs
        file_handler = RotatingFileHandler(
            filename=str(LOG_FILE),
            maxBytes=2 * 1024 * 1024,  # 2 Mo
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(FORMATTER)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # 2. Handler console (uniquement pour les avertissements et erreurs)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(FORMATTER)
        console_handler.setLevel(logging.WARNING)
        logger.addHandler(console_handler)

    return logger
