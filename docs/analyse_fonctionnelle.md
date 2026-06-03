# Analyse Fonctionnelle et Architecture Technique — E4 (C14, C15, C16)

---

## C14 — Analyse fonctionnelle

### Contexte et besoin

Une entreprise e-commerce souhaite analyser automatiquement les avis de ses clients pour mieux comprendre leur satisfaction. Actuellement, les avis sont lus manuellement, ce qui est coûteux et lent.

**Besoin utilisateur :** "Je veux savoir rapidement si les clients sont satisfaits de mes produits, sans avoir à lire des centaines d'avis."

### Acteurs du système

| Acteur | Rôle |
|--------|------|
| Analyste produit | Consulte les statistiques, filtre par produit |
| Administrateur | Gère la BDD, surveille l'application |
| Système de scraping | Collecte automatiquement les avis |
| API externe | Fournit des données complémentaires |

### Cas d'usage principaux

**UC1 — Analyser un avis texte**
- Acteur : Analyste produit
- Précondition : L'API modèle est opérationnelle
- Scénario : Saisir un texte → Cliquer "Analyser" → Voir résultat POSITIF/NÉGATIF avec score

**UC2 — Consulter les statistiques d'un produit**
- Acteur : Analyste produit
- Scénario : Sélectionner un produit → Voir note moyenne, % d'avis positifs, histogramme

**UC3 — Rechercher dans les avis**
- Acteur : Analyste produit
- Scénario : Entrer des mots-clés → Voir la liste des avis correspondants

**UC4 — Surveiller l'application**
- Acteur : Administrateur
- Scénario : Accéder au dashboard monitoring → Voir les logs, alertes, métriques

### Exigences fonctionnelles

| ID | Exigence | Priorité |
|----|----------|----------|
| F1 | Analyser le sentiment d'un texte en < 2s | Haute |
| F2 | Afficher les statistiques par produit | Haute |
| F3 | Rechercher des avis par mots-clés | Moyenne |
| F4 | Analyser plusieurs avis en lot (batch) | Moyenne |
| F5 | Exporter les résultats | Basse |

### Exigences non-fonctionnelles

| ID | Exigence |
|----|----------|
| NF1 | Conformité RGPD (pseudonymisation, durée de conservation) |
| NF2 | Disponibilité > 95% |
| NF3 | Temps de réponse API < 500ms (hors modèle IA) |
| NF4 | Documentation API automatique (OpenAPI/Swagger) |
| NF5 | Authentification API Key sur toutes les routes sensibles |
| NF6 | Conformité OWASP API Top 10 sur les points critiques |
| NF7 | Accessibilité WCAG 2.1 AA pour l'interface Streamlit |
| NF8 | Éco-conception : modèle local CPU, pas de transferts inutiles |

### Sécurité — OWASP API Top 10 (C9, C17)

| ID OWASP | Risque | Implémentation dans le projet |
|----------|--------|-------------------------------|
| A01 | Broken Object Level Authorization | API Key obligatoire sur tous les endpoints sensibles (`X-API-Key`) |
| A02 | Broken Authentication | Clé lue depuis variable d'environnement, jamais hardcodée en clair |
| A03 | Broken Object Property | Validation Pydantic : types, longueurs, valeurs autorisées |
| A04 | Unrestricted Resource Consumption | `limit` max 100 sur `/avis`, `max_items=10` sur batch |
| A05 | Broken Function Level Auth | `/health` public, `/predict` et `/avis` protégés |
| A08 | Security Misconfiguration | Variables d'environnement pour les secrets, pas de `.env` en Git |

### Accessibilité WCAG 2.1 AA

| Critère WCAG | Niveau | Implémentation |
|---|---|---|
| 1.4.3 Contraste des textes | AA | Thème Streamlit par défaut (ratio > 4.5:1) |
| 2.1.1 Accessibilité clavier | A | Tous les composants Streamlit sont navigables |
| 2.4.2 Titre de page | A | `st.set_page_config(page_title="Analyseur de Sentiment")` |
| 3.3.1 Identification des erreurs | A | Messages d'erreur explicites si API indisponible |
| 4.1.2 Nom, rôle, valeur | A | Labels descriptifs sur tous les inputs |

---

## C15 — Architecture technique

### Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    UTILISATEUR (Navigateur)                  │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP (port 8501)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND (Streamlit — app/main.py)             │
│                    http://localhost:8501                      │
└──────────┬──────────────────────────────────┬───────────────┘
           │ POST /predict                      │ GET /avis
           │ (port 8000)                        │ (port 8001)
           ▼                                    ▼
┌─────────────────────┐            ┌─────────────────────────┐
│  API MODÈLE IA      │            │   API DONNÉES           │
│  (FastAPI)          │            │   (FastAPI)             │
│  api_model/main.py  │            │   api_data/main.py      │
│  port 8000          │            │   port 8001             │
└──────────┬──────────┘            └───────────┬─────────────┘
           │                                    │
           ▼                                    ▼
