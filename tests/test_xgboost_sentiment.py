"""
test_xgboost_sentiment.py — C12 : Tests automatisés du modèle XGBoost
=====================================================================
Tests pytest du module ml/xgboost_sentiment.py :
  - construction du pipeline TF-IDF + XGBoost
  - métriques de classification (accuracy, precision, recall, F1, ROC-AUC,
    matrice de confusion, rapport)
  - GridSearchCV (recherche d'hyperparamètres)
  - courbe d'apprentissage (learning curve)
  - entraînement complet (avec MLflow optionnel)

Lancer : pytest tests/test_xgboost_sentiment.py -v
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from ml import xgboost_sentiment as xs


# ─────────────────────────────────────────────
# JEU DE DONNÉES JOUET (déterministe, séparable)
# ─────────────────────────────────────────────
@pytest.fixture(scope="module")
def toy_data():
    """
    Petit corpus binaire clairement séparable :
      label 1 = avis positif, label 0 = avis négatif.
    Volume suffisant pour entraîner XGBoost et faire une CV à 3 plis.
    """
    positifs = [
        "great excellent product i love it",
        "amazing quality fantastic and perfect",
        "wonderful highly recommend really good",
        "superb best purchase very happy",
        "awesome love this great value",
        "perfect works great so good",
        "brilliant fantastic excellent service",
        "happy great product recommend it",
        "good great love amazing quality",
        "excellent perfect wonderful happy",
        "great value good love it",
        "amazing perfect best love great",
    ]
    negatifs = [
        "terrible awful product i hate it",
        "horrible quality bad and broken",
        "worst purchase very disappointed poor",
        "useless waste of money terrible",
        "bad broken does not work awful",
        "poor quality hate it disappointed",
        "horrible terrible worst experience bad",
        "broken useless poor awful product",
        "disappointed bad worst hate it",
        "terrible poor broken waste money",
        "awful bad horrible useless product",
        "worst terrible hate poor quality",
    ]
    X = positifs + negatifs
    y = [1] * len(positifs) + [0] * len(negatifs)
    return X, y


# ─────────────────────────────────────────────
# 1. PIPELINE
# ─────────────────────────────────────────────
def test_build_pipeline_structure():
    """Le pipeline contient bien une étape TF-IDF et un classifieur XGBoost."""
    pipe = xs.build_pipeline()
    noms = dict(pipe.named_steps)
    assert "tfidf" in noms
    assert "clf" in noms
    assert noms["clf"].__class__.__name__ == "XGBClassifier"


def test_pipeline_fit_predict(toy_data):
    """Le pipeline s'entraîne et prédit des labels binaires valides."""
    X, y = toy_data
    pipe = xs.build_pipeline(n_estimators=50, max_depth=3)
    pipe.fit(X, y)
    preds = pipe.predict(X)
    assert len(preds) == len(y)
    assert set(np.unique(preds)).issubset({0, 1})


# ─────────────────────────────────────────────
# 2. MÉTRIQUES DE CLASSIFICATION
# ─────────────────────────────────────────────
def test_evaluate_classification_keys(toy_data):
    """Toutes les métriques attendues sont présentes."""
    X, y = toy_data
    pipe = xs.build_pipeline(n_estimators=50, max_depth=3)
    pipe.fit(X, y)
    metrics = xs.evaluate_classification(pipe, X, y)
    for cle in ("accuracy", "precision", "recall", "f1", "roc_auc",
                "confusion_matrix", "classification_report"):
        assert cle in metrics


def test_evaluate_classification_valeurs(toy_data):
    """Les métriques sont dans [0, 1] et le modèle apprend les données jouet."""
    X, y = toy_data
    pipe = xs.build_pipeline(n_estimators=80, max_depth=3)
    pipe.fit(X, y)
    metrics = xs.evaluate_classification(pipe, X, y)
    for cle in ("accuracy", "precision", "recall", "f1"):
        assert 0.0 <= metrics[cle] <= 1.0
    # Données séparables : le modèle doit très bien réussir en ré-substitution
    assert metrics["accuracy"] >= 0.9
    # Matrice de confusion 2x2
    cm = np.array(metrics["confusion_matrix"])
    assert cm.shape == (2, 2)


# ─────────────────────────────────────────────
# 3. GRIDSEARCH
# ─────────────────────────────────────────────
def test_run_gridsearch(toy_data):
    """GridSearchCV retourne un meilleur estimateur et des hyperparamètres."""
    X, y = toy_data
    petite_grille = {"clf__n_estimators": [30, 60], "clf__max_depth": [2, 3]}
    grid = xs.run_gridsearch(X, y, param_grid=petite_grille, cv=3, scoring="f1")
    assert grid.best_estimator_ is not None
    assert "clf__n_estimators" in grid.best_params_
    assert 0.0 <= grid.best_score_ <= 1.0


# ─────────────────────────────────────────────
# 4. COURBE D'APPRENTISSAGE
# ─────────────────────────────────────────────
def test_compute_learning_curve(toy_data):
    """La courbe d'apprentissage renvoie des tableaux cohérents."""
    X, y = toy_data
    pipe = xs.build_pipeline(n_estimators=40, max_depth=3)
    lc = xs.compute_learning_curve(
        pipe, X, y, cv=3, scoring="f1",
        train_sizes=np.linspace(0.3, 1.0, 3),
    )
    assert len(lc["train_sizes"]) == 3
    assert len(lc["train_mean"]) == 3
    assert len(lc["val_mean"]) == 3
    # Les scores moyens restent dans [0, 1]
    assert np.all(lc["val_mean"] >= 0) and np.all(lc["val_mean"] <= 1)


# ─────────────────────────────────────────────
# 5. ENTRAÎNEMENT COMPLET (+ MLflow optionnel)
# ─────────────────────────────────────────────
def test_train_with_mlflow(tmp_path, toy_data):
    """L'entraînement complet renvoie métriques et meilleurs hyperparamètres."""
    X, y = toy_data
    # Tracking MLflow sur une base SQLite temporaire (si MLflow est installé)
    uri = "sqlite:///" + str(tmp_path / "mlflow.db").replace(os.sep, "/")
    petite_grille = {"clf__n_estimators": [30], "clf__max_depth": [3]}
    res = xs.train_with_mlflow(
        X, y, X, y,
        param_grid=petite_grille,
        cv=3,
        experiment_name="test-xgboost",
        tracking_uri=uri,
    )
    assert "metrics" in res
    assert "best_params" in res
    assert 0.0 <= res["metrics"]["f1"] <= 1.0
    assert res["model"] is not None
    # Si MLflow est dispo, un run_id doit avoir été créé
    if xs.MLFLOW_DISPONIBLE:
        assert res["run_id"] is not None
