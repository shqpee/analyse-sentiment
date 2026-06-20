# Veille Technologique et Benchmark — E2 (C6, C7, C8)
## Projet : Analyseur de Sentiment d'Avis Clients

---

## C6 — Veille technologique et réglementaire

### 0. Organisation de la veille

**Planification hebdomadaire (à minima 1h/semaine) :**

| Jour | Créneau | Activité de veille |
|------|---------|-------------------|
| Lundi | 8h00–9h00 | Lecture des flux RSS HuggingFace, Papers With Code, arXiv NLP |
| Mercredi | 12h00–12h30 | Newsletter AI Weekly + suivi LinkedIn (chercheurs NLP) |
| Vendredi | 17h00–17h30 | Veille réglementaire (CNIL, AI Act updates) |

**Outils d'agrégation utilisés :**

| Outil | Type | Sources ciblées | Coût |
|-------|------|-----------------|------|
| Feedly (plan gratuit) | Agrégateur RSS | HuggingFace Blog, arXiv, InfoQ, Towards Data Science | Gratuit |
| Newsletter "AI Weekly" | Email hebdomadaire | Actualités IA grand public | Gratuit |
| GitHub Watch | Notifications Git | Dépôts HuggingFace Transformers, FastAPI, Streamlit | Gratuit |
| CNIL.fr flux RSS | RSS réglementaire | Publications CNIL, RGPD, AI Act | Gratuit |
| LinkedIn | Réseau professionnel | Chercheurs NLP, communauté Simplon, Yann LeCun | Gratuit |

**Format des synthèses :**
Les synthèses de veille sont rédigées en Markdown (.md) hébergé dans le dépôt Git. Ce format respecte les recommandations d'accessibilité (Association Valentin Haüy) : texte structuré, titres hiérarchiques (H1/H2/H3), pas d'information transmise uniquement par la couleur.

### 1. Veille sur les technologies IA de traitement du langage

**Dernières avancées (2023-2024) :**

**Transformers et modèles de langage**
Les architectures Transformer (BERT, GPT, T5) dominent le NLP. HuggingFace s'est imposé comme la plateforme de référence avec plus de 500 000 modèles disponibles. DistilBERT, la version allégée de BERT, offre 97% des performances pour 60% du poids.

**LLMs (Large Language Models)**
GPT-4, Claude, Gemini permettent désormais une analyse de sentiment nuancée, avec compréhension du contexte et du sarcasme. Mais leur coût (API payante) les rend moins adaptés pour une analyse en volume.

**Évolution vers le multilinguisme**
Les modèles comme CamemBERT (BERT entraîné sur du français) permettent d'analyser directement des avis en français sans traduction préalable.

### 2. Veille réglementaire — IA et données personnelles

**Règlement Général sur la Protection des Données (RGPD)**
- En vigueur depuis mai 2018 dans l'UE
- Oblige à minimiser les données collectées (ne collecter que le nécessaire)
- Droit à l'oubli : possibilité de supprimer ses données sur demande
- Durée de conservation limitée (notre projet : 3 ans)
- Base légale pour le traitement : consentement ou intérêt légitime

