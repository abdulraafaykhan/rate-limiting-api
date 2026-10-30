import { Download, ShieldCheck, Zap } from "lucide-react";
import { ALGORITHMS } from "../lib/experiments.js";
import { SectionTitle, number } from "./shared.jsx";

// ----- Independent per-algorithm summaries and downloadable evidence -----
export function ResultsPanel({ lab }) {
  return (
    <section className="panel" id="comparison">
      <SectionTitle
        eyebrow="03 / COMPARE"
        title="The same traffic. Two approaches."
      >
        <button
          className="button subtle"
          disabled={!lab.reports.length}
          onClick={lab.download}
        >
          <Download size={15} />
          Export JSON
        </button>
      </SectionTitle>
      {!lab.reports.length ? (
        <div className="comparison-empty">
          <div className="algorithm-card">
            <div className="algorithm-icon blue">
              <Zap size={20} />
            </div>
            <h3>Token Bucket</h3>
            <p>
              Capacity-sized bursts.
              <br />
              Steady token replenishment.
            </p>
            <span className="tag">BURST TOLERANCE</span>
          </div>
          <div className="comparison-divider">vs</div>
          <div className="algorithm-card">
            <div className="algorithm-icon violet">
              <ShieldCheck size={20} />
            </div>
            <h3>Sliding Window Log</h3>
            <p>
              Exact timestamp tracking.
              <br />A strict rolling-window cap.
            </p>
            <span className="tag violet-text">ROLLING ACCURACY</span>
          </div>
        </div>
      ) : (
        <div className="report-grid">
          {lab.reports.map((report) => (
            <article className="report-card" key={report.algorithm}>
              <div className="report-top">
                <h3>{ALGORITHMS[report.algorithm]}</h3>
                <span
                  className={`badge ${report.policy === "Within policy" && !report.cancelled ? "live" : "warning"}`}
                >
                  {report.cancelled ? "Stopped / partial" : report.policy}
                </span>
              </div>
              <div className="report-big">
                {report.allowed}
                <span> / {report.total} allowed</span>
              </div>
              <div className="result-bar">
                <span
                  style={{
                    width: `${report.total ? (report.allowed / report.total) * 100 : 0}%`,
                  }}
                />
              </div>
              <dl className="metrics-grid">
                {[
                  [
                    "Throttled",
                    `${report.blocked} (${number(report.dropRate)}%)`,
                  ],
                  ["Errors", report.errors],
                  ["Mean latency", `${number(report.average)} ms`],
                  ["p95 latency", `${number(report.p95)} ms`],
                  ["Observed throughput", `${number(report.throughput)} req/s`],
                  ["Rolling-window peak", report.rollingPeak],
                  ["Mean admission gap", `${number(report.meanGap)} ms`],
                  ["Longest admission gap", `${number(report.maxGap)} ms`],
                ].map(([title, value]) => (
                  <div key={title}>
                    <dt>{title}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
              </dl>
              <p className="report-foot">
                {report.profile} · quota {report.limit}/{report.window}s ·{" "}
                {number(report.duration)}s observed
                <br />
                {report.quotaBlocked} quota blocks · {report.activeBlocked}{" "}
                active-limit blocks
              </p>
            </article>
          ))}
        </div>
      )}
      <div className="comparison-foot">
        <ShieldCheck size={16} />
        <p>
          Sliding Window Log checks the exact rolling cap. Token Bucket checks
          capacity + earned refill. A lower drop rate alone does not mean
          greater accuracy. Latency includes the browser, proxy, network, and
          API.
        </p>
      </div>
    </section>
  );
}
