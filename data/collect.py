"""
collect.py — C1 : Extraction de données depuis plusieurs sources
=================================================================
Ce script collecte des avis clients depuis :
  1. Un fichier CSV local (simulation de données Amazon/Fnac)
  2. Une API REST publique (JSONPlaceholder — simulation)
  3. (Bonus) Une requête web simple avec BeautifulSoup

Compétence couverte : C1 — Extraire des données depuis des sources hétérogènes
"""

import csv
import json
import os
import requests
import pandas as pd
from datetime import datetime


# ─────────────────────────────────────────────
# SOURCE 1 : Lecture d'un fichier CSV local
# ─────────────────────────────────────────────
def lire_csv(chemin_fichier: str) -> list[dict]:
    """
    Lit un fichier CSV et retourne une liste de dictionnaires.
    Chaque ligne du CSV devient un dictionnaire clé/valeur.
    """
    avis = []
    with open(chemin_fichier, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for ligne in reader:
            avis.append(dict(ligne))
    print(f"[CSV] {len(avis)} avis chargés depuis {chemin_fichier}")
    return avis


# ─────────────────────────────────────────────
# SOURCE 2 : API REST publique (JSONPlaceholder)
# Ici on simule des "commentaires" comme des avis
# ─────────────────────────────────────────────
def extraire_api_publique(url: str = "https://jsonplaceholder.typicode.com/comments") -> list[dict]:
    """
    Interroge une API REST publique et transforme les données
    au format attendu par notre application.

    On utilise JSONPlaceholder (fausse API de test gratuite)
    pour simuler des avis clients venant d'une source externe.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() 

        commentaires = response.json()
        avis_api = []

        for i, com in enumerate(commentaires[:20], start=1000):
            # On transforme le format de l'API pour correspondre à notre schéma
            avis_api.append({
                "id": str(i),
                "source": "api_externe",
                "texte": com.get("body", ""),
                "produit": "Produit Générique",
                "note": "3",  # Valeur par défaut, l'API n'a pas de note
                "date": datetime.today().strftime("%Y-%m-%d"),
                "auteur_pseudo": com.get("email", "anonyme").split("@")[0],
            })

        print(f"[API] {len(avis_api)} avis extraits de l'API publique")
        return avis_api

    except requests.exceptions.ConnectionError:
        print("[API] Pas de connexion Internet, source API ignorée.")
        return []
    except Exception as e:
        print(f"[API] Erreur lors de l'appel API : {e}")
        return []


# ─────────────────────────────────────────────
# SOURCE 3 : Scraping web basique
# (exemple pédagogique avec requests + BeautifulSoup)
# ─────────────────────────────────────────────
def scraper_page_exemple(url: str = "https://quotes.toscrape.com") -> list[dict]:
    """
    Exemple de scraping web avec BeautifulSoup.
    On utilise quotes.toscrape.com (site fait exprès pour s'entraîner).
    On récupère des citations comme si c'étaient des avis.

    RGPD : on ne scrape que des données publiques et anonymes.
    """
    try:
        from bs4 import BeautifulSoup

        headers = {"User-Agent": "Mozilla/5.0 (educational scraper)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        citations = soup.find_all("div", class_="quote")

        avis_scrapes = []
        for i, quote in enumerate(citations, start=2000):
            texte = quote.find("span", class_="text").get_text(strip=True)
            auteur = quote.find("small", class_="author").get_text(strip=True)

            avis_scrapes.append({
                "id": str(i),
                "source": "scraping",
                "texte": texte.strip('"').strip('“').strip('”'),
                "produit": "Produit Scraping",
                "note": "3",
                "date": datetime.today().strftime("%Y-%m-%d"),
                "auteur_pseudo": auteur.replace(" ", "_").lower(),
            })

        print(f"[Scraping] {len(avis_scrapes)} avis scrapés depuis {url}")
        return avis_scrapes

    except ImportError:
        print("[Scraping] BeautifulSoup non installé. Installez : pip install beautifulsoup4")
        return []
    except Exception as e:
        print(f"[Scraping] Erreur : {e}")
        return []


# ─────────────────────────────────────────────
# AGRÉGATION DES SOURCES
# ─────────────────────────────────────────────
def collecter_toutes_les_sources(dossier_data: str = ".") -> pd.DataFrame:
    """
    Collecte toutes les sources et les fusionne dans un DataFrame pandas.
    Retourne un DataFrame unifié prêt pour le nettoyage.
    """
    tous_les_avis = []

    # Source 1 : CSV local
    chemin_csv = os.path.join(dossier_data, "sample_reviews.csv")
    if os.path.exists(chemin_csv):
        tous_les_avis.extend(lire_csv(chemin_csv))

    # Source 2 : API REST
    tous_les_avis.extend(extraire_api_publique())

    # Source 3 : Scraping
    tous_les_avis.extend(scraper_page_exemple())

    df = pd.DataFrame(tous_les_avis)
    print(f"\n[TOTAL] {len(df)} avis collectés depuis toutes les sources")
    return df


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    df = collecter_toutes_les_sources(dossier_data=".")
    print("\nAperçu des données collectées :")
    print(df.head())
    print(f"\nColonnes : {list(df.columns)}")
    print(f"Types : \n{df.dtypes}")

    # Sauvegarde brute avant nettoyage
    df.to_csv("raw_collected.csv", index=False, encoding="utf-8")
    print("\nDonnées brutes sauvegardées dans raw_collected.csv")
