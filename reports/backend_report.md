# Backend completion report

Verified on 29 October 2026. UI work remains deferred.

## Result

All five core tasks, all four required endpoints, and all four bonus items
pass the checks described below. The original two reproduced defects are
resolved. Final automated result: **104 passed in 36.54 seconds**.
The suite is run under both algorithm settings; explicitly parametrized
algorithm tests also run within those settings.

Two real, separate uvicorn processes shared live Redis. The required
100-request test produced exactly 10 HTTP 200 and 90 HTTP 429 responses
under both algorithms. Five users generated 500 simultaneous requests
across those processes, with no unexpected statuses. Each process's Redis
pool was deliberately limited to 10 connections during that test.

Fresh package installation, installed console startup, packaged Lua execution,
and all three existing demo scripts were also verified successfully.

## Added, edited and removed

The exact inventory below compares files with a snapshot made at the start
of this implementation turn. Git cannot provide a reliable original diff
because the source files were already untracked. The five extra users
`user_104` through `user_108` were added during the preceding review and
are retained with quotas 3, 4, 5, 7 and 10 per minute. Their keys are
`key-user-104` through `key-user-108`.

### Added files

- `app/services/lua/count_active_requests.lua`
- `app/services/lua/renew_active_request.lua`
- `loadtest/verify_requirements.py`
- `reports/backend_report.md`
- `reports/backend_verification.json`
- `reports/change_manifest.json`
- `reports/demo_verification.json`
- `reports/installation_verification.json`
- `reports/test_results.txt`
- `tests/test_backend_regressions.py`

### Edited files

- `.env.example`
- `.gitignore`
- `.python-version`
- `README.md`
- `app/controllers/config_controller.py`
- `app/dependencies.py`
- `app/error_handlers.py`
- `app/exceptions.py`
- `app/models/rate_limit.py`
- `app/redis_client.py`
- `app/redis_keys.py`
- `app/services/active_request_service.py`
- `app/services/algorithms/sliding_window_log.py`
- `app/services/algorithms/token_bucket.py`
- `app/services/config_service.py`
- `app/services/lua/acquire_active_request.lua`
- `app/services/lua/release_active_request.lua`
- `app/services/lua/sliding_window_log.lua`
- `app/services/lua/token_bucket.lua`
- `app/settings.py`
- `app/views/responses.py`
- `loadtest/common.py`
- `loadtest/concurrency_attack.py`
- `loadtest/multi_user_attack.py`
- `loadtest/two_instances_demo.py`
- `pyproject.toml`
- `requirements-dev.txt`
- `requirements.txt`
- `src/rate_limiter_api/__init__.py`
- `tests/conftest.py`
- `tests/test_five_additional_users.py`

### Removed

No source files were deleted. Removed/replaced behaviors:

- The expiring integer active-request counter was replaced with owned leases.
- Hardcoded active-limit retry configuration was removed from active code and
  `.env.example`; older private `.env` copies can retain an ignored value.
- Separate quota-save and counter-reset commands became one Redis transaction.
- Test `FLUSHDB` was replaced with cleanup limited to a unique test prefix.
- The installed command's placeholder greeting became a real API startup.

### What changed and why

| Area | Change | Evidence |
|---|---|---|
| Connection pool | Bounded blocking pool with configurable connection, queue and socket limits | Previously failing five-user stress tests now pass; real HTTP stress also passes with 10 connections per process |
| Active slots | Unique owners in a versioned sorted-set key, atomic acquire/release/count, recurring renewal | Long request remains counted beyond its original TTL; a second process returns 429 |
| Crash and cancellation | Expiry for abandoned owners; shielded owner-specific cleanup; lost renewal stops work and returns 503 | Tests cover cancellation, late release, cleanup outage and renewal loss; real process-kill recovery passes |
| Quota changes | Transaction writes configuration and resets both algorithms; Lua reads saved quota atomically | Stale Python config cannot admit requests using an old quota |
| Headers | Active rejection includes rate quota and calculated lease retry hint | Captured active 429 has all three headers |
| Tests | Both algorithms, 500 concurrent requests, outages, lease lifecycle, configuration and spoofing checks | 104 passing tests; test cleanup never flushes a shared database |
| Packaging | Python 3.12 minimum, actual dependencies, packaged Lua and usable console command | Fresh non-editable installation executes protected requests outside the source folder |
| Demo scripts | Strict status checks, nonzero failures, configurable target URLs and admin key | All three scripts pass under both algorithms |

