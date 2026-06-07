"""
entrainer_mlflow.py — Entraîne XGBoost (FR) et logge TOUT le modèle dans MLflow
================================================================================
Un seul run MLflow contient tout ce qui est nécessaire pour la certification,
prêt à être capturé depuis l'UI MLflow (http://127.0.0.1:5000) :

  • Parameters  : hyperparamètres du modèle (best params), cv, scoring, tailles
  • Metrics     : accuracy, precision, recall, f1, roc_auc, cv_best_f1
  • Artifacts   :
        - classification_report.txt    (rapport de classification)
        - gridsearch_results.csv       (TOUTES les combinaisons testées + rangs)
        - learning_curve.png           (courbe d'apprentissage)
        - confusion_matrix.png         (matrice de confusion)
        - model/                       (pipeline TF-IDF + XGBoost sérialisé)

Lancer : python ml/entrainer_mlflow.py
UI     : mlflow ui --backend-store-uri sqlite:///mlflow.db   (http://127.0.0.1:5000)
"""

import os
import sys

# Garde anti-crash d'encodage sur la console Windows (cp1252) : on force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import matplotlib
matplotlib.use("Agg")  # pas d'affichage : on enregistre les figures en fichiers
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import train_test_split

from ml import xgboost_sentiment as xs

RACINE = os.path.dirname(os.path.dirname(__file__))
CACHE_FR = os.path.join(RACINE, "data", "df_final_fr.csv")
DOSSIER_ART = os.path.join(RACINE, "ml", "artifacts")
RANDOM_STATE = 42


