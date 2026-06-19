"""
benchmark_modeles.py — Compare plusieurs modèles de sentiment sur le MÊME jeu
de test FRANÇAIS et loggue chaque résultat dans MLflow.
================================================================================
But : répondre à « notre XGBoost FR est-il bon par rapport aux modèles
transformers français existants ? » avec des chiffres comparables.

Modèles comparés (chacun = 1 run MLflow dans l'experiment 'benchmark-sentiment-fr') :
  - XGBoost (FR)             : notre pipeline ml/models/xgboost_sentiment.joblib
  - nlptown/...multilingual  : BERT multilingue, note 1-5 → binaire
  - cmarkea/distilcamembert  : CamemBERT FR, note 1-5 → binaire
  - distilbert-sst-2-english : l'ANCIEN modèle anglais (baseline : montre qu'il
                               est mauvais en français)

Jeu de test : on reconstruit EXACTEMENT le split de ml/entrainer_mlflow.py
(test_size=0.25, random_state=42, stratify) afin que XGBoost soit évalué sur des
données qu'il n'a pas vues, et que les transformers soient jugés en zero-shot sur
le même set. Sous-échantillonnage optionnel (--n-test) car l'inférence BERT sur
CPU est lente.

Lancer :
    set MLFLOW_TRACKING_URI=http://localhost:5000
    python ml/benchmark_modeles.py --n-test 500
"""

import argparse
import os
import re
import sys
import time

# Console Windows en UTF-8 (évite les crashs d'encodage).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
)

RACINE = os.path.dirname(os.path.dirname(__file__))
CACHE_FR = os.path.join(RACINE, "data", "df_final_fr.csv")
CHEMIN_XGB = os.path.join(RACINE, "ml", "models", "xgboost_sentiment.joblib")
DOSSIER_ART = os.path.join(RACINE, "ml", "artifacts")
RANDOM_STATE = 42


# ─────────────────────────────────────────────
# Outils
# ─────────────────────────────────────────────
def _star(label: str) -> int:
    """Extrait le nombre d'étoiles d'un label ('4 stars' → 4 ; 'LABEL_3' → 4)."""
    m = re.search(r"\d+", label)
    if not m:
        return 0
    n = int(m.group())
    # Convention HuggingFace : LABEL_0..LABEL_4 correspondent à 1..5 étoiles.
    return n + 1 if label.upper().startswith("LABEL_") else n


def _metrics(y_true, y_pred, pos_proba=None) -> dict:
    roc = None
    if pos_proba is not None:
        try:
            roc = float(roc_auc_score(y_true, pos_proba))
        except Exception:
            roc = None
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": roc,
    }


# ─────────────────────────────────────────────
# Évaluateurs
# ─────────────────────────────────────────────
def eval_xgboost(textes):
    import joblib
    if not os.path.exists(CHEMIN_XGB):
        raise FileNotFoundError(f"Modèle XGBoost introuvable : {CHEMIN_XGB}")
    modele = joblib.load(CHEMIN_XGB)
    preds = modele.predict(textes).astype(int).tolist()
    proba = None
    if hasattr(modele, "predict_proba"):
        proba = modele.predict_proba(textes)[:, 1].tolist()
    return preds, proba


def eval_transformer(model_name, textes, kind, batch_size=16):
    """kind = 'stars' (1-5) ou 'binary' (POSITIVE/NEGATIVE)."""
    from transformers import pipeline
    clf = pipeline(
        "sentiment-analysis", model=model_name, device=-1,
        truncation=True, max_length=256, top_k=None,
    )
    preds, pos_proba = [], []
    for sorties in clf(list(textes), batch_size=batch_size):
        # top_k=None → 'sorties' est la liste de tous les labels avec leur score
        scores = {o["label"]: float(o["score"]) for o in sorties}
        if kind == "stars":
            p_pos = sum(s for lab, s in scores.items() if _star(lab) >= 4)
        else:  # binaire
            # gère POSITIVE/NEGATIVE quelle que soit la casse
            p_pos = next((s for lab, s in scores.items() if lab.upper().startswith("POS")), 0.0)
        preds.append(1 if p_pos >= 0.5 else 0)
        pos_proba.append(p_pos)
    return preds, pos_proba


# Catalogue des modèles à benchmarker
MODELES = [
    {"label": "XGBoost (FR)", "type": "tfidf+xgboost", "fn": ("xgb", None)},
    {"label": "nlptown-multilingual", "type": "bert-multilingue", "fn": ("hf", ("nlptown/bert-base-multilingual-uncased-sentiment", "stars"))},
    {"label": "distilbert-sst2-en (ancien)", "type": "bert-anglais", "fn": ("hf", ("distilbert-base-uncased-finetuned-sst-2-english", "binary"))},
    # cmarkea/distilcamembert-base-sentiment : retiré — crash natif (segfault
    # SentencePiece/CamemBERT) sur cet environnement Windows. À réessayer sous
    # Linux/Docker ou avec un tokenizer 'slow' si besoin.
]


