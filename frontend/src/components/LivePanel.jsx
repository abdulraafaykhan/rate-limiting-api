import { Radio, Waves } from "lucide-react";
import { ALGORITHMS } from "../lib/experiments.js";
import { SectionTitle } from "./shared.jsx";

// ----- Live recovery chart and real quota counters -----
export function QuotaChart({ history, limit }) {
  const max = Math.max(1, limit || 10);
  const data = history.slice(-100);
  const start = data[0]?.time || 0;
  const span = Math.max(10000, (data.at(-1)?.time || start) - start);
  const points = data
    .map(
      (row) =>
        `${(((row.time - start) / span) * 540).toFixed(1)},${(140 - (row.remaining / max) * 125).toFixed(1)}`,
    )
    .join(" ");
  return (
    <div className="quota-chart">
      <div className="chart-y">
        <span>{max}</span>
        <span>{Math.round(max / 2)}</span>
        <span>0</span>
      </div>
      <div className="chart-canvas">
        <svg
          viewBox="0 0 540 150"
          role="img"
          aria-label="Remaining user quota over time"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="quota-fill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#3976f6" stopOpacity=".16" />
              <stop offset="100%" stopColor="#3976f6" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[15, 77.5, 140].map((y) => (
            <line
              key={y}
              x1="0"
              x2="540"
              y1={y}
              y2={y}
              stroke="#e7edf5"
              strokeDasharray="4 5"
            />
          ))}
          {data.length > 1 && (
            <>
              <polygon
                points={`0,150 ${points} ${((data.at(-1).time - start) / span) * 540},150`}
                fill="url(#quota-fill)"
              />
              <polyline
                points={points}
                fill="none"
                stroke="#3976f6"
                strokeWidth="2.5"
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
              />
            </>
          )}
        </svg>
        {!data.length && (
          <span className="chart-placeholder">
            Live quota will appear after connecting
          </span>
        )}
        <div className="chart-x">
          <span>Observation start</span>
          <span>{Math.round(span / 1000)}s</span>
        </div>
      </div>
    </div>
  );
}

export function LivePanel({ lab }) {
  const status = lab.status;
  const last = lab.records.at(-1);
  const allowed = lab.records.filter((row) => row.status === 200).length;
  const blocked = lab.records.filter((row) => row.status === 429).length;
  return (
    <section className="panel live-panel">
      <SectionTitle eyebrow="02 / OBSERVE" title="Watch the limit in action">
        <span className={`badge ${lab.connected ? "live" : ""}`}>
          <span className="dot" />
          {lab.connected ? "LIVE · 500 ms" : "NOT CONNECTED"}
        </span>
      </SectionTitle>
      <div className="live-summary">
        <div>
          <p className="muted small">Remaining quota</p>
          <div className="quota-number">
            {status ? status.remaining_requests : "—"}
            <span>/ {status?.limit ?? "—"} requests</span>
          </div>
        </div>
        <div className="algorithm-label">
          <Waves size={17} />
          <span>
            {ALGORITHMS[lab.activeAlgorithm || status?.algorithm] ||
              "Choose an algorithm"}
            <small>
              {lab.userId} · {status?.window_seconds ?? lab.form.window}s window
            </small>
          </span>
        </div>
      </div>
      <div className="quota-track">
        <span
          style={{
            width: status
              ? `${Math.min(100, (status.remaining_requests / status.limit) * 100)}%`
              : "0%",
          }}
        />
      </div>
      <div className="chart-heading">
        <span>
          <span className="legend-line" />
          Available requests
        </span>
        <span>Redis-backed · automatic recovery</span>
      </div>
      <QuotaChart history={lab.history} limit={status?.limit} />
      <div className="header-counters">
        <div>
          <code>X-RateLimit-Limit</code>
          <strong>{status?.limit ?? "—"}</strong>
          <small>Configured capacity</small>
        </div>
        <div>
          <code>X-RateLimit-Remaining</code>
          <strong>{status?.remaining_requests ?? "—"}</strong>
          <small>Live status observation</small>
        </div>
        <div>
          <code>Retry-After</code>
          <strong>{last?.retry == null ? "—" : `${last.retry}s`}</strong>
          <small>
            Last response header · live wait {status?.retry_after ?? "—"}s
          </small>
        </div>
      </div>
      <div className="decision-totals">
        <span>
          <i className="dot green" />
          {allowed} allowed
        </span>
        <span>
          <i className="dot red" />
          {blocked} throttled
        </span>
        <span>{status?.active_requests ?? 0} active requests</span>
      </div>
      <p className="notice" aria-live="polite">
        <Radio size={15} />
        {lab.notice}
      </p>
    </section>
  );
}
