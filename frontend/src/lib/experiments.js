// Traffic profiles: identical timing and a fresh quota for each algorithm.
export const ALGORITHMS = {
  token_bucket: "Token Bucket",
  sliding_window_log: "Sliding Window Log",
};
export const PROFILES = {
  burst: {
    title: "Instant burst",
    detail:
      "Send all requests together. Both algorithms admit up to the available capacity.",
  },
  waves: {
    title: "Burst & recovery",
    detail:
      "Two equal waves, half a window apart. Compare steady token refill with strict rolling-window protection.",
  },
  sustained: {
    title: "Sustained traffic",
    detail:
      "Space requests across 1.5 windows. Observe throughput, throttling, and admission gaps.",
  },
  concurrency: {
    title: "Concurrency accuracy",
    detail:
      "Send requests together with a 1-hour window to avoid a whole-token refill. Try 100 requests and quota 10.",
  },
};

export function scheduleRequests(count, profile, windowSeconds) {
  return Array.from({ length: count }, (_, index) => {
    if (profile === "waves")
      return index < Math.ceil(count / 2) ? 0 : windowSeconds * 500;
    if (profile === "sustained")
      return count > 1 ? (index * windowSeconds * 1500) / (count - 1) : 0;
    return 0;
  });
}

export function delay(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted)
      return reject(new DOMException("Stopped", "AbortError"));
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Stopped", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", abort, { once: true });
  });
}

// Summary math uses Redis decision timestamps for admission-policy checks.
export function summarize(records, config, elapsedMs) {
  const allowed = records.filter((row) => row.status === 200);
  const blocked = records.filter((row) => row.status === 429);
  const errors = records.length - allowed.length - blocked.length;
  const quotaBlocked = blocked.filter(
    (row) => row.reason === "Rate limit exceeded",
  ).length;
  const activeBlocked = blocked.length - quotaBlocked;
  const latencies = records
    .filter((row) => row.status)
    .map((row) => row.latency)
    .sort((a, b) => a - b);
  const times = allowed
    .map((row) => row.at)
    .filter(Number.isFinite)
    .sort((a, b) => a - b);
  let left = 0,
    rollingPeak = 0,
    envelopeExcess = 0;
  for (let right = 0; right < times.length; right++) {
    while (times[right] - times[left] >= config.window - 0.00001) left++;
    rollingPeak = Math.max(rollingPeak, right - left + 1);
    for (let start = 0; start <= right; start++) {
      const bound =
        config.limit +
        ((times[right] - times[start]) * config.limit) / config.window;
      envelopeExcess = Math.max(envelopeExcess, right - start + 1 - bound);
    }
  }
  const gaps = times
    .slice(1)
    .map((time, index) => (time - times[index]) * 1000);
  const mean = (values) =>
    values.length ? values.reduce((a, b) => a + b, 0) / values.length : 0;
  const policyPass =
    config.algorithm === "sliding_window_log"
      ? rollingPeak <= config.limit
      : envelopeExcess < 0.001;
  return {
    ...config,
    total: records.length,
    allowed: allowed.length,
    blocked: blocked.length,
    errors,
    quotaBlocked,
    activeBlocked,
    dropRate: records.length ? (blocked.length / records.length) * 100 : 0,
    average: mean(latencies),
    p95: latencies[Math.max(0, Math.ceil(latencies.length * 0.95) - 1)] || 0,
    throughput: records.length / Math.max(elapsedMs / 1000, 0.001),
    duration: elapsedMs / 1000,
    rollingPeak,
    meanGap: mean(gaps),
    maxGap: gaps.length ? Math.max(...gaps) : 0,
    policy:
      errors || times.length !== allowed.length
        ? "Incomplete"
        : policyPass
          ? "Within policy"
          : "Violation observed",
    records,
  };
}
