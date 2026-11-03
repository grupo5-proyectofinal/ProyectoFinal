#!/usr/bin/env bash
# Deja PoolShop listo para trabajar y testear en un contenedor Linux sin Docker:
# Postgres local, .env, venv con deps, node_modules y migraciones aplicadas.
# Idempotente: se puede correr las veces que haga falta.
set -euo pipefail

RAIZ="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
cd "$RAIZ"

# 1. Postgres (cluster del sistema; en Windows/Mac usar `docker compose up -d db`)
if command -v pg_lsclusters >/dev/null 2>&1; then
  if ! pg_lsclusters --no-header | grep -q online; then
    service postgresql start >/dev/null
  fi
  su postgres -c "psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='poolshop'\"" | grep -q 1 \
    || su postgres -c "psql -qc \"CREATE USER poolshop WITH PASSWORD 'poolshop' CREATEDB;\""
  su postgres -c "psql -tAc \"SELECT 1 FROM pg_database WHERE datname='poolshop'\"" | grep -q 1 \
    || su postgres -c "psql -qc \"CREATE DATABASE poolshop OWNER poolshop;\""
fi

# 2. .env de desarrollo (no se commitea: está en .gitignore)
if [ ! -f .env ]; then
  cat > .env <<'ENV'
SECRET_KEY=dev-secret-key-local-solo-para-tests
POSTGRES_DB=poolshop
POSTGRES_USER=poolshop
POSTGRES_PASSWORD=poolshop
POSTGRES_PORT=5432
POSTGRES_HOST=127.0.0.1
FRONTEND_URL=http://localhost:5173
ENV
fi

# 3. Backend
cd backend
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
python manage.py migrate -v0
cd ..

# 4. Frontend
cd frontend
[ -d node_modules ] || npm ci --silent
cd ..

echo "Entorno listo. Backend: backend/.venv · Front: frontend/node_modules"
