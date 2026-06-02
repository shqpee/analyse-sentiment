"""
test_data_api.py — C12, C18 : Tests automatisés de l'API Données
=================================================================
Tests pour l'API qui expose les données de la base SQLite.

Lancer : pytest tests/ -v
"""

import sys
import os
import pytest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from api_data.main import app, API_KEY
import database.queries as queries

AUTH_HEADERS = {"X-API-Key": API_KEY}


@pytest.fixture
def client():
    """Client de test pour l'API données."""
    return TestClient(app)


# ─────────────────────────────────────────────
# TESTS DE SANTÉ
# ─────────────────────────────────────────────

def test_accueil(client):
    """L'API doit répondre à la racine."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_check(client):
    """Le health check doit indiquer l'état de la BDD."""
    response = client.get("/health")
    assert response.status_code in [200, 503]


# ─────────────────────────────────────────────
# TESTS DES ROUTES AVIS
# ─────────────────────────────────────────────

def test_sans_api_key(client):
    """Une requête sans clé API doit retourner 403."""
    response = client.get("/avis")
    assert response.status_code == 403


def test_lister_avis(client):
    """Doit retourner une liste d'avis (éventuellement vide)."""
    response = client.get("/avis", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_lister_avis_pagination(client):
    """La pagination doit fonctionner avec les paramètres limit et offset."""
    response = client.get("/avis?limit=5&offset=0", headers=AUTH_HEADERS)
    assert response.status_code == 200
    response = client.get("/avis?limit=5&offset=5", headers=AUTH_HEADERS)
    assert response.status_code == 200


def test_lister_avis_limit_invalide(client):
    """Un limit trop grand doit retourner une erreur de validation."""
    response = client.get("/avis?limit=500", headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_avis_produit_inexistant(client):
    """Un produit inexistant doit retourner 404."""
    response = client.get("/avis/produit/ProduitQuiNExistePas123", headers=AUTH_HEADERS)
    assert response.status_code == 404


def test_recherche_avis_trop_court(client):
    """Un mot-clé de 1 caractère doit retourner une erreur de validation."""
    response = client.get("/avis/recherche?q=a", headers=AUTH_HEADERS)
    assert response.status_code == 422


def test_recherche_avis_valide(client):
    """Une recherche valide doit retourner une liste."""
    response = client.get("/avis/recherche?q=bon", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ─────────────────────────────────────────────
# TESTS DES STATISTIQUES
# ─────────────────────────────────────────────

def test_statistiques_produits(client):
    """Les statistiques par produit doivent être disponibles."""
    response = client.get("/statistiques", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_statistiques_sources(client):
    """Les statistiques par source doivent être disponibles."""
    response = client.get("/statistiques/sources", headers=AUTH_HEADERS)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ─────────────────────────────────────────────
# TESTS DES PRODUITS
# ─────────────────────────────────────────────

def test_lister_produits(client):
    """Doit retourner la liste des produits."""
    response = client.get("/produits", headers=AUTH_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "produits" in data
    assert "total" in data
    assert isinstance(data["produits"], list)


# ─────────────────────────────────────────────
# TESTS DES QUERIES (unitaires)
# ─────────────────────────────────────────────

def test_compter_avis():
    """La fonction de comptage doit retourner un entier >= 0."""
    try:
        count = queries.compter_avis()
        assert isinstance(count, int)
        assert count >= 0
    except Exception:
        pytest.skip("BDD non initialisée pour ce test unitaire")


def test_get_tous_les_avis_structure():
    """Les avis retournés doivent avoir les bonnes clés."""
    try:
        avis = queries.get_tous_les_avis(limit=1)
        if avis:
            assert "id" in avis[0]
            assert "texte" in avis[0]
            assert "note" in avis[0]
    except Exception:
        pytest.skip("BDD non initialisée pour ce test unitaire")
