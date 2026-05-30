"""
api_data/main.py — C5 : API REST exposant les données de la BDD
================================================================
Cette API FastAPI expose les données des avis clients via HTTP.
Elle permet à d'autres applications (comme Streamlit) de lire les données.

Compétence couverte : C5 — Créer une API REST pour exposer les données

AUTHENTIFICATION : API Key envoyée dans le header HTTP "X-API-Key"
  - En développement : clé définie dans la variable d'environnement API_KEY
  - Valeur par défaut (dev) : "dev-secret-key-change-in-production"
  - Documentation OpenAPI : http://localhost:8001/docs

Lancer : uvicorn api_data.main:app --reload --port 8001
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Query, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from database import queries


# ─────────────────────────────────────────────
# AUTHENTIFICATION PAR API KEY (C5)
# Le header "X-API-Key" est obligatoire sur toutes les routes protégées.
# Conforme OWASP API Security Top 10 — A01 : Broken Object Level Authorization
# ─────────────────────────────────────────────

# Lecture de la clé depuis la variable d'environnement (bonne pratique sécurité)
# En production : définir API_KEY dans les secrets Docker/GitHub Actions
API_KEY = os.environ.get("API_KEY", "dev-secret-key-change-in-production")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verifier_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency FastAPI : vérifie que la requête contient une API Key valide.
    Si la clé est absente ou incorrecte, retourne une erreur 403.

    Exemple d'appel curl :
        curl -H "X-API-Key: dev-secret-key-change-in-production" http://localhost:8001/avis
    """
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Accès refusé : clé API invalide ou manquante. "
                   "Envoyez votre clé dans le header 'X-API-Key'.",
        )
    return api_key


# ─────────────────────────────────────────────
# INITIALISATION DE L'APPLICATION
# ─────────────────────────────────────────────
app = FastAPI(
    title="API Données - Avis Clients",
    description="API REST pour accéder aux données d'avis clients stockées en BDD.",
    version="1.0.0",
)

# CORS : autorise les requêtes depuis le frontend Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En production, mettre l'URL exacte du frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# MODÈLES PYDANTIC (validation des données)
# ─────────────────────────────────────────────
class AvisResponse(BaseModel):
    id: int
    texte: str
    note: int
    source: str
    date_avis: Optional[str] = None
    auteur_pseudo: Optional[str] = None
    produit: Optional[str] = None


class StatistiquesResponse(BaseModel):
    produit: str
    nb_avis: int
    note_moyenne: float
    note_min: int
    note_max: int
    nb_positifs: int
    pct_positifs: float


# ─────────────────────────────────────────────
# MIDDLEWARE DE LOGGING
# Enregistre chaque requête dans les logs_api de la BDD
# ─────────────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        debut = time.time()
        response = await call_next(request)
        duree_ms = round((time.time() - debut) * 1000, 2)

        # Enregistrer le log en BDD (en arrière-plan)
        try:
            queries.inserer_log_api(
                endpoint=request.url.path,
                methode=request.method,
                statut=response.status_code,
                duree_ms=duree_ms,
            )
        except Exception:
            pass  # Ne pas bloquer la réponse si le log échoue

        return response


app.add_middleware(LoggingMiddleware)


# ─────────────────────────────────────────────
# MÉTRIQUES PROMETHEUS (C11 / C20)
# Expose un endpoint /metrics au format Prometheus, scrapé par Prometheus
# et visualisé dans Grafana (taux de requêtes, latence P95, erreurs).
# ─────────────────────────────────────────────
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ─────────────────────────────────────────────
# ROUTES DE L'API
# ─────────────────────────────────────────────

@app.get("/", tags=["Santé"])
def accueil():
    """Point de vérification public (pas d'auth requise)."""
    return {"status": "ok", "message": "API Données opérationnelle"}


@app.get("/health", tags=["Santé"])
def health_check():
    """Health check public pour Docker et le monitoring."""
    try:
        nb = queries.compter_avis()
        return {"status": "healthy", "nb_avis_en_bdd": nb}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"BDD inaccessible : {e}")


@app.get("/avis", response_model=list[AvisResponse], tags=["Avis"])
def lister_avis(
    limit: int = Query(default=20, ge=1, le=100, description="Nombre d'avis à retourner"),
    offset: int = Query(default=0, ge=0, description="Décalage pour la pagination"),
    _key: str = Depends(verifier_api_key),  # 🔒 Auth requise
):
    """
    Retourne la liste des avis clients avec pagination.

    - **limit** : max 100 par page
    - **offset** : pour paginer (ex: offset=20 pour la page 2)
    """
    avis = queries.get_tous_les_avis(limit=limit, offset=offset)
    return avis


@app.get("/avis/produit/{nom_produit}", response_model=list[AvisResponse], tags=["Avis"])
def avis_par_produit(nom_produit: str, _key: str = Depends(verifier_api_key)):
    """Retourne tous les avis pour un produit donné. 🔒 Auth requise."""
    avis = queries.get_avis_par_produit(nom_produit)
    if not avis:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun avis trouvé pour le produit '{nom_produit}'"
        )
    return avis


@app.get("/avis/recherche", response_model=list[AvisResponse], tags=["Avis"])
def rechercher_avis(
    q: str = Query(..., min_length=2, description="Mots-clés à rechercher"),
    _key: str = Depends(verifier_api_key),
):
    """Recherche textuelle dans les avis. 🔒 Auth requise."""
    resultats = queries.rechercher_avis(q)
    return resultats


@app.get("/statistiques", response_model=list[StatistiquesResponse], tags=["Statistiques"])
def statistiques_produits(_key: str = Depends(verifier_api_key)):
    """Statistiques agrégées par produit. 🔒 Auth requise."""
    return queries.get_statistiques_par_produit()


@app.get("/statistiques/sources", tags=["Statistiques"])
def statistiques_sources(_key: str = Depends(verifier_api_key)):
    """Répartition des avis par source. 🔒 Auth requise."""
    return queries.get_statistiques_par_source()


@app.get("/produits", tags=["Produits"])
def lister_produits(_key: str = Depends(verifier_api_key)):
    """Liste de tous les produits. 🔒 Auth requise."""
    produits = queries.get_liste_produits()
    return {"produits": produits, "total": len(produits)}


@app.get("/logs", tags=["Monitoring"])
def logs_recents(
    limit: int = Query(default=20, ge=1, le=100),
    _key: str = Depends(verifier_api_key),
):
    """Derniers logs d'API. 🔒 Auth requise."""
    return queries.get_logs_recents(limit=limit)


# ─────────────────────────────────────────────
# POINT D'ENTRÉE (lancement direct)
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)
