# Documentation du Monitoring — C20
## Projet : Analyseur de Sentiment d'Avis Clients

---

## 1. Métriques surveillées et seuils d'alerte

| Métrique | Description | Seuil WARNING | Seuil CRITIQUE | Action |
|----------|-------------|---------------|----------------|--------|
| **Taux d'erreurs 5xx** | % de requêtes en erreur serveur | > 2% | > 5% | Vérifier les logs, redémarrer le service |
| **Latence P95** | 95e percentile du temps de réponse | > 1000ms | > 2000ms | Analyser les requêtes lentes, optimiser |
| **Latence P50** | Médiane du temps de réponse | > 500ms | > 1000ms | Vérifier la charge CPU |
| **Erreurs 4xx** | Requêtes non autorisées / invalides | > 10/h | > 50/h | Vérifier les clés API, valider les entrées |
| **Drift du modèle** | Variation % positif/négatif vs baseline | > 10% | > 20% | Re-valider le modèle, vérifier les données |
| **Prédictions/heure** | Volume d'utilisation | < 1/h (inactivité) | 0 pendant 24h | Vérifier la disponibilité du service |

**Baseline du modèle :** 55% POSITIVE / 45% NEGATIVE (mesurée sur les données initiales)

---

## 2. Outils de monitoring installés

### 2.1 Collecteurs de logs

**Fichier de log applicatif** (`monitoring/app.log`) :
- Généré par `monitoring/monitor.py` via le module `logging` Python
- Format : `YYYY-MM-DD HH:MM:SS | LEVEL | module | message`
- Rotation : quotidienne, conservation 30 jours

**Table `logs_api` (SQLite)** :
- Chaque requête API est enregistrée automatiquement
- Colonnes : endpoint, methode_http, statut_http, duree_ms, message_erreur, enregistre_le

### 2.2 Outil de journalisation

```python
# Intégré dans api_model/main.py et api_data/main.py
# À chaque requête :
log = LogAPI(
    endpoint=str(request.url.path),
    methode_http=request.method,
    statut_http=response.status_code,
    duree_ms=round((time.time() - debut) * 1000),
    enregistre_le=datetime.now().isoformat()
)
```

### 2.3 Dashboard de restitution en temps réel

**Outil retenu : Page "Monitoring" dans l'application Streamlit** (http://localhost:8501)

**Justification du choix :**
- Accessible à toutes les parties prenantes (navigateur web)
- Respecte les recommandations d'accessibilité WCAG 2.1 AA (contraste, navigation clavier)
- Python natif, pas de dépendance supplémentaire
- Données rafraîchies à chaque visite (quasi temps-réel)

**Métriques affichées dans le dashboard :**
- Total de prédictions et temps de traitement moyen
- Répartition POSITIVE/NEGATIVE (graphique en barres)
- Derniers logs API (tableau filtrable)
- Alertes actives (si seuils dépassés)

### 2.4 Outil de surveillance continue

```bash
# Lancement de la surveillance en arrière-plan
python monitoring/monitor.py --continu
# Rapport toutes les 30 secondes, logs dans monitoring/app.log
```

### 2.5 Stack Prometheus + Grafana (métriques temps réel)

En complément du monitoring applicatif maison, le projet intègre la stack
standard de l'industrie **Prometheus + Grafana** pour la collecte et la
visualisation des métriques techniques des APIs.

**Architecture :**

```
API Modèle (:8000/metrics) ─┐
                            ├─►  Prometheus (:9090)  ──►  Grafana (:3000)
API Données (:8001/metrics)─┘     (scrape /metrics       (dashboards)
                                   toutes les 15s)
```

**Instrumentation des APIs :** chaque API FastAPI expose un endpoint `/metrics`
grâce à `prometheus-fastapi-instrumentator`. Les métriques exposées incluent :

| Métrique Prometheus | Type | Usage |
|---------------------|------|-------|
| `http_requests_total{handler,method,status}` | Counter | Débit de requêtes, taux d'erreurs par code HTTP |
| `http_request_duration_seconds_bucket` | Histogram | Latence P50 / P95 / P99 |
| `http_request_size_bytes` / `http_response_size_bytes` | Summary | Volume de données échangées |

**Prometheus** (`monitoring/prometheus/prometheus.yml`) interroge les deux APIs
toutes les 15 secondes et stocke les séries temporelles.

**Grafana** (`monitoring/grafana/`) se connecte automatiquement à Prometheus
(source de données auto-provisionnée) et charge au démarrage le dashboard
**« Avis Sentiment — APIs »** (`monitoring/grafana/dashboards/avis-sentiment.json`),
qui affiche : total des requêtes, débit par service, taux d'erreurs 5xx,
latence P50/P95/P99, répartition par code de statut et top des endpoints.

**Lancement (via Docker Compose) :**

```bash
docker-compose up --build
```

| Service | URL | Identifiants |
|---------|-----|--------------|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |

> La requête PromQL de la latence P95 utilisée dans le dashboard :
> `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, job))`

---

## 3. Procédure d'installation du monitoring

### Prérequis
```bash
pip install -r requirements.txt
# Inclut déjà : fastapi, uvicorn, streamlit, sqlite3 (inclus dans Python)
```

### Étape 1 — Initialiser la base de données
```bash
python database/init_db.py
# Crée la table logs_api dans avis.db
```

### Étape 2 — Lancer les APIs avec logging activé
```bash
uvicorn api_model.main:app --port 8000  # logging intégré
uvicorn api_data.main:app --port 8001   # logging intégré
```

### Étape 3 — Lancer le dashboard Streamlit
```bash
streamlit run app/main.py
# Aller sur http://localhost:8501 → page "Monitoring"
```

### Étape 4 — Lancer la surveillance continue (optionnel)
```bash
python monitoring/monitor.py --continu
```

### Étape 5 — Vérifier que la chaîne fonctionne
```bash
# Faire quelques requêtes test
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: dev-secret-key-change-in-production" \
  -H "Content-Type: application/json" \
  -d '{"texte": "Excellent produit!"}'

# Vérifier dans le dashboard que le log apparaît
```

---

## 4. Alertes configurées

Les alertes sont déclenchées automatiquement par `monitoring/monitor.py` :

```python
SEUIL_ERREURS = 5       # Alerte si >= 5 erreurs 5xx dans les 100 dernières requêtes
SEUIL_LATENCE_MS = 2000 # Alerte si latence max > 2000ms
```

**Sortie d'une alerte :**
```
2024-01-15 14:32:01 | WARNING  | avis-sentiment | ALERTE : 6 erreurs 5xx détectées !
2024-01-15 14:32:01 | WARNING  | avis-sentiment | ALERTE : Latence maximale élevée (2450ms > 2000ms)
```

---

## 5. Conformité RGPD dans le monitoring

| Donnée de log | Traitement | Durée de conservation |
|---------------|-----------|----------------------|
| Endpoint appelé | Pseudonymisé (pas d'IP) | 30 jours |
| Code HTTP retourné | Numérique, non personnel | 30 jours |
| Durée de traitement | Numérique, non personnel | 30 jours |
| Message d'erreur | Sans données utilisateur | 30 jours |

**Principe appliqué :** Aucune donnée personnelle n'est enregistrée dans les logs (pas d'IP, pas de contenu des requêtes, pas d'identifiant utilisateur).

---

## 6. Procédure de nettoyage des logs (maintenance)

```python
# Supprimer les logs de plus de 30 jours
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('database/avis.db')
date_limite = (datetime.now() - timedelta(days=30)).isoformat()
conn.execute("DELETE FROM logs_api WHERE enregistre_le < ?", (date_limite,))
conn.commit()
conn.close()
```
