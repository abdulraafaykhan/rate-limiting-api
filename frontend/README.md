# Rate Limit Lab — React + Vite

## Start locally (PowerShell)

Keep Redis running. Start the API in one terminal:

```powershell
cd C:\Projects\rate_limiter_api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8001
```

Start Vite in another:

```powershell
cd C:\Projects\rate_limiter_api\frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Enter the configured admin API key (demo default:
`admin-secret-key`), select the user, and connect. A custom user key can be
entered when it differs from the demo pattern.

If `npm` is not on PATH on this Windows installation, use
`& 'C:\Program Files\nodejs\npm.cmd' run dev`.
For a different API port, set `$env:API_PROXY_TARGET='http://127.0.0.1:8011'`
before starting Vite. The Vite proxy keeps API calls same-origin, including
Swagger docs; no permissive CORS configuration is needed.

## Run a comparison

1. Select Token Bucket, Sliding Window Log, or Compare both algorithms.
2. Set request count (1–500), quota (1–1000), window, and traffic profile.
3. Run. The selected user's quota is reset with the chosen algorithm before
   each run, using the existing admin-only `/api/config` endpoint.
4. Inspect the live chart, response headers, summary cards and activity log.
5. Watch automatic recovery after a run. Export JSON to retain both reports
   and every completed response; keys are excluded from exports.

Both algorithms use identical counts, quota and schedule in comparison mode.
They run sequentially, with a fresh quota each time. This is a local admin
experiment: it deliberately changes the selected user's configured algorithm
and quota, which persist in Redis after the run. Other users are unaffected.

## What each traffic profile tests

| Profile | Schedule | What to observe |
|---|---|---|
| Instant burst | All requests scheduled together | Both algorithms allow up to available capacity. |
| Burst & recovery | Two waves half a window apart | Token Bucket earns new tokens before Sliding Window Log's oldest admissions expire. Recommended: count 20, quota 10, window 8s. |
| Sustained traffic | Requests spread across 1.5 windows | Admission gaps, HTTP latency, drop rate and throughput under sustained load. |
| Concurrency accuracy | All requests, window forced to 3600s | With count 100 and quota 10, expect 10 allowed and 90 blocked when no whole token refills. |

A browser has connection limits: requests are scheduled concurrently, not a
claim that every request reaches Redis at the exact same instant. The backend
verification script separately proves concurrency across API processes.

## Metric definitions

- Allowed = HTTP 200; throttled = HTTP 429. Network and other HTTP errors are
  counted separately, not mislabeled as rate-limit drops.
- Throttle percentage = HTTP 429 responses / completed attempts × 100.
  These synthetic requests are not classified as legitimate or malicious.
- Latency and p95 are browser round-trip times, including proxy and network.
  Throughput is completed attempts / experiment wall time, including planned
  gaps. These are application-level comparisons, not pure Lua benchmarks.
- Sliding accuracy uses the peak allowed count in a rolling window, based on
  Redis decision timestamps returned in `X-RateLimit-Timestamp`.
- Token Bucket checks the burst-plus-refill envelope B + r × elapsed for
  observed admission intervals. It can legally exceed B within a rolling
  window; this is different from violating its own policy.
- Mean and longest admission gaps describe observed smoothness. Neither
  algorithm guarantees evenly spaced admissions: both admit an initial burst.
- The three header cards show configured limit, current status remaining,
  and the last response's actual Retry-After. The adjacent live-wait value is
  calculated by `/api/status`; a missing header is shown as a dash, not zero.
- Reports are per-run and kept in this tab. User analytics are cumulative Redis
  decision counters. Quota resets do not erase analytics. A stopped run is
  partial; aborted requests can already have consumed quota on the server.

## Backend changes

- `/api/config` optionally accepts a validated per-user `algorithm` field.
  Saved selection is shared across API instances. Legacy requests without
  this field select the server's configured default algorithm.
- Atomic limiter scripts reject stale algorithm dispatch before updating any
  state. The service rereads configuration and retries boundedly.
- `/api/analytics` retains existing per-user totals and adds per-user,
  per-algorithm allowed/blocked counters under `algorithms`.
- Admin-only `/api/users` supplies user IDs/configuration, never credentials.
- Protected responses add algorithm and Redis-decision timestamp headers.
- After `npm run build`, the API can serve `frontend/dist` at `/` on a fresh
  startup. Vite is only needed for development. Docker remains backend-only.

## Code map

- `src/components/SetupPanel.jsx`: credentials, selectors and traffic controls.
- `src/components/LivePanel.jsx`: quota chart, recovery and header cards.
- `src/components/ResultsPanel.jsx`: performance and policy summaries.
- `src/components/AnalyticsPanel.jsx`: persistent per-user/algorithm counts.
- `src/components/RequestLog.jsx`: latest 40 actual responses.
- `src/hooks/useLab.js`: authentication, polling, run lifecycle and cancellation.
- `src/lib/api.js`: HTTP transport and response-header parsing.
- `src/lib/experiments.js`: schedules and documented metric calculations.
- `src/styles.css`: commented layout sections and mobile breakpoints.

## Build and verification

```powershell
npm test
npm run build
npm run format
```

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m loadtest.verify_requirements
```

The admin key is entered manually and kept in React memory. It is not in the
bundle, Vite environment variables, localStorage, analytics or report exports.
Only the existing public demonstration default is shown as a UI hint.
