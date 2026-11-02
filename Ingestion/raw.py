import gzip
import os
from pathlib import Path

"""
Module Ingestion : lecture des fichiers de logs bruts (texte et archives .gz)
depuis le dossier de données.
"""

def toRows(path="./Data"):
    """
    Lit tous les fichiers logs du dossier spécifié (fichiers texte et archives gzip)
    et retourne la liste complète des lignes de logs sous forme de chaînes.
    """
    rows = []
    data_dir = Path(path)

    if not data_dir.exists():
        # Essayer avec le chemin relatif depuis la racine si exécuté depuis un sous-dossier
        alt_path = Path(__file__).resolve().parent.parent / "Data"
        if alt_path.exists():
            data_dir = alt_path
        else:
            print(f"[!] Dossier introuvable : {path}")
            return rows

    # Tri pour assurer un ordre chronologique des fichiers de logs
    for file_name in sorted(os.listdir(data_dir)):
        # Ignorer les archives tar globales ou fichiers cachés
        if file_name.endswith(".tar.gz") or file_name.startswith("."):
            continue

        file_path = data_dir / file_name
        if not file_path.is_file():
            continue

        # Lecture selon le format : archive .gz ou fichier texte normal
        if file_name.endswith(".gz"):
            with gzip.open(file_path, mode="rt", encoding="utf-8", errors="ignore") as f:
                rows.extend(f.readlines())
        else:
            with open(file_path, mode="r", encoding="utf-8", errors="ignore") as f:
                rows.extend(f.readlines())

    return rows


def read_raw_data(path="./Data"):
    """Alias pour toRows pour compatibilité."""
    return toRows(path)


if __name__ == "__main__":
    logs = toRows("./Data")
    print(f"Total de lignes chargées : {len(logs)}")
    if logs:
        print("Exemple de première ligne :", logs[0].strip())
