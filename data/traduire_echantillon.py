"""
traduire_echantillon.py — Traduit EN→FR l'intégralité de l'échantillon d'entraînement
======================================================================================
Construit l'échantillon équilibré utilisé par XGBoost (notebook 8.2) et traduit
**tous** les avis anglais en français, en garantissant zéro anglais résiduel :

  1. batch de 50 (rapide)
  2. retry par item sur les lots/éléments en échec
  3. les avis réellement intraduisibles (après retries) sont retirés et comptés

Produit le cache `data/df_final_fr.csv` (colonnes + `texte_fr` + `label`),
réutilisé tel quel par le notebook xgboost_sentiment_page.

Lancer : python data/traduire_echantillon.py [--par-classe 1000]
"""

import argparse
import os
import re
import sys
import time

import pandas as pd
from deep_translator import GoogleTranslator

# Garde anti-crash d'encodage sur la console Windows (cp1252) : on force UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ICI = os.path.dirname(__file__)
CSV_FR = os.path.join(ICI, "sample_reviews2.csv")   # 25 avis déjà en français
CSV_EN = os.path.join(ICI, "sample_reviews.csv")    # avis Amazon en anglais
CACHE_FR = os.path.join(ICI, "df_final_fr.csv")     # sortie (cache du notebook)
RANDOM_STATE = 42


def _nettoyer(txt: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", str(txt))   # retire le HTML (<br />, ...)
    return re.sub(r"\s+", " ", txt).strip()


def construire_echantillon(par_classe: int) -> pd.DataFrame:
    """Reproduit la préparation du notebook : concat FR+EN, label binaire, sous-échantillon équilibré."""
    df_fr = pd.read_csv(CSV_FR)[["texte", "note"]].copy()
    df_fr["langue"] = "fr"

    df_en = pd.read_csv(CSV_EN, low_memory=False)
    df_en = df_en.rename(columns={"Text": "texte", "Score": "note"})[["texte", "note"]].copy()
    df_en["langue"] = "en"

    d = pd.concat([df_fr, df_en], ignore_index=True)
    d["note"] = pd.to_numeric(d["note"], errors="coerce")
    d = d[d["note"] != 3].dropna(subset=["note", "texte"])      # on retire la note neutre (3)
    d["label"] = (d["note"] >= 4).astype(int)                    # >=4 positif, <=2 négatif
    d["texte"] = d["texte"].map(_nettoyer)
    d = d[d["texte"].str.len() > 0]

    pos = d[d.label == 1].sample(n=min(par_classe, int((d.label == 1).sum())), random_state=RANDOM_STATE)
    neg = d[d.label == 0].sample(n=min(par_classe, int((d.label == 0).sum())), random_state=RANDOM_STATE)
    ech = pd.concat([pos, neg]).sample(frac=1, random_state=RANDOM_STATE).reset_index(drop=True)
    print(f"Échantillon équilibré : {len(ech)} lignes | {ech['label'].value_counts().to_dict()}")
    print(f"  → à traduire (anglais) : {int(ech['langue'].eq('en').sum())} | déjà FR : {int(ech['langue'].eq('fr').sum())}")
    return ech


def traduire_tout(textes: list[str]) -> list[str]:
    """Traduit EN→FR ; renvoie None pour les avis restés intraduisibles après retries."""
    tr = GoogleTranslator(source="en", target="fr")
    out: list = [None] * len(textes)

    # Passe 1 — par lots de 50 (rapide)
    for i in range(0, len(textes), 50):
        idx = list(range(i, min(i + 50, len(textes))))
        lot = [textes[j][:4900] for j in idx]
        try:
            trad = tr.translate_batch(lot)
            for k, j in enumerate(idx):
                out[j] = trad[k] if k < len(trad) else None
        except Exception as e:
            print(f"  ⚠️ lot {i}-{i+len(idx)} en échec ({type(e).__name__}) → retry par item")
        print(f"  …{min(i+50, len(textes))}/{len(textes)} traités", end="\r")
        time.sleep(0.3)
    print()

    # Passe 2 — retry individuel sur les éléments encore vides
    restants = [j for j in range(len(textes)) if not (out[j] and str(out[j]).strip())]
    if restants:
        print(f"  Retry par item sur {len(restants)} avis…")
    for n, j in enumerate(restants, 1):
        for _ in range(3):
            try:
                t = tr.translate(textes[j][:4900])
                if t and t.strip():
                    out[j] = t
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if n % 20 == 0:
            print(f"  …retry {n}/{len(restants)}", end="\r")
    print()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--par-classe", type=int, default=1000, help="Nombre d'avis par classe")
    args = parser.parse_args()

    print("=" * 64)
    print("  TRADUCTION EN→FR DE L'ÉCHANTILLON D'ENTRAÎNEMENT")
    print("=" * 64)

    ech = construire_echantillon(args.par_classe)

    masque_en = ech["langue"].eq("en")
    ech["texte_fr"] = ech["texte"]  # les avis FR restent inchangés
    t0 = time.time()
    traductions = traduire_tout(ech.loc[masque_en, "texte"].tolist())
    ech.loc[masque_en, "texte_fr"] = traductions
    print(f"Traduction terminée en {time.time()-t0:.0f}s")

    # Garantie « zéro anglais résiduel » : on retire les avis non traduits
    avant = len(ech)
    non_traduits = ech["texte_fr"].isna() | (ech["texte_fr"].astype(str).str.strip() == "")
    if non_traduits.any():
        print(f"⚠️ {int(non_traduits.sum())} avis intraduisibles après retries → retirés")
        ech = ech[~non_traduits].reset_index(drop=True)

    ech.to_csv(CACHE_FR, index=False)
    print("=" * 64)
    print(f"✅ {len(ech)} avis 100% en français écrits dans : {CACHE_FR}")
    print(f"   (retirés : {avant - len(ech)}) | répartition labels : {ech['label'].value_counts().to_dict()}")
    print("   Le notebook xgboost_sentiment_page réutilisera ce cache automatiquement.")
    print("=" * 64)


if __name__ == "__main__":
    main()
