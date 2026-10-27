@echo off
REM Run the NexusSim Postman collection headless with Newman.
REM Usage:  postman\run_postman_tests.bat
REM Requires: all services running (run.bat) and Node.js (npx).
REM The gateway serves HTTPS with a local self-signed cert, hence --insecure.

cd /d "%~dp0\.."

npx --yes newman run ^
  postman\NexusSim_API_Collection.json ^
  -e postman\NexusSim_Environment.json ^
  --insecure ^
  --reporters cli
