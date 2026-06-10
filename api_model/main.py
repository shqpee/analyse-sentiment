"""
api_model/main.py — C9 : API REST exposant le modèle IA
========================================================
Cette API FastAPI permet d'analyser le sentiment de textes.
Elle encapsule le modèle HuggingFace et l'expose via HTTP.

Compétences couvertes :
  - C9  : API REST exposant un modèle IA (avec authentification)
  - C11 : Monitoring du modèle (statistiques d'utilisation)

AUTHENTIFICATION : API Key envoyée dans le header HTTP "X-API-Key"
  - En développement : clé définie dans la variable d'environnement API_KEY
  - Valeur par défaut (dev) : "dev-secret-key-change-in-production"

SÉCURITÉ (OWASP API Top 10) :
  - A01 Broken Object Level Auth → API Key sur toutes les routes sensibles
  - A02 Broken Authentication    → Clé lue depuis variable d'environnement
  - A03 Broken Object Property   → Pydantic valide et filtre les entrées
  - A04 Unrestricted Resource    → limit/max_items sur les endpoints batch
  - A05 Broken Function Level Auth → /health public, /predict protégé

Lancer : uvicorn api_model.main:app --reload --port 8000
Documentation : http://localhost:8000/docs
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from api_model.model import predire_sentiment, get_statistiques_modele, charger_modele
from database import queries


# ─────────────────────────────────────────────
# AUTHENTIFICATION PAR API KEY (C9 — OWASP A01, A02)
# ─────────────────────────────────────────────

API_KEY = os.environ.get("API_KEY", "dev-secret-key-change-in-production")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verifier_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Vérifie l'API Key dans le header 'X-API-Key'.
    Retourne 403 si absente ou incorrecte.

    Exemple :
        curl -H "X-API-Key: dev-secret-key-change-in-production" \\
             -X POST http://localhost:8000/predict \\
             -H "Content-Type: application/json" \\
             -d '{"texte": "This product is amazing!"}'
    """
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Accès refusé : clé API invalide ou manquante.",
        )
    return api_key


# ─────────────────────────────────────────────
# INITIALISATION
# ─────────────────────────────────────────────
app = FastAPI(
    title="API Modèle IA - Analyse de Sentiment",
    description="""
    API REST pour l'analyse de sentiment d'avis clients.

    **Modèle utilisé :** XGBoost (TF-IDF) entraîné sur des avis en français
    **Tâche :** Classification binaire (POSITIVE / NEGATIVE)
    """,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# ÉVÉNEMENTS DE CYCLE DE VIE
# ─────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    """Charge le modèle au démarrage de l'API (évite un délai à la première requête)."""
    charger_modele()


# ─────────────────────────────────────────────
# MODÈLES PYDANTIC
# ─────────────────────────────────────────────
class TexteRequest(BaseModel):
    texte: str = Field(
        ...,
        min_length=5,
        max_length=5000,  # borne anti-DoS (OWASP A04) ; le modèle tronque ensuite à 512 tokens
        description="Le texte à analyser",
        example="Ce produit est vraiment fantastique, je le recommande vivement !"
    )
    sauvegarder: bool = Field(
        default=False,
        description="Si True, sauvegarde la prédiction en base de données"
    )
    avis_id: Optional[int] = Field(
        default=None,
        description="ID de l'avis en BDD (si sauvegarder=True)"
    )


class PredictionResponse(BaseModel):
    texte: str
    label: str          # POSITIVE ou NEGATIVE
    score: float        # Confiance entre 0 et 1
    sentiment_fr: str   # "Positif" ou "Négatif" (pour l'affichage)
    duree_ms: float
    modele: str


class TextesBatchRequest(BaseModel):
    textes: list[str] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Liste de textes à analyser (max 10)"
    )


