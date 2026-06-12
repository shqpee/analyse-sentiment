"""
app/main.py — C10, C17 : Application Streamlit (Frontend)
==========================================================
Application web qui intègre :
  - L'API Données (http://localhost:8001) pour lire les avis
  - L'API Modèle IA (http://localhost:8000) pour analyser le sentiment
    → sert le modèle XGBoost (TF-IDF) entraîné EN FRANÇAIS

Authentification : une clé API (header X-API-Key) est envoyée à chaque appel.
La clé est saisie dans la barre latérale (ou lue depuis la variable
d'environnement API_KEY par défaut).

Compétences couvertes :
  - C9   : Consommer une API sécurisée (authentification par clé)
  - C10  : Intégrer une API IA dans une application
  - C17  : Développer des composants d'application

Lancer : streamlit run app/main.py
"""

import streamlit as st
import requests
import pandas as pd
import os

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
API_MODELE_URL = os.environ.get("API_MODELE_URL", "http://localhost:8000")
API_DONNEES_URL = os.environ.get("API_DONNEES_URL", "http://localhost:8001")

# Clé API par défaut (lue depuis l'environnement) ; modifiable dans la sidebar.
API_KEY_DEFAUT = os.environ.get("API_KEY", "dev-secret-key-change-in-production")

st.set_page_config(
    page_title="Analyseur de Sentiment (FR)",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
# AUTHENTIFICATION
# ─────────────────────────────────────────────
def cle_api() -> str:
    """Retourne la clé API courante (saisie dans la sidebar, sinon valeur par défaut)."""
    return st.session_state.get("api_key", API_KEY_DEFAUT)


def headers_auth() -> dict:
    """Header d'authentification envoyé à chaque appel API."""
    return {"X-API-Key": cle_api()}


# ─────────────────────────────────────────────
# FONCTIONS D'APPEL AUX APIs
# ─────────────────────────────────────────────
def appeler_api(url: str, methode: str = "GET", donnees: dict = None) -> dict | None:
    """
    Appel générique à une API REST.
    Envoie automatiquement la clé API dans le header X-API-Key.
    Gère les erreurs réseau / authentification et retourne None en cas d'échec.
    """
    try:
        if methode == "GET":
            response = requests.get(url, headers=headers_auth(), timeout=10)
        else:
            response = requests.post(url, json=donnees, headers=headers_auth(), timeout=30)

        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            st.error("🔒 Authentification refusée : vérifiez la clé API dans la barre latérale.")
        else:
            st.error(f"Erreur API {e.response.status_code} : {e.response.text}")
        return None
    except Exception as e:
        st.error(f"Erreur inattendue : {e}")
        return None


def verifier_apis():
    """Vérifie que les deux APIs sont accessibles (le /health est public)."""
    modele_ok = appeler_api(f"{API_MODELE_URL}/health") is not None
    donnees_ok = appeler_api(f"{API_DONNEES_URL}/health") is not None
    return modele_ok, donnees_ok


# ─────────────────────────────────────────────
# BARRE LATÉRALE
# ─────────────────────────────────────────────
def afficher_sidebar():
    """Barre latérale : authentification, statut des services et navigation."""
    with st.sidebar:
        st.title("Analyseur de Sentiment")
        st.caption("Modèle : XGBoost (TF-IDF) — entraîné en français")
        st.markdown("---")

        # Authentification (clé API)
        st.subheader("🔒 Authentification")
        if "api_key" not in st.session_state:
            st.session_state["api_key"] = API_KEY_DEFAUT
        st.text_input(
            "Clé API",
            type="password",
            key="api_key",
            help="Clé envoyée dans le header X-API-Key à chaque appel.",
        )

        st.markdown("---")

        # Statut des APIs
        st.subheader("Statut des services")
        modele_ok, donnees_ok = verifier_apis()

        col1, col2 = st.columns(2)
        with col1:
            if modele_ok:
                st.success("IA ✅")
            else:
                st.error("IA ❌")
        with col2:
            if donnees_ok:
                st.success("Data ✅")
            else:
                st.error("Data ❌")

        if not modele_ok or not donnees_ok:
            st.warning(
                "⚠️ Une ou plusieurs APIs sont hors ligne.\n\n"
                "Lancez les services :\n"
                "```\ndocker compose up\n```"
            )

        st.markdown("---")

        # Navigation
        st.subheader("Navigation")
        page = st.radio(
            "Page",
            ["Analyser un texte", "Tableau de bord"],
            label_visibility="collapsed",
        )
        return page


# ─────────────────────────────────────────────
# PAGE 1 — ANALYSE D'UN TEXTE
# ─────────────────────────────────────────────
def page_analyser_texte():
    st.header("Analyser un avis client")
    st.markdown("Saisissez un avis client **en français** pour analyser son sentiment.")

    texte = st.text_area(
        "Texte de l'avis",
        placeholder="Ex : Ce produit est vraiment excellent, je le recommande vivement !",
        height=150,
        max_chars=1000,
    )

    analyser = st.button("Analyser", type="primary", disabled=len(texte) < 5)

    if analyser and len(texte) >= 5:
        with st.spinner("Analyse en cours..."):
            resultat = appeler_api(
                f"{API_MODELE_URL}/predict",
                methode="POST",
                donnees={"texte": texte},
            )

        if resultat:
            st.markdown("---")
            sentiment = resultat.get("label", "UNKNOWN")
            score = resultat.get("score", 0)
            duree = resultat.get("duree_ms", 0)

            col1, col2, col3 = st.columns(3)
            with col1:
                if sentiment == "POSITIVE":
                    st.metric("Sentiment", "😊 Positif")
                    st.success(f"Confiance : **{score * 100:.1f}%**")
                else:
                    st.metric("Sentiment", "😞 Négatif")
                    st.error(f"Confiance : **{score * 100:.1f}%**")
            with col2:
                st.metric("Temps de traitement", f"{duree:.0f} ms")
            with col3:
                st.metric("Modèle utilisé", "XGBoost (FR)")

            st.markdown("**Score de confiance :**")
            st.progress(score, text=f"{score * 100:.1f}%")
        else:
            st.warning("L'API modèle est indisponible (port 8000) ou la clé API est invalide.")


# ─────────────────────────────────────────────
# PAGE 2 — TABLEAU DE BORD
# ─────────────────────────────────────────────
def page_tableau_de_bord():
    st.header("Tableau de bord")

    stats = appeler_api(f"{API_DONNEES_URL}/statistiques")
    stats_sources = appeler_api(f"{API_DONNEES_URL}/statistiques/sources")

    if not stats:
        st.warning("API données indisponible.")
        return

    st.subheader("Métriques globales")
    total_avis = sum(s["nb_avis"] for s in stats)
    note_globale = round(sum(s["note_moyenne"] * s["nb_avis"] for s in stats) / total_avis, 2)
    pct_positifs = round(sum(s["nb_positifs"] for s in stats) / total_avis * 100, 1)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total d'avis", total_avis)
    col2.metric("Note moyenne", f"⭐ {note_globale}/5")
    col3.metric("Avis positifs", f"😊 {pct_positifs}%")

    st.markdown("---")
    st.subheader("Statistiques par produit")
    df_stats = pd.DataFrame(stats)
    df_affichage = df_stats[["produit", "nb_avis", "note_moyenne", "pct_positifs"]].copy()
    df_affichage.columns = ["Produit", "Nb Avis", "Note Moyenne", "% Positifs"]
    df_affichage["Note Moyenne"] = df_affichage["Note Moyenne"].apply(lambda x: f"⭐ {x}")
    df_affichage["% Positifs"] = df_affichage["% Positifs"].apply(lambda x: f"{x}%")
    st.dataframe(df_affichage, use_container_width=True, hide_index=True)

    st.subheader("Notes moyennes par produit")
    chart_data = pd.DataFrame({
        "Produit": [s["produit"] for s in stats],
        "Note Moyenne": [s["note_moyenne"] for s in stats],
    })
    st.bar_chart(chart_data.set_index("Produit"))

    if stats_sources:
        st.markdown("---")
        st.subheader("Répartition par source")
        st.dataframe(pd.DataFrame(stats_sources), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# POINT D'ENTRÉE PRINCIPAL
# ─────────────────────────────────────────────
def main():
    page = afficher_sidebar()
    if page == "Analyser un texte":
        page_analyser_texte()
    elif page == "Tableau de bord":
        page_tableau_de_bord()


if __name__ == "__main__":
    main()
