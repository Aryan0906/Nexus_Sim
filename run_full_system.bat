@echo off
setlocal enabledelayedexpansion
REM ====================================================================
REM  NexusSim — Full System Launcher
REM  Single console window: every service is backgrounded (start /b) and
REM  logs to logs\ so no extra PowerShell/cmd windows pop up.
REM ====================================================================

if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help

set CITY=%~1
if "%CITY%"=="" set CITY=piedmont

REM ---- ensure OpenSSL/zlib DLLs are on PATH (needed by engine.exe) ----
set PATH=C:\msys64\mingw64\bin;%PATH%

REM ---- copy required runtime DLLs next to engine.exe ------------------
if exist engine\build\engine.exe (
    if exist "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" engine\build\ >nul
    if exist "C:\msys64\mingw64\bin\libssl-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libssl-3-x64.dll" engine\build\ >nul
    if exist "C:\msys64\mingw64\bin\zlib1.dll" copy /Y "C:\msys64\mingw64\bin\zlib1.dll" engine\build\ >nul
    REM ONNX Runtime DLL (from build tree if present)
    for %%d in ("engine\build\onnxruntime.dll") do if exist "%%d" copy /Y "%%d" engine\build\ >nul
)

echo ====================================================================
echo   NexusSim Full System Launcher
echo   Default city: %CITY%
echo ====================================================================
echo.

REM ---- 0. CUDA / GPU probe -------------------------------------------
echo [0/7] Probing CUDA / GPU...
set "PY_CMD=.venv\Scripts\python.exe"
if not exist "!PY_CMD!" set "PY_CMD=python"

REM Unified probe via cuda_detect.py (checks PyTorch, ONNX Runtime, OpenCV)
!PY_CMD! ml/cuda_detect.py 2>nul || echo "  [WARN] cuda_detect.py not available"

REM Determine engine ONNX provider from probe
set "ORT_PROVIDER=cpu"
for /f "tokens=* delims=" %%a in ('!PY_CMD! -c "from ml.cuda_detect import CudaEnv; e=CudaEnv.probe(); print(e.recommended_onnx_provider)" 2>nul') do set "ORT_PROVIDER=%%a"
echo   Engine ONNX provider: !ORT_PROVIDER!
echo.

REM ---- prepare logs dir ----------------------------------------------
if not exist logs mkdir logs

REM Helper: launch a service backgrounded in THIS window (no new window)
REM usage: call :launch "Log tag" "command > logfile 2>&1"
set LAUNCH_OK=1

REM ---- 1. C++ Simulation Engine (WS :9001) ---------------------------
echo [1/7] Starting C++ Simulation Engine (WS :9001)...
if exist engine\build\engine.exe (
    set "ENGINE_ARGS=--city %CITY% --port 9001 --onnx-provider !ORT_PROVIDER!"
    if exist certs\server.crt if exist certs\server.key set "ENGINE_ARGS=!ENGINE_ARGS! --ssl-cert certs\server.crt --ssl-key certs\server.key"
    start /b "" cmd /c "engine\build\engine.exe !ENGINE_ARGS! > logs\engine.log 2>&1"
    echo   engine backgrounded -> logs\engine.log
) else (
    echo   [WARN] engine\build\engine.exe not found; build it first (run.bat or cmake)
)

REM ---- 2. Unified API Gateway (:8000) --------------------------------
echo [2/7] Starting Unified API Gateway (:8000)...
start /b "" cmd /c "!PY_CMD! -m gateway.server > logs\gateway.log 2>&1"
echo   gateway backgrounded -> logs\gateway.log

REM ---- 3. CV Virtual Camera (:9003) ----------------------------------
echo [3/7] Starting CV Virtual Camera (:9003)...
start /b "" cmd /c "!PY_CMD! ml\cv\virtual_camera_service.py > logs\camera.log 2>&1"
echo   camera backgrounded -> logs\camera.log

REM ---- 4. NLP Chat & Incident Sidecar (:9004) ------------------------
echo [4/7] Starting NLP Chat & Incident Sidecar (:9004)...
start /b "" cmd /c "!PY_CMD! ml\nlp\chat_service.py > logs\nlp.log 2>&1"
echo   nlp backgrounded -> logs\nlp.log

REM ---- 5. Cross-Subject Event Bus (:9005) ----------------------------
echo [5/7] Starting Cross-Subject Event Bus (:9005)...
start /b "" cmd /c "!PY_CMD! pipeline\src\event_bus.py > logs\eventbus.log 2>&1"
echo   event bus backgrounded -> logs\eventbus.log

REM ---- 6. Algorithm Explorer API Sidecar (:9006) ---------------------
echo [6/7] Starting Algorithm Explorer API (:9006)...
start /b "" cmd /c "!PY_CMD! ml\sidecars\algo_explorer_service.py > logs\algo.log 2>&1"
echo   algo explorer backgrounded -> logs\algo.log

echo.
echo ====================================================================
echo   All NexusSim services started (single window; logs in logs\).
echo ====================================================================
echo   Default city:      %CITY%
echo   Engine WS:         ws://localhost:9001
echo   Gateway:           https://localhost:8000
echo   Dashboard:         http://localhost:3000  (run: cd dashboard && npm run dev)
echo   API docs:          https://localhost:8000/docs
echo   Logs:              logs\
echo ====================================================================
echo   Services run backgrounded; this window stays open to keep them alive.
echo   Close this window or press Ctrl+C to stop all services.
echo ====================================================================
goto end

:show_help
echo Usage: run_full_system.bat [CITY_ID]
echo.
echo   CITY_ID   City to simulate (default: piedmont)
echo             Use a city registered via /api/cities/upload or in cities.yaml
echo.
echo Examples:
echo   run_full_system.bat
echo   run_full_system.bat chicago
echo   run_full_system.bat mumbai
goto end

:end
endlocal