def main():
    parser = argparse.ArgumentParser(description="Benchmark de modèles de sentiment FR")
    parser.add_argument("--n-test", type=int, default=500, help="Taille du sous-échantillon de test (0 = tout)")
    parser.add_argument("--tracking-uri", default=os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    if not os.path.exists(CACHE_FR):
        print(f"❌ Dataset introuvable : {CACHE_FR}")
        sys.exit(1)
    os.makedirs(DOSSIER_ART, exist_ok=True)

    # 1) Reconstruire le même split test que l'entraînement
    df = pd.read_csv(CACHE_FR)
    X = df["texte_fr"].astype(str).tolist()
    y = df["label"].astype(int).tolist()
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )
    if args.n_test and args.n_test < len(X_test):
        X_test, y_test = X_test[:args.n_test], y_test[:args.n_test]
    print(f"📦 Jeu de test : {len(X_test)} avis | positifs={sum(y_test)} négatifs={len(y_test)-sum(y_test)}")

    # 2) MLflow
    import mlflow
    mlflow.set_tracking_uri(args.tracking_uri)
    mlflow.set_experiment("benchmark-sentiment-fr")
    print(f"🎯 MLflow : {args.tracking_uri} | experiment 'benchmark-sentiment-fr'")

    resultats = []
    for spec in MODELES:
        label, mtype = spec["label"], spec["type"]
        print(f"\n──────── {label} ────────")
        t0 = time.time()
        try:
            kind, payload = spec["fn"]
            if kind == "xgb":
                preds, proba = eval_xgboost(X_test)
            else:
                model_name, hf_kind = payload
                print(f"  Chargement/inférence {model_name} (CPU, peut télécharger le modèle)...")
                preds, proba = eval_transformer(model_name, X_test, hf_kind, args.batch_size)
        except Exception as e:
            print(f"  ⚠️ Ignoré ({type(e).__name__}: {e})")
            resultats.append({"modele": label, "type": mtype, "statut": "SKIP", "erreur": str(e)[:120]})
            continue

        duree = time.time() - t0
        m = _metrics(y_test, preds, proba)
        ms_par_avis = round(duree / max(len(X_test), 1) * 1000, 2)
        print(f"  accuracy={m['accuracy']:.4f}  f1={m['f1']:.4f}  "
              f"roc_auc={m['roc_auc'] if m['roc_auc'] is None else round(m['roc_auc'],4)}  "
              f"({ms_par_avis} ms/avis)")

        with mlflow.start_run(run_name=label):
            mlflow.log_param("modele", label)
            mlflow.log_param("type", mtype)
            mlflow.log_param("n_test", len(X_test))
            mlflow.log_param("dataset", "df_final_fr.csv (split test, seed 42)")
            for k, v in m.items():
                if v is not None:
                    mlflow.log_metric(k, v)
            mlflow.log_metric("ms_par_avis", ms_par_avis)

        ligne = {"modele": label, "type": mtype, "statut": "OK", "ms_par_avis": ms_par_avis}
        ligne.update({k: (round(v, 4) if v is not None else None) for k, v in m.items()})
        resultats.append(ligne)

    # 3) Tableau récapitulatif + graphique, loggés dans un run de synthèse
    df_res = pd.DataFrame(resultats)
    ok = df_res[df_res["statut"] == "OK"].sort_values("f1", ascending=False)
    print("\n" + "=" * 70)
    print("  CLASSEMENT (par F1)")
    print("=" * 70)
    cols = [c for c in ["modele", "accuracy", "f1", "roc_auc", "ms_par_avis"] if c in ok.columns]
    print(ok[cols].to_string(index=False))

    chemin_csv = os.path.join(DOSSIER_ART, "benchmark_resultats.csv")
    df_res.to_csv(chemin_csv, index=False)

    chemin_png = os.path.join(DOSSIER_ART, "benchmark_f1.png")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(ok["modele"][::-1], ok["f1"][::-1], color="#6366F1")
        ax.bar_label(ax.containers[0], fmt="%.3f", padding=3)
        ax.set_xlim(0, 1.05); ax.set_xlabel("F1-score")
        ax.set_title("Benchmark sentiment FR — F1 par modèle", fontweight="bold")
        fig.tight_layout(); fig.savefig(chemin_png, dpi=120); plt.close(fig)
    except Exception as e:
        chemin_png = None
        print(f"  (graphique ignoré : {e})")

    with mlflow.start_run(run_name="benchmark-synthese"):
        mlflow.log_param("n_modeles", len(resultats))
        mlflow.log_param("n_test", len(X_test))
        if not ok.empty:
            mlflow.log_param("meilleur_modele", ok.iloc[0]["modele"])
            mlflow.log_metric("meilleur_f1", float(ok.iloc[0]["f1"]))
        mlflow.log_artifact(chemin_csv)
        if chemin_png:
            mlflow.log_artifact(chemin_png)

    print(f"\n✅ Résultats loggés dans MLflow (experiment 'benchmark-sentiment-fr').")
    print(f"   Tableau : {chemin_csv}")
    print(f"   Ouvrez : {args.tracking_uri}")


if __name__ == "__main__":
    main()
