import { useCallback, useEffect, useRef, useState } from "react";
import { request, sendData } from "../lib/api.js";
import { delay, scheduleRequests, summarize } from "../lib/experiments.js";

export function useLab() {
  // ----- Connection and editable experiment settings -----
  const [adminKey, setAdminKey] = useState("");
  const [userKey, setUserKey] = useState("key-user-104");
  const [userId, setUserId] = useState("user_104");
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState({
    algorithm: "both",
    profile: "waves",
    count: 20,
    limit: 10,
    window: 8,
  });
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [history, setHistory] = useState([]);
  const [records, setRecords] = useState([]);
  const [reports, setReports] = useState([]);
  const [running, setRunning] = useState(false);
  const [activeAlgorithm, setActiveAlgorithm] = useState(null);
  const [progress, setProgress] = useState(0);
  const [notice, setNotice] = useState(
    "Connect with your admin key to start a real API test.",
  );
  const runController = useRef(null);
  const runLocked = useRef(false);

  // ----- Public health, live quota and Redis analytics polling -----
  useEffect(() => {
    const controller = new AbortController();
    const check = () =>
      request("/health", { signal: controller.signal })
        .then(({ data }) => setHealth(data))
        .catch(() => {
          if (!controller.signal.aborted) setHealth({ status: "unhealthy" });
        });
    check();
    const timer = setInterval(check, 10000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  const readStatus = useCallback(
    async (signal) => {
      const { data } = await request("/api/status", { key: userKey, signal });
      if (data.user_id !== userId)
        throw new Error("The user API key does not match the selected user.");
      if (signal?.aborted) return data;
      setStatus(data);
      setHistory((previous) => [
        ...previous.slice(-159),
        {
          time: Date.now(),
          remaining: data.remaining_requests,
          limit: data.limit,
        },
      ]);
      return data;
    },
    [userKey, userId],
  );

  const readAnalytics = useCallback(
    async (signal) => {
      const { data } = await request("/api/analytics", {
        key: adminKey,
        signal,
      });
      if (!signal?.aborted) setAnalytics(data);
    },
    [adminKey],
  );

  useEffect(() => {
    if (!connected) return;
    const controller = new AbortController();
    let timer,
      ticks = 0;
    const poll = async () => {
      try {
        await readStatus(controller.signal);
        if (ticks++ % 6 === 0) await readAnalytics(controller.signal);
      } catch (problem) {
        if (!controller.signal.aborted) setError(problem.message);
      }
      if (!controller.signal.aborted) timer = setTimeout(poll, 500);
    };
    poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [connected, readStatus, readAnalytics]);

  useEffect(() => () => runController.current?.abort(), []);

  // ----- Authentication stays in component memory, never localStorage -----
  async function connect() {
    if (!adminKey.trim()) {
      setError("Enter your admin API key first.");
      return;
    }
    setError("");
    setConnecting(true);
    try {
      const { data } = await request("/api/users", { key: adminKey });
      setUsers(data.users);
      await readStatus();
      await readAnalytics();
      setConnected(true);
      setNotice(
        "Connected. Each algorithm starts with a fresh quota for this user.",
      );
    } catch (problem) {
      setConnected(false);
      setError(problem.message);
    } finally {
      setConnecting(false);
    }
  }

  function chooseUser(id) {
    setUserId(id);
    setUserKey(`key-${id.replace("_", "-")}`);
    setStatus(null);
    setHistory([]);
    setRecords([]);
    setReports([]);
  }

  // ----- Real HTTP experiment orchestration, with cooperative cancellation -----
  async function run() {
    if (runLocked.current || !connected) return;
    const config = {
      ...form,
      count: Number(form.count),
      limit: Number(form.limit),
      window: form.profile === "concurrency" ? 3600 : Number(form.window),
    };
    if (
      !Number.isInteger(config.count) ||
      config.count < 1 ||
      config.count > 500 ||
      !Number.isInteger(config.limit) ||
      config.limit < 1 ||
      config.limit > 1000 ||
      !Number.isInteger(config.window) ||
      config.window < 1 ||
      config.window > 3600
    ) {
      setError(
        "Use 1–500 requests, quota 1–1000, and a whole-number window of 1–3600 seconds.",
      );
      return;
    }
    runLocked.current = true;
    const controller = new AbortController();
    runController.current = controller;
    const signal = controller.signal;
    setRunning(true);
    setError("");
    setReports([]);
    setProgress(0);
    const algorithms =
      config.algorithm === "both"
        ? ["token_bucket", "sliding_window_log"]
        : [config.algorithm];
    try {
      // Verify identity before any admin action changes the selected quota.
      await readStatus(signal);
      for (
        let algorithmIndex = 0;
        algorithmIndex < algorithms.length;
        algorithmIndex++
      ) {
        const algorithm = algorithms[algorithmIndex];
        if (signal.aborted) break;
        setActiveAlgorithm(algorithm);
        setRecords([]);
        setHistory([]);
        await request("/api/config", {
          key: adminKey,
          method: "POST",
          signal,
          body: {
            user_id: userId,
            limit: config.limit,
            window_seconds: config.window,
            algorithm,
          },
        });
        await readStatus(signal);
        setNotice(
          `Running ${algorithm.replaceAll("_", " ")} with a fresh quota…`,
        );
        const rows = [];
        const started = performance.now();
        const schedule = scheduleRequests(
          config.count,
          config.profile,
          config.window,
        );
        await Promise.all(
          schedule.map(async (offset, index) => {
            try {
              await delay(
                Math.max(0, offset - (performance.now() - started)),
                signal,
              );
              const row = {
                ...(await sendData(userKey, signal)),
                id: index + 1,
                elapsed: (performance.now() - started) / 1000,
              };
              rows.push(row);
              setRecords((previous) => [...previous, row]);
              setProgress(
                ((algorithmIndex * config.count + rows.length) /
                  (algorithms.length * config.count)) *
                  100,
              );
            } catch (problem) {
              if (signal.aborted) return;
              const row = {
                id: index + 1,
                status: 0,
                latency: 0,
                reason: problem.message,
                elapsed: (performance.now() - started) / 1000,
              };
              rows.push(row);
              setRecords((previous) => [...previous, row]);
            }
          }),
        );
        const summary = summarize(
          rows,
          { ...config, algorithm, userId, cancelled: signal.aborted },
          performance.now() - started,
        );
        setReports((previous) => [...previous, summary]);
        if (signal.aborted) break;
        await readStatus(signal);
        await readAnalytics(signal);
      }
      setNotice(
        signal.aborted
          ? "Stopped. Reports contain completed responses only; in-flight requests may already have consumed quota."
          : "Test complete. Watch the live quota recover, or run another profile.",
      );
      if (!signal.aborted) setProgress(100);
    } catch (problem) {
      if (!signal.aborted) setError(problem.message);
    } finally {
      if (signal.aborted)
        setNotice(
          "Stopped. Reports contain completed responses only; in-flight requests may already have consumed quota.",
        );
      setRunning(false);
      setActiveAlgorithm(null);
      runLocked.current = false;
    }
  }

  function download() {
    const blob = new Blob(
      [
        JSON.stringify(
          { generated_at: new Date().toISOString(), reports },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "rate-limit-comparison.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return {
    adminKey,
    setAdminKey,
    userKey,
    setUserKey,
    userId,
    chooseUser,
    users,
    form,
    setForm,
    connected,
    connecting,
    health,
    error,
    setError,
    status,
    analytics,
    history,
    records,
    reports,
    running,
    activeAlgorithm,
    progress,
    notice,
    connect,
    run,
    stop: () => runController.current?.abort(),
    download,
  };
}
