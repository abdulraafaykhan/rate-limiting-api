import test from "node:test";
import assert from "node:assert/strict";
import { sendData } from "./api.js";

test("missing headers remain unknown instead of becoming false zero quotas", async (context) => {
  context.mock.method(
    globalThis,
    "fetch",
    async () =>
      new Response(JSON.stringify({ error: "Unavailable" }), { status: 503 }),
  );
  const row = await sendData("test-key");
  assert.equal(row.status, 503);
  assert.equal(row.remaining, null);
  assert.equal(row.limit, null);
  assert.equal(row.retry, null);
});

test("non-JSON HTTP errors preserve their HTTP status for honest summaries", async (context) => {
  context.mock.method(
    globalThis,
    "fetch",
    async () => new Response("Gateway error", { status: 502 }),
  );
  const row = await sendData("test-key");
  assert.equal(row.status, 502);
  assert.match(row.reason, /HTTP 502/);
});
