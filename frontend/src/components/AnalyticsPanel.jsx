import { SectionTitle, number } from "./shared.jsx";

// ----- Persistent user analytics and a bounded request log -----
export function AnalyticsPanel({ lab }) {
  const users = lab.analytics?.users || {};
  return (
    <section className="panel" id="analytics">
      <SectionTitle eyebrow="04 / ANALYTICS" title="Traffic by user">
        <span className="tag">LIFETIME DECISIONS</span>
      </SectionTitle>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Allowed</th>
              <th>Blocked</th>
              <th>Throttle rate</th>
              <th>Token Bucket A / B</th>
              <th>Sliding Log A / B</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(users).map(([id, stats]) => {
              const algorithms = lab.analytics.algorithms?.[id] || {};
              const total = stats.allowed + stats.blocked;
              return (
                <tr
                  key={id}
                  className={id === lab.userId ? "current-user" : ""}
                >
                  <td>
                    <span className="user-mark">{id.slice(-2)}</span>
                    {id}
                    {id === lab.userId && (
                      <span className="small muted"> · selected</span>
                    )}
                  </td>
                  <td className="positive">{stats.allowed}</td>
                  <td>{stats.blocked}</td>
                  <td>
                    {total ? number((stats.blocked / total) * 100) : "0"}%
                  </td>
                  <td>
                    {algorithms.token_bucket?.allowed ?? 0} /{" "}
                    {algorithms.token_bucket?.blocked ?? 0}
                  </td>
                  <td>
                    {algorithms.sliding_window_log?.allowed ?? 0} /{" "}
                    {algorithms.sliding_window_log?.blocked ?? 0}
                  </td>
                </tr>
              );
            })}
            {!Object.keys(users).length && (
              <tr>
                <td colSpan="6" className="table-empty">
                  Connect to see actual per-user counters from Redis.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="table-note">
        Allowed / Blocked (A / B) are decisions, not completed work. Quota
        resets preserve analytics. Older totals can predate algorithm-specific
        tracking.
      </p>
    </section>
  );
}
