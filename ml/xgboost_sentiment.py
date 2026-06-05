"""
ml/xgboost_sentiment.py — Classification de sentiment avec XGBoost
===================================================================
Logique cœur (importable et testable) pour l'analyse de sentiment binaire
avec XGBoost. Ce module est utilisé par le notebook
`sentiment_from_scratch_vs_transfer_learning.ipynb` et par les tests pytest
`tests/test_xgboost_sentiment.py`.

Il fournit :
  - build_pipeline()        : pipeline TF-IDF + XGBClassifier
  - run_gridsearch()        : recherche d'hyperparamètres (GridSearchCV)
  - evaluate_classification(): métriques de classification (accuracy, precision,
                              recall, F1, ROC-AUC, matrice de confusion, rapport)
  - compute_learning_curve(): données de la courbe d'apprentissage
  - plot_learning_curve()   : tracé de la courbe d'apprentissage
  - plot_confusion()        : tracé de la matrice de confusion
  - train_with_mlflow()     : entraînement complet + suivi MLflow (optionnel)

Compétences couvertes :
  - C9/C10 : Entraîner et évaluer un modèle de Machine Learning
  - C11    : Suivi des expérimentations (MLflow)
  - C12    : Tests automatisés du modèle
"""

from __future__ import annotations

import os
from typing import Optional, Sequence

import numpy as np

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GridSearchCV, learning_curve
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix,
)

from xgboost import XGBClassifier


# ─────────────────────────────────────────────
# MLflow est OPTIONNEL : le module fonctionne même s'il n'est pas installé.
# MLflow >= 3 bloque le backend "file store" (./mlruns) par défaut ; on
# l'autorise AVANT l'import pour garder le mode local simple du projet.
# ─────────────────────────────────────────────
os.environ.setdefault("MLFLOW_ALLOW_FILE_STORE", "true")

try:
    import mlflow
    import mlflow.sklearn

    MLFLOW_DISPONIBLE = True
except ImportError:  # pragma: no cover
    MLFLOW_DISPONIBLE = False


# ─────────────────────────────────────────────
# 1. CONSTRUCTION DU PIPELINE
# ─────────────────────────────────────────────
def build_pipeline(
    max_features: int = 20_000,
    ngram_range: tuple[int, int] = (1, 2),
    min_df: int = 1,
    n_estimators: int = 300,
    max_depth: int = 6,
    learning_rate: float = 0.1,
    subsample: float = 0.9,
    colsample_bytree: float = 0.9,
    random_state: int = 42,
) -> Pipeline:
    """
    Construit un pipeline scikit-learn : TF-IDF -> XGBClassifier.

    Le TF-IDF transforme le texte en vecteurs numériques, puis XGBoost
    (gradient boosting d'arbres de décision) effectue la classification binaire.
    """
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=max_features,
                    ngram_range=ngram_range,
                    min_df=min_df,
                    sublinear_tf=True,
                ),
            ),
            (
                "clf",
                XGBClassifier(
                    n_estimators=n_estimators,
                    max_depth=max_depth,
                    learning_rate=learning_rate,
                    subsample=subsample,
                    colsample_bytree=colsample_bytree,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    tree_method="hist",
                    n_jobs=-1,
                    random_state=random_state,
                ),
            ),
        ]
    )


# ─────────────────────────────────────────────
# 2. RECHERCHE D'HYPERPARAMÈTRES (GridSearchCV)
# ─────────────────────────────────────────────
def default_param_grid() -> dict[str, list]:
    """Grille d'hyperparamètres par défaut pour XGBoost."""
    return {
        "clf__n_estimators": [200, 400],
        "clf__max_depth": [4, 6],
        "clf__learning_rate": [0.1, 0.3],
    }


def run_gridsearch(
    X_train: Sequence[str],
    y_train: Sequence[int],
    param_grid: Optional[dict[str, list]] = None,
    cv: int = 3,
    scoring: str = "f1",
    verbose: int = 0,
) -> GridSearchCV:
    """
    Lance une recherche par grille (GridSearchCV) sur le pipeline XGBoost.

    Retourne l'objet GridSearchCV entraîné. On accède ensuite à :
      - .best_estimator_  : le meilleur pipeline
      - .best_params_     : les meilleurs hyperparamètres
      - .best_score_      : le meilleur score de validation croisée
    """
    if param_grid is None:
        param_grid = default_param_grid()

    pipeline = build_pipeline()
    grid = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        cv=cv,
        scoring=scoring,
        n_jobs=-1,
        verbose=verbose,
        refit=True,
    )
    grid.fit(X_train, y_train)
    return grid


