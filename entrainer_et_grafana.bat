@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem ============================================================
rem  Python a utiliser. Par defaut "python" (votre env actif).
rem  Modifiez la ligne ci-dessous pour pointer vers un env precis, ex :
rem  set "PYTHON=C:\Users\Utilisateur\AppData\Local\miniconda3\envs\VOTRE_ENV\python.exe"
rem ============================================================
set "PYTHON=python"

echo ============================================================
echo   ENTRAINEMENT XGBoost (MLflow) + REMPLISSAGE GRAFANA
echo ============================================================
echo.

rem --- Verifie les dependances ML ---
%PYTHON% -c "import xgboost, sklearn, mlflow, pandas, requests" 2>nul
if errorlevel 1 (
  echo [ERREUR] L'environnement Python ne contient pas xgboost/sklearn/mlflow/pandas/requests.
  echo Activez l'environnement conda du projet, ou installez les dependances :
  echo     pip install -r requirements.txt
  echo Puis relancez ce script ^(ou editez la variable PYTHON en haut du fichier^).
  pause
  exit /b 1
)

rem --- Verifie que le dataset traduit existe (sinon on le genere) ---
if not exist "data\df_final_fr.csv" (
  echo [INFO] data\df_final_fr.csv introuvable : generation de la traduction d'abord...
  %PYTHON% data\traduire_echantillon.py
  if errorlevel 1 ( echo [ERREUR] La traduction a echoue. & pause & exit /b 1 )
)

rem ============================================================
rem  Choix du backend MLflow
rem  - Si le serveur MLflow du docker-compose repond sur le port 5000,
rem    on logge DEDANS (les runs apparaissent dans l'UI Docker).
rem  - Sinon, on bascule sur une base locale sqlite + UI MLflow locale.
rem ============================================================
set "MLFLOW_TRACKING_URI=http://localhost:5000"
set "MLFLOW_LOCAL="
%PYTHON% -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=3)" 2>nul
if errorlevel 1 (
  echo [INFO] Serveur MLflow Docker injoignable sur http://localhost:5000.
  echo        Bascule sur une base MLflow locale ^(sqlite:///mlflow.db^).
  echo        Astuce : lancez lancer_projet.bat pour demarrer le serveur MLflow Docker.
  set "MLFLOW_TRACKING_URI=sqlite:///mlflow.db"
  set "MLFLOW_LOCAL=1"
) else (
  echo [OK] Serveur MLflow Docker detecte : les runs seront logges sur http://localhost:5000
)
echo     MLFLOW_TRACKING_URI=%MLFLOW_TRACKING_URI%

echo.
echo [1/4] Entrainement XGBoost + logging MLflow (quelques minutes)...
echo ------------------------------------------------------------
%PYTHON% ml\entrainer_mlflow.py
if errorlevel 1 ( echo [ERREUR] L'entrainement a echoue. & pause & exit /b 1 )

echo.
echo [2/4] Benchmark des modeles de sentiment FR (optionnel)...
echo ------------------------------------------------------------
echo     Compare notre XGBoost FR aux modeles transformers (nlptown, distilbert-en),
echo     sur le meme jeu de test ; chaque modele = 1 run MLflow.
echo     1er lancement = telechargement des modeles HuggingFace (~1 Go, peut etre long).
set "RUN_BENCH=N"
set /p "RUN_BENCH=Lancer le benchmark ? (o/N) : "
if /i "%RUN_BENCH%"=="o" (
  %PYTHON% ml\benchmark_modeles.py --n-test 300
  if errorlevel 1 ( echo [ATTENTION] Le benchmark a echoue ^(voir messages ci-dessus^). )
) else (
  echo     Benchmark ignore.
)

echo.
echo [3/4] Interface MLflow...
echo ------------------------------------------------------------
if defined MLFLOW_LOCAL (
  echo     Ouverture de l'UI MLflow locale dans une nouvelle fenetre...
  start "MLflow UI" %PYTHON% -m mlflow ui --backend-store-uri sqlite:///mlflow.db
  echo     -^> http://127.0.0.1:5000
) else (
  echo     UI deja servie par le conteneur Docker : http://localhost:5000
)

echo.
echo [4/4] Generation de trafic pour remplir le dashboard Grafana...
echo     (les APIs doivent tourner : lancez d'abord lancer_projet.bat)
echo ------------------------------------------------------------
%PYTHON% monitoring\generer_trafic.py --requetes 300

echo.
echo ============================================================
echo   TERMINE
echo   - MLflow  : http://localhost:5000   (experiments 'sentiment-xgboost' et 'benchmark-sentiment-fr')
echo   - Grafana : http://localhost:3000   (admin / admin)
echo   Astuce Grafana : reglez la fenetre de temps sur "Last 15 minutes".
echo ============================================================
pause
