#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate

python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

# Destructive: deletes all users except protected phones + superusers, then Jolly/FourAces demo.
# Set SEED_PROFESSOR_DEMO=1 on the web service (see render.yaml). Omit or set to 0 to skip.
if [ "${SEED_PROFESSOR_DEMO:-}" = "1" ]; then
  echo "SEED_PROFESSOR_DEMO=1: running seed_professor_demo --force"
  python manage.py seed_professor_demo --force || true
fi
