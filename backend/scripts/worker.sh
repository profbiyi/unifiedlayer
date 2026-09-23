#!/usr/bin/env bash
# Dedicated Celery worker (+ embedded beat) for UnifiedLayer.
#
# Use this to run pipeline sync execution as its OWN Railway service, separate
# from the web API — the path to horizontal scale (add worker replicas without
# touching the API). Set up a new Railway service pointing at this same repo/
# image with:
#     Start command:  bash backend/scripts/worker.sh
# give it the same env as the backend (DATABASE_URL, REDIS_URL, ENCRYPTION_KEY,
# MANAGED_STORAGE_*, etc.), and set RUN_WORKER_IN_WEB=false on the WEB service so
# beat runs in exactly one place (avoids duplicate scheduled triggers).
#
# CELERY_CONCURRENCY controls how many syncs run in parallel per worker.
set -euo pipefail

exec python3 -m celery -A backend.celery_app worker \
    --loglevel=info \
    -Q pipelines,default,dbt,health \
    --concurrency="${CELERY_CONCURRENCY:-4}" \
    --beat \
    --schedule=/tmp/celerybeat-schedule \
    --without-gossip --without-mingle