## Problem statement cross-reference

| Problem statement item | Project implementation | Actual verification result |
|---|---|---|
| Python and FastAPI | `app/main.py`, `pyproject.toml` | Source startup and fresh installed command both serve healthy responses |
| GET `/api/data` | `app/controllers/data_controller.py` | With quota 3, first response is 200 with 2 remaining; fourth is 429 |
| GET `/api/status` | `app/controllers/status_controller.py` | Repeated initial peeks preserve quota 3; exhausted status reports 0 |
| POST `/api/config`, admin only | `app/controllers/config_controller.py`, `app/services/config_service.py` | Admin sets user_104 to 3/60 successfully; user_104 attempting to change user_105 receives 403 |
| GET `/health` | `app/controllers/health_controller.py` | Real Redis returns 200/up; simulated Redis outage returns 503/down |
| Exceeded quota returns HTTP 429 | `app/services/lua/*.lua`, `app/views/responses.py` | Exhausted quota returns the required error body, 429 and matching Retry-After |
| Retry is calculated | Algorithm Lua scripts | Same quota 3/60 produces sliding-window retry 60 seconds and token-bucket retry 20 seconds |
| Task 1: two handwritten algorithms | `app/services/algorithms/`, sliding-window and token-bucket Lua | Both pass endpoint, concurrency, recovery, shared-state and restart checks; no limiter package is used |
| Task 1: burst explanation | README algorithm comparison | Token bucket permits saved capacity then smooth refill; sliding log enforces an exact rolling-window cap |
| Task 2: authenticated users | `app/services/auth_service.py`, `app/known_users.py` | Missing/invalid API keys return 401; spoofed user-ID header cannot override API-key identity |
| Task 2: independent and different quotas | User config and per-user Redis keys | Five users admit exactly 3, 4, 5, 7 and 10 requests respectively during the stress run |
| Task 2: prevent unauthorized quota changes | `require_admin_user` dependency | Ordinary callers cannot configure their own or another user's quota; analytics also requires admin |
| Task 3: concurrency safety | Atomic Redis Lua checks | 100 simultaneous requests / quota 10 -> exactly 10 allowed and 90 blocked for both algorithms |
| Task 4: Redis state and atomic updates | Redis algorithms, config transaction, owned active leases | No process-local quota counters; checks and updates are atomic |
| Task 4: two instances | `loadtest/verify_requirements.py`, compose definition | Actual response headers identify both verification-api1 and verification-api2 sharing the same quota |
| Task 4: survive API restart | Redis-backed counters and config | After killing/restarting one API, user_108 remains at 0/10 with a 3600-second window and its next call is 429 |
| Task 5: automated coverage | `tests/` | Normal, exceeded, recovery, multiple users, concurrency and invalid auth are covered, with 104 passing checks |
| Bonus 1 (+5): headers | `app/views/responses.py` | X-RateLimit-Limit and Remaining on quota responses; all three headers on quota/active 429; body and Retry-After agree |
| Bonus 2 (+5): active limit | `app/services/active_request_service.py`, lease Lua scripts | Max 1 blocks an overlapping request on the other process after original TTL; killed-owner lease expires and another request succeeds |
| Bonus 3 (+5): analytics | `app/services/analytics_service.py`, analytics controller | Real sample: user_104 has allowed=3, blocked=1; five-user counts verified against all observed statuses; active blocks also counted |
| Bonus 4 (+5): performance comparison | `benchmarks/compare_algorithms.py` | Measured throughput, mean/p95 latency and Redis memory for both algorithms; results below |

## Five-user real HTTP stress result

All 500 requests were issued together across two API processes. For this test,
admin temporarily set a 3600-second window so no whole token refilled during
the run. These are test configurations; source defaults remain per minute.

