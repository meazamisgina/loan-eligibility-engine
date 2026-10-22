@echo off
REM Local pre-push check: mirrors .github/workflows/ci.yml step for step
setlocal

if exist .venv\Scripts\python.exe (set PY=.venv\Scripts\python) else (set PY=py)

echo === 1/4 Install dependencies (mirrors CI) ===
%PY% -m pip install -r ingest\requirements-dev.txt -q
if errorlevel 1 goto :fail

echo === 2/4 Lint (ruff) ===
%PY% -m ruff check ingest\ api\
if errorlevel 1 goto :fail

echo === 3/4 Tests (pytest) ===
%PY% -m pytest ingest/tests api/tests -q
if errorlevel 1 goto :fail

echo === 4/4 docker-compose validation ===
if exist docker-compose.yml (
    docker compose -f docker-compose.yml config --quiet
    if errorlevel 1 goto :fail
    echo docker-compose.yml is valid
) else (
    echo docker-compose.yml not present yet - skipping
)

echo.
echo ALL CHECKS PASSED - safe to push
exit /b 0

:fail
echo CHECKS FAILED - do not push
exit /b 1