-- ============================================================
-- schema.sql — C4 : Schéma de la base de données
-- Modélisation conforme au RGPD (Règlement Général sur la
-- Protection des Données)
-- ============================================================

-- ──────────────────────────────────────────
-- TABLE : produits
-- Référentiel des produits analysés
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS produits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT NOT NULL UNIQUE,         -- Nom du produit
    categorie   TEXT,                          -- Ex: "Électronique", "Mode"
    cree_le     TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────
-- TABLE : avis
-- Stockage des avis clients (données personnelles minimisées)
-- RGPD : on ne stocke PAS l'email, l'IP, ni le nom complet
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS avis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,             -- 'amazon', 'fnac', 'api_externe', 'scraping'
    texte           TEXT NOT NULL,             -- Texte de l'avis (max 1000 chars)
    note            INTEGER CHECK(note BETWEEN 1 AND 5),  -- Note de 1 à 5
    date_avis       TEXT,                      -- Date de l'avis (YYYY-MM-DD)
    auteur_pseudo   TEXT,                      -- Pseudo anonymisé (ex: "jea*****")
    produit_id      INTEGER REFERENCES produits(id),
    cree_le         TEXT DEFAULT CURRENT_TIMESTAMP,
    -- RGPD : durée de conservation (on peut purger après 3 ans)
    a_supprimer_le  TEXT                       -- Date prévue de suppression
);

-- ──────────────────────────────────────────
-- TABLE : predictions_sentiment
-- Résultats de l'analyse IA (C11 : monitoring)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS predictions_sentiment (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    avis_id         INTEGER REFERENCES avis(id),
    label           TEXT NOT NULL,             -- 'POSITIVE' ou 'NEGATIVE'
    score           REAL NOT NULL,             -- Score de confiance entre 0 et 1
    modele_utilise  TEXT DEFAULT 'distilbert-base-uncased-finetuned-sst-2-english',
    predit_le       TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────
-- TABLE : logs_api
-- Journalisation des appels API (C20 : monitoring)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS logs_api (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint        TEXT NOT NULL,             -- Ex: '/predict', '/avis'
    methode_http    TEXT NOT NULL,             -- GET, POST, etc.
    statut_http     INTEGER,                   -- 200, 400, 500, etc.
    duree_ms        REAL,                      -- Durée de la requête en ms
    message_erreur  TEXT,                      -- Null si pas d'erreur
    enregistre_le   TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ──────────────────────────────────────────
-- TABLE : consentements_rgpd
-- Traçabilité des consentements (obligatoire RGPD)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS consentements_rgpd (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    auteur_pseudo   TEXT NOT NULL,
    type_donnee     TEXT NOT NULL,             -- 'avis_client'
    consentement    INTEGER DEFAULT 1,         -- 1 = accordé, 0 = refusé
    date_consentement TEXT DEFAULT CURRENT_TIMESTAMP,
    base_legale     TEXT DEFAULT 'intérêt légitime' -- Base légale RGPD
);

-- ──────────────────────────────────────────
-- INDEX pour améliorer les performances des requêtes
-- ──────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_avis_produit ON avis(produit_id);
CREATE INDEX IF NOT EXISTS idx_avis_source ON avis(source);
CREATE INDEX IF NOT EXISTS idx_predictions_avis ON predictions_sentiment(avis_id);
CREATE INDEX IF NOT EXISTS idx_logs_endpoint ON logs_api(endpoint);

-- ──────────────────────────────────────────
-- VUE : avis_avec_sentiment
-- Join pratique pour récupérer avis + prédiction IA
-- ──────────────────────────────────────────
CREATE VIEW IF NOT EXISTS avis_avec_sentiment AS
    SELECT
        a.id,
        a.texte,
        a.note,
        a.source,
        a.date_avis,
        a.auteur_pseudo,
        p.nom AS produit,
        ps.label AS sentiment,
        ps.score AS score_confiance
    FROM avis a
    LEFT JOIN produits p ON a.produit_id = p.id
    LEFT JOIN predictions_sentiment ps ON ps.avis_id = a.id;
