@echo off
setlocal enabledelayedexpansion
REM ====================================================================
REM  NexusSim — Full 48-Algorithm Multi-Subject System Launcher
REM  With Dynamic City Onboarding Support
REM ====================================================================

if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help

set CITY=%~1
if "%CITY%"=="" set CITY=chicago

echo ====================================================================
echo   NexusSim Full System Launcher
echo   City: %CITY%
echo ====================================================================
echo.

echo [1/6] Launching C++ Simulation Engine on port 9001...
start "NexusSim C++ Engine" cmd /k "run.bat --city %CITY% --duration 60"

echo [2/6] Launching CV Virtual Camera Service on port 9003...
start "NexusSim Virtual Camera" cmd /k ".venv\Scripts\python.exe ml\cv\virtual_camera_service.py"

echo [3/6] Launching NLP Chat & Incident Sidecar on port 9004...
start "NexusSim NLP Chat" cmd /k ".venv\Scripts\python.exe ml\nlp\chat_service.py"

echo [4/6] Launching Cross-Subject Event Bus on port 9005...
start "NexusSim Event Bus" cmd /k ".venv\Scripts\python.exe pipeline\src\event_bus.py"

echo [5/6] Launching Algorithm Explorer API Sidecar on port 9006...
start "NexusSim Algo Explorer API" cmd /k ".venv\Scripts\python.exe ml\sidecars\algo_explorer_service.py"

echo [6/6] Launching Unified API Gateway on port 8000...
start "NexusSim API Gateway" cmd /k "python -m gateway.server"

echo.
echo ====================================================================
echo   All NexusSim services started.
echo ====================================================================
echo   City:           %CITY%
echo   Engine WS:      ws://localhost:9001
echo   Gateway:        https://localhost:8000
echo   Gateway WS:     wss://localhost:8000/ws
echo   Dashboard:      http://localhost:3000  (run: cd dashboard ^&^& npm run dev)
echo   API Docs:       https://localhost:8000/docs
echo   Auth Login:     POST https://localhost:8000/api/auth/login
echo   City Upload:    POST https://localhost:8000/api/cities/upload
echo   Simulations:    POST https://localhost:8000/api/simulations
echo   Scenarios:      POST https://localhost:8000/api/scenarios
echo ====================================================================
echo   To run a different city:  run_full_system.bat <city_id>
echo   To upload a new city OSM: POST /api/cities/upload with .osm/.pbf/.graphml
echo ====================================================================
goto end

:show_help
echo Usage: run_full_system.bat [CITY_ID]
echo.
echo   CITY_ID   City to simulate (default: chicago)
echo             Use a city registered via /api/cities/upload or in cities.yaml
echo.
echo Examples:
echo   run_full_system.bat
echo   run_full_system.bat chicago
echo   run_full_system.bat mumbai
goto end

:end
endlocal
