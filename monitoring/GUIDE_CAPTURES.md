# Guide de captures d'écran — Monitoring (Prometheus / Grafana)

> **Important (intégrité).** Ce guide produit des captures d'écran **réelles** d'une
> stack qui tourne vraiment. Pour une certification, ne jamais fabriquer/retoucher de
> fausses captures : le jury peut demander une démonstration live. La procédure
> ci-dessous prend ~10 minutes et donne des preuves authentiques.

---

## Étape 0 — Lancer la stack

```bash
# À la racine du projet
docker-compose up --build -d

# Vérifier que les 5 services tournent
docker-compose ps
```

Services attendus :

| Service | URL | Identifiants |
|---------|-----|--------------|
| API Modèle | http://localhost:8000/docs | clé API : `dev-secret-key-change-in-production` |
| API Données | http://localhost:8001/docs | idem |
| Streamlit | http://localhost:8501 | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | `admin` / `admin` |

---

## Étape 1 — Générer du trafic réel

Sans trafic, les graphiques sont vides. On envoie de vraies requêtes (succès + erreurs) :

```bash
# Trafic nominal (≈ 200 requêtes, mélange 200/403/404/422)
python monitoring/generer_trafic.py --requetes 200

# Puis une rafale orientée erreurs (pour voir les courbes d'erreurs monter)
python monitoring/generer_trafic.py --requetes 100 --erreurs
```

---

## Étape 2 — Captures **Prometheus** (http://localhost:9090)

1. **Cibles UP** — menu *Status > Targets*.
   → 📸 **Capture 1** : les jobs `api_modele`, `api_donnees`, `prometheus` en **UP** (vert).

2. **Taux de requêtes** — onglet *Graph*, coller la requête puis *Execute > Graph* :
   ```promql
   sum by (handler) (rate(http_requests_total[1m]))
   ```
   → 📸 **Capture 2** : courbes de trafic par endpoint.

3. **Erreurs HTTP** :
   ```promql
   sum by (status) (rate(http_requests_total{status=~"4..|5.."}[1m]))
   ```
   → 📸 **Capture 3** : les codes 403 / 404 / 422 apparaissent.

4. **Latence P95** :
   ```promql
   histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[5m])))
   ```
   → 📸 **Capture 4** : latence 95e percentile.

---

## Étape 3 — Captures **Grafana** (http://localhost:3000)

1. Connexion `admin` / `admin` (passer l'écran de changement de mot de passe).
2. Menu *Dashboards* → ouvrir **Avis Sentiment** (provisionné automatiquement).
   → 📸 **Capture 5** : le dashboard complet avec les panneaux remplis.
3. (Optionnel) *Connections > Data sources* → **Prometheus** marqué *Working*.
   → 📸 **Capture 6** : datasource Prometheus opérationnelle.

> Si un panneau est vide : relancer `generer_trafic.py`, puis régler la fenêtre de
> temps en haut à droite sur *Last 15 minutes* et l'auto-refresh sur *5s*.

---

## Étape 4 — Captures de l'**incident d'arrêt de conteneur** (réel)

On provoque *réellement* l'arrêt d'un conteneur (cf. `incident_report.md` #003) :

```bash
# 1. Arrêter brutalement l'API modèle (simule une panne / OOM)
docker stop avis-api-modele

# 2. Observer l'état : Exited
docker-compose ps
```
→ 📸 **Capture 7** : `avis-api-modele` en état **Exited**.

```bash
# 3. Dans Prometheus, la cible passe DOWN :
#    Status > Targets   (api_modele en rouge / DOWN)
#    ou requête :  up{job="api_modele"}   → vaut 0
```
→ 📸 **Capture 8** : cible `api_modele` **DOWN** dans Prometheus.

```bash
# 4. Rapport de monitoring applicatif en mode dégradé
python monitoring/monitor.py
```
→ 📸 **Capture 9** : rapport `monitor.py` (erreurs / statut DEGRADED).

```bash
# 5. Remise en service et vérification
docker start avis-api-modele
curl http://localhost:8000/health
```
→ 📸 **Capture 10** : cible repassée **UP** + `/health` `healthy`.

---

## Rangement conseillé des captures

```
docs/captures/
├── 01_prometheus_targets_up.png
├── 02_prometheus_taux_requetes.png
├── 03_prometheus_erreurs.png
├── 04_prometheus_latence_p95.png
├── 05_grafana_dashboard.png
├── 06_grafana_datasource.png
├── 07_docker_conteneur_exited.png
├── 08_prometheus_cible_down.png
├── 09_monitor_degraded.png
└── 10_retour_nominal.png
```

Ces 10 captures couvrent **C11** (monitoring du modèle), **C20** (surveillance
applicative) et **C21** (détection + résolution d'incident) avec des preuves réelles.
