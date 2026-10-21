@echo off
REM Local pre-push check: mirrors .github/workflows/ci.yml exactly
setlocal

echo === 1/3 Lint (ruff) ===
py -m ruff check ingest\
if errorlevel 1 goto :fail

echo === 2/3 Unit tests (pytest) ===
py -m pytest ingest/tests -q
if errorlevel 1 goto :fail

echo === 3/3 docker-compose validation ===
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
echo.
echo CHECKS FAILED - do not push
exit /b 1