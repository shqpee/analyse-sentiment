# Rapport d'Incident Technique — C21
## Application : Analyseur de Sentiment d'Avis Clients

---

## Modèle de Rapport d'Incident

*Utiliser ce modèle pour documenter chaque incident en production.*

---

### INCIDENT #001 — Exemple : Timeout de l'API Modèle

| Champ | Valeur |
|-------|--------|
| **Date** | 2024-03-15 14:32:00 |
| **Sévérité** | Haute (P2) |
| **Service affecté** | API Modèle IA (port 8000) |
| **Durée** | 47 minutes |
| **Détecté par** | Monitoring automatique (monitor.py) |

#### Description du problème
L'API modèle retournait des erreurs 504 (Gateway Timeout) pour toutes les requêtes `/predict`.
Le temps de réponse dépassait 30 secondes, causant des timeouts côté Streamlit.

#### Cause racine identifiée
Le modèle HuggingFace tentait de se télécharger à nouveau depuis internet (cache corrompu),
causant un blocage lors du chargement à froid.

#### Étapes de résolution

1. **Détection** (14h32) : Monitoring automatique a détecté >5 erreurs 5xx en 10 minutes
2. **Diagnostic** (14h40) : Consultation des logs → erreur `OSError: [Errno 28] No space left on device`
3. **Isolation** (14h45) : Redémarrage du conteneur en mode dégradé (simulation)
4. **Correction** (14h55) : Libération de l'espace disque + suppression du cache corrompu
5. **Redémarrage** (15h05) : Rechargement propre du modèle
6. **Vérification** (15h19) : Tests automatiques verts, monitoring nominal

#### Commandes utilisées lors de la résolution

```bash
# Voir les logs du conteneur Docker
docker logs avis-api-modele --tail 100

# Vérifier l'espace disque
df -h

# Supprimer le cache HuggingFace corrompu
rm -rf ~/.cache/huggingface/

# Redémarrer le service
docker-compose restart api_modele

# Vérifier que le health check passe
curl http://localhost:8000/health
```

#### Actions préventives
- [ ] Ajouter une alerte disque à 80% d'utilisation
- [ ] Configurer un volume Docker dédié pour le cache modèle
- [ ] Implémenter un fallback en mode simulation si le modèle ne charge pas

---

### INCIDENT #002 — Exemple : Base de données verrouillée

| Champ | Valeur |
|-------|--------|
| **Date** | 2024-04-02 09:15:00 |
| **Sévérité** | Moyenne (P3) |
| **Service affecté** | API Données (port 8001) |
| **Durée** | 12 minutes |

#### Description
SQLite retournait `database is locked` lors des insertions simultanées.

#### Cause racine
Plusieurs processus tentaient d'écrire dans SQLite simultanément (pas de gestion de la concurrence).

#### Résolution
Ajout de `timeout=30` dans les connexions SQLite et utilisation de transactions explicites.

#### Correction dans le code
```python
# Avant (problématique)
conn = sqlite3.connect("avis.db")

# Après (corrigé)
conn = sqlite3.connect("avis.db", timeout=30, check_same_thread=False)
```

---

### INCIDENT #003 — Exemple : Arrêt inattendu d'un conteneur Docker (OOMKilled)

| Champ | Valeur |
|-------|--------|
| **Date** | 2024-05-10 11:48:00 |
| **Sévérité** | Haute (P2) |
| **Service affecté** | Conteneur `avis-api-modele` (port 8000) |
| **Durée** | 18 minutes |
| **Détecté par** | Healthcheck Docker `unhealthy` + alerte Grafana (cible Prometheus `down`) |

#### Description du problème
Le conteneur `avis-api-modele` s'est arrêté brutalement et redémarrait en boucle
(`Restarting`). Sur Grafana, la cible Prometheus `api_modele` est passée en `DOWN`
(métrique `up == 0`) et toutes les requêtes `/predict` échouaient côté Streamlit.

#### Cause racine identifiée
Le conteneur a été tué par le *OOM Killer* du noyau (mémoire insuffisante allouée à
Docker pour le chargement de PyTorch + DistilBERT). Le conteneur s'arrête alors avec
le **code de sortie 137** (= 128 + signal 9 / SIGKILL), typique d'un `OOMKilled`.

#### Diagnostic — ce qu'on observe

```bash
# 1. État des conteneurs : api-modele en "Restarting" ou "Exited (137)"
docker-compose ps

# 2. Inspecter la raison de l'arrêt → OOMKilled: true, ExitCode: 137
docker inspect avis-api-modele --format '{{json .State}}'
# {"Status":"restarting","ExitCode":137,"OOMKilled":true, ...}

# 3. Derniers logs avant l'arrêt
docker logs avis-api-modele --tail 50
# ... Killed

# 4. Évènements Docker (confirme le kill)
docker events --filter container=avis-api-modele --since 30m
# ... container die ... exitCode=137
# ... container oom ...
```

#### Symptôme côté monitoring
- **Prometheus** : la requête `up{job="api_modele"}` retourne `0` pendant l'incident.
- **Grafana** : le panneau de disponibilité passe au rouge ; le taux de requêtes `/predict` chute à 0.
- **monitor.py** : le rapport bascule en statut `DEGRADED` (erreurs 5xx en hausse).

#### Étapes de résolution

1. **Détection** (11h48) : healthcheck `unhealthy`, cible Prometheus `down`.
2. **Diagnostic** (11h52) : `docker inspect` → `OOMKilled: true`, `ExitCode: 137`.
3. **Mitigation immédiate** (11h58) : augmentation de la mémoire allouée au service.
4. **Correction** (12h02) : ajout de limites/réservations mémoire dans `docker-compose.yml`.
5. **Redémarrage** (12h04) : `docker-compose up -d api_modele`.
6. **Vérification** (12h06) : healthcheck vert, cible Prometheus `up == 1`, trafic nominal.

#### Correction appliquée (docker-compose.yml)

```yaml
  api_modele:
    # ... configuration existante ...
    deploy:
      resources:
        limits:
          memory: 2g        # plafond pour éviter de saturer l'hôte
        reservations:
          memory: 1g        # mémoire garantie au chargement du modèle
```

#### Actions préventives
- [ ] Définir des `limits`/`reservations` mémoire pour **tous** les services.
- [ ] Ajouter une alerte Grafana sur `up == 0` pendant > 1 min (cible injoignable).
- [ ] Ajouter une alerte sur les redémarrages répétés d'un conteneur.
- [ ] Documenter la RAM minimale requise dans le README (chargement PyTorch).

---

## Procédure d'Urgence Générale (Runbook)

### En cas d'API inaccessible

```bash
# 1. Vérifier que les conteneurs tournent
docker-compose ps

# 2. Voir les logs d'erreur
docker-compose logs --tail 50

# 3. Redémarrer un service spécifique
docker-compose restart api_modele
docker-compose restart api_donnees

# 4. Redémarrer tout le stack
docker-compose down && docker-compose up -d

# 5. Vérifier les health checks
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### En cas d'erreurs dans les prédictions

```bash
# Tester l'API directement
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"texte": "This is a test"}'

# Voir le monitoring du modèle
curl http://localhost:8000/monitoring
```

### En cas de corruption de la base de données

```bash
# Sauvegarder la BDD (avant toute intervention)
cp database/avis.db database/avis_backup_$(date +%Y%m%d).db

# Vérifier l'intégrité
sqlite3 database/avis.db "PRAGMA integrity_check;"

# Recréer la BDD depuis les CSV si nécessaire
python database/init_db.py
```
