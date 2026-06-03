# Wireframes et Parcours Utilisateurs — C14
## Application : Analyseur de Sentiment d'Avis Clients

---

## 1. Flux utilisateur global (User Flow)

```
[Utilisateur arrive sur l'application]
              │
              ▼
    ┌─────────────────┐
    │   Page d'accueil│
    │  (Sidebar nav)  │
    └────────┬────────┘
             │
    ┌────────┼──────────────────────────┐
    │        │                          │
    ▼        ▼                          ▼
┌────────┐ ┌──────────────┐ ┌────────────────────┐
│Analyser│ │   Tableau    │ │  Base de données   │
│un texte│ │  de bord     │ │  (exploration)     │
└───┬────┘ └──────┬───────┘ └─────────┬──────────┘
    │             │                   │
    ▼             ▼                   ▼
┌───────────────────────────────────────────────┐
│              Page Monitoring                  │
│         (Logs API + stats modèle)             │
└───────────────────────────────────────────────┘
```

---

## 2. Wireframes des 4 pages

### Page 1 — Analyser un texte

```
╔══════════════════════════════════════════════════════════════════╗
║  SIDEBAR                  │  🔍 Analyser un avis client          ║
║  ─────────────────────    │  ──────────────────────────────────  ║
║  🎯 Analyseur de Sentiment│                                      ║
║                           │  Saisissez un avis client en anglais ║
║  📡 Statut des services   │  ou en français pour analyser son    ║
║  [IA ✅] [Data ✅]         │  sentiment.                         ║
║                           │                                      ║
║  📑 Navigation            │  ┌──────────────────────────────┐   ║
║  > 🔍 Analyser un texte   │  │ This product is absolutely   │   ║
║    📊 Tableau de bord     │  │ fantastic...                 │   ║
║    🗄️ Base de données     │  │                              │   ║
║    📈 Monitoring          │  └──────────────────────────────┘   ║
║                           │  [    🚀 Analyser    ] (bouton)     ║
║                           │                                      ║
║                           │  ────────────────────────────────── ║
║                           │                                      ║
║                           │  ┌──────────┐ ┌────────┐ ┌───────┐ ║
║                           │  │Sentiment │ │ Temps  │ │Modèle │ ║
║                           │  │😊 Positif│ │ 45 ms  │ │Distil │ ║
║                           │  └──────────┘ └────────┘ └───────┘ ║
║                           │                                      ║
║                           │  Score de confiance :               ║
║                           │  ████████████████░░░░  85.0%        ║
║                           │                                      ║
║                           │  💡 Exemples à tester               ║
║                           │  [📝 This product is amazing!]      ║
║                           │  [📝 Terrible quality, broke...]    ║
╚══════════════════════════════════════════════════════════════════╝
```

**Parcours utilisateur :**
1. L'utilisateur arrive sur la page
2. Il saisit un texte dans la zone de texte (min 5 caractères, max 1000)
3. Il clique sur "Analyser" (bouton désactivé si texte < 5 chars)
4. Un spinner s'affiche pendant l'appel à l'API modèle
5. Le résultat s'affiche : sentiment, score, temps de traitement
6. L'utilisateur peut cliquer sur un exemple prédéfini pour le tester

**Critères d'acceptation (User Story) :**
- *En tant qu'analyste*, je veux saisir un texte *afin de* connaître son sentiment
- Critère : le résultat s'affiche en moins de 3 secondes
- Critère : le score de confiance est visible sous forme de barre de progression
- Accessibilité WCAG 2.1 AA : contrastes suffisants, labels sur tous les inputs

---

### Page 2 — Tableau de bord

```
╔══════════════════════════════════════════════════════════════════╗
║  SIDEBAR                  │  📊 Tableau de bord                  ║
║  (identique)              │  ──────────────────────────────────  ║
║                           │                                      ║
║                           │  Métriques globales                  ║
║                           │  ┌──────────┐ ┌──────────┐ ┌──────┐ ║
║                           │  │Total avis│ │Note moy. │ │%Pos. │ ║
║                           │  │   25     │ │⭐ 3.4/5  │ │😊 44%│ ║
║                           │  └──────────┘ └──────────┘ └──────┘ ║
║                           │                                      ║
║                           │  ── Statistiques par produit ──────  ║
║                           │  ┌─────────────────────────────────┐ ║
║                           │  │Produit     │Nb│Note │%Positifs  │ ║
║                           │  │App. Photo  │5 │⭐3.4 │40%       │ ║
║                           │  │Casque BT   │5 │⭐3.4 │40%       │ ║
║                           │  │Enceinte    │5 │⭐3.4 │40%       │ ║
║                           │  └─────────────────────────────────┘ ║
║                           │                                      ║
║                           │  ── Notes moyennes par produit ───── ║
║                           │  Appareil Photo  ████████░░  3.4    ║
║                           │  Casque BT       ████████░░  3.4    ║
║                           │  Enceinte        ████████░░  3.4    ║
║                           │                                      ║
║                           │  ── Répartition par source ──────── ║
║                           │  [Tableau: amazon/fnac/api]          ║
╚══════════════════════════════════════════════════════════════════╝
```