| User | Quota | Sliding log: 200 / 429 | Token bucket: 200 / 429 |
|---|---:|---:|---:|
| user_104 | 3 | 3 / 97 | 3 / 97 |
| user_105 | 4 | 4 / 96 | 4 / 96 |
| user_106 | 5 | 5 / 95 | 5 / 95 |
| user_107 | 7 | 7 / 93 | 7 / 93 |
| user_108 | 10 | 10 / 90 | 10 / 90 |

## Actual request and response samples

These responses are copied from `backend_verification.json`. Temporary server
ports vary on each run; the paths and headers below are the actual inputs.
The demo admin key shown is the project's default demonstration credential.

### Admin configuration

POST `/api/config`, header `X-API-Key: admin-secret-key`, body:

```json
{"user_id":"user_104","limit":3,"window_seconds":60}
```

Captured response:

```json
{
  "status": 200,
  "headers": {
    "x-served-by": "verification-api1"
  },
  "body": {
    "message": "Rate limit updated",
    "user_id": "user_104",
    "limit": 3,
    "window_seconds": 60
  }
}
```

### Successful protected request

GET `/api/data`, header `X-API-Key: key-user-104`:

```json
{
  "status": 200,
  "headers": {
    "x-ratelimit-limit": "3",
    "x-ratelimit-remaining": "2",
    "x-served-by": "verification-api1"
  },
  "body": {
    "message": "Request successful",
    "user_id": "user_104",
    "remaining_requests": 2
  }
}
```

### Exceeded quota, both algorithms

Fourth GET `/api/data` using the same key, after consuming quota 3:

Sliding Window Log:

```json
{
  "status": 429,
  "headers": {
    "x-ratelimit-limit": "3",
    "x-ratelimit-remaining": "0",
    "retry-after": "60",
    "x-served-by": "verification-api2"
  },
  "body": {
    "error": "Rate limit exceeded",
    "retry_after": 60
  }
}
```

Token Bucket:

```json
{
  "status": 429,
  "headers": {
    "x-ratelimit-limit": "3",
    "x-ratelimit-remaining": "0",
    "retry-after": "20",
    "x-served-by": "verification-api2"
  },
  "body": {
    "error": "Rate limit exceeded",
    "retry_after": 20
  }
}
```

### Quota status

GET `/api/status`, header `X-API-Key: key-user-104`:

```json
{
  "status": 200,
  "headers": {
    "x-ratelimit-limit": "3",
    "x-ratelimit-remaining": "0",
    "x-served-by": "verification-api2"
  },
  "body": {
    "user_id": "user_104",
    "algorithm": "sliding_window_log",
    "limit": 3,
    "window_seconds": 60,
    "remaining_requests": 0,
    "retry_after": 60,
    "active_requests": 0,
    "max_active_requests": 200
  }
}
```

### Health

GET `/health`, no authentication header:

```json
{
  "status": 200,
  "headers": {
    "x-served-by": "verification-api1"
  },
  "body": {
    "status": "ok",
    "redis": "up",
    "instance_id": "verification-api1"
  }
}
```

### Invalid authentication and unauthorized configuration

GET `/api/data`, header `X-API-Key: invalid`:

```json
{
  "status": 401,
  "headers": {
    "x-served-by": "verification-api1"
  },
  "body": {
    "error": "Invalid or missing API key"
  }
}
```

POST `/api/config` using user_104's key to change user_105:

```json
{
  "status": 403,
  "headers": {
    "x-served-by": "verification-api2"
  },
  "body": {
    "error": "Admin access required"
  }
}
```

### Analytics

GET `/api/analytics`, admin key, after three allowed requests and one block:

```json
{
  "status": 200,
  "headers": {
    "x-served-by": "verification-api2"
  },
  "body": {
    "users": {
      "user_101": {
        "allowed": 0,
        "blocked": 0
      },
      "user_102": {
        "allowed": 0,
        "blocked": 0
      },
      "user_103": {
        "allowed": 0,
        "blocked": 0
      },
      "user_104": {
        "allowed": 3,
        "blocked": 1
      },
      "user_105": {
        "allowed": 0,
        "blocked": 0
      },
      "user_106": {
        "allowed": 0,
        "blocked": 0
      },
      "user_107": {
        "allowed": 0,
        "blocked": 0
      },
      "user_108": {
        "allowed": 0,
        "blocked": 0
      }
    },
    "total_allowed": 3,
    "total_blocked": 1
  }
}
```

