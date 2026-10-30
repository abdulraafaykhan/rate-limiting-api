import {
  Activity,
  ArrowUpRight,
  BarChart3,
  FlaskConical,
  ShieldCheck,
} from "lucide-react";
import { useLab } from "./hooks/useLab.js";
import { AnalyticsPanel } from "./components/AnalyticsPanel.jsx";
import { LivePanel } from "./components/LivePanel.jsx";
import { RequestLog } from "./components/RequestLog.jsx";
import { ResultsPanel } from "./components/ResultsPanel.jsx";
import { SetupPanel } from "./components/SetupPanel.jsx";

export default function App() {
  const lab = useLab();
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#overview">
            <span className="brand-icon">
              <Activity size={21} />
            </span>
            Rate Limit<span className="brand-light">Lab</span>
          </a>
          <nav aria-label="Main navigation">
            <a className="active" href="#overview">
              <FlaskConical size={15} /> Playground
            </a>
            <a href="#comparison">
              <BarChart3 size={15} /> Comparison
            </a>
            <a href="#analytics">User analytics</a>
          </nav>
          <a
            className="docs-link"
            href="/docs"
            target="_blank"
            rel="noreferrer"
          >
            API docs <ArrowUpRight size={14} />
          </a>
        </div>
      </header>
      <main id="overview">
        <div className="page-heading">
          <div>
            <p className="eyebrow">FASTAPI + REDIS / EXPERIMENT WORKSPACE</p>
            <h1>
              Put your rate limits to the test<span>.</span>
            </h1>
            <p>
              Send real traffic. Watch quota recover. Understand the trade-offs.
            </p>
          </div>
          <div
            className={`health-badge ${lab.health?.status === "ok" ? "healthy" : ""}`}
          >
            <span className="dot" />
            {lab.health == null
              ? "Checking API…"
              : lab.health.status === "ok"
                ? "API & Redis online"
                : "API unavailable"}
          </div>
        </div>
        {lab.error && (
          <div className="error-banner" role="alert">
            <span>{lab.error}</span>
            <button aria-label="Dismiss error" onClick={() => lab.setError("")}>
              ×
            </button>
          </div>
        )}
        <div className="workspace-grid">
          <SetupPanel lab={lab} />
          <LivePanel lab={lab} />
        </div>
        <ResultsPanel lab={lab} />
        <AnalyticsPanel lab={lab} />
        <RequestLog records={lab.records} />
        <footer>
          <span>
            <ShieldCheck size={14} /> Handwritten algorithms. Atomic Redis
            decisions.
          </span>
          <span>Rate Limit Lab · Local testing workspace</span>
        </footer>
      </main>
    </>
  );
}
