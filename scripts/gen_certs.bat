@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "CERTS_DIR=%REPO_ROOT%\certs"

if not exist "%CERTS_DIR%" mkdir "%CERTS_DIR%"

if exist "%CERTS_DIR%\server.crt" if exist "%CERTS_DIR%\server.key" (
    echo TLS certificates already exist in %CERTS_DIR%.
    exit /b 0
)

echo Generating self-signed development TLS certificate...
where openssl >nul 2>&1
if errorlevel 1 (
    echo WARNING: openssl not found in PATH. Cannot generate certificates.
    exit /b 1
)

openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout "%CERTS_DIR%\server.key" -out "%CERTS_DIR%\server.crt" -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >nul 2>&1
if errorlevel 1 (
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout "%CERTS_DIR%\server.key" -out "%CERTS_DIR%\server.crt" -subj "/CN=localhost"
)

echo Certificates generated at %CERTS_DIR%.