**AI Act (Règlement européen sur l'IA)**
- Adopté en 2024, applicable progressivement
- Notre application : système IA à **risque minimal** (pas de décision impactant des droits)
- Obligations : transparence, traçabilité des prédictions

**Application dans notre projet :**
- Pseudonymisation des auteurs (user_42 → "use*****")
- Durée de conservation enregistrée en BDD (champ `a_supprimer_le`)
- Traçabilité des consentements (table `consentements_rgpd`)
- Logs des accès API pour audit

---

## C7 — Benchmark des services IA de sentiment

### Services évalués

| Critère | HuggingFace DistilBERT | AWS Comprehend | Google Natural Language API | Azure Text Analytics |
|---------|----------------------|----------------|---------------------------|---------------------|
| **Prix** | Gratuit (open source) | ~0.01$/1000 unités | ~0.001$/requête | ~0.001$/requête |
| **Précision** | ~91% (SST-2) | ~85-90% | ~88-92% | ~88-90% |
| **Langues** | Anglais | 12 langues | 10 langues | 10 langues |
| **Latence** | 50-200ms (local) | 200-500ms (API) | 100-300ms (API) | 150-400ms (API) |
| **Confidentialité** | Totale (local) | Données envoyées à AWS | Données envoyées à Google | Données envoyées à Microsoft |
| **Intégration** | Python natif | SDK boto3 | SDK google-cloud | SDK azure-ai |
| **Mise en place** | pip install | Compte AWS requis | Compte GCP requis | Compte Azure requis |
| **Conformité RGPD** | ✅ Optimal (pas de transfert) | ⚠️ Transfert hors EU possible | ⚠️ Transfert hors EU possible | ⚠️ Transfert hors EU possible |

### Démarche éco-responsable des services étudiés (C7)

Le benchmark intègre systématiquement l'impact environnemental de chaque solution.

| Service | Empreinte carbone | Éco-responsabilité |
|---------|-------------------|-------------------|
| **HuggingFace DistilBERT (local)** | Très faible — calcul sur CPU local, pas de transfert réseau | ✅ Optimal : aucune énergie gaspillée en transit |
| **AWS Comprehend** | Moyenne — data centers AWS certifiés 100% énergie renouvelable depuis 2025, mais transfert réseau | ⚠️ Dépend de la région AWS choisie |
| **Google NLP** | Moyenne — Google vise la neutralité carbone, mais appels API = latence + énergie réseau | ⚠️ Bonne démarche globale, mais transferts |
| **Azure Text Analytics** | Moyenne — Microsoft engage sur la neutralité carbone en 2030 | ⚠️ Similaire à Google |

**Principe éco-conception retenu** (Green IT) :
- Modèle local → **zéro appel réseau** → économie d'énergie réseau estimée à ~0.001 kWh/1000 requêtes
- DistilBERT (66M paramètres) vs BERT-large (340M) → **utilise 5× moins de RAM** et de CPU
- Inférence sur CPU plutôt que GPU → économie d'énergie pour ce cas d'usage à faible volume

### Services non étudiés et raisons d'exclusion

| Service | Raison d'exclusion |
|---------|-------------------|
| **OpenAI GPT-4 / GPT-3.5** | Coût API élevé (~0.002$/token), données envoyées hors UE → non-conformité RGPD |
| **Mistral AI API** | Service en beta au moment du projet, documentation instable, pas adapté pour analyse de sentiment binaire simple |
| **Cohere API** | Coût non nul, données hébergées hors UE, moins de documentation communautaire |
| **TextBlob / VADER** | Bibliothèques basées sur des règles (non ML), précision < 75% sur des avis informels |
| **spaCy TextCategorizer** | Nécessite un entraînement from scratch avec nos données — complexité disproportionnée pour un MVP |

**Justification du périmètre étudié :** Le benchmark se concentre sur les 4 leaders du marché des services cloud NLP + la solution open source de référence (HuggingFace), couvrant ainsi plus de 90% des solutions utilisées en entreprise.

### Analyse et choix

**Service retenu : HuggingFace + DistilBERT**

**Justification :**
1. **Coût nul** : aucun coût API, modèle exécuté localement
2. **Confidentialité maximale** : les avis clients ne quittent jamais nos serveurs → conformité RGPD parfaite
3. **Performances suffisantes** : 91% de précision pour une analyse binaire (positif/négatif)
4. **Impact environnemental minimal** : zéro réseau, modèle léger, inférence CPU
5. **Déploiement simple** : une seule ligne de code (`pipeline("sentiment-analysis")`)
6. **Communauté active** : mises à jour régulières, documentation excellente

**Limitation identifiée :**
Le modèle DistilBERT est entraîné en anglais. Pour les avis en français, nous utilisons soit la traduction automatique, soit le modèle CamemBERT (alternative possible).

---

## C8 — Configuration du service IA

### Paramètres de configuration du modèle

```python
from transformers import pipeline

# Configuration du modèle
modele = pipeline(
    task="sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    device=-1,          # -1 = CPU, 0 = GPU si disponible
    max_length=512,     # Limite du tokenizer
    truncation=True,    # Tronquer si texte trop long
)
```

### Choix du modèle alternatif pour le français

```python
# Pour les avis en français :
modele_fr = pipeline(
    task="text-classification",
    model="tblard/tf-allocine",  # Fine-tuné sur des critiques de films français
)
```

### Paramètres de performance

| Paramètre | Valeur | Explication |
|-----------|--------|-------------|
| `device=-1` | CPU | Pas besoin de GPU pour ce cas d'usage |
| `batch_size=8` | 8 | Traitement de 8 textes simultanément |
| `max_length=512` | 512 tokens | Limite maximale du modèle |
| `truncation=True` | Activé | Couper les textes trop longs |

### Monitoring du modèle (C11)

Métriques surveillées :
- Nombre de prédictions par heure
- Temps de réponse moyen et P95
- Répartition POSITIVE/NEGATIVE (pour détecter un drift)
- Taux d'erreurs

**Drift de données :** Si la proportion de prédictions positives/négatives change fortement par rapport à la baseline, cela peut indiquer que le modèle ne correspond plus aux nouvelles données. Action corrective : re-fine-tuner ou changer de modèle.
