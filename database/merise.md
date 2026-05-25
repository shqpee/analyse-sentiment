# Modélisation Merise — C4
## Projet : Analyseur de Sentiment d'Avis Clients

---

## 1. MCD — Modèle Conceptuel de Données

Le MCD représente les entités du domaine métier et leurs associations, **indépendamment** de toute
considération technique ou informatique.

```
┌─────────────────┐         ┌──────────────────────────────┐         ┌──────────────────┐
│    UTILISATEUR  │         │            AVIS              │         │     PRODUIT      │
│─────────────────│         │──────────────────────────────│         │──────────────────│
│ pseudo          │  rédige │ texte                        │ concerne│ nom              │
│ (anonymisé)     ├─────────┤ note (1-5)                   ├─────────┤ catégorie        │
│                 │  0,N    │ date                         │  1,1    │                  │
└─────────────────┘         │ source                       │         └──────────────────┘
                             └──────────────────────────────┘
                                          │ fait l'objet de
                                          │ 0,1
                                          ▼
                             ┌──────────────────────────────┐
                             │   PREDICTION_SENTIMENT       │
                             │──────────────────────────────│
                             │ label (POSITIVE/NEGATIVE)    │
                             │ score (0.0 – 1.0)            │
                             │ date_prediction              │
                             │ modele_utilise               │
                             └──────────────────────────────┘

┌─────────────────┐
│  CONSENTEMENT   │
│─────────────────│   concerne
│ type_donnee     ├──────────────── UTILISATEUR (1,1)
│ accordé (bool)  │   1,N
│ base_légale     │
│ date            │
└─────────────────┘

┌─────────────────┐
│    LOG_API      │
│─────────────────│
│ endpoint        │   (entité technique — pas de relation métier directe)
│ methode_http    │
│ statut_http     │
│ duree_ms        │
│ date            │
└─────────────────┘
```

### Cardinalités expliquées

| Association | Sens | Cardinalité | Signification |
|---|---|---|---|
| UTILISATEUR **rédige** AVIS | 1 utilisateur / N avis | (0,N) | Un utilisateur peut rédiger 0 ou plusieurs avis |
| AVIS **concerne** PRODUIT | 1 avis / 1 produit | (1,1) | Un avis concerne obligatoirement 1 produit |
| AVIS **fait l'objet de** PRÉDICTION | 1 avis / 0 ou 1 prédiction | (0,1) | Un avis peut avoir 0 ou 1 prédiction IA |
| CONSENTEMENT **concerne** UTILISATEUR | 1 consentement / 1 utilisateur | (1,1) | Un consentement est lié à 1 utilisateur |

---

## 2. MLD — Modèle Logique de Données

Le MLD traduit le MCD en tables relationnelles. Les clés primaires (**PK**) et étrangères (*FK*)
sont explicitement indiquées.

```
produits (#id_produit, nom, categorie, cree_le)

utilisateurs (#pseudo_anonymise, date_creation)
  → Note RGPD : pas de données personnelles identifiantes stockées

avis (#id_avis, texte, note, date_avis, source, a_supprimer_le,
      *pseudo_anonymise → utilisateurs,
      *id_produit       → produits)

predictions_sentiment (#id_prediction, label, score, modele_utilise, predit_le,
                       *id_avis → avis)

consentements_rgpd (#id_consentement, type_donnee, consentement, base_legale,
                    date_consentement,
                    *pseudo_anonymise → utilisateurs)

logs_api (#id_log, endpoint, methode_http, statut_http, duree_ms,
          message_erreur, enregistre_le)
```

### Règles d'intégrité

| Règle | Table | Contrainte |
|---|---|---|
| La note doit être entre 1 et 5 | avis | `CHECK(note BETWEEN 1 AND 5)` |
| Le score de confiance est entre 0 et 1 | predictions_sentiment | `CHECK(score BETWEEN 0 AND 1)` |
| Le label est POSITIVE ou NEGATIVE | predictions_sentiment | `CHECK(label IN ('POSITIVE','NEGATIVE'))` |
| Le texte ne peut pas être vide | avis | `NOT NULL` + vérification longueur > 10 |
| La suppression d'un produit ne supprime pas les avis | avis | `ON DELETE RESTRICT` |