**Parcours utilisateur :**
1. L'utilisateur arrive sur la page
2. Les métriques se chargent automatiquement depuis l'API données
3. Il visualise les statistiques globales et par produit
4. Les graphiques permettent une comparaison visuelle rapide

---

### Page 3 — Base de données

```
╔══════════════════════════════════════════════════════════════════╗
║  SIDEBAR                  │  🗄️ Exploration des données          ║
║  (identique)              │  ──────────────────────────────────  ║
║                           │                                      ║
║                           │  ┌──────────────┐ ┌──────────────┐  ║
║                           │  │Filtrer par   │ │🔍 Rechercher │  ║
║                           │  │[Tous produits│ │[livraison   ]│  ║
║                           │  │▼            ]│ │              │  ║
║                           │  └──────────────┘ └──────────────┘  ║
║                           │                                      ║
║                           │  ┌────────────────────────────────┐  ║
║                           │  │ID│Avis          │Note│Source   │  ║
║                           │  │1 │Ce produit est│⭐⭐⭐⭐⭐│amazon │  ║
║                           │  │2 │Très déçu...  │⭐   │amazon   │  ║
║                           │  │3 │Bon rapport..│⭐⭐⭐⭐│amazon  │  ║
║                           │  └────────────────────────────────┘  ║
║                           │  50 avis affichés                    ║
║                           │                                      ║
║                           │  🤖 Analyser tous ces avis           ║
║                           │  [Lancer l'analyse IA sur ces avis]  ║
║                           │                                      ║
║                           │  ┌────────────────────────────────┐  ║
║                           │  │Texte    │Label   │Score        │  ║
║                           │  │Ce prod..│POSITIVE│0.89         │  ║
║                           │  │Très déçu│NEGATIVE│0.95         │  ║
║                           │  └────────────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════╝
```

**Parcours utilisateur :**
1. L'utilisateur arrive sur la page
2. Il peut filtrer par produit **ou** rechercher par mots-clés
3. Le tableau se met à jour automatiquement
4. Il peut lancer une analyse IA sur le batch d'avis affichés
5. Les résultats de l'analyse s'affichent dans un second tableau

---

### Page 4 — Monitoring

```
╔══════════════════════════════════════════════════════════════════╗
║  SIDEBAR                  │  📈 Monitoring                       ║
║  (identique)              │  ──────────────────────────────────  ║
║                           │                                      ║
║  ┌──────────────────────┐ │  ┌─────────────────┐ ┌────────────┐ ║
║  │ 🤖 Modèle IA         │ │  │Prédictions tot. │ │Temps moyen │ ║
║  │ ──────────────────── │ │  │      127         │ │   48 ms    │ ║
║  │ Prédictions : 127    │ │  └─────────────────┘ └────────────┘ ║
║  │ Temps moy : 48ms     │ │                                      ║
║  │                      │ │  Répartition des prédictions :      ║
║  │  Positif  ██████ 60% │ │  Positif  ████████████  60%         ║
║  │  Négatif  ████░░ 40% │ │  Négatif  ████████░░░░  40%         ║
║  └──────────────────────┘ │                                      ║
║                           │  📋 Derniers logs API               ║
║  ┌──────────────────────┐ │  ┌──────────────────────────────┐   ║
║  │ 📋 Logs API          │ │  │Endpoint │Meth│Statut│Durée   │   ║
║  │ ──────────────────── │ │  │/predict │POST│ 200  │ 45ms   │   ║
║  │/predict  POST 200    │ │  │/avis    │GET │ 200  │  8ms   │   ║
║  │/avis     GET  200    │ │  │/predict │POST│ 403  │  1ms   │   ║
║  │/predict  POST 403    │ │  └──────────────────────────────┘   ║
║  └──────────────────────┘ │                                      ║
╚══════════════════════════════════════════════════════════════════╝
```

**Parcours utilisateur :**
1. L'administrateur accède à la page monitoring
2. Les statistiques du modèle IA se chargent (total prédictions, temps moyen)
3. Un graphique montre la répartition positif/négatif (détection de drift)
4. Les derniers logs API permettent de détecter les erreurs

---

## 3. Accessibilité (WCAG 2.1 AA)

| Critère | Implémentation |
|---|---|
| **1.4.3 Contraste** | Streamlit utilise un thème avec ratio > 4.5:1 |
| **2.1.1 Clavier** | Tous les composants Streamlit sont navigables au clavier |
| **2.4.2 Titre de page** | `st.set_page_config(page_title="Analyseur de Sentiment")` |
| **3.3.1 Identification des erreurs** | Messages d'erreur explicites si API indisponible |
| **4.1.2 Nom, rôle, valeur** | Labels sur tous les inputs (`st.text_area("Texte de l'avis", ...)`) |