# ─────────────────────────────────────────────
# 3. MÉTRIQUES DE CLASSIFICATION
# ─────────────────────────────────────────────
def evaluate_classification(
    model,
    X_test: Sequence[str],
    y_test: Sequence[int],
    target_names: Sequence[str] = ("NEGATIVE", "POSITIVE"),
) -> dict:
    """
    Calcule les métriques de classification d'un modèle entraîné.

    Retourne un dict avec :
      accuracy, precision, recall, f1, roc_auc,
      confusion_matrix (liste 2x2), classification_report (str).
    """
    y_pred = model.predict(X_test)

    # ROC-AUC : nécessite des probabilités (predict_proba)
    roc_auc = None
    if hasattr(model, "predict_proba"):
        try:
            y_proba = model.predict_proba(X_test)[:, 1]
            roc_auc = float(roc_auc_score(y_test, y_proba))
        except Exception:
            roc_auc = None

    # Étiquettes explicites (ex: [0, 1]) pour garantir une forme binaire,
    # même si une seule classe est présente dans y_test ou y_pred.
    etiquettes = list(range(len(target_names)))

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": roc_auc,
        "confusion_matrix": confusion_matrix(y_test, y_pred, labels=etiquettes).tolist(),
        "classification_report": classification_report(
            y_test, y_pred, labels=etiquettes,
            target_names=list(target_names), zero_division=0
        ),
    }
    return metrics


# ─────────────────────────────────────────────
# 4. COURBE D'APPRENTISSAGE (learning curve)
# ─────────────────────────────────────────────
def compute_learning_curve(
    model,
    X: Sequence[str],
    y: Sequence[int],
    cv: int = 3,
    scoring: str = "f1",
    train_sizes: Optional[np.ndarray] = None,
    random_state: int = 42,
) -> dict:
    """
    Calcule la courbe d'apprentissage : performance en fonction de la taille
    du jeu d'entraînement, pour détecter sur-apprentissage / sous-apprentissage.

    Retourne un dict avec train_sizes, train_mean, train_std, val_mean, val_std.
    """
    if train_sizes is None:
        train_sizes = np.linspace(0.1, 1.0, 5)

    sizes, train_scores, val_scores = learning_curve(
        estimator=model,
        X=list(X),
        y=list(y),
        cv=cv,
        scoring=scoring,
        train_sizes=train_sizes,
        n_jobs=-1,
        shuffle=True,
        random_state=random_state,
    )
    return {
        "train_sizes": sizes,
        "train_mean": train_scores.mean(axis=1),
        "train_std": train_scores.std(axis=1),
        "val_mean": val_scores.mean(axis=1),
        "val_std": val_scores.std(axis=1),
        "scoring": scoring,
    }


def plot_learning_curve(lc: dict, ax=None, titre: str = "Courbe d'apprentissage — XGBoost"):
    """Trace la courbe d'apprentissage à partir du dict de compute_learning_curve()."""
    import matplotlib.pyplot as plt

    if ax is None:
        _, ax = plt.subplots(figsize=(7, 5))

    sizes = lc["train_sizes"]
    ax.plot(sizes, lc["train_mean"], "o-", color="#6366F1", label="Score d'entraînement")
    ax.fill_between(
        sizes,
        lc["train_mean"] - lc["train_std"],
        lc["train_mean"] + lc["train_std"],
        alpha=0.15,
        color="#6366F1",
    )
    ax.plot(sizes, lc["val_mean"], "o-", color="#F97316", label="Score de validation (CV)")
    ax.fill_between(
        sizes,
        lc["val_mean"] - lc["val_std"],
        lc["val_mean"] + lc["val_std"],
        alpha=0.15,
        color="#F97316",
    )
    ax.set_title(titre, fontweight="bold")
    ax.set_xlabel("Nombre d'exemples d'entraînement")
    ax.set_ylabel(f"Score ({lc.get('scoring', 'f1')})")
    ax.legend(loc="best")
    ax.grid(alpha=0.3)
    return ax