### Active-request rejection after the original lease TTL

With maximum active requests=1, TTL=1 second and work=1.8 seconds, another
process is still blocked after waiting 1.15 seconds:

```json
{
  "status": 429,
  "headers": {
    "x-ratelimit-limit": "100",
    "x-ratelimit-remaining": "99",
    "retry-after": "1",
    "x-served-by": "verification-api2"
  },
  "body": {
    "error": "Too many simultaneous requests",
    "max_active_requests": 1,
    "retry_after": 1
  }
}
```

### Real API restart and recovery

After restarting API process 1, user_108's configuration and exhausted quota persist:

```json
{
  "status": 200,
  "headers": {
    "x-ratelimit-limit": "10",
    "x-ratelimit-remaining": "0",
    "x-served-by": "verification-api1"
  },
  "body": {
    "user_id": "user_108",
    "algorithm": "sliding_window_log",
    "limit": 10,
    "window_seconds": 3600,
    "remaining_requests": 0,
    "retry_after": 3597,
    "active_requests": 0,
    "max_active_requests": 200
  }
}
```

For quota 2/2 seconds, automatic recovery occurred after the returned retry
interval: sliding window 2 seconds; token bucket 1 second. Both next calls
returned 200. After killing a process holding an active slot, the other
process observed active_requests=0 after 1.2 seconds and accepted new work.

## Actual benchmark

Environment: Python 3.12.10; Redis 8.0.5; Windows-11-10.0.26200-SP0.
These are local measurements with 2,000 requests per mode and concurrency 50.
The comparison measures algorithm/Redis calls, not whole HTTP endpoint capacity.
Memory was sampled after 4,000 allowed operations for one user per algorithm.

```text

2000 requests per test, concurrency 50

algorithm            mode           req/sec    avg ms    p95 ms
---------------------------------------------------------------
sliding_window_log   sequential        1561     0.640     1.176
sliding_window_log   concurrent        2195    17.999    34.832
token_bucket         sequential        1813     0.551     0.865
token_bucket         concurrent        4295     7.231    11.543

Redis memory used by ONE user's data after the test:
  sliding_window_log   552064 bytes
  token_bucket         216 bytes
```

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m loadtest.verify_requirements
```

With two API processes running, the individual demonstrations also pass:

```powershell
.\.venv\Scripts\python.exe loadtest/concurrency_attack.py
.\.venv\Scripts\python.exe loadtest/multi_user_attack.py
.\.venv\Scripts\python.exe loadtest/two_instances_demo.py
```

Use LOADTEST_BASE_URL and LOADTEST_INSTANCE_URLS for alternative ports.

## Evidence and practical limits

- `backend_verification.json`: captured HTTP responses, stress counts,
  process restart/crash results, recovery and benchmark output.
- `demo_verification.json`: outputs of the three original demos for each algorithm.
- `installation_verification.json`: installed package paths, packaged scripts,
  installed CLI health result and protected 200/429 execution.
- `test_results.txt`: final automated suite result.
- `change_manifest.json`: exact added/edited/removed file inventory.
- Docker is unavailable in this environment. Compose configuration was reviewed;
  container startup and the Nginx hop were not executed. The required two API
  instances were demonstrated as real native processes sharing Redis.
- API restart persistence was tested. A Redis-server restart was not performed
  against the existing shared Redis service; compose enables AOF and a volume.
- Active-slot leases assume the event loop and Redis remain responsive within
  the configured TTL. Renewal loss stops current work; abandoned leases expire.
  Active-limit Retry-After is a hint based on current lease expiry, which running
  work can extend. It does not promise the next attempt will succeed.
- Demo keys remain static, and analytics records allow/block decisions rather
  than completed business operations. Production identity management is beyond
  this assignment's scope.

The backend is ready to proceed to a separate UI design discussion. No UI code
was added, edited or removed.
