#!/usr/bin/env bash
# Generate self-signed TLS certificates for local development and CI testing.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CERTS_DIR="${REPO_ROOT}/certs"
mkdir -p "${CERTS_DIR}"

CRT="${CERTS_DIR}/server.crt"
KEY="${CERTS_DIR}/server.key"

if [ -f "${CRT}" ] && [ -f "${KEY}" ]; then
  echo "TLS certificates already exist in ${CERTS_DIR}."
  exit 0
fi

echo "Generating self-signed development TLS certificate..."

if openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${KEY}" -out "${CRT}" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null; then
  echo "Generated certificate with SAN at ${CRT}"
else
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${KEY}" -out "${CRT}" \
    -subj "/CN=localhost"
  echo "Generated basic certificate at ${CRT}"
fi
chmod 600 "${KEY}" 2>/dev/null || true
chmod 644 "${CRT}" 2>/dev/null || true
echo "Certificates generated successfully."
