@echo off
setlocal enabledelayedexpansion
REM ====================================================================
REM  NexusSim — Unified System Launcher
REM  Builds the C++ engine, optionally trains the MARL policy, and launches
REM  the full multi-service stack (engine, gateway, sidecars) in a single
REM  console window. Services are backgrounded (start /b) and log to logs\.
REM ====================================================================

if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help

REM ---------------------- default configuration -----------------------
set CITY=piedmont
set AGENTS=500
set DURATION=5
set BUILD_TYPE=Release
set OD_PATH=
set DEMAND_SCALE=
set START_HOUR=8.0
set SPEED_FACTOR=0.55
set ROUTE_SPREAD=0.2
set CHAOS=0.1
set JOURNEY_PATH=
set FAST=0
set NO_WS=0
set REBUILD=0
set POLICY=
set TRAIN=0
set TRAIN_CITY=toy
set TRAIN_EPISODES=200
set TRAIN_DEVICE=auto
set TRAIN_BATCH=0
set PYTHON=python
set DASHBOARD_ONLY=0

REM ---------------------- parse arguments -----------------------------
:parse_args
if "%~1"=="" goto cuda_preflight
if "%~1"=="--city" ( set "CITY=%~2" & shift & shift & goto parse_args )
if "%~1"=="--agents" ( set "AGENTS=%~2" & shift & shift & goto parse_args )
if "%~1"=="--duration" ( set "DURATION=%~2" & shift & shift & goto parse_args )
if "%~1"=="--od" ( set "OD_PATH=%~2" & shift & shift & goto parse_args )
if "%~1"=="--demand-scale" ( set "DEMAND_SCALE=%~2" & shift & shift & goto parse_args )
if "%~1"=="--start-hour" ( set "START_HOUR=%~2" & shift & shift & goto parse_args )
if "%~1"=="--speed-factor" ( set "SPEED_FACTOR=%~2" & shift & shift & goto parse_args )
if "%~1"=="--route-spread" ( set "ROUTE_SPREAD=%~2" & shift & shift & goto parse_args )
if "%~1"=="--chaos" ( set "CHAOS=%~2" & shift & shift & goto parse_args )
if "%~1"=="--journey" ( set "JOURNEY_PATH=%~2" & shift & shift & goto parse_args )
if "%~1"=="--fast" ( set "FAST=1" & shift & goto parse_args )
if "%~1"=="--no-ws" ( set "NO_WS=1" & shift & goto parse_args )
if "%~1"=="--debug" ( set "BUILD_TYPE=Debug" & shift & goto parse_args )
if "%~1"=="--rebuild" ( set "REBUILD=1" & shift & goto parse_args )
if "%~1"=="--policy" ( set "POLICY=%~2" & shift & shift & goto parse_args )
if "%~1"=="--train" ( set "TRAIN=1" & shift & goto parse_args )
if "%~1"=="--train-city" ( set "TRAIN_CITY=%~2" & shift & shift & goto parse_args )
if "%~1"=="--train-episodes" ( set "TRAIN_EPISODES=%~2" & shift & shift & goto parse_args )
if "%~1"=="--train-device" ( set "TRAIN_DEVICE=%~2" & shift & shift & goto parse_args )
if "%~1"=="--train-batch-size" ( set "TRAIN_BATCH=%~2" & shift & shift & goto parse_args )
if "%~1"=="--python" ( set "PYTHON=%~2" & shift & shift & goto parse_args )
if "%~1"=="--dashboard-only" ( set "DASHBOARD_ONLY=1" & shift & goto parse_args )
if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help
shift
goto parse_args

