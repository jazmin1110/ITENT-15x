#!/usr/bin/env bash
# Load DATABASE_URL from render_database.env (gitignored) and seed Render Postgres from your laptop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${RENDER_DB_ENV:-$ROOT/render_database.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing: $ENV_FILE"
  echo "Copy render_database.env.example → render_database.env and set DATABASE_URL to your Render Postgres External URL."
  echo "Or: export DATABASE_URL='postgresql://...' and run: python manage.py migrate --noinput && python manage.py seed_professor_demo --force"
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is empty in $ENV_FILE"
  exit 1
fi

python manage.py migrate --noinput
python manage.py seed_professor_demo --force

echo ""
echo "Done. Open your Render URL and sign in (e.g. employer 09178153228 / ProfDemo2026!)."
