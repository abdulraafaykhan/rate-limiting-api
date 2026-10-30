import {
  FlaskConical,
  KeyRound,
  Play,
  ShieldCheck,
  Square,
} from "lucide-react";
import { ALGORITHMS, PROFILES } from "../lib/experiments.js";
import { SectionTitle } from "./shared.jsx";

// ----- Connection and traffic controls -----
export function SetupPanel({ lab }) {
  const { form, setForm, running } = lab;
  const update = (name, value) =>
    setForm((previous) => ({ ...previous, [name]: value }));
  const ids = lab.users.length
    ? lab.users.map((user) => user.user_id)
    : Array.from({ length: 8 }, (_, i) => `user_${101 + i}`);
  return (
    <section className="panel setup-panel" aria-labelledby="setup-heading">
      <SectionTitle eyebrow="01 / CONFIGURE" title="Set up your experiment">
        <FlaskConical size={19} />
      </SectionTitle>
      <div className="connection-box">
        <label htmlFor="admin-key">
          Admin API key <span>Required to reset test quotas</span>
        </label>
        <div className="connect-row">
          <div className="input-icon">
            <KeyRound size={15} />
            <input
              id="admin-key"
              type="password"
              value={lab.adminKey}
              placeholder="Enter admin key"
              autoComplete="off"
              disabled={running}
              onChange={(e) => {
                lab.setAdminKey(e.target.value);
              }}
            />
          </div>
          <button
            className="button secondary"
            onClick={lab.connect}
            disabled={running || lab.connecting}
          >
            {lab.connecting
              ? "Connecting…"
              : lab.connected
                ? "Reconnect"
                : "Connect"}
          </button>
        </div>
        <small>
          Demo default: <code>admin-secret-key</code>. Keys stay in this tab’s
          memory.
        </small>
      </div>
      <fieldset disabled={running}>
        <div className="field-grid">
          <label>
            User
            <select
              value={lab.userId}
              onChange={(e) => lab.chooseUser(e.target.value)}
            >
              {ids.map((id) => (
                <option key={id}>{id}</option>
              ))}
            </select>
          </label>
          <label>
            Algorithm
            <select
              value={form.algorithm}
              onChange={(e) => update("algorithm", e.target.value)}
            >
              <option value="both">Compare both algorithms</option>
              {Object.entries(ALGORITHMS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="field-spaced">
          User API key
          <input
            value={lab.userKey}
            autoComplete="off"
            onChange={(e) => {
              lab.setUserKey(e.target.value);
            }}
          />
        </label>
        <label className="field-spaced">
          Traffic profile
          <select
            value={form.profile}
            onChange={(e) => update("profile", e.target.value)}
          >
            {Object.entries(PROFILES).map(([value, profile]) => (
              <option key={value} value={value}>
                {profile.title}
              </option>
            ))}
          </select>
        </label>
        <p className="field-description">{PROFILES[form.profile].detail}</p>
        <div className="field-grid three">
          <label>
            Requests
            <input
              type="number"
              min="1"
              max="500"
              value={form.count}
              onChange={(e) => update("count", e.target.value)}
            />
          </label>
          <label>
            Quota
            <input
              type="number"
              min="1"
              max="1000"
              value={form.limit}
              onChange={(e) => update("limit", e.target.value)}
            />
          </label>
          <label>
            Window (s)
            <input
              type="number"
              min="1"
              max="3600"
              value={form.profile === "concurrency" ? 3600 : form.window}
              disabled={form.profile === "concurrency"}
              onChange={(e) => update("window", e.target.value)}
            />
          </label>
        </div>
        <div className="quick-counts">
          <span>Quick select</span>
          {[10, 20, 100, 500].map((value) => (
            <button
              key={value}
              className={
                Number(form.count) === value ? "chip selected" : "chip"
              }
              onClick={() => update("count", value)}
            >
              {value}
            </button>
          ))}
        </div>
      </fieldset>
      <div className="fresh-note">
        <ShieldCheck size={16} />
        <span>
          Fresh quota before each algorithm. Applies only to the selected user.
        </span>
      </div>
      <div className="run-actions">
        <button
          className="button primary"
          disabled={!lab.connected || running || lab.connecting}
          onClick={lab.run}
        >
          <Play size={15} fill="currentColor" />
          {running
            ? "Experiment running…"
            : form.algorithm === "both"
              ? "Run comparison"
              : "Run experiment"}
        </button>
        {running && (
          <button className="button secondary" onClick={lab.stop}>
            <Square size={13} />
            Stop
          </button>
        )}
      </div>
      <div
        className="run-progress"
        role="progressbar"
        aria-label="Experiment progress"
        aria-valuenow={Math.round(lab.progress)}
        aria-valuemin="0"
        aria-valuemax="100"
      >
        <span style={{ width: `${lab.progress}%` }} />
      </div>
    </section>
  );
}
