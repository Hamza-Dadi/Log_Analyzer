import json
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

# Permet l'import de la configuration si exécuté de façon isolée
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.logger import get_logger

logger = get_logger("Process.geolocation")

"""
Module Geolocation :
Interroge l'API IPinfo avec le token personnel pour récupérer les données
géographiques d'une adresse IP (pays, ville, organisation).
Comprend un système de cache local JSON pour éviter les requêtes redondantes
et préserver le quota d'API.
Journalise toutes les opérations et erreurs réseau ou de sérialisation.
"""

# Token personnel fourni pour le projet
DEFAULT_TOKEN = os.getenv("IPINFO_TOKEN", "8bb730052f446e")

# Chemin du cache local dans le dossier Storage
CACHE_FILE = ROOT_DIR / "Storage" / "ip_cache.json"

# Cache en mémoire
_CACHE = {}


def _load_cache():
    """Charge le cache des adresses IP depuis le fichier JSON."""
    global _CACHE
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
            logger.debug(f"Cache IP charge depuis le disque : {len(_CACHE)} entrees.")
        except json.JSONDecodeError as e:
            logger.error(f"Fichier de cache IP corrompu (JSONDecodeError) : {e}. Reinitialisation.")
            _CACHE = {}
        except Exception as e:
            logger.error(f"Erreur inattendue lors du chargement du cache IP : {e}")
            _CACHE = {}
    else:
        logger.debug("Aucun fichier de cache IP existant. Demarrage avec cache vide.")
    return _CACHE


def _save_cache():
    """Sauvegarde le cache en mémoire dans le fichier JSON."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, indent=2, ensure_ascii=False)
        logger.debug(f"Cache IP sauvegarde ({len(_CACHE)} entrees).")
    except PermissionError as e:
        logger.error(f"Permission refusee pour ecrire le cache IP dans {CACHE_FILE} : {e}")
    except Exception as e:
        logger.error(f"Erreur de sauvegarde du cache IP : {e}")


# Chargement initial au chargement du module
_load_cache()


def is_private_ip(ip):
    """Vérifie si une adresse IP est locale ou privée."""
    if not ip or ip == "127.0.0.1" or ip.startswith("10.") or ip.startswith("192.168."):
        return True
    if ip.startswith("172."):
        parts = ip.split(".")
        if len(parts) > 1 and 16 <= int(parts[1]) <= 31:
            return True
    return False


def get_location(ip, token=DEFAULT_TOKEN):
    """
    Récupère la géolocalisation d'une adresse IP depuis le cache ou l'API IPinfo.
    Retourne un dictionnaire avec : country, city, region, org, loc.
    Gère et journalise les erreurs réseau, timeouts et codes HTTP anormaux.
    """
    if not ip:
        return {"country": "Inconnu", "city": "Inconnu", "org": "N/A"}

    # Vérification des adresses locales
    if is_private_ip(ip):
        return {"country": "Local", "city": "Reseau prive", "org": "LAN", "loc": "0,0"}

    # 1. Vérification dans le cache local
    if ip in _CACHE:
        return _CACHE[ip]

    # 2. Requête vers l'API IPinfo avec le token
    url = f"https://ipinfo.io/{ip}/json"
    params = {"token": token} if token else {}

    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            info = {
                "country": data.get("country", "Inconnu"),
                "city": data.get("city", "Inconnu"),
                "region": data.get("region", "Inconnu"),
                "org": data.get("org", "Inconnu"),
                "loc": data.get("loc", "")
            }
            _CACHE[ip] = info
            _save_cache()
            return info
        else:
            logger.warning(f"Reponse API IPinfo inattendue pour {ip} : statut HTTP {response.status_code}")
            fallback = {"country": "Inconnu", "city": "Inconnu", "org": f"HTTP {response.status_code}"}
            _CACHE[ip] = fallback
            return fallback

    except requests.exceptions.Timeout:
        logger.error(f"Timeout (5s) depasse lors de la requete IPinfo pour l'adresse {ip}")
        return {"country": "Inconnu", "city": "Timeout", "org": "Erreur reseau"}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Erreur de connexion a l'API IPinfo pour {ip} : {e}")
        return {"country": "Inconnu", "city": "Erreur connexion", "org": "Erreur reseau"}
    except Exception as e:
        logger.error(f"Erreur inattendue IPinfo pour {ip} : {e}")
        return {"country": "Inconnu", "city": "Erreur", "org": str(e)}


def get_locations_bulk(unique_ips, token=DEFAULT_TOKEN, max_workers=8):
    """
    Récupère en parallèle les géolocalisations pour une liste d'adresses IP uniques
    en utilisant ThreadPoolExecutor.
    """
    results = {}
    missing_ips = [ip for ip in unique_ips if ip and ip not in _CACHE and not is_private_ip(ip)]

    # Mettre immédiatement les IPs déjà en cache
    for ip in unique_ips:
        if ip in _CACHE:
            results[ip] = _CACHE[ip]
        elif is_private_ip(ip):
            results[ip] = {"country": "Local", "city": "Reseau prive", "org": "LAN"}

    if not missing_ips:
        logger.info(f"Geolocalisation : Toutes les {len(unique_ips)} adresses sont deja en cache local.")
        return results

    logger.info(
        f"Interrogation IPinfo pour {len(missing_ips)} adresses IP uniques manquantes (sur {len(unique_ips)} demandees)..."
    )

    def fetch(ip):
        return ip, get_location(ip, token=token)

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for ip, info in executor.map(fetch, missing_ips):
                results[ip] = info
    except Exception as e:
        logger.error(f"Erreur lors de l'execution du pool de threads IPinfo : {e}")

    _save_cache()
    return results


if __name__ == "__main__":
    test_ips = ["109.109.109.109", "109.199.110.135", "203.171.18.62"]
    for test_ip in test_ips:
        loc = get_location(test_ip)
        print(f"{test_ip} -> {loc.get('country')}, {loc.get('city')} ({loc.get('org')})")
