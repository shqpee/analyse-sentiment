"""
model.py — C8 : Chargement et utilisation du modèle de sentiment (XGBoost FR)
==============================================================================
Ce module gère le modèle de sentiment du projet : le pipeline XGBoost
(TF-IDF + XGBClassifier) entraîné sur des avis EN FRANÇAIS et sérialisé dans
`ml/models/xgboost_sentiment.joblib` par `ml/entrainer_mlflow.py`.

C'est le MÊME modèle que celui suivi dans MLflow : l'API, le front et le suivi
d'expériences sont donc cohérents (avant, l'API servait un DistilBERT anglais
alors que le modèle entraîné était XGBoost français — incohérent).

Modèle : Pipeline scikit-learn  TF-IDF (1,2)-grammes  →  XGBClassifier
  - Entraîné sur df_final_fr.csv (avis traduits/écrits en français)
  - Classification binaire : NEGATIVE (0) / POSITIVE (1)
  - Léger (~1,5 Mo) et très rapide (pas de réseau de neurones, CPU pur)

Compétences couvertes : C8 — Configurer un service IA
"""

import os
import time
import logging
from typing import Optional

# Configuration du logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Import conditionnel : le module reste importable même si joblib/sklearn manquent
# (mode simulation), ce qui évite de casser les tests dans un env minimal.
try:
    import joblib
    JOBLIB_DISPONIBLE = True
except ImportError:
    JOBLIB_DISPONIBLE = False
    logger.warning("'joblib' n'est pas installé : mode simulation activé.")


# ─────────────────────────────────────────────
# CONFIGURATION DU MODÈLE
# ─────────────────────────────────────────────
NOM_MODELE = "XGBoost (TF-IDF) — FR"

# Chemin du pipeline sérialisé. Résolu par rapport à la racine du projet pour
# fonctionner aussi bien en local (api_model/) que dans le conteneur (/app).
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEMIN_MODELE = os.environ.get(
    "CHEMIN_MODELE",
    os.path.join(RACINE, "ml", "models", "xgboost_sentiment.joblib"),
)

# Instance globale du modèle (chargée une seule fois au démarrage)
_modele = None
_statistiques = {
    "total_predictions": 0,
    "predictions_positives": 0,
    "predictions_negatives": 0,
    "temps_total_ms": 0.0,
    "erreurs": 0,
}


def charger_modele():
    """
    Charge le pipeline XGBoost depuis le fichier .joblib (singleton).
    Le modèle est chargé une seule fois et réutilisé.
    Retourne None si le fichier est absent ou joblib indisponible (mode simulation).
    """
    global _modele

    if _modele is not None:
        return _modele

    if not JOBLIB_DISPONIBLE:
        logger.warning("joblib indisponible : mode simulation.")
        return None

    if not os.path.exists(CHEMIN_MODELE):
        logger.warning(
            f"Modèle introuvable : {CHEMIN_MODELE} — mode simulation. "
            "Entraînez-le avec : python ml/entrainer_mlflow.py"
        )
        return None

    logger.info(f"Chargement du modèle XGBoost '{CHEMIN_MODELE}'...")
    debut = time.time()
    _modele = joblib.load(CHEMIN_MODELE)
    duree = round((time.time() - debut) * 1000)
    logger.info(f"Modèle chargé en {duree}ms")
    return _modele


def _simulation_prediction(texte: str) -> dict:
    """
    Mode simulation si le modèle n'est pas disponible.
    Retourne un résultat fictif basé sur des mots-clés français/anglais simples.
    """
    texte_lower = texte.lower()
    mots_positifs = ["excellent", "parfait", "super", "génial", "bravo", "top", "great", "good", "love", "amazing", "ravi", "recommande"]
    mots_negatifs = ["mauvais", "nul", "décevant", "horrible", "terrible", "bad", "awful", "hate", "poor", "worst", "déçu", "cassé"]

    score_pos = sum(1 for m in mots_positifs if m in texte_lower)
    score_neg = sum(1 for m in mots_negatifs if m in texte_lower)

    if score_pos > score_neg:
        return {"label": "POSITIVE", "score": 0.85}
    elif score_neg > score_pos:
        return {"label": "NEGATIVE", "score": 0.82}
    else:
        return {"label": "POSITIVE", "score": 0.55}


def predire_sentiment(texte: str) -> dict:
    """
    Analyse le sentiment d'un texte (avis client) avec le pipeline XGBoost FR.

    Returns:
        dict avec :
        - label: "POSITIVE" ou "NEGATIVE"
        - score: confiance entre 0 et 1 (probabilité de la classe prédite)
        - duree_ms: temps de traitement
        - modele: nom du modèle utilisé
    """
    global _statistiques

    debut = time.time()

    try:
        modele = charger_modele()

        if modele is None:
            # Mode simulation (modèle absent)
            resultat = _simulation_prediction(texte)
            label, score = resultat["label"], resultat["score"]
        else:
            # Prédiction réelle : le pipeline prend une LISTE de textes
            pred = int(modele.predict([texte])[0])
            label = "POSITIVE" if pred == 1 else "NEGATIVE"
            # Score = probabilité de la classe prédite (si disponible)
            if hasattr(modele, "predict_proba"):
                proba = modele.predict_proba([texte])[0]
                score = float(proba[pred])
            else:
                score = 1.0

        duree_ms = round((time.time() - debut) * 1000, 2)

        # Mise à jour des statistiques
        _statistiques["total_predictions"] += 1
        _statistiques["temps_total_ms"] += duree_ms
        if label == "POSITIVE":
            _statistiques["predictions_positives"] += 1
        else:
            _statistiques["predictions_negatives"] += 1

        logger.info(f"Prédiction : '{texte[:50]}...' → {label} ({score:.2f}) en {duree_ms}ms")

        return {
            "label": label,
            "score": round(float(score), 4),
            "duree_ms": duree_ms,
            "modele": NOM_MODELE,
        }

    except Exception as e:
        _statistiques["erreurs"] += 1
        logger.error(f"Erreur de prédiction : {e}")
        raise RuntimeError(f"Erreur du modèle : {e}")


def get_statistiques_modele() -> dict:
    """
    Retourne les statistiques d'utilisation du modèle.
    Utilisé pour le monitoring (C11).
    """
    stats = _statistiques.copy()

    # Calculer les métriques dérivées
    if stats["total_predictions"] > 0:
        stats["temps_moyen_ms"] = round(
            stats["temps_total_ms"] / stats["total_predictions"], 2
        )
        stats["pct_positifs"] = round(
            stats["predictions_positives"] / stats["total_predictions"] * 100, 1
        )
        stats["pct_negatifs"] = round(
            stats["predictions_negatives"] / stats["total_predictions"] * 100, 1
        )
    else:
        stats["temps_moyen_ms"] = 0
        stats["pct_positifs"] = 0
        stats["pct_negatifs"] = 0

    stats["modele"] = NOM_MODELE
    stats["modele_charge"] = _modele is not None

    return stats
