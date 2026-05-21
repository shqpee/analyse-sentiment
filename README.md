# 🎯 Analyseur de Sentiment d'Avis Clients
## Projet RNCP37827 — Développeur en Intelligence Artificielle

---

## 📋 Description

Application complète d'analyse de sentiment d'avis clients.
Elle couvre les **21 compétences** du titre RNCP Développeur en IA (Bac+3/4).

Deux approches de modélisation sont mises en œuvre et comparées :

- **Transfer Learning** — modèle pré-entraîné HuggingFace `distilbert-base-uncased-finetuned-sst-2-english` (utilisé par l'API en production).
- **From Scratch** — modèles entraînés sur les données du projet (Naive Bayes, Régression Logistique, SVM, et **XGBoost**). Le modèle XGBoost (`ml/xgboost_sentiment.py`) fournit les **métriques de classification** (accuracy, precision, recall, F1, ROC-AUC, matrice de confusion), une **recherche d'hyperparamètres GridSearchCV**, une **courbe d'apprentissage**, un **suivi d'expériences MLflow** et des **tests pytest** dédiés.

Le notebook `sentiment_from_scratch_vs_transfer_learning.ipynb` compare les deux approches ; la page `xgboost_sentiment_page.ipynb` est prête à coller dans ce notebook.

## 🗂️ Structure du projet

```
avis-sentiment/
├── data/
│   ├── collect.py          # C1 — Extraction de données
│   ├── clean.py            # C3 — Nettoyage et agrégation
│   └── sample_reviews.csv  # Données d'exemple
├── database/
│   ├── schema.sql          # C4 — Schéma BDD (RGPD)
│   ├── init_db.py          # C4 — Initialisation
│   ├── queries.py          # C2 — Requêtes SQL
│   └── avis.db             # SQLite (généré)
├── api_data/
│   └── main.py             # C5 — API REST données
├── api_model/
│   ├── model.py            # C8 — Modèle HuggingFace
│   └── main.py             # C9, C11 — API REST + monitoring
├── ml/
│   └── xgboost_sentiment.py # C9-C11 — Modèle XGBoost (métriques, GridSearch,
│                            #          learning curve, suivi MLflow)
├── app/
│   └── main.py             # C10, C17 — Streamlit
├── tests/
│   ├── test_model_api.py   # C12, C18 — Tests API modèle
│   ├── test_data_api.py    # Tests API données
│   └── test_xgboost_sentiment.py # C12 — Tests du modèle XGBoost
├── sentiment_from_scratch_vs_transfer_learning.ipynb  # Notebook comparatif
├── xgboost_sentiment_page.ipynb # Page XGBoost à coller dans le notebook
├── monitoring/
│   ├── monitor.py          # C20 — Surveillance
│   └── incident_report.md  # C21 — Résolution incidents
├── .github/workflows/
│   ├── ci.yml              # C13, C18 — CI (tests auto)
│   └── cd.yml              # C19 — CD (livraison)
├── Dockerfile.model_api
├── Dockerfile.data_api
├── docker-compose.yml
├── requirements.txt        # Dépendances complètes (dev + notebook)
├── requirements-model.txt  # Dépendances minimales image API Modèle
└── requirements-data.txt   # Dépendances minimales image API Données
```

---

## 🚀 Installation et lancement

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Préparer les données et la base

```bash
# Étape 1 : collecter et nettoyer les données
python data/collect.py
python data/clean.py

# Étape 2 : créer la base de données
python database/init_db.py
```

### 3. Lancer les APIs (dans des terminaux séparés)

```bash
# Terminal 1 : API Modèle IA (port 8000)
uvicorn api_model.main:app --reload --port 8000

# Terminal 2 : API Données (port 8001)
uvicorn api_data.main:app --reload --port 8001
```

### 4. Lancer le frontend Streamlit

```bash
streamlit run app/main.py
```

Ouvrez le navigateur sur http://localhost:8501

---

## 🐳 Lancement avec Docker

```bash
# Tout lancer d'un coup
docker-compose up --build

# Arrêter
docker-compose down
```

**Images optimisées :** chaque service installe uniquement ses dépendances pour
des builds rapides et légers :

| Image | Fichier de dépendances | Particularité |
|-------|------------------------|---------------|
| API Données | `requirements-data.txt` | FastAPI + SQLite uniquement (pas de PyTorch) |
| API Modèle | `requirements-model.txt` | PyTorch installé en **version CPU-only** (~190 Mo au lieu de ~2 Go GPU) |

> Les bibliothèques d'expérimentation ML (`xgboost`, `mlflow`, `scikit-learn`)
> ne sont pas embarquées dans les images : elles servent au notebook et aux
> tests, et restent dans `requirements.txt`.

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest tests/ -v

# Avec couverture de code
pytest tests/ --cov=. --cov-report=term-missing
```

---

## 📡 Documentation des APIs

| Service | URL | Description |
|---------|-----|-------------|
| API Modèle | http://localhost:8000/docs | Analyse de sentiment |
| API Données | http://localhost:8001/docs | Données avis clients |
| Frontend | http://localhost:8501 | Application Streamlit |

---

## 🗺️ Couverture des compétences RNCP

| Compétence | Fichier | Description |
|-----------|---------|-------------|
| C1 | data/collect.py | Extraction multi-sources |
| C2 | database/queries.py | Requêtes SQL |
| C3 | data/clean.py | Nettoyage et agrégation |
| C4 | database/schema.sql | BDD RGPD |
| C5 | api_data/main.py | API REST données |
| C6-C7 | docs/veille_benchmark.md | Veille et benchmark |
| C8 | api_model/model.py | Config modèle HuggingFace |
| C9 | api_model/main.py | API REST modèle |
| C10 | app/main.py | Intégration IA dans l'app |
| C11 | api_model/main.py + monitoring/ | Monitoring modèle |
| C12 | tests/ | Tests automatisés |
| C13 | .github/workflows/ci.yml | Pipeline CI |
| C14-C16 | docs/ | Analyse fonctionnelle |
| C17 | app/main.py | Développement composants |
| C18 | tests/ + ci.yml | Tests dans CI |
| C19 | .github/workflows/cd.yml | Livraison continue |
| C20 | monitoring/monitor.py | Monitoring applicatif |
| C21 | monitoring/incident_report.md | Résolution incidents |
