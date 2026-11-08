import sys
from pathlib import Path

# Assure que la racine du projet est dans sys.path quel que soit le dossier d'appel
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from Storage.main import run_pipeline

"""
Point d'entrée principal du projet Log Analyzer.
Lance l'exécution complète du pipeline de données :
Ingestion -> Process (Regex + IPinfo) -> Storage (PostgreSQL + CSV/JSON) -> Serving (Dashboard interactif)
"""

if __name__ == "__main__":
    run_pipeline()
