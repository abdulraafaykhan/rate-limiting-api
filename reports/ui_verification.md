# React + Vite dashboard verification

Verified on 30 October 2026. The UI runs real FastAPI requests backed by Redis.

## Delivered

- Clean responsive React + Vite dashboard, split into feature components,
  an experiment hook, an HTTP transport module and metric/scheduling helpers.
- Admin connection, selected user/API key, algorithm dropdown including Both,
  number-of-requests field and 10/20/100/500 quick-select buttons.
- Fresh quota per algorithm, as confirmed by the user; comparisons run each
  algorithm sequentially with the same configuration and schedule.
- Instant burst, burst-and-recovery, sustained traffic and concurrency profiles.
- Live quota chart and automatic recovery, 500ms status polling, active requests,
  all three required header readouts, progress and a stop action.
- Per-algorithm allow/block counts, throttle percentage, errors, mean/p95 HTTP
  latency, observed throughput, rolling peak and admission-gap summaries.
- Timestamp-based checks against each algorithm's own policy, not a false claim
  that token buckets enforce the same strict rolling cap as sliding logs.
- Persistent per-user/algorithm analytics, actual response log and JSON export.

## Necessary backend changes

| Change | Why |
|---|---|
| Optional admin-only `algorithm` on `/api/config` | Switch the actual selected user's limiter without restarting or changing another user |
| Persist algorithm in Redis and reject stale dispatch in Lua | All API instances use the same selected algorithm atomically |
| Extend `/api/analytics` with per-user algorithm counters | Retain old totals and show both algorithms separately |
| Admin-only `/api/users` | Populate real user metadata without returning credentials |
| Add algorithm and Redis-decision timestamp response headers | Identify the real algorithm and evaluate observed admission policy accurately |
| Serve a Vite production build at `/` | Single-origin local deployment without requiring Vite at runtime |

The original four endpoints, authentication, required rate headers, Redis
persistence, active request limits and handwritten algorithms remain in use.
No ready-made rate-limiting package was added. No new storage service was added.

## Automated results

- Backend: **118 passed in 47.91 seconds**.
- Frontend: **6 tests passed** (traffic schedules, policy calculations,
  error/drop separation, missing headers and non-JSON HTTP failures).
- Vite production build: passed.
- Two-process backend verifier: passed both algorithms, 100/500 concurrent
  request checks, recovery, API restart and active-slot crash recovery.
- Additional two-process UI integration: passed changing user_104's algorithm
  from Token Bucket to Sliding Window Log without either process restarting.
  Each algorithm produced 3 allowed/1 blocked with quota 3. Per-algorithm
  analytics matched. Production UI and Swagger were served directly by FastAPI.

## Actual browser checks

| Test | Actual result |
|---|---|
| Two waves of 10, quota 10, window 8 seconds | Token Bucket: **15 allowed / 5 throttled**; Sliding Window Log: **10 allowed / 10 throttled**; both within policy, zero errors |
| 100-request concurrency profile, quota 10, window 3600 seconds | Both: **10 allowed / 90 throttled**, zero errors |
| Sustained traffic, 20 requests, quota 3, window 2 seconds | Token Bucket: **7 allowed / 13 throttled**; Sliding Window Log: **6 allowed / 14 throttled**, zero errors |
| Single-algorithm dropdown + 10-request button, quota 3 | Token Bucket: **3 allowed / 7 throttled**, zero errors |
| Stop scheduled sustained traffic | Stopped after completed responses; report marked **Stopped / partial**, controls usable again |
| JSON export | Export downloaded successfully and retained per-response evidence without credentials |
| Quota recovery | Live remaining quota returned to capacity through polling without consuming requests |
| Desktop 1366px and mobile 390px | No intersecting control bounding boxes and no horizontal document overflow; tables scroll within their own containers |

Screenshots are available as `ui-desktop.png` and `ui-mobile.png`.
Browser screenshots/DOM checks were performed using the Sites local-preview
workflow. Temporary viewport overrides were reset after responsive testing.

## Evidence

- `ui-wave-comparison.json`: exported real browser wave test, including records.
- `ui-concurrency-comparison.json`: exported real browser 100-request comparison.
- `ui_backend_integration.json`: two-process algorithm switching and analytics.
- `backend_verification.json`: the rerun of the original full live verifier.
- `test_results.txt`: automated results.

## How to run

API terminal, with Redis running:

```powershell
cd C:\Projects\rate_limiter_api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

UI terminal:

```powershell
cd C:\Projects\rate_limiter_api\frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173, enter your admin key (demo default
`admin-secret-key`), connect and run. See `frontend/README.md` for component
locations, profiles, metrics, the proxy target and build instructions.

## Interpretation limits

- Browser concurrency is subject to browser connection scheduling. Separate
  backend tests verify true API concurrency; the UI does not claim all requests
  arrive at Redis at exactly the same instant.
- Frontend throughput includes scheduled gaps. Latency includes HTTP, the
  browser, the proxy and network; use the existing benchmark for pure limiter
  comparisons. The UI does not prescribe a universal fastest algorithm.
- Both algorithms permit an initial burst up to capacity. Sliding Window Log
  enforces a rolling count, not equally spaced traffic. Token Bucket allows
  capacity-sized bursts plus tokens earned over time.
- Throttle percentage counts synthetic HTTP 429 responses, not a classification
  of legitimate versus malicious traffic. Other errors are reported separately.
- Tests intentionally change the selected user's quota and saved algorithm.
  They preserve cumulative analytics and leave other users' limits alone.
- Reports are held in tab memory until exported. Credentials are held only in
  tab memory, never browser storage or exports. The displayed demo key is public
  demonstration material already present in the backend source.
- No cloud deployment was requested. Docker remains the existing backend-only
  configuration; Docker/Nginx execution is still unverified on this machine.
