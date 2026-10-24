import gzip
import os
import sys
from pathlib import Path

# Permet l'import de la configuration si exécuté de façon isolée
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.logger import get_logger

logger = get_logger("Ingestion.raw")

"""
Module Ingestion : lecture des fichiers de logs bruts (texte et archives .gz)
depuis le dossier de données avec journalisation complète des événements et erreurs.
"""


def toRows(path="./Data"):
    """
    Lit tous les fichiers logs du dossier spécifié (fichiers texte et archives gzip)
    et retourne la liste complète des lignes de logs sous forme de chaînes.
    """
    rows = []
    data_dir = Path(path)

    if not data_dir.exists():
        alt_path = ROOT_DIR / "Data"
        if alt_path.exists():
            data_dir = alt_path
        else:
            logger.error(f"Dossier de donnees introuvable : {path}")
            return rows

    logger.info(f"Debut de l'ingestion depuis le dossier : {data_dir}")

    try:
        file_list = sorted(os.listdir(data_dir))
    except Exception as e:
        logger.error(f"Impossible de lister le contenu du dossier {data_dir} : {e}")
        return rows

    for file_name in file_list:
        # Ignorer les archives tar globales ou fichiers cachés
        if file_name.endswith(".tar.gz") or file_name.startswith("."):
            logger.debug(f"Fichier ignore : {file_name}")
            continue

        file_path = data_dir / file_name
        if not file_path.is_file():
            continue

        file_rows = []
        try:
            if file_name.endswith(".gz"):
                logger.info(f"Decompression et lecture de l'archive : {file_name}")
                with gzip.open(file_path, mode="rt", encoding="utf-8", errors="ignore") as f:
                    file_rows = f.readlines()
            else:
                logger.info(f"Lecture du fichier texte : {file_name}")
                with open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
                    file_rows = f.readlines()

            rows.extend(file_rows)
            logger.info(f"Succes : {file_name} ({len(file_rows):,} lignes lues)")

        except gzip.BadGzipFile as e:
            logger.error(f"Archive gzip corrompue dans {file_name} : {e}")
        except PermissionError as e:
            logger.error(f"Permission refusee pour lire {file_name} : {e}")
        except FileNotFoundError as e:
            logger.error(f"Fichier introuvable {file_name} : {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la lecture de {file_name} : {e}")

    logger.info(f"Fin de l'ingestion : {len(rows):,} lignes totales chargees.")
    return rows


def read_raw_data(path="./Data"):
    """Alias pour toRows pour compatibilité."""
    return toRows(path)


if __name__ == "__main__":
    logs = toRows("./Data")
    print(f"Total de lignes chargées : {len(logs)}")
    if logs:
        print("Exemple de première ligne :", logs[0].strip())