REM ---------------------- show help -----------------------------------
:show_help
echo Usage: run.bat [OPTIONS]
echo.
echo Core options:
echo   --city NAME        City to simulate (default: piedmont)
echo   --agents N         Number of agents (uniform mode, default: 500)
echo   --duration N       Duration in minutes (default: 5)
echo   --od PATH          OD demand matrix (real-traffic mode)
echo   --demand-scale N   Scale factor for OD demand (auto if omitted)
echo   --start-hour H     Simulation start hour 0-23 (default: 8)
echo   --speed-factor N   Congestion factor on IDM desired speeds (default: 0.55)
echo   --route-spread N   Stochastic route-choice spread 0-1 (default: 0.2)
echo   --chaos N          Lane-discipline chaos coefficient 0-1 (default: 0.1)
echo   --journey PATH     Where to write journey times CSV
echo   --fast             Headless mode: no pacing, exits when sim finishes
echo   --no-ws            Disable WebSocket server (no dashboard)
echo   --debug            Build in Debug mode
echo   --rebuild          Force a clean rebuild
echo   --dashboard-only   Start dashboard only (skip build/run)
echo.
echo ML policy options:
echo   --train            Train the MAPPO policy, export to ONNX, run engine with it
echo   --train-city NAME  City to train on (default: toy)
echo   --train-episodes N Training episodes (default: 200)
echo   --train-device DEV auto (CUDA when available, else CPU), cpu, cuda, cuda:N
echo   --train-batch-size N PPO minibatch size; 0 scales with sample count
echo   --policy PATH      ONNX policy file for the engine (e.g. ml\policy.onnx)
echo   --python PATH      Python interpreter (default: python)
echo.
echo Examples:
echo   run.bat
echo   run.bat --train --train-city piedmont --train-device cuda
echo   run.bat --city chicago --agents 2000 --duration 10
echo   run.bat --city chicago --od data\chicago\od_matrix.json --duration 60
echo   run.bat --fast --no-ws --od data\chicago\od_matrix.json --duration 60
echo   run.bat --dashboard-only
exit /b 0

REM ---------------------- CUDA preflight ------------------------------
:cuda_preflight
echo ====================================================================
echo   NexusSim Unified System Launcher
echo   City: %CITY%
echo ====================================================================
echo.

REM ensure OpenSSL/zlib DLLs are on PATH (needed by engine.exe)
set PATH=C:\msys64\mingw64\bin;%PATH%

REM copy required runtime DLLs next to engine.exe (only if not already present)
if exist engine\build\engine.exe (
    if not exist "engine\build\libcrypto-3-x64.dll" if exist "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" "engine\build\" >nul
    if not exist "engine\build\libssl-3-x64.dll" if exist "C:\msys64\mingw64\bin\libssl-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libssl-3-x64.dll" "engine\build\" >nul
    if not exist "engine\build\zlib1.dll" if exist "C:\msys64\mingw64\bin\zlib1.dll" copy /Y "C:\msys64\mingw64\bin\zlib1.dll" "engine\build\" >nul
)

echo [0/6] Probing CUDA / GPU...
set "PY_CMD=.venv\Scripts\python.exe"
if not exist "!PY_CMD!" set "PY_CMD=python"

set "ORT_PROVIDER=cpu"
set "TRAIN_DEVICE_DEFAULT=cpu"
set "GPU_BAT=%TEMP%\nexus_gpu_%RANDOM%.bat"
!PY_CMD! ml\cuda_detect.py --export-bat "!GPU_BAT!"
if exist "!GPU_BAT!" (
    call "!GPU_BAT!"
    del "!GPU_BAT!" >nul 2>&1
)
if "%CUDA_AVAILABLE%"=="1" set "TRAIN_DEVICE_DEFAULT=cuda"
echo   Engine ONNX provider: !ORT_PROVIDER!
echo   Training device:      !TRAIN_DEVICE_DEFAULT!
echo.

REM ---------------------- build ---------------------------------------
if "%DASHBOARD_ONLY%"=="1" goto dashboard_only

:build
if "%REBUILD%"=="0" if exist "engine\build\engine.exe" (
    echo [1/5] engine.exe found — skipping build (pass --rebuild to force)
    goto train
)

echo [1/5] Configuring CMake...
if not exist "engine\build" mkdir "engine\build"
cd engine\build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=%BUILD_TYPE% -DENABLE_TESTING=OFF -DENABLE_ONNX_CUDA=AUTO -DCMAKE_C_COMPILER=C:/msys64/mingw64/bin/gcc.exe -DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe
if errorlevel 1 (
    echo ERROR: CMake configuration failed!
    cd ..\..
    exit /b 1
)