# ─────────────────────────────────────────────
# MIDDLEWARE DE LOGGING
# ─────────────────────────────────────────────
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        debut = time.time()
        response = await call_next(request)
        duree_ms = round((time.time() - debut) * 1000, 2)
        try:
            queries.inserer_log_api(
                endpoint=request.url.path,
                methode=request.method,
                statut=response.status_code,
                duree_ms=duree_ms,
            )
        except Exception:
            pass
        return response

app.add_middleware(LoggingMiddleware)


# ─────────────────────────────────────────────
# MÉTRIQUES PROMETHEUS (C11 / C20)
# Expose un endpoint /metrics au format Prometheus :
#   - http_requests_total{handler,method,status}
#   - http_request_duration_seconds_bucket (histogramme → latence P95)
# Ces métriques sont scrapées par Prometheus puis visualisées dans Grafana.
# ─────────────────────────────────────────────
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/", tags=["Santé"])
def accueil():
    """Point de vérification public (pas d'auth requise)."""
    return {"status": "ok", "message": "API Modèle IA opérationnelle"}


@app.get("/health", tags=["Santé"])
def health_check():
    """Health check public pour Docker et la CI/CD."""
    stats = get_statistiques_modele()
    return {
        "status": "healthy",
        "modele_charge": stats["modele_charge"],
        "total_predictions": stats["total_predictions"],
    }


@app.post("/predict", response_model=PredictionResponse, tags=["Prédiction"])
def predire(
    requete: TexteRequest,
    background_tasks: BackgroundTasks,
    _key: str = Depends(verifier_api_key),  # 🔒 Auth requise
):
    """
    Analyse le sentiment d'un texte.

    Retourne :
    - **label** : POSITIVE ou NEGATIVE
    - **score** : niveau de confiance (0 à 1)
    - **duree_ms** : temps de traitement

    Exemple d'utilisation :
    ```json
    {"texte": "Ce produit est excellent !"}
    ```
    """
    try:
        resultat = predire_sentiment(requete.texte)

        # Sauvegarde optionnelle en BDD (en tâche de fond pour ne pas ralentir la réponse)
        if requete.sauvegarder and requete.avis_id:
            background_tasks.add_task(
                queries.inserer_prediction,
                requete.avis_id,
                resultat["label"],
                resultat["score"],
                resultat["modele"],
            )

        return PredictionResponse(
            texte=requete.texte,
            label=resultat["label"],
            score=resultat["score"],
            sentiment_fr="Positif" if resultat["label"] == "POSITIVE" else "Négatif",
            duree_ms=resultat["duree_ms"],
            modele=resultat["modele"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch", tags=["Prédiction"])
def predire_batch(requete: TextesBatchRequest, _key: str = Depends(verifier_api_key)):
    """
    Analyse plusieurs textes en une seule requête (max 10).
    Utile pour analyser tous les avis d'un produit.
    """
    resultats = []
    for texte in requete.textes:
        try:
            res = predire_sentiment(texte)
            resultats.append({
                "texte": texte,
                "label": res["label"],
                "score": res["score"],
                "sentiment_fr": "Positif" if res["label"] == "POSITIVE" else "Négatif",
            })
        except Exception as e:
            resultats.append({
                "texte": texte,
                "erreur": str(e),
            })
    return {"resultats": resultats, "total": len(resultats)}


@app.get("/monitoring", tags=["Monitoring"])
def monitoring_modele(_key: str = Depends(verifier_api_key)):
    """
    Statistiques d'utilisation du modèle IA.
    Couverture C11 — Monitorer un modèle IA.

    Retourne :
    - Nombre total de prédictions
    - % positifs / négatifs
    - Temps moyen de réponse
    """
    return get_statistiques_modele()


@app.get("/monitoring/logs", tags=["Monitoring"])
def monitoring_logs(limit: int = 20, _key: str = Depends(verifier_api_key)):
    """Derniers logs d'appels API. 🔒 Auth requise."""
    return queries.get_logs_recents(limit=limit)


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
