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
echo Usage: run_full_system.bat [OPTIONS]
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
echo   run_full_system.bat
echo   run_full_system.bat --train --train-city piedmont --train-device cuda
echo   run_full_system.bat --city chicago --agents 2000 --duration 10
echo   run_full_system.bat --city chicago --od data\chicago\od_matrix.json --duration 60
echo   run_full_system.bat --fast --no-ws --od data\chicago\od_matrix.json --duration 60
echo   run_full_system.bat --dashboard-only
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

REM copy required runtime DLLs next to engine.exe (if it exists)
if exist engine\build\engine.exe (
    if exist "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" engine\build\ >nul
    if exist "C:\msys64\mingw64\bin\libssl-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libssl-3-x64.dll" engine\build\ >nul
    if exist "C:\msys64\mingw64\bin\zlib1.dll" copy /Y "C:\msys64\mingw64\bin\zlib1.dll" engine\build\ >nul
    for %%d in ("engine\build\onnxruntime.dll") do if exist "%%d" copy /Y "%%d" engine\build\ >nul
)

echo [0/6] Probing CUDA / GPU...
set "PY_CMD=.venv\Scripts\python.exe"
if not exist "!PY_CMD!" set "PY_CMD=python"

REM Unified probe via cuda_detect.py (PyTorch, ONNX Runtime, OpenCV)
!PY_CMD! ml/cuda_detect.py 2>nul || echo "  [WARN] cuda_detect.py not available"

REM Determine engine ONNX provider from probe
set "ORT_PROVIDER=cpu"
for /f "tokens=* delims=" %%a in ('!PY_CMD! -c "from ml.cuda_detect import CudaEnv; e=CudaEnv.probe(); print(e.recommended_onnx_provider)" 2>nul') do set "ORT_PROVIDER=%%a"
echo   Engine ONNX provider: !ORT_PROVIDER!

REM Determine training device from probe
set "TRAIN_DEVICE_DEFAULT=cpu"
for /f "tokens=* delims=" %%a in ('!PY_CMD! -c "from ml.cuda_detect import CudaEnv; e=CudaEnv.probe(); print(e.recommended_device)" 2>nul') do set "TRAIN_DEVICE_DEFAULT=%%a"
if "%CUDA_AVAILABLE%"=="1" set "TRAIN_DEVICE_DEFAULT=cuda"
echo   Training device: %TRAIN_DEVICE_DEFAULT%
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

REM copy runtime DLLs next to engine.exe
if exist engine\build\engine.exe (
    if exist "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libcrypto-3-x64.dll" engine\build\ >nul
    if exist "C:\msys64\mingw64\bin\libssl-3-x64.dll" copy /Y "C:\msys64\mingw64\bin\libssl-3-x64.dll" engine\build\ >nul
    if exist "C:\msys64\mingw64\bin\zlib1.dll" copy /Y "C:\msys64\mingw64\bin\zlib1.dll" engine\build\ >nul
    for %%d in ("engine\build\onnxruntime.dll") do if exist "%%d" copy /Y "%%d" engine\build\ >nul
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

REM 1. C++ Simulation Engine (WS :9001)
echo   [1/4] C++ Simulation Engine (WS :9001)...
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
echo   [2/4] Unified API Gateway (:8000)...
start /b "" cmd /c "!PY_CMD! -m gateway.server > logs\gateway.log 2>&1"
echo     backgrounded -> logs\gateway.log

REM 3. CV Virtual Camera (:9003)
echo   [3/4] CV Virtual Camera (:9003)...
start /b "" cmd /c "!PY_CMD! ml\cv\virtual_camera_service.py > logs\camera.log 2>&1"
echo     backgrounded -> logs\camera.log

REM 4. NLP Chat & Incident Sidecar (:9004)
echo   [4/4] NLP Chat & Incident Sidecar (:9004)...
start /b "" cmd /c "!PY_CMD! ml\nlp\chat_service.py > logs\nlp.log 2>&1"
echo     backgrounded -> logs\nlp.log

REM 5. Cross-Subject Event Bus (:9005)
echo   [5/5] Cross-Subject Event Bus (:9005)...
start /b "" cmd /c "!PY_CMD! pipeline\src\event_bus.py > logs\eventbus.log 2>&1"
echo     backgrounded -> logs\eventbus.log

REM 6. Algorithm Explorer API Sidecar (:9006)
echo   [6/6] Algorithm Explorer API (:9006)...
start /b "" cmd /c "!PY_CMD! ml\sidecars\algo_explorer_service.py > logs\algo.log 2>&1"
echo     backgrounded -> logs\algo.log

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
echo   ONNX provider:     !ORT_PROVIDER!
echo ====================================================================
echo   Services run backgrounded; this window stays open to keep them alive.
echo   Close this window or press Ctrl+C to stop all services.
echo ====================================================================
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