echo.
echo [2/5] Building engine...
cmake --build .
if errorlevel 1 (
    echo ERROR: Build failed!
    cd ..\..
    exit /b 1
)

REM copy runtime DLLs next to engine.exe (only if not already present)
if exist engine\build\engine.exe (
    if not exist "engine\build\libcrypto-3-x64.dll" if exist "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" "engine\build\" >nul
    if not exist "engine\build\libssl-3-x64.dll" if exist "C:\msys64\mingw64\bin\libssl-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libssl-3-x64.dll" "engine\build\" >nul
    if not exist "engine\build\zlib1.dll" if exist "C:\msys64\mingw64\bin\zlib1.dll" copy /Y "C:\msys64\mingw64\bin\zlib1.dll" "engine\build\" >nul
)

cd ..\..

REM ---------------------- train ---------------------------------------
:train
if "%TRAIN%"=="0" goto run_system
REM Use auto-detected device when --train-device not explicitly set
if "%TRAIN_DEVICE%"=="auto" set "TRAIN_DEVICE=%TRAIN_DEVICE_DEFAULT%"
echo.
echo [3/5] Training MARL policy
echo ====================================================================
echo   City: %TRAIN_CITY%   Episodes: %TRAIN_EPISODES%   Device: %TRAIN_DEVICE%
echo.
cd ml
!PY_CMD! -u -m train.train --city %TRAIN_CITY% --episodes %TRAIN_EPISODES% --device %TRAIN_DEVICE% --batch-size %TRAIN_BATCH% --checkpoint-interval 50 --log-interval 10
if errorlevel 1 (
    echo ERROR: Training failed!
    cd ..
    exit /b 1
)
set "LAST_CKPT="
for /f "delims=" %%f in ('dir /b /o-n "checkpoints\%TRAIN_CITY%\*.pt" 2^>nul') do if not defined LAST_CKPT set "LAST_CKPT=checkpoints\%TRAIN_CITY%\%%f"
if not defined LAST_CKPT (
    echo ERROR: no checkpoint was written to checkpoints\%TRAIN_CITY%
    cd ..
    exit /b 1
)
echo Exporting ONNX policy from %LAST_CKPT% ...
!PY_CMD! -u -m export.export_onnx --checkpoint "%LAST_CKPT%" --output policy.onnx
if errorlevel 1 (
    echo ERROR: ONNX export failed!
    cd ..
    exit /b 1
)
cd ..
set "POLICY=ml\policy.onnx"
echo Policy ready: ml\policy.onnx

REM ---------------------- run system ----------------------------------
:run_system
echo.
echo [4/5] Starting services...

if not exist "logs" mkdir "logs"

