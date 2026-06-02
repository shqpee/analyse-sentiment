"""
conftest.py — Configuration globale de pytest
"""
import sys
import os

# S'assurer que le répertoire racine est dans le chemin Python
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
