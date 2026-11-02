import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests

"""
Module Geolocation :
Interroge l'API IPinfo avec le token personnel pour récupérer les données
géographiques d'une adresse IP (pays, ville, organisation).
Comprend un système de cache local JSON pour éviter les requêtes redondantes
et préserver le quota d'API.
"""

# Token personnel fourni pour le projet
DEFAULT_TOKEN = os.getenv("IPINFO_TOKEN", "8bb730052f446e")

# Chemin du cache local dans le dossier Storage
CACHE_FILE = Path(__file__).resolve().parent.parent / "Storage" / "ip_cache.json"

# Cache en mémoire
_CACHE = {}


def _load_cache():
    """Charge le cache des adresses IP depuis le fichier JSON."""
    global _CACHE
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
        except Exception:
            _CACHE = {}
    return _CACHE


def _save_cache():
    """Sauvegarde le cache en mémoire dans le fichier JSON."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_CACHE, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Erreur de sauvegarde du cache IP : {e}")


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
            fallback = {"country": "Inconnu", "city": "Inconnu", "org": f"HTTP {response.status_code}"}
            _CACHE[ip] = fallback
            return fallback
    except Exception as e:
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
        return results

    print(f"[*] Interrogation de l'API IPinfo pour {len(missing_ips)} nouvelle(s) adresse(s) IP...")

    def fetch(ip):
        return ip, get_location(ip, token=token)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for ip, info in executor.map(fetch, missing_ips):
            results[ip] = info

    _save_cache()
    return results


if __name__ == "__main__":
    test_ips = ["109.109.109.109", "109.199.110.135", "203.171.18.62"]
    for test_ip in test_ips:
        loc = get_location(test_ip)
        print(f"{test_ip} -> {loc.get('country')}, {loc.get('city')} ({loc.get('org')})")