REM Clean up any stale running instances to release log file locks and ports
taskkill /F /IM engine.exe >nul 2>&1
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,9001,9003,9004,9005,9006,3000 -ErrorAction SilentlyContinue | ForEach-Object { if ($_.OwningProcess -gt 0) { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }; exit 0" >nul 2>&1

REM Ensure dev TLS certificates are available
if not exist "certs\server.crt" if exist "scripts\gen_certs.bat" (
    call scripts\gen_certs.bat >nul 2>&1
)

REM 1. C++ Simulation Engine (WS :9001)
echo   [1/7] C++ Simulation Engine (WS :9001)...
if exist engine\build\engine.exe (
    set "ENGINE_ARGS=--city %CITY% --port 9001 --onnx-provider !ORT_PROVIDER!"
    if exist certs\server.crt if exist certs\server.key set "ENGINE_ARGS=!ENGINE_ARGS! --ssl-cert certs\server.crt --ssl-key certs\server.key"
    if "%NO_WS%"=="1" set "ENGINE_ARGS=!ENGINE_ARGS! --no-ws"
    if "%FAST%"=="1" set "ENGINE_ARGS=!ENGINE_ARGS! --fast"
    if not "%OD_PATH%"=="" (
        set "ENGINE_ARGS=!ENGINE_ARGS! --od %OD_PATH%"
        if not "%DEMAND_SCALE%"=="" set "ENGINE_ARGS=!ENGINE_ARGS! --demand-scale %DEMAND_SCALE%"
        set "ENGINE_ARGS=!ENGINE_ARGS! --start-hour %START_HOUR% --speed-factor %SPEED_FACTOR% --route-spread %ROUTE_SPREAD%"
    )
    if not "%JOURNEY_PATH%"=="" set "ENGINE_ARGS=!ENGINE_ARGS! --journey %JOURNEY_PATH%"
    if not "%CHAOS%"=="" set "ENGINE_ARGS=!ENGINE_ARGS! --chaos %CHAOS%"
    if not "%POLICY%"=="" set "ENGINE_ARGS=!ENGINE_ARGS! --policy %POLICY%"
    start /b "" cmd /c "engine\build\engine.exe !ENGINE_ARGS! > logs\engine.log 2>&1"
    echo     backgrounded -> logs\engine.log
) else (
    echo     [WARN] engine\build\engine.exe not found; build it first
)

REM 2. Unified API Gateway (:8000)
echo   [2/7] Unified API Gateway (:8000)...
start /b "" cmd /c "!PY_CMD! -m gateway.server > logs\gateway.log 2>&1"
echo     backgrounded -> logs\gateway.log

REM 3. CV Virtual Camera (:9003)
echo   [3/7] CV Virtual Camera (:9003)...
start /b "" cmd /c "!PY_CMD! ml\cv\virtual_camera_service.py > logs\camera.log 2>&1"
echo     backgrounded -> logs\camera.log

REM 4. NLP Chat & Incident Sidecar (:9004)
echo   [4/7] NLP Chat ^& Incident Sidecar (:9004)...
start /b "" cmd /c "!PY_CMD! ml\nlp\chat_service.py --city %CITY% > logs\nlp.log 2>&1"
echo     backgrounded -> logs\nlp.log

REM 5. Cross-Subject Event Bus (:9005)
echo   [5/7] Cross-Subject Event Bus (:9005)...
start /b "" cmd /c "!PY_CMD! pipeline\src\event_bus.py > logs\eventbus.log 2>&1"
echo     backgrounded -> logs\eventbus.log

REM 6. Algorithm Explorer API Sidecar (:9006)
echo   [6/7] Algorithm Explorer API (:9006)...
start /b "" cmd /c "!PY_CMD! ml\sidecars\algo_explorer_service.py > logs\algo.log 2>&1"
echo     backgrounded -> logs\algo.log

REM 7. React Dashboard (:3000)
echo   [7/7] React Dashboard (:3000)...
if exist "dashboard\package.json" (
    start /b "" cmd /c "cd dashboard && npm run dev > ..\logs\dashboard.log 2>&1"
    echo     backgrounded -> logs\dashboard.log
)

echo.
echo ====================================================================
echo   All NexusSim services started (single window; logs in logs\).
echo ====================================================================
echo   Default city:      %CITY%
echo   Engine WS:         wss://localhost:9001
echo   Gateway:           https://localhost:8000
echo   Dashboard:         https://localhost:3000
echo   API docs:          https://localhost:8000/docs
echo   Logs:              logs\
echo   ONNX provider:     !ORT_PROVIDER!
echo ====================================================================
echo   Services are running in background.
echo   Press any key or Ctrl+C to stop all services...
echo ====================================================================
pause >nul

echo Stopping services...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8000,9001,9003,9004,9005,9006,3000 -ErrorAction SilentlyContinue | ForEach-Object { if ($_.OwningProcess -gt 0) { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }; exit 0" >nul 2>&1
taskkill /F /IM engine.exe >nul 2>&1
echo All services stopped.
goto end

REM ---------------------- dashboard only ------------------------------
:dashboard_only
cd dashboard
if not exist "node_modules" (
    echo Installing dashboard dependencies...
    call npm install
)
start "" cmd /c "npm run dev"
cd ..
goto end

REM ---------------------- end -----------------------------------------
:end
endlocal