def plot_confusion(cm, target_names: Sequence[str] = ("NEGATIVE", "POSITIVE"), ax=None):
    """Trace une matrice de confusion (cm = liste/array 2x2)."""
    import matplotlib.pyplot as plt
    from sklearn.metrics import ConfusionMatrixDisplay

    if ax is None:
        _, ax = plt.subplots(figsize=(5, 4))
    disp = ConfusionMatrixDisplay(np.array(cm), display_labels=list(target_names))
    disp.plot(ax=ax, colorbar=False, cmap="Greens")
    ax.set_title("Matrice de confusion — XGBoost", fontweight="bold")
    return ax


# ─────────────────────────────────────────────
# 5. ENTRAÎNEMENT COMPLET + SUIVI MLflow
# ─────────────────────────────────────────────
def train_with_mlflow(
    X_train: Sequence[str],
    y_train: Sequence[int],
    X_test: Sequence[str],
    y_test: Sequence[int],
    param_grid: Optional[dict[str, list]] = None,
    cv: int = 3,
    scoring: str = "f1",
    experiment_name: str = "sentiment-xgboost",
    run_name: str = "xgboost-gridsearch",
    tracking_uri: str = "sqlite:///mlflow.db",
) -> dict:
    """
    Pipeline complet :
      1. GridSearchCV pour trouver les meilleurs hyperparamètres
      2. Évaluation des métriques de classification sur le jeu de test
      3. Suivi de l'expérience dans MLflow (params + métriques + modèle)

    Si MLflow n'est pas installé, l'entraînement et l'évaluation se font
    quand même (le logging est simplement ignoré).

    Retourne un dict : best_params, cv_best_score, metrics, model, run_id.
    """
    grid = run_gridsearch(
        X_train, y_train, param_grid=param_grid, cv=cv, scoring=scoring
    )
    best_model = grid.best_estimator_
    metrics = evaluate_classification(best_model, X_test, y_test)

    resultat = {
        "best_params": grid.best_params_,
        "cv_best_score": float(grid.best_score_),
        "metrics": metrics,
        "model": best_model,
        "run_id": None,
    }

    if not MLFLOW_DISPONIBLE:
        return resultat

    # On force l'URI de suivi (backend SQLite recommandé par MLflow >= 3).
    # Passer par la variable d'environnement garantit la prise en compte
    # quel que soit le contexte d'exécution (notebook, pytest, script).
    if tracking_uri:
        os.environ["MLFLOW_TRACKING_URI"] = tracking_uri
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=run_name) as run:
        # Hyperparamètres
        mlflow.log_params(grid.best_params_)
        mlflow.log_param("cv_folds", cv)
        mlflow.log_param("scoring", scoring)
        mlflow.log_param("algo", "XGBClassifier")

        # Métriques (on ne loggue que les valeurs numériques)
        for cle in ("accuracy", "precision", "recall", "f1", "roc_auc"):
            valeur = metrics.get(cle)
            if valeur is not None:
                mlflow.log_metric(cle, valeur)
        mlflow.log_metric("cv_best_f1", grid.best_score_)

        # Rapport de classification en artefact texte
        mlflow.log_text(metrics["classification_report"], "classification_report.txt")

        # Modèle
        try:
            mlflow.sklearn.log_model(best_model, name="model")
        except Exception:
            pass

        resultat["run_id"] = run.info.run_id

    return resultat


# ─────────────────────────────────────────────
# 6. EXPORT / IMPORT DU MODÈLE (sérialisation)
# ─────────────────────────────────────────────
def save_model(model, path: str = "ml/models/xgboost_sentiment.joblib") -> str:
    """
    Exporte un modèle/pipeline entraîné sur le disque avec joblib.

    joblib sérialise l'ensemble du pipeline (TF-IDF + XGBClassifier), si bien
    qu'il suffit ensuite de recharger un seul fichier pour faire des prédictions.

    Retourne le chemin absolu du fichier écrit.
    """
    import os
    import joblib

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    joblib.dump(model, path)
    return os.path.abspath(path)


def load_model(path: str = "ml/models/xgboost_sentiment.joblib"):
    """
    Recharge un modèle/pipeline exporté avec save_model().

    Exemple :
        model = load_model()
        model.predict(["this product is great"])
    """
    import joblib

    return joblib.load(path)


__all__ = [
    "build_pipeline",
    "default_param_grid",
    "run_gridsearch",
    "evaluate_classification",
    "compute_learning_curve",
    "plot_learning_curve",
    "plot_confusion",
    "train_with_mlflow",
    "save_model",
    "load_model",
    "MLFLOW_DISPONIBLE",
]
