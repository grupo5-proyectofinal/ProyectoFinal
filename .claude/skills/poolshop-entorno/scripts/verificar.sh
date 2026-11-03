#!/usr/bin/env bash
# Corre todo lo que tiene que estar en verde antes de un push.
# Uso: verificar.sh [rapido]   (rapido = sin pytest completo, solo ruff + front)
set -uo pipefail
RAIZ="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
fallas=0

cd "$RAIZ/backend" && . .venv/bin/activate
echo "== ruff"; ruff check . --extend-ignore EXE001 || fallas=1
if [ "${1:-}" != "rapido" ]; then
  echo "== pytest"; pytest -q -p no:cacheprovider 2>&1 | tail -3; [ "${PIPESTATUS[0]}" -eq 0 ] || fallas=1
fi

cd "$RAIZ/frontend"
echo "== node --test"; node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)|^not ok"; [ "${PIPESTATUS[0]}" -eq 0 ] || fallas=1
echo "== build"; npm run build >/tmp/poolshop-build.log 2>&1 && echo "build ok" || { tail -20 /tmp/poolshop-build.log; fallas=1; }

[ $fallas -eq 0 ] && echo "TODO EN VERDE" || { echo "HAY FALLAS"; exit 1; }
