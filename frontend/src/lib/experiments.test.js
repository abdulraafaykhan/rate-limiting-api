import test from "node:test";
import assert from "node:assert/strict";
import { scheduleRequests, summarize } from "./experiments.js";

test("profiles preserve exact count, ordering, and comparable timing", () => {
  assert.deepEqual(scheduleRequests(5, "waves", 8), [0, 0, 0, 4000, 4000]);
  assert.deepEqual(scheduleRequests(3, "sustained", 4), [0, 3000, 6000]);
  assert.deepEqual(scheduleRequests(3, "concurrency", 3600), [0, 0, 0]);
});
const row = (at, status = 200) => ({
  at,
  status,
  latency: 10,
  reason: status === 429 ? "Rate limit exceeded" : "Request successful",
});
test("summary distinguishes errors from throttles and checks rolling accuracy", () => {
  const result = summarize(
    [row(1), row(2), row(3), row(4, 429), { status: 0 }],
    { algorithm: "sliding_window_log", limit: 2, window: 10 },
    1000,
  );
  assert.equal(result.policy, "Incomplete");
  assert.equal(
    summarize(
      [row(1), row(2), row(3)],
      { algorithm: "sliding_window_log", limit: 2, window: 10 },
      1000,
    ).policy,
    "Violation observed",
  );
  assert.equal(result.dropRate, 20);
  assert.equal(result.errors, 1);
  assert.equal(result.quotaBlocked, 1);
});
test("token bucket checks burst plus refill rather than a strict rolling cap", () => {
  const records = [row(0), row(0), row(5)];
  const result = summarize(
    records,
    { algorithm: "token_bucket", limit: 2, window: 10 },
    5000,
  );
  assert.equal(result.rollingPeak, 3);
  assert.equal(result.policy, "Within policy");
});
test("missing decision timestamps never produce a false accuracy pass", () => {
  assert.equal(
    summarize(
      [row(null)],
      { algorithm: "sliding_window_log", limit: 2, window: 10 },
      100,
    ).policy,
    "Incomplete",
  );
});