---

## 3. MPD — Modèle Physique de Données (SQLite)

Le MPD correspond aux instructions SQL de création effectives (voir `schema.sql`).
SQLite est choisi pour sa légèreté — pour un déploiement en production avec plusieurs
utilisateurs simultanés, PostgreSQL serait préférable.

### Justification des types SQLite

| Type SQLite | Équivalent SQL standard | Utilisation |
|---|---|---|
| `INTEGER` | INT | Identifiants, notes |
| `TEXT` | VARCHAR / TEXT | Textes, dates (ISO 8601), labels |
| `REAL` | FLOAT / DOUBLE | Scores de confiance |
| `AUTOINCREMENT` | SERIAL | Génération automatique des IDs |

### Conformité RGPD du schéma

| Principe RGPD | Implémentation dans le schéma |
|---|---|
| Minimisation des données | Pas d'email, d'IP ni de nom complet stocké |
| Durée de conservation | Champ `a_supprimer_le` dans la table `avis` |
| Traçabilité | Table `consentements_rgpd` avec `base_legale` |
| Droit à l'oubli | Procédure : `DELETE FROM avis WHERE a_supprimer_le < date('now')` |
| Pseudonymisation | Pseudos tronqués : `jean.dupont` → `jea*****` |

---

## 4. Registre des traitements de données personnelles (RGPD Art. 30)

Conformément à l'article 30 du RGPD, tout responsable de traitement doit tenir un registre des activités de traitement.

| # | Traitement | Finalité | Base légale | Données concernées | Durée | Destinataires |
|---|-----------|---------|------------|-------------------|-------|---------------|
| T1 | Collecte d'avis clients | Analyse de sentiment pour améliorer les produits | Intérêt légitime (Art. 6.1.f) | Texte d'avis, note, pseudo anonymisé | 3 ans | Équipe produit |
| T2 | Pseudonymisation des auteurs | Protection de l'identité | Obligation légale RGPD | Pseudo → `jea*****` | Permanent | Aucun tiers |
| T3 | Consentements | Traçabilité des bases légales | Consentement (Art. 6.1.a) | Type données, date, accord booléen | 3 ans + 1 an | DPO |
| T4 | Logs d'accès API | Sécurité et audit | Intérêt légitime (Art. 6.1.f) | Endpoint, statut HTTP, durée (pas d'IP) | 30 jours | Admin technique |
| T5 | Prédictions IA | Amélioration du modèle | Intérêt légitime | Label POSITIVE/NEGATIVE, score | 1 an | Équipe data |

**Responsable du traitement :** Projet RNCP37827 — Analyseur de Sentiment

---

## 5. Procédures de tri et de conformité RGPD

### Procédure 1 — Suppression automatique des données expirées (mensuelle)

```sql
-- Supprimer les avis dont la durée de conservation est dépassée
DELETE FROM avis WHERE a_supprimer_le < date('now');

-- Supprimer les prédictions orphelines
DELETE FROM predictions_sentiment
WHERE id_avis NOT IN (SELECT id_avis FROM avis);

-- Supprimer les consentements expirés
DELETE FROM consentements_rgpd
WHERE date_consentement < date('now', '-3 years');
```

**Fréquence :** Mensuelle | **Responsable :** Administrateur technique

### Procédure 2 — Exercice du droit à l'oubli (sur demande, délai 72h)

```sql
-- Supprimer toutes les données d'un utilisateur
DELETE FROM avis WHERE pseudo_anonymise = ?;
DELETE FROM consentements_rgpd WHERE pseudo_anonymise = ?;
DELETE FROM utilisateurs WHERE pseudo_anonymise = ?;
```

### Procédure 3 — Vérification de conformité (trimestrielle)

- [ ] Vérifier que `logs_api` ne contient aucune donnée personnelle (IP, email)
- [ ] Vérifier que `a_supprimer_le` est renseigné pour tous les avis
- [ ] Confirmer que la pseudonymisation fonctionne (`jea*****` et non nom complet)
- [ ] Mettre à jour ce registre si de nouveaux traitements ont été ajoutés
