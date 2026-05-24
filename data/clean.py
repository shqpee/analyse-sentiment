"""
clean.py — C3 : Nettoyage et agrégation des données
=====================================================
Ce script nettoie les données brutes et les prépare pour
l'insertion en base de données.

Compétence couverte : C3 — Agréger et nettoyer des données
"""

import pandas as pd
import re
import os


# ─────────────────────────────────────────────
# FONCTIONS DE NETTOYAGE
# ─────────────────────────────────────────────

def supprimer_doublons(df: pd.DataFrame) -> pd.DataFrame:
    avant = len(df)
    df = df.drop_duplicates(subset=["texte"], keep="first")
    apres = len(df)
    print(f"[Doublons] {avant - apres} doublons supprimés. Reste : {apres} lignes")
    return df


def nettoyer_texte(texte: str) -> str:
    """
    Nettoie texte en :
    - Supprimant les espaces en trop
    - Retirant les caractères spéciaux inutiles
    - Limitant la longueur à 1000 caractères
    """
    if not isinstance(texte, str):
        return ""
    # Supprimer les sauts de ligne multiples
    texte = re.sub(r'\s+', ' ', texte).strip()
    # Supprimer les caractères non imprimables
    texte = re.sub(r'[^\x20-\x7ÉàáâãäåæçèéêëìíîïðñòóôõöùúûüýÿÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖÙÚÛÜÝ€%°!?.,;:\'\"()\-]', '', texte)
    # Limiter la longueur (RGPD : pas de textes infinis stockés)
    return texte[:1000]


def valider_note(note) -> int:
    """Valide que la note est bien entre 1 et 5."""
    try:
        note = int(float(str(note)))
        return max(1, min(5, note))  # On force entre 1 et 5
    except (ValueError, TypeError):
        return 3  # Valeur par défaut si invalide


def anonymiser_auteur(pseudo: str) -> str:
    """
    Anonymise partiellement le pseudo (conformité RGPD).
    Ex: 'jean.dupont' -> 'jea*****'
    """
    if not isinstance(pseudo, str) or len(pseudo) < 3:
        return "anonyme"
    return pseudo[:3] + "*" * max(3, len(pseudo) - 3)


def normaliser_date(date_str: str) -> str:
    """Normalise le format de date en YYYY-MM-DD."""
    if not isinstance(date_str, str):
        return "2024-01-01"
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            from datetime import datetime
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return "2024-01-01"  # Valeur par défaut


def supprimer_avis_vides(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les avis avec un texte vide ou trop court."""
    avant = len(df)
    df = df[df["texte"].str.len() > 10]
    apres = len(df)
    print(f"[Vides] {avant - apres} avis trop courts supprimés. Reste : {apres} lignes")
    return df


# ─────────────────────────────────────────────
# PIPELINE DE NETTOYAGE COMPLET
# ─────────────────────────────────────────────

def nettoyer_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline complet de nettoyage :
    1. Vérification des colonnes requises
    2. Suppression des doublons
    3. Nettoyage des textes
    4. Validation des notes
    5. Anonymisation des auteurs (RGPD)
    6. Normalisation des dates
    7. Suppression des avis vides
    """
    print("\n=== NETTOYAGE DES DONNÉES ===")
    print(f"Données brutes : {len(df)} lignes")

    # S'assurer que les colonnes existent
    colonnes_requises = ["id", "source", "texte", "produit", "note", "date", "auteur_pseudo"]
    for col in colonnes_requises:
        if col not in df.columns:
            df[col] = "" if col != "note" else 3

    # 1. Supprimer les doublons
    df = supprimer_doublons(df)

    # 2. Nettoyer les textes
    df["texte"] = df["texte"].apply(nettoyer_texte)

    # 3. Valider les notes
    df["note"] = df["note"].apply(valider_note)

    # 4. Anonymiser les auteurs (RGPD)
    df["auteur_pseudo"] = df["auteur_pseudo"].apply(anonymiser_auteur)

    # 5. Normaliser les dates
    df["date"] = df["date"].apply(normaliser_date)

    # 6. Supprimer les avis vides
    df = supprimer_avis_vides(df)

    # 7. Réinitialiser l'index
    df = df.reset_index(drop=True)

    print(f"Données nettoyées : {len(df)} lignes")
    return df


# ─────────────────────────────────────────────
# AGRÉGATION STATISTIQUE (C3)
# ─────────────────────────────────────────────

def calculer_statistiques(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule des statistiques agrégées par produit.
    Retourne un DataFrame avec :
    - Nombre d'avis par produit
    - Note moyenne
    - Répartition positifs/négatifs
    """
    stats = df.groupby("produit").agg(
        nb_avis=("id", "count"),
        note_moyenne=("note", "mean"),
        note_min=("note", "min"),
        note_max=("note", "max"),
    ).round(2).reset_index()

    # Calculer le % d'avis positifs (note >= 4)
    avis_positifs = df[df["note"] >= 4].groupby("produit").size().reset_index(name="nb_positifs")
    stats = stats.merge(avis_positifs, on="produit", how="left").fillna(0)
    stats["pct_positifs"] = (stats["nb_positifs"] / stats["nb_avis"] * 100).round(1)

    print("\n=== STATISTIQUES PAR PRODUIT ===")
    print(stats.to_string(index=False))
    return stats


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────

if __name__ == "__main__":
    # Charger les données brutes (depuis collect.py ou directement le CSV)
    chemin_csv = os.path.join(os.path.dirname(__file__), "sample_reviews.csv")

    if os.path.exists(chemin_csv):
        df_brut = pd.read_csv(chemin_csv, encoding="utf-8")
    else:
        # Fallback : essayer de lancer collect.py
        from collect import collecter_toutes_les_sources
        df_brut = collecter_toutes_les_sources(os.path.dirname(__file__))

    # Nettoyage
    df_propre = nettoyer_dataset(df_brut)

    # Statistiques
    stats = calculer_statistiques(df_propre)

    # Sauvegarde
    dossier = os.path.dirname(__file__)
    df_propre.to_csv(os.path.join(dossier, "cleaned_reviews.csv"), index=False, encoding="utf-8")
    stats.to_csv(os.path.join(dossier, "stats_produits.csv"), index=False, encoding="utf-8")
    print("\nFichiers sauvegardés : cleaned_reviews.csv, stats_produits.csv")
