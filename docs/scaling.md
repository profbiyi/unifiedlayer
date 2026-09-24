# Scaling sync capacity — ops runbook

How to give the platform enough concurrent-sync capacity for N tenants, and how
fairness keeps one tenant from starving the others.

## How capacity works

**Total slots = worker replicas × `CELERY_CONCURRENCY`.** A "slot" runs one sync
at a time. Triggered syncs that don't get a slot **queue** in Redis and start as
slots free — they never fail or clash (each run is isolated + tenant-scoped, and a
guard blocks the same pipeline running twice).

Syncs run on a **Celery worker**, never in the web process, so the API stays
responsive no matter how many syncs are churning.

## Current setup (default)

- Worker + beat run **inside the web container** (`RUN_WORKER_IN_WEB=true`).
- `CELERY_CONCURRENCY=8` → **8 slots** on a 24 GB container (each sync ~0.3–2 GB;
  8 fits comfortably). Fine for a pilot of light/SME syncs.
- This single-container worker is capped by the container's RAM/CPU — don't crank
  concurrency arbitrarily high for heavy syncs. Past ~8–10, scale out instead.

## Scaling out: dedicated worker service (the real capacity lever)

For more simultaneous capacity, run workers as their **own Railway service(s)**,
scaled independently of the API. Each replica is its own container (own CPU/RAM),
so there's no single-container contention.

1. **New Railway service** from this same repo/image.
2. Start command: `bash backend/scripts/worker.sh`
3. Same env as `backend` (`DATABASE_URL`, `REDIS_URL`, `ENCRYPTION_KEY`,
   `MANAGED_STORAGE_*`, …) plus `CELERY_CONCURRENCY=4` (per replica).
4. On the **web** service set `RUN_WORKER_IN_WEB=false` (stop the in-container worker).
5. **Scale the worker service to R replicas.** Total slots = `R × CELERY_CONCURRENCY`.

### Beat must run in exactly one place

`worker.sh` embeds beat (`-B`). With **more than one replica**, run the scheduler
once instead of R times (avoids duplicate scheduled triggers):

- Simplest: keep `-B` on a **single** worker service (replicas = 1) and add a
  **second** worker service without `-B` for extra slots; or
- Run a dedicated 1-replica **beat** service (`celery -A backend.celery_app beat`)
  and drop `-B` from `worker.sh`.

(The scheduler already guards against duplicate runs, so a brief overlap during a
change is harmless — but don't run many beats steady-state.)

## Sizing guide

Syncs are short (SME syncs ~15–30 s) and tenants rarely all fire the same second,
so you need far fewer slots than `tenants × peak`. Fairness (below) fills the gaps.

| Scenario | Suggested total slots | Example |
|---|---|---|
| Pilot, 5–10 tenants, light syncs | 8 | in-container `CELERY_CONCURRENCY=8` (current) |
| 12 tenants testing | 12 | 1 worker svc × 12, or 3 replicas × 4 |
| Heavier / bursty, 12–25 tenants | 16–24 | 4–6 replicas × 4 |
| Large simultaneous loads | scale replicas + load-test | measure first |

## Fairness — one tenant can't starve another

**Work-conserving per-org fairness** is built in:

- Each org has a **guaranteed share** (`MAX_ORG_CONCURRENT_SYNCS`, default **3**).
- Within that share it always runs.
- **Above** it, an org keeps bursting into **idle** slots — but the moment another
  org has a run **waiting**, the burster's extra runs defer back to their share so
  the waiting tenant gets a slot.

So a company can run 10+ at once on a quiet platform and is throttled back the
instant someone else needs capacity. No org is ever starved by another.

## Knobs (env vars, all optional)

| Var | Default | What |
|---|---|---|
| `CELERY_CONCURRENCY` | 2 | slots per worker replica |
| `RUN_WORKER_IN_WEB` | true | run worker+beat in the web container |
| `MAX_ORG_CONCURRENT_SYNCS` | 3 | per-org guaranteed share (0 = disable fairness) |
| `ORG_DEFER_SECONDS` | 15 | re-check interval for a deferred run |
| `PIPELINE_FETCH_RETRIES` / `PIPELINE_FETCH_RETRY_DELAY` | 2 / 20 | extract retry budget (fail fast → free slots) |
| `PIPELINE_LOAD_RETRIES` / `PIPELINE_LOAD_RETRY_DELAY` | 2 / 20 | load retry budget |
| `PIPELINE_TASK_SOFT_TIME_LIMIT` / `PIPELINE_TASK_TIME_LIMIT` | 3600 / 3900 | per-run time limits |

## Monitoring

- **`GET /admin/system/sync-capacity`** (super-admin): running vs pending runs,
  worker count + total concurrency, a `backlogged` flag, last-hour throughput.
- **`celery -A backend.celery_app inspect stats`**: live worker pool / concurrency.

## Not yet done

A **high-volume load test** to put a hard number on the throughput ceiling. The
"N slots run in parallel, the rest queue fairly" behavior is verified; the absolute
throughput ceiling per replica is not yet measured.
