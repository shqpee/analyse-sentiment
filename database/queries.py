"""
queries.py — C2 : Requêtes SQL pour exploiter la base de données
=================================================================
Ce module contient toutes les requêtes SQL de l'application.
Elles utilisent des paramètres préparés (protection contre les injections SQL).

Compétence couverte : C2 — Requêtes SQL pour extraire et agréger des données
"""

import sqlite3
import os

CHEMIN_DB = os.path.join(os.path.dirname(__file__), "avis.db")


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion à la base SQLite avec les résultats en dictionnaires."""
    conn = sqlite3.connect(CHEMIN_DB)
    conn.row_factory = sqlite3.Row  # Les résultats sont des dict-like objects
    return conn


# ─────────────────────────────────────────────
# REQUÊTES DE LECTURE
# ─────────────────────────────────────────────

def get_tous_les_avis(limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Récupère tous les avis avec leur produit associé.
    Utilise JOIN pour combiner les tables avis et produits.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                a.id,
                a.texte,
                a.note,
                a.source,
                a.date_avis,
                a.auteur_pseudo,
                p.nom AS produit
            FROM avis a
            LEFT JOIN produits p ON a.produit_id = p.id
            ORDER BY a.id DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
    return [dict(r) for r in rows]


def get_avis_par_produit(nom_produit: str) -> list[dict]:
    """
    Filtre les avis par nom de produit.
    Paramètre préparé : protection contre les injections SQL.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.id, a.texte, a.note, a.source, a.date_avis
            FROM avis a
            JOIN produits p ON a.produit_id = p.id
            WHERE p.nom = ?
            ORDER BY a.note DESC
        """, (nom_produit,)).fetchall()
    return [dict(r) for r in rows]


def get_statistiques_par_produit() -> list[dict]:
    """
    Agrégation SQL : note moyenne, min, max et nombre d'avis par produit.
    Utilise GROUP BY et les fonctions d'agrégation COUNT, AVG, MIN, MAX.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                p.nom AS produit,
                COUNT(a.id) AS nb_avis,
                ROUND(AVG(a.note), 2) AS note_moyenne,
                MIN(a.note) AS note_min,
                MAX(a.note) AS note_max,
                SUM(CASE WHEN a.note >= 4 THEN 1 ELSE 0 END) AS nb_positifs,
                ROUND(
                    100.0 * SUM(CASE WHEN a.note >= 4 THEN 1 ELSE 0 END) / COUNT(a.id),
                    1
                ) AS pct_positifs
            FROM produits p
            LEFT JOIN avis a ON a.produit_id = p.id
            GROUP BY p.id, p.nom
            ORDER BY note_moyenne DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_statistiques_par_source() -> list[dict]:
    """
    Agrégation par source de données (Amazon, Fnac, etc.)
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                source,
                COUNT(id) AS nb_avis,
                ROUND(AVG(note), 2) AS note_moyenne
            FROM avis
            GROUP BY source
            ORDER BY nb_avis DESC
        """).fetchall()
    return [dict(r) for r in rows]


def rechercher_avis(mots_cles: str) -> list[dict]:
    """
    Recherche textuelle dans les avis.
    Utilise LIKE pour la recherche par mots-clés.
    """
    pattern = f"%{mots_cles}%"
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT a.id, a.texte, a.note, p.nom AS produit
            FROM avis a
            LEFT JOIN produits p ON a.produit_id = p.id
            WHERE a.texte LIKE ?
            ORDER BY a.id DESC
        """, (pattern,)).fetchall()
    return [dict(r) for r in rows]


def get_avis_avec_sentiment() -> list[dict]:
    """
    Récupère les avis qui ont déjà été analysés par le modèle IA.
    Utilise la vue SQL créée dans le schéma.
    """
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM avis_avec_sentiment
            ORDER BY id DESC
        """).fetchall()
    return [dict(r) for r in rows]


def inserer_prediction(avis_id: int, label: str, score: float, modele: str) -> int:
    """
    Insère le résultat d'une prédiction IA en base.
    Retourne l'ID de la prédiction créée.
    """
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO predictions_sentiment (avis_id, label, score, modele_utilise)
            VALUES (?, ?, ?, ?)
        """, (avis_id, label, score, modele))
        conn.commit()
        return cursor.lastrowid


def inserer_log_api(endpoint: str, methode: str, statut: int, duree_ms: float, erreur: str = None):
    """
    Enregistre un log d'appel API en base.
    Utilisé pour le monitoring (C20).
    """
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO logs_api (endpoint, methode_http, statut_http, duree_ms, message_erreur)
            VALUES (?, ?, ?, ?, ?)
        """, (endpoint, methode, statut, duree_ms, erreur))
        conn.commit()


def get_logs_recents(limit: int = 50) -> list[dict]:
    """Récupère les derniers logs d'API pour le monitoring."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM logs_api
            ORDER BY enregistre_le DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def compter_avis() -> int:
    """Retourne le nombre total d'avis en base."""
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM avis").fetchone()[0]


def get_liste_produits() -> list[str]:
    """Retourne la liste de tous les produits disponibles."""
    with get_connection() as conn:
        rows = conn.execute("SELECT nom FROM produits ORDER BY nom").fetchall()
    return [r[0] for r in rows]


# ─────────────────────────────────────────────
# TEST RAPIDE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=== TEST DES REQUÊTES SQL ===\n")

    print("Produits disponibles :", get_liste_produits())
    print(f"Total avis : {compter_avis()}")

    print("\n-- Statistiques par produit --")
    for stat in get_statistiques_par_produit():
        print(stat)

    print("\n-- Statistiques par source --")
    for stat in get_statistiques_par_source():
        print(stat)

    print("\n-- Derniers avis --")
    for avis in get_tous_les_avis(limit=3):
        print(avis)