┌─────────────────────┐            ┌─────────────────────────┐
│  MODÈLE HUGGINGFACE │            │   BASE DE DONNÉES       │
│  DistilBERT SST-2   │            │   SQLite (avis.db)      │
│  (local, CPU)       │            │   database/             │
└─────────────────────┘            └─────────────────────────┘
                    ▲                           ▲
                    │                           │
           ┌────────┴───────────────────────────┘
           │         COLLECTE DE DONNÉES
           │         data/collect.py
           │         data/clean.py
           └──────────────────────────────────────
```

### Choix technologiques

| Couche | Technologie | Justification |
|--------|-------------|---------------|
| Frontend | Streamlit | Simple, Python natif, pas de HTML/CSS requis |
| API | FastAPI | Performant, documentation auto (Swagger), validation Pydantic |
| BDD | SQLite | Zéro configuration, fichier unique, parfait pour un projet solo |
| IA | HuggingFace Transformers | Open source, communauté large, modèles pré-entraînés |
| Tests | pytest | Standard Python, simple à écrire |
| CI/CD | GitHub Actions | Gratuit pour repos publics, intégré à GitHub |
| Déploiement | Docker | Portabilité, isolation, standard industrie |

### Flux de données

1. **Collecte** : `data/collect.py` extrait les avis (CSV, API, scraping)
2. **Nettoyage** : `data/clean.py` nettoie et normalise
3. **Stockage** : `database/init_db.py` insère dans SQLite
4. **Exposition** : `api_data/main.py` expose via HTTP REST
5. **Analyse** : `api_model/main.py` analyse le sentiment via DistilBERT
6. **Présentation** : `app/main.py` affiche tout dans Streamlit

### Diagramme de flux de données (DFD)

Le DFD représente les **transformations des données** à travers le système (niveau 1).

```
╔═══════════════════════════════════════════════════════════════════════╗
║                   DFD — Analyseur de Sentiment                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  [SOURCES]          [TRAITEMENT]          [STOCKAGE]   [SORTIE]       ║
║                                                                       ║
║  ┌──────────┐                                                         ║
║  │ CSV      │──┐                                                      ║
║  │ fichier  │  │   ┌────────────┐   ┌──────────────┐                 ║
║  └──────────┘  ├──►│  collect   │──►│   clean.py   │                 ║
║                │   │  .py       │   │ (validation, │                 ║
║  ┌──────────┐  │   │ (agrégat.) │   │  normalise,  │                 ║
║  │ API REST │──┘   └────────────┘   │  RGPD)       │                 ║
║  │ externe  │                       └──────┬───────┘                 ║
║  └──────────┘                              │                          ║
║                                            ▼                          ║
║  ┌──────────┐                     ┌──────────────┐                   ║
║  │ Scraping │──────────────────►  │  init_db.py  │                   ║
║  │ (HTML)   │    (données brutes) │  ───────────►│                   ║
║  └──────────┘                     │  avis.db     │                   ║
║                                   │  (SQLite)    │                   ║
║                                   └──────┬───────┘                   ║
║                                          │                            ║
║                              ┌───────────┴──────────┐                ║
║                              │                       │                ║
║                              ▼                       ▼                ║
║                     ┌──────────────┐       ┌──────────────┐          ║
║                     │ api_data     │       │ api_model    │          ║
║                     │ (GET /avis)  │       │ (POST        │          ║
║                     │  ──────────► │       │  /predict)   │          ║
║                     │ données JSON │       │  ──────────► │          ║
║                     └──────┬───────┘       │ label+score  │          ║
║                            │               └──────┬───────┘          ║
║                            └──────────┬───────────┘                  ║
║                                       ▼                               ║
║                              ┌──────────────────┐                    ║
║                              │  Streamlit       │                    ║
║                              │  app/main.py     │                    ║
║                              │  (agrège et      │                    ║
║                              │   affiche)       │                    ║
║                              └────────┬─────────┘                   ║
║                                       ▼                               ║
║                              ┌──────────────────┐                    ║
║                              │  UTILISATEUR     │                    ║
║                              │  (navigateur)    │                    ║
║                              └──────────────────┘                    ║
╚═══════════════════════════════════════════════════════════════════════╝

Flux de données :
  ──►  Données brutes (textes, notes, sources)
  ──►  Données nettoyées et validées
  ──►  Données stockées (SQLite)
  ──►  Données exposées (JSON via HTTP)
  ──►  Résultats d'analyse (label + score de confiance)
  ──►  Données présentées (tableaux, graphiques)
