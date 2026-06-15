"""
generer_trafic.py — Génère du trafic réel sur les APIs pour le monitoring
=========================================================================
But : alimenter Prometheus, Grafana et la table `logs_api` avec de VRAIES
requêtes, afin de réaliser des captures d'écran de monitoring authentiques
(pas de données simulées / inventées).

Le script envoie un mélange réaliste de requêtes :
  - requêtes nominales (HTTP 200)        → trafic normal
  - mauvaise clé API (HTTP 403)          → erreurs d'authentification
  - ressource introuvable (HTTP 404)     → erreurs client
  - entrée invalide (HTTP 422)           → validation Pydantic
  - texte volumineux                     → variation de latence

Pré-requis : la stack doit tourner (docker-compose up, ou les 2 APIs en local).

Lancer :
    python monitoring/generer_trafic.py                 # 200 requêtes
    python monitoring/generer_trafic.py --requetes 500  # 500 requêtes
    python monitoring/generer_trafic.py --erreurs       # accentue les erreurs
"""

import argparse
import os
import random
import sys
import time

import requests

# Garde anti-crash d'encodage sur la console Windows (cp1252) : on force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Configuration ────────────────────────────────────────────────────────────
API_MODELE = os.environ.get("API_MODELE_URL", "http://localhost:8000")
API_DONNEES = os.environ.get("API_DONNEES_URL", "http://localhost:8001")
API_KEY = os.environ.get("API_KEY", "dev-secret-key-change-in-production")

HEADERS_OK = {"X-API-Key": API_KEY}
HEADERS_KO = {"X-API-Key": "mauvaise-cle"}   # provoque des HTTP 403

TEXTES = [
    "Ce produit est vraiment fantastique, je le recommande vivement !",
    "Très déçu, le casque est tombé en panne après une semaine.",
    "Bon rapport qualité-prix, livraison rapide.",
    "Qualité médiocre, ne vaut absolument pas son prix.",
    "Parfait ! Son excellent et très confortable à porter.",
    "Service après-vente catastrophique, je déconseille.",
]


def _log(statut, methode, url):
    couleur = "✅" if statut < 400 else ("🔸" if statut < 500 else "❌")
    print(f"  {couleur} {statut} {methode:4} {url}")


def une_requete(forcer_erreurs: bool):
    """Effectue une requête aléatoire et renvoie le code HTTP obtenu."""
    # Probabilité d'erreur : ~15 % en mode normal, ~45 % en mode --erreurs
    tirage = random.random()
    seuil_erreur = 0.45 if forcer_erreurs else 0.15

    try:
        if tirage < seuil_erreur:
            # ── Cas d'erreurs (volontaires) ──
            cas = random.choice(["403", "404", "422"])
            if cas == "403":  # mauvaise clé API
                r = requests.post(f"{API_MODELE}/predict", json={"texte": "test"},
                                  headers=HEADERS_KO, timeout=10)
            elif cas == "404":  # produit inexistant
                r = requests.get(f"{API_DONNEES}/avis/produit/ProduitInconnu",
                                 headers=HEADERS_OK, timeout=10)
            else:  # 422 : texte trop court (min_length=5)
                r = requests.post(f"{API_MODELE}/predict", json={"texte": "x"},
                                  headers=HEADERS_OK, timeout=10)
        else:
            # ── Trafic nominal ──
            choix = random.random()
            if choix < 0.5:
                r = requests.post(f"{API_MODELE}/predict",
                                  json={"texte": random.choice(TEXTES)},
                                  headers=HEADERS_OK, timeout=15)
            elif choix < 0.7:
                r = requests.get(f"{API_DONNEES}/avis",
                                 params={"limit": random.randint(5, 50)},
                                 headers=HEADERS_OK, timeout=10)
            elif choix < 0.85:
                r = requests.get(f"{API_DONNEES}/statistiques",
                                 headers=HEADERS_OK, timeout=10)
            else:
                r = requests.get(f"{API_MODELE}/health", timeout=10)

        _log(r.status_code, r.request.method, r.request.path_url)
        return r.status_code
    except requests.RequestException as e:
        print(f"  ⚠️  Connexion impossible ({e}). La stack est-elle lancée ?")
        return None


def main():
    parser = argparse.ArgumentParser(description="Générateur de trafic monitoring")
    parser.add_argument("--requetes", type=int, default=200, help="Nombre de requêtes")
    parser.add_argument("--erreurs", action="store_true", help="Accentue les erreurs")
    parser.add_argument("--pause", type=float, default=0.2, help="Pause entre requêtes (s)")
    args = parser.parse_args()

    print("=" * 64)
    print("  GÉNÉRATION DE TRAFIC POUR LE MONITORING")
    print(f"  API Modèle  : {API_MODELE}")
    print(f"  API Données : {API_DONNEES}")
    print(f"  Requêtes    : {args.requetes} | mode erreurs : {args.erreurs}")
    print("=" * 64)

    compteur = {}
    for i in range(args.requetes):
        statut = une_requete(args.erreurs)
        if statut is None:
            print("\nArrêt : aucune API ne répond. Lancez `docker-compose up` d'abord.")
            return
        compteur[statut] = compteur.get(statut, 0) + 1
        time.sleep(args.pause)

    print("\n" + "=" * 64)
    print("  RÉSUMÉ DU TRAFIC GÉNÉRÉ")
    for statut in sorted(compteur):
        print(f"    HTTP {statut} : {compteur[statut]} requêtes")
    print("=" * 64)
    print("\n👉 Visualisez maintenant :")
    print("   • Prometheus : http://localhost:9090  (ex: rate(http_requests_total[1m]))")
    print("   • Grafana    : http://localhost:3000  (admin / admin)")
    print("   • Logs BDD   : python monitoring/monitor.py")


if __name__ == "__main__":
    main()
