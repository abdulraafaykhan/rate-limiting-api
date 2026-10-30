import { SectionTitle, number } from "./shared.jsx";

// ----- Bounded request log with the actual HTTP response headers -----
export function RequestLog({ records }) {
  const visible = records.slice(-40).reverse();
  return (
    <section className="panel">
      <SectionTitle title="Request activity">
        <span className="muted small">
          Last 40 responses · current algorithm
        </span>
      </SectionTitle>
      <div className="table-scroll request-log">
        <table>
          <thead>
            <tr>
              <th>Request</th>
              <th>Response</th>
              <th>Remaining</th>
              <th>Retry-After</th>
              <th>Latency</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.id}>
                <td>#{String(row.id).padStart(3, "0")}</td>
                <td>
                  <span
                    className={`status-code ${row.status === 200 ? "ok" : row.status === 429 ? "blocked" : "failed"}`}
                  >
                    {row.status || "NETWORK ERROR"}
                  </span>
                </td>
                <td>{Number.isFinite(row.remaining) ? row.remaining : "—"}</td>
                <td>{row.retry == null ? "—" : `${row.retry}s`}</td>
                <td>{number(row.latency)} ms</td>
                <td>{row.reason}</td>
              </tr>
            ))}
            {!visible.length && (
              <tr>
                <td colSpan="6" className="table-empty">
                  Your real API responses will appear here when a test starts.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
