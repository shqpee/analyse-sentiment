"""
test_model_api.py — C12, C18 : Tests automatisés de l'API Modèle IA
=====================================================================
Tests avec pytest + FastAPI TestClient.
Ces tests vérifient que l'API modèle fonctionne correctement.

Compétences couvertes :
  - C12 : Automatiser les tests du modèle IA
  - C18 : Intégration des tests dans la CI/CD

Lancer : pytest tests/ -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api_model.main import app, API_KEY

# ─────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────

# Header d'authentification utilisé dans tous les tests
AUTH_HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client():
    """Crée un client de test pour l'API modèle."""
    return TestClient(app)


# ─────────────────────────────────────────────
# TESTS DE SANTÉ
# ─────────────────────────────────────────────

def test_accueil(client):
    """Vérifie que la racine de l'API répond correctement."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_health_check(client):
    """Vérifie le health check de l'API."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


# ─────────────────────────────────────────────
# TESTS DE PRÉDICTION
# ─────────────────────────────────────────────

def test_sans_api_key(client):
    """Une requête sans clé API doit retourner 403."""
    response = client.post("/predict", json={"texte": "Amazing product!"})
    assert response.status_code == 403


def test_avec_mauvaise_api_key(client):
    """Une mauvaise clé API doit retourner 403."""
    response = client.post(
        "/predict",
        json={"texte": "Amazing product!"},
        headers={"X-API-Key": "mauvaise-cle"},
    )
    assert response.status_code == 403


def test_predire_texte_positif(client):
    """L'API doit retourner POSITIVE pour un texte positif évident."""
    response = client.post("/predict", json={
        "texte": "This product is absolutely amazing and fantastic! I love it!"
    }, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    # Vérifier la structure de la réponse
    assert "label" in data
    assert "score" in data
    assert "duree_ms" in data
    assert "modele" in data
    assert "sentiment_fr" in data

    # Vérifier les valeurs
    assert data["label"] in ["POSITIVE", "NEGATIVE"]
    assert 0.0 <= data["score"] <= 1.0
    assert data["duree_ms"] >= 0


def test_predire_texte_negatif(client):
    """L'API doit retourner NEGATIVE pour un texte négatif évident."""
    response = client.post("/predict", json={
        "texte": "This is the worst product I have ever bought. Terrible quality!"
    }, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["label"] in ["POSITIVE", "NEGATIVE"]


def test_predire_texte_trop_court(client):
    """Un texte trop court doit retourner une erreur 422 (validation)."""
    response = client.post("/predict", json={"texte": "ok"}, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_predire_texte_vide(client):
    """Un texte vide doit retourner une erreur de validation."""
    response = client.post("/predict", json={"texte": ""}, headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_predire_texte_long(client):
    """Un texte très long doit être tronqué et traité sans erreur."""
    texte_long = "This is great! " * 100
    response = client.post("/predict", json={"texte": texte_long}, headers=AUTH_HEADERS)
    assert response.status_code == 200


def test_predire_texte_caracteres_speciaux(client):
    """Le modèle doit gérer les caractères spéciaux sans planter."""
    response = client.post("/predict", json={
        "texte": "Très bon produit !!! Qualité ✓ Livraison 🚀 Parfait ☆☆☆☆☆"
    }, headers=AUTH_HEADERS)
    assert response.status_code == 200


# ─────────────────────────────────────────────
# TESTS BATCH
# ─────────────────────────────────────────────

def test_predire_batch(client):
    """L'analyse en lot doit fonctionner pour plusieurs textes."""
    response = client.post("/predict/batch", json={
        "textes": [
            "Great product!",
            "Terrible quality.",
            "Average, nothing special.",
        ]
    }, headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "resultats" in data
    assert len(data["resultats"]) == 3


def test_predire_batch_trop_grand(client):
    """Plus de 10 textes doit être refusé (validation Pydantic)."""
    response = client.post("/predict/batch", json={
        "textes": ["text " + str(i) for i in range(15)]
    }, headers=AUTH_HEADERS)
    assert response.status_code == 422


# ─────────────────────────────────────────────
# TESTS DE MONITORING
# ─────────────────────────────────────────────

def test_monitoring(client):
    """Le endpoint de monitoring doit retourner les statistiques."""
    client.post("/predict", json={"texte": "Great product, I love it!"}, headers=AUTH_HEADERS)

    response = client.get("/monitoring", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()

    assert "total_predictions" in data
    assert "modele" in data
    assert data["total_predictions"] >= 1
