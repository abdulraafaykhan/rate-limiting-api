# Project context: Rate Limiting API

## 1. Goal

Build a Rate Limiting API with Python and FastAPI. Many users call one API.
Each user may only make a set number of requests per time window. Going over
returns `HTTP 429 Too Many Requests`. Limits refill by themselves according
to the algorithm. Users must be independent of each other.

Do NOT use ready-made rate-limiting packages (slowapi, fastapi-limiter,
limits, ...). The core algorithm is written by us.

## 2. Required endpoints

| Method | Path | Notes |
|---|---|---|
| GET | `/api/data` | Sample protected API |
| GET | `/api/status` | Current user's remaining quota (must not use quota) |
| POST | `/api/config` | Set a user's limit. ADMIN ONLY |
| GET | `/health` | Health check |
| GET | `/api/analytics` | Bonus 3 (admin only in this project) |

Example, user with 5 per minute. First 5 requests, HTTP 200:

```json
{"message": "Request successful", "user_id": "user_101", "remaining_requests": 0}
```

6th request, HTTP 429 (retry time is CALCULATED, never hardcoded):

```json
{"error": "Rate limit exceeded", "retry_after": 42}
```

## 3. Core requirements

1. Two algorithms (we use Sliding Window Log and Token Bucket) and an
   explanation of which handles bursts better (README, section on bursts).
2. Per-user limits: identify by `X-API-Key`, separate counters per user,
   different limits per user, a normal user can never change a quota.
3. Concurrency: 100 simultaneous requests with a quota of 10 means exactly
   10 succeed and 90 get 429 (no refill during the test). No race conditions.
4. Redis holds all state, so counters survive a server restart. Checks and
   updates are atomic (Lua scripts). Demonstrate 2 API instances sharing Redis.
5. Automated tests: normal requests, quota exceeded, quota recovery,
   multiple users, concurrency, invalid authentication.

## 4. Bonus requirements (all implemented)

1. `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After` headers.
2. Redis-backed limit on simultaneous active requests.
3. Analytics endpoint: allowed and blocked per user.
4. Performance comparison of the two algorithms.

## 5. Design decisions (already made, keep them)

- Architecture: MVC. Models = `app/models/`, Views = `app/views/`,
  Controllers = `app/controllers/`. Business logic = `app/services/`.
- SOLID only where useful: algorithms share the `RateLimitAlgorithm`
  base class; services receive Redis and settings through their constructor.
- Redis only. No MongoDB (not required, keeps the project small).
- All tweakable values live in `app/settings.py` (env or `.env` overrides).
- Users and API keys live in `app/known_users.py` (plain dict, demo only).
- Each rate-limit check is ONE Lua script in `app/services/lua/`, using the
  Redis `TIME` command so several API copies agree on the time.
- `consume=False` runs the same script without counting, used by `/api/status`.
- Concurrency check runs BEFORE the rate limit, so a refusal for too many
  active requests does not cost quota.
- Default `MAX_ACTIVE_REQUESTS_PER_USER` is 200 so it does not disturb the
  100-request concurrency test. Lower it to demo the feature.

## 6. Folder map

```
app/main.py              app creation
app/settings.py          all tweakable values
app/known_users.py       users, keys, starting limits
app/redis_client.py      shared Redis connection
app/redis_keys.py        all Redis key names
app/exceptions.py        custom errors
app/error_handlers.py    error -> HTTP response
app/middleware.py        X-Served-By header
app/dependencies.py      service wiring, auth, enforce_limits
app/models/              user, rate_limit, schemas
app/views/responses.py   every JSON response
app/controllers/         data, status, config, analytics, health
app/services/            config, limiter, active_request, analytics, auth
app/services/algorithms/ base, sliding_window_log, token_bucket
app/services/lua/        4 Lua scripts
tests/                   pytest suite (uses Redis DB 15)
loadtest/                attack simulations
benchmarks/              algorithm comparison
```

## 7. Code standards

- PEP 8, maximum line length 79.
- A comment above each step that explains WHY, not just what.
- Plain, readable names (`remaining`, `retry_after_seconds`, not `r`, `ra`).
- One responsibility per file. Do not merge files.
- No new dependency unless a requirement needs it.

## 8. Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker run -d --name redis -p 6379:6379 redis:7
uvicorn app.main:app --port 8001
pytest -v
python loadtest/concurrency_attack.py
python -m benchmarks.compare_algorithms
docker compose up --build
```

## 9. Phases (do them in order)

**Phase 1: Setup.** Create the virtualenv, install `requirements-dev.txt`,
start Redis, check `redis-cli ping`.
Done when: `python -c "import app.main"` works.

**Phase 2: Boot and smoke test.** Start `uvicorn app.main:app --port 8001`.
Call `/health`, `/api/data` (6 times with `key-user-101`), `/api/status`.
Done when: the 6th call returns 429 with a numeric `retry_after`, and the
`X-RateLimit-*` and `Retry-After` headers are present.

**Phase 3: Tests.** Run `pytest -v`. Fix failures. Known risk areas: the
pytest-asyncio loop-scope settings in `pytest.ini`, Lua script syntax, and
FastAPI yield-dependency timing.
Done when: all tests pass. Run them 3 times to catch flaky ones.

**Phase 4: Concurrency and attack simulation.** Run
`python loadtest/concurrency_attack.py` and `loadtest/multi_user_attack.py`.
Done when: the first prints exactly 200 x10 and 429 x90 and both say PASS.
Also run it with `RATE_LIMIT_ALGORITHM=token_bucket`.

**Phase 5: Two instances and persistence.** Run `docker compose up --build`
(or two uvicorn processes). Run `loadtest/two_instances_demo.py`. Then use up
a quota, restart one API container, and confirm `/api/status` still shows the
used quota.
Done when: the demo says PASS and the quota survives the restart.

**Phase 6: Bonus checks.** Start the server with
`MAX_ACTIVE_REQUESTS_PER_USER=3 SIMULATED_WORK_SECONDS=2`, fire 10 parallel
requests, confirm 3 succeed and 7 get 429. Check `/api/analytics`.
Run `python -m benchmarks.compare_algorithms` and paste the table into the
README under a new heading "Benchmark results".

**Phase 7: Final review.** Walk through the acceptance checklist below.

## 10. Acceptance checklist

- [ ] All 4 required endpoints work, plus analytics
- [ ] 429 body and `Retry-After` header match, retry time is calculated
- [ ] Two algorithms selectable by `RATE_LIMIT_ALGORITHM`
- [ ] Users are independent and have different limits
- [ ] Normal user gets 403 on `/api/config`; bad key gets 401
- [ ] 100 concurrent requests, quota 10: exactly 10 x 200 and 90 x 429
- [ ] State is in Redis and survives an API restart
- [ ] Two API instances share one limit
- [ ] Tests cover: normal, exceeded, recovery, multiple users,
      concurrency, invalid auth
- [ ] Bonus 1, 2, 3 and 4 demonstrated
- [ ] README explains which algorithm handles bursts better and why
- [ ] No rate-limit library in `requirements.txt`
- [ ] PEP 8 line length respected, comments explain the why

## 11. Final report (agent fills this in)

- Test results:
- Concurrency result:
- Benchmark table:
- Bugs found and fixed:
- Anything left undone:
