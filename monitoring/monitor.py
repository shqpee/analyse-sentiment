"""
monitor.py — C20 : Monitoring et journalisation de l'application
=================================================================
Ce module gère la surveillance de l'application en production :
- Logs structurés (avec niveaux : INFO, WARNING, ERROR)
- Alertes automatiques si les erreurs dépassent un seuil
- Rapport d'état périodique

Compétences couvertes :
  - C20 : Surveiller l'application et journaliser les événements
  - C21 : Détecter et résoudre les incidents techniques

Lancer en surveillance continue : python monitoring/monitor.py
"""

import sys
import os
import logging
import time
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database import queries


# ─────────────────────────────────────────────
# CONFIGURATION DU LOGGER
# ─────────────────────────────────────────────

def configurer_logger(nom: str = "avis-sentiment", fichier_log: str = "app.log") -> logging.Logger:
    """
    Configure un logger qui écrit à la fois dans :
    - La console (affichage en temps réel)
    - Un fichier log (pour l'historique)
    """
    logger = logging.getLogger(nom)
    logger.setLevel(logging.DEBUG)

    # Format des messages de log
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Handler fichier
    dossier_logs = os.path.dirname(__file__)
    chemin_log = os.path.join(dossier_logs, fichier_log)
    file_handler = logging.FileHandler(chemin_log, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)  # Tout enregistrer dans le fichier
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Logger global de l'application
logger = configurer_logger()


# ─────────────────────────────────────────────
# MÉTRIQUES ET ALERTES (C20)
# ─────────────────────────────────────────────

class MonitoringApp:
    """
    Classe de monitoring qui surveille l'état de l'application.
    Elle lit les logs de la BDD et génère des alertes si nécessaire.
    """

    SEUIL_ERREURS = 5       # Alerte si plus de 5 erreurs en 1 heure
    SEUIL_LATENCE_MS = 2000 # Alerte si temps de réponse > 2 secondes

    def __init__(self):
        self.alertes_actives = []

    def generer_rapport(self) -> dict:
        """
        Génère un rapport d'état complet de l'application.
        Inspecte les logs de la BDD pour calculer des métriques.
        """
        try:
            logs = queries.get_logs_recents(limit=100)
        except Exception as e:
            logger.error(f"Impossible de lire les logs BDD : {e}")
            return {"erreur": str(e)}

        if not logs:
            return {"message": "Aucun log disponible", "statut": "unknown"}

        # Calculer les métriques
        total_requetes = len(logs)
        erreurs = [l for l in logs if l.get("statut_http", 200) >= 500]
        warnings = [l for l in logs if 400 <= l.get("statut_http", 200) < 500]
        latences = [l.get("duree_ms", 0) for l in logs if l.get("duree_ms")]

        taux_erreurs = len(erreurs) / total_requetes * 100 if total_requetes > 0 else 0
        latence_moyenne = sum(latences) / len(latences) if latences else 0
        latence_max = max(latences) if latences else 0

        rapport = {
            "horodatage": datetime.now().isoformat(),
            "statut": "healthy",
            "metriques": {
                "total_requetes": total_requetes,
                "nb_erreurs_5xx": len(erreurs),
                "nb_erreurs_4xx": len(warnings),
                "taux_erreurs_pct": round(taux_erreurs, 2),
                "latence_moyenne_ms": round(latence_moyenne, 2),
                "latence_max_ms": round(latence_max, 2),
            },
            "alertes": [],
        }

        # Générer des alertes si nécessaire
        if len(erreurs) >= self.SEUIL_ERREURS:
            alerte = f"ALERTE : {len(erreurs)} erreurs 5xx détectées !"
            rapport["alertes"].append(alerte)
            rapport["statut"] = "degraded"
            logger.warning(alerte)

        if latence_max > self.SEUIL_LATENCE_MS:
            alerte = f"ALERTE : Latence maximale élevée ({latence_max:.0f}ms > {self.SEUIL_LATENCE_MS}ms)"
            rapport["alertes"].append(alerte)
            rapport["statut"] = "degraded"
            logger.warning(alerte)

        return rapport

    def afficher_rapport(self):
        """Affiche le rapport formaté dans la console."""
        rapport = self.generer_rapport()

        print("\n" + "=" * 60)
        print(f"  RAPPORT DE MONITORING — {rapport.get('horodatage', 'N/A')}")
        print("=" * 60)

        metriques = rapport.get("metriques", {})
        print(f"  Statut global    : {rapport.get('statut', 'unknown').upper()}")
        print(f"  Total requêtes   : {metriques.get('total_requetes', 0)}")
        print(f"  Erreurs 5xx      : {metriques.get('nb_erreurs_5xx', 0)}")
        print(f"  Erreurs 4xx      : {metriques.get('nb_erreurs_4xx', 0)}")
        print(f"  Taux d'erreurs   : {metriques.get('taux_erreurs_pct', 0)}%")
        print(f"  Latence moyenne  : {metriques.get('latence_moyenne_ms', 0)} ms")
        print(f"  Latence max      : {metriques.get('latence_max_ms', 0)} ms")

        alertes = rapport.get("alertes", [])
        if alertes:
            print("\n  ⚠️  ALERTES ACTIVES :")
            for a in alertes:
                print(f"     → {a}")
        else:
            print("\n  ✅ Aucune alerte active")
        print("=" * 60 + "\n")

    def surveiller_en_continu(self, intervalle_secondes: int = 60):
        """
        Surveillance continue : génère un rapport toutes les N secondes.
        Utile pour surveiller l'application en production.
        """
        logger.info(f"Démarrage de la surveillance (intervalle : {intervalle_secondes}s)")
        print(f"Surveillance démarrée. Rapport toutes les {intervalle_secondes} secondes.")
        print("Appuyez sur Ctrl+C pour arrêter.\n")

        try:
            while True:
                self.afficher_rapport()
                time.sleep(intervalle_secondes)
        except KeyboardInterrupt:
            logger.info("Surveillance arrêtée par l'utilisateur.")
            print("\nSurveillance arrêtée.")


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    monitor = MonitoringApp()

    if "--continu" in sys.argv:
        monitor.surveiller_en_continu(intervalle_secondes=30)
    else:
        monitor.afficher_rapport()