def main():
    if not os.path.exists(CACHE_FR):
        print(f"❌ Dataset introuvable : {CACHE_FR}")
        print("   Lancez d'abord : python data/traduire_echantillon.py")
        sys.exit(1)

    os.makedirs(DOSSIER_ART, exist_ok=True)

    # 1) Données françaises
    df = pd.read_csv(CACHE_FR)
    X = df["texte_fr"].astype(str).tolist()
    y = df["label"].astype(int).tolist()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y
    )
    print(f"📦 {len(df)} avis | train {len(X_train)} / test {len(X_test)}")

    # 2) GridSearch (toutes les combinaisons) + meilleur modèle
    print("🔎 GridSearch en cours...")
    grid = xs.run_gridsearch(X_train, y_train)
    best = grid.best_estimator_
    print(f"   Meilleurs hyperparamètres : {grid.best_params_}")

    # 3) Métriques sur le test
    metrics = xs.evaluate_classification(best, X_test, y_test)
    print(f"   Accuracy {metrics['accuracy']:.4f} | F1 {metrics['f1']:.4f} | ROC-AUC {metrics['roc_auc']:.4f}")

    # 4) Artefacts modèle ──────────────────────────────────────────────
    # 4a) Résultats COMPLETS du GridSearch (toutes les combinaisons + rangs)
    cv = pd.DataFrame(grid.cv_results_)
    colonnes = [c for c in cv.columns if c.startswith("param_")] + \
               ["mean_test_score", "std_test_score", "rank_test_score", "mean_fit_time"]
    chemin_grid = os.path.join(DOSSIER_ART, "gridsearch_results.csv")
    cv[colonnes].sort_values("rank_test_score").to_csv(chemin_grid, index=False)

    # 4b) Courbe d'apprentissage
    print("📈 Calcul de la courbe d'apprentissage...")
    lc = xs.compute_learning_curve(
        xs.build_pipeline(n_estimators=200, max_depth=4), X_train, y_train
    )
    fig, ax = plt.subplots(figsize=(7, 5))
    xs.plot_learning_curve(lc, ax=ax)
    fig.tight_layout()
    chemin_lc = os.path.join(DOSSIER_ART, "learning_curve.png")
    fig.savefig(chemin_lc, dpi=120)
    plt.close(fig)

    # 4c) Matrice de confusion
    fig, ax = plt.subplots(figsize=(5, 4))
    xs.plot_confusion(metrics["confusion_matrix"], ax=ax)
    fig.tight_layout()
    chemin_cm = os.path.join(DOSSIER_ART, "confusion_matrix.png")
    fig.savefig(chemin_cm, dpi=120)
    plt.close(fig)

    # 4d) Graphique d'OVERFITTING : écart Train vs Test (accuracy & F1)
    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score
    y_train_pred = best.predict(X_train)
    acc_tr, f1_tr = accuracy_score(y_train, y_train_pred), f1_score(y_train, y_train_pred)
    groupes = ["Accuracy", "F1-score"]
    vals_train = [acc_tr, f1_tr]
    vals_test = [metrics["accuracy"], metrics["f1"]]
    xpos = np.arange(len(groupes)); largeur = 0.35
    fig, ax = plt.subplots(figsize=(6.5, 5))
    b1 = ax.bar(xpos - largeur / 2, vals_train, largeur, label="Train", color="#6366F1")
    b2 = ax.bar(xpos + largeur / 2, vals_test, largeur, label="Test (généralisation)", color="#F97316")
    ax.bar_label(b1, fmt="%.3f", padding=2)
    ax.bar_label(b2, fmt="%.3f", padding=2)
    for i in range(len(groupes)):
        ecart = vals_train[i] - vals_test[i]
        ax.annotate(f"écart {ecart:.2f}",
                    xy=(xpos[i], max(vals_train[i], vals_test[i]) + 0.07),
                    ha="center", fontweight="bold", color="#b91c1c")
    ax.set_xticks(xpos); ax.set_xticklabels(groupes)
    ax.set_ylim(0, 1.18); ax.set_ylabel("Score")
    ax.set_title("Overfitting — écart Train vs Test\n(un grand écart = sur-apprentissage)", fontweight="bold")
    ax.legend(loc="lower right"); ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    chemin_of = os.path.join(DOSSIER_ART, "overfitting.png")
    fig.savefig(chemin_of, dpi=120)
    plt.close(fig)

    # 4e) Rapport de classification (texte)
    chemin_rapport = os.path.join(DOSSIER_ART, "classification_report.txt")
    with open(chemin_rapport, "w", encoding="utf-8") as f:
        f.write(metrics["classification_report"])

    # 5) Logging MLflow : TOUT dans un seul run ────────────────────────
    if not xs.MLFLOW_DISPONIBLE:
        print("\nℹ️ MLflow non installé : artefacts générés dans ml/artifacts/ mais pas de run.")
        print("   pip install mlflow  pour activer le tracking.")
        return

    import mlflow

    # On sauvegarde le pipeline AVANT le run pour le logger comme artefact .joblib
    # (évite l'erreur "untrusted types" de mlflow.sklearn.log_model avec XGBoost).
    chemin_modele = xs.save_model(best)

    # MLflow dockerisé si MLFLOW_TRACKING_URI est défini (ex: http://localhost:5000),
    # sinon base locale sqlite. → permet de logger dans le service MLflow du docker-compose.
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("sentiment-xgboost")
    with mlflow.start_run(run_name="xgboost-fr-complet") as run:
        # Parameters
        mlflow.log_params(grid.best_params_)
        mlflow.log_param("algo", "XGBClassifier")
        mlflow.log_param("cv_folds", 3)
        mlflow.log_param("scoring", "f1")
        mlflow.log_param("n_train", len(X_train))
        mlflow.log_param("n_test", len(X_test))
        mlflow.log_param("dataset", "df_final_fr.csv (avis traduits EN→FR)")
        # Metrics (test + train pour visualiser l'overfitting)
        for cle in ("accuracy", "precision", "recall", "f1", "roc_auc"):
            if metrics.get(cle) is not None:
                mlflow.log_metric(cle, metrics[cle])
        mlflow.log_metric("cv_best_f1", grid.best_score_)
        mlflow.log_metric("accuracy_train", acc_tr)
        mlflow.log_metric("f1_train", f1_tr)
        mlflow.log_metric("overfit_gap_f1", f1_tr - metrics["f1"])
        # Artifacts
        mlflow.log_artifact(chemin_rapport)
        mlflow.log_artifact(chemin_grid)
        mlflow.log_artifact(chemin_lc)
        mlflow.log_artifact(chemin_cm)
        mlflow.log_artifact(chemin_of)  # graphique d'overfitting
        mlflow.log_artifact(chemin_modele, artifact_path="model")  # binaire .joblib du pipeline
        run_id = run.info.run_id

    print("\n" + "=" * 60)
    print(f"✅ Run MLflow complet : {run_id}")
    print("   Ouvrez l'UI :  mlflow ui --backend-store-uri sqlite:///mlflow.db")
    print("   Puis http://127.0.0.1:5000  → experiment 'sentiment-xgboost' → ce run")
    print("   À CAPTURER dans le run :")
    print("     • onglet Parameters  → hyperparamètres du modèle")
    print("     • onglet Metrics     → accuracy / f1 / roc_auc")
    print("     • Artifacts > learning_curve.png")
    print("     • Artifacts > confusion_matrix.png")
    print("     • Artifacts > classification_report.txt")
    print("     • Artifacts > gridsearch_results.csv")
    print(f"   Modèle local : {chemin_modele}")
    print("=" * 60)


if __name__ == "__main__":
    main()
