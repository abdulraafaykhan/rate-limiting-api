// API transport: all measurements come from real FastAPI responses.
export async function request(path, { key, body, signal, ...options } = {}) {
  const response = await fetch(path, {
    ...options,
    signal,
    headers: {
      ...(key ? { "X-API-Key": key } : {}),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response
    .json()
    .catch(() => ({ error: "The API returned an unreadable response." }));
  if (!response.ok)
    throw new Error(
      data.error ||
        data.detail?.[0]?.msg ||
        `API returned HTTP ${response.status}`,
    );
  return { data, headers: response.headers };
}

export async function sendData(key, signal) {
  const start = performance.now();
  const response = await fetch("/api/data", {
    headers: { "X-API-Key": key },
    signal,
  });
  const body = await response.json().catch(() => ({
    error: `API returned HTTP ${response.status} without a JSON body`,
  }));
  const headerNumber = (name) => {
    const value = response.headers.get(name);
    return value === null ? null : Number(value);
  };
  return {
    status: response.status,
    latency: performance.now() - start,
    at: Number(response.headers.get("X-RateLimit-Timestamp")) || null,
    remaining: headerNumber("X-RateLimit-Remaining"),
    limit: headerNumber("X-RateLimit-Limit"),
    retry: response.headers.get("Retry-After")
      ? Number(response.headers.get("Retry-After"))
      : null,
    algorithm: response.headers.get("X-RateLimit-Algorithm"),
    reason: body.error || "Request successful",
  };
}
