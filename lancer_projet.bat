@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   LANCEMENT DU PROJET - Analyseur de Sentiment (Docker)
echo ============================================================
echo.

rem --- Verifie que Docker est disponible ---
where docker >nul 2>nul
if errorlevel 1 (
  echo [ERREUR] Docker n'est pas installe ou absent du PATH.
  echo Installez Docker Desktop, lancez-le, puis relancez ce script.
  pause
  exit /b 1
)

rem --- Detecte "docker compose" (v2) sinon "docker-compose" (v1) ---
docker compose version >nul 2>nul
if errorlevel 1 (
  set "DC=docker-compose"
) else (
  set "DC=docker compose"
)

echo Une fois les conteneurs demarres, ouvrez dans le navigateur :
echo   - Application Streamlit : http://localhost:8501
echo   - API Modele IA (docs)  : http://localhost:8000/docs
echo   - API Donnees   (docs)  : http://localhost:8001/docs
echo   - Prometheus            : http://localhost:9090
echo   - Grafana               : http://localhost:3000   (admin / admin)
echo   - MLflow                : http://localhost:5000
echo.
echo Construction + demarrage en cours...
echo (la toute premiere fois, le build peut prendre plusieurs minutes)
echo Appuyez sur Ctrl+C dans cette fenetre pour tout arreter.
echo ------------------------------------------------------------
echo.

%DC% up --build

echo.
echo ------------------------------------------------------------
echo Projet arrete. (Pour nettoyer : %DC% down)
pause
