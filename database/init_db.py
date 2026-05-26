"""
init_db.py — C4 : Initialisation de la base de données SQLite
==============================================================
Ce script :
1. Crée la base de données SQLite
2. Applique le schéma SQL
3. Insère les données nettoyées depuis le CSV

Compétence couverte : C4 — Créer une base de données conforme RGPD
"""

import sqlite3
import csv
import os
from datetime import datetime, timedelta


# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
DOSSIER_BASE = os.path.dirname(__file__)
CHEMIN_DB = os.path.join(DOSSIER_BASE, "avis.db")
CHEMIN_SCHEMA = os.path.join(DOSSIER_BASE, "schema.sql")
CHEMIN_CSV = os.path.join(DOSSIER_BASE, "..", "data", "sample_reviews.csv")


# ─────────────────────────────────────────────
# CRÉATION DE LA BASE DE DONNÉES
# ─────────────────────────────────────────────
def creer_base_de_donnees():
    """
    Crée la base SQLite et applique le schéma SQL.
    Si la base existe déjà, on la recréé à zéro (pour les tests).
    """
    # Supprimer l'ancienne base si elle existe (mode dev)
    if os.path.exists(CHEMIN_DB):
        os.remove(CHEMIN_DB)
        print(f"Ancienne base supprimée : {CHEMIN_DB}")

    # Connexion (crée le fichier si inexistant)
    conn = sqlite3.connect(CHEMIN_DB)
    cursor = conn.cursor()

    # Lire et exécuter le schéma SQL
    with open(CHEMIN_SCHEMA, encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    conn.commit()
    print(f"Base de données créée : {CHEMIN_DB}")
    return conn


# ─────────────────────────────────────────────
# INSERTION DES DONNÉES
# ─────────────────────────────────────────────
def inserer_donnees_csv(conn: sqlite3.Connection, chemin_csv: str):
    """
    Lit le CSV nettoyé et insère les données dans la BDD.
    Crée les produits à la volée si nécessaire.
    """
    cursor = conn.cursor()

    produits_ids = {}  # Cache pour éviter des requêtes répétées

    with open(chemin_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for ligne in reader:
            # 1. Créer ou récupérer le produit
            nom_produit = ligne.get("produit", "Inconnu")

            if nom_produit not in produits_ids:
                cursor.execute(
                    "INSERT OR IGNORE INTO produits (nom, categorie) VALUES (?, ?)",
                    (nom_produit, "Électronique")
                )
                cursor.execute("SELECT id FROM produits WHERE nom = ?", (nom_produit,))
                produits_ids[nom_produit] = cursor.fetchone()[0]

            produit_id = produits_ids[nom_produit]

            # 2. Calculer la date de suppression RGPD (3 ans après la création)
            date_suppression = (datetime.today() + timedelta(days=3*365)).strftime("%Y-%m-%d")

            # 3. Insérer l'avis
            cursor.execute("""
                INSERT INTO avis (source, texte, note, date_avis, auteur_pseudo, produit_id, a_supprimer_le)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ligne.get("source", "inconnu"),
                ligne.get("texte", ""),
                int(float(ligne.get("note", 3))),
                ligne.get("date", datetime.today().strftime("%Y-%m-%d")),
                ligne.get("auteur_pseudo", "anonyme"),
                produit_id,
                date_suppression,
            ))

            # 4. Enregistrer le consentement RGPD
            cursor.execute("""
                INSERT INTO consentements_rgpd (auteur_pseudo, type_donnee, consentement, base_legale)
                VALUES (?, 'avis_client', 1, 'intérêt légitime')
            """, (ligne.get("auteur_pseudo", "anonyme"),))

    conn.commit()

    # Afficher un résumé
    cursor.execute("SELECT COUNT(*) FROM avis")
    nb_avis = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM produits")
    nb_produits = cursor.fetchone()[0]
    print(f"Données insérées : {nb_avis} avis, {nb_produits} produits")


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== INITIALISATION DE LA BASE DE DONNÉES ===\n")

    # Créer la BDD
    conn = creer_base_de_donnees()

    # Insérer les données
    if os.path.exists(CHEMIN_CSV):
        inserer_donnees_csv(conn, CHEMIN_CSV)
    else:
        print(f"Fichier CSV introuvable : {CHEMIN_CSV}")
        print("Lancez d'abord data/clean.py pour générer les données.")

    conn.close()
    print("\nBase de données prête !")
    print(f"Fichier : {CHEMIN_DB}")