```

### Preuve de concept (PoC) — Conclusion et décision

**Objectif du PoC :** Valider la faisabilité technique de l'analyse automatique de sentiment sur des avis clients avec un modèle open source local.

**Résultats obtenus :**

| Critère | Résultat | Seuil acceptable |
|---------|----------|-----------------|
| Précision sur données test | ~91% | > 80% |
| Latence P95 (inférence) | < 200ms (CPU) | < 500ms |
| Conformité RGPD | ✅ Totale | Obligatoire |
| Coût d'exploitation | 0 € (open source) | < budget alloué |
| Déploiement Docker | ✅ Fonctionnel | Requis |

**Conclusion PoC :**
La preuve de concept démontre que l'analyse automatique de sentiment sur des avis clients est **techniquement faisable et pertinente** avec la stack choisie (DistilBERT + FastAPI + Streamlit). Les performances dépassent les seuils acceptables, le coût est nul et la conformité RGPD est garantie.

**Recommandation :** ✅ **Poursuivre le projet en production** avec les améliorations suivantes pour une version v2 :
- Passer à CamemBERT pour les avis en français
- Ajouter un fine-tuning sur des données métier réelles
- Migrer vers PostgreSQL si le volume dépasse 100 000 avis

---

## C16 — Coordination et méthode Agile

### Sprints du projet

**Sprint 1 — Données (2 semaines)**
- ✅ Script de collecte CSV + API
- ✅ Script de nettoyage
- ✅ Schéma base de données + init

**Sprint 2 — APIs (2 semaines)**
- ✅ API données (FastAPI)
- ✅ Intégration modèle HuggingFace
- ✅ API modèle avec monitoring

**Sprint 3 — Frontend + Tests (2 semaines)**
- ✅ Application Streamlit (4 pages)
- ✅ Tests automatisés (pytest)
- ✅ Pipeline CI/CD (GitHub Actions)

**Sprint 4 — DevOps + Documentation (1 semaine)**
- ✅ Docker + docker-compose
- ✅ Monitoring et rapports d'incidents
- ✅ Documentation technique

### Rituels Agile / Scrum

**Daily Standup (quotidien, 15 min)**
Chaque matin en début de sprint, le développeur répond à 3 questions :
1. Qu'est-ce que j'ai fait hier ?
2. Qu'est-ce que je fais aujourd'hui ?
3. Y a-t-il des blocages ?

Exemple pour ce projet :
- *Hier : j'ai terminé l'API `/predict` avec authentification*
- *Aujourd'hui : je teste l'API et j'écris les tests pytest*
- *Blocage : la base SQLite ne se crée pas en sandbox Linux — contournement prévu*

**Sprint Review (fin de sprint, 1h)**
Démonstration des fonctionnalités terminées devant le Product Owner / formateur.
Pour ce projet : démonstration de l'application Streamlit avec une analyse en temps réel.
Critères d'acceptation vérifiés : toutes les User Stories du sprint.

**Rétrospective (fin de sprint, 45 min)**
Bilan de l'organisation du sprint, pas des fonctionnalités :
- **Ce qui a bien fonctionné** : découpage des tâches en Issues GitHub, commits conventionnels
- **À améliorer** : estimer la durée des tâches Docker (sous-estimées)
- **Action concrète** : ajouter des tests d'intégration dans le sprint suivant

**Backlog Refinement (milieu de sprint, 30 min)**
Révision et priorisation des prochaines User Stories avec le Product Owner.

**Burndown Chart**
Graphique qui montre l'avancement du sprint : nombre de tâches restantes (axe Y) par jour (axe X).
Idéalement, la courbe descend régulièrement. Si elle stagne, le sprint est en retard.

```
Tâches
restantes
  20 │ *
  16 │   *
  12 │       *                ← Idéal (ligne théorique)
   8 │          *    *
   4 │               *   *
   0 │                     *
      ─────────────────────────▶ Jours (Sprint 2 semaines)
      J1  J3  J5  J7  J9  J10
```

**Vélocité**
Mesure de la quantité de travail réalisée par sprint (en points d'effort).
Sprint 1 : 21 points / Sprint 2 : 18 points / Sprint 3 : 24 points → vélocité moyenne : 21 pts/sprint.
Utilisée pour prédire ce qu'on peut réaliser dans les sprints suivants.

### Outils de gestion de projet

| Outil | Usage |
|-------|-------|
| GitHub | Hébergement du code, Issues, Pull Requests |
| GitHub Projects | Tableau Kanban (Backlog / En cours / Terminé) |
| GitHub Actions | CI/CD automatique |
| Commits conventionnels | `feat:`, `fix:`, `test:`, `docs:` |

### Éco-conception (C17)

Principes **Green IT** appliqués dans ce projet :

| Principe | Implémentation |
|---------|----------------|
| Modèle local (pas de cloud) | DistilBERT tourne en local → 0 transfert réseau par prédiction |
| Modèle léger | DistilBERT (66 Mo) vs BERT-large (340 Mo) → 5× moins de RAM/CPU |
| Inférence CPU | Pas de GPU nécessaire pour ce volume → économie énergie |
| Mise en cache SQLite | Résultats déjà calculés relus en BDD, pas recalculés |
| Pas de polling inutile | Streamlit ne rafraîchit que sur action utilisateur |
| Format de données minimal | JSON léger, pas de payload inutile dans les réponses API |

Ces choix sont détaillés dans `docs/veille_benchmark.md` (section éco-responsabilité).
