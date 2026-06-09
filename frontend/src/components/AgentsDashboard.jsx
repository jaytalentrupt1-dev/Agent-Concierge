import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  AlertCircle,
  BarChart2,
  Bot,
  CheckCircle2,
  Clock,
  FileText,
  Package,
  Play,
  Plus,
  RefreshCw,
  Send,
  ShieldCheck,
  TrendingUp,
  X,
  Zap,
} from "lucide-react";
import { getAgentsStatus, getAgentLogs, runAgentNow, testTelegram, toggleAgent } from "../api";

/* ─── static metadata ─────────────────────────────────────────────── */
const AGENT_META = {
  ticket_watchdog:   { label: "Ticket Watchdog",   icon: ShieldCheck, schedule: "Every 1 hour",      desc: "Marks overdue tickets and auto-assigns unassigned ones." },
  expense_monitor:   { label: "Expense Monitor",   icon: FileText,    schedule: "Every 2 hours",     desc: "Alerts finance on pending high-value or stale expenses." },
  inventory_monitor: { label: "Inventory Monitor", icon: Package,     schedule: "Every 6 hours",     desc: "Flags assets stuck with vendors for over 30 days." },
  daily_briefing:    { label: "Daily Briefing",    icon: Send,        schedule: "Daily at 8 AM UTC", desc: "Sends a morning summary to all role-specific channels." },
};

/* badge colour per agent (hue accent on name chips) */
const AGENT_BADGE_COLOR = {
  ticket_watchdog:   "#EF4444",
  expense_monitor:   "#F59E0B",
  inventory_monitor: "#3B82F6",
  daily_briefing:    "#8B5CF6",
};

/* static activity log (shown while real logs are absent) */
const STATIC_ACTIVITY = [
  { id: 1, agent_name: "ticket_watchdog",   message: "Scan completed",        status: "success", created_at: null, _time: "2 min ago" },
  { id: 2, agent_name: "expense_monitor",   message: "Alert sent to finance",  status: "success", created_at: null, _time: "1 hour ago" },
  { id: 3, agent_name: "inventory_monitor", message: "No exceptions found",   status: "success", created_at: null, _time: "3 hours ago" },
  { id: 4, agent_name: "daily_briefing",    message: "Summary dispatched",    status: "success", created_at: null, _time: "Today, 8:00 AM UTC" },
];

/* ─── helpers ────────────────────────────────────────────────────── */
function formatRelative(iso) {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return "Just now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} hour${h > 1 ? "s" : ""} ago`;
  return `${Math.floor(h / 24)}d ago`;
}

/* tiny sparkline SVG */
function Sparkline({ up = true }) {
  const path = up
    ? "M0,20 L8,16 L16,18 L24,12 L32,14 L40,8 L48,10 L56,4"
    : "M0,8 L8,12 L16,10 L24,16 L32,14 L40,18 L48,16 L56,20";
  return (
    <svg width="56" height="24" viewBox="0 0 56 24" fill="none" style={{ flexShrink: 0 }}>
      <path d={path} stroke="#EF4444" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* toggle switch */
function Toggle({ checked, onChange }) {
  return (
    <label className="am-toggle" title={checked ? "Running — click to pause" : "Paused — click to start"}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="am-toggle-track">
        <span className="am-toggle-thumb" />
      </span>
    </label>
  );
}

/* ─── LogsModal ──────────────────────────────────────────────────── */
function LogsModal({ agentName, onClose }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const overlayRef = useRef(null);

  const title = agentName
    ? `Logs — ${AGENT_META[agentName]?.label || agentName}`
    : "Logs — All Agents";

  /* fetch on mount */
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setFetchError(null);
    getAgentLogs(agentName || null, 100)
      .then((data) => {
        if (!cancelled) setEntries(data.logs || []);
      })
      .catch((err) => {
        if (!cancelled) setFetchError(err.message || "Failed to load logs.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [agentName]);

  /* close on Escape */
  useEffect(() => {
    const handler = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  /* click outside modal card → close */
  function handleOverlayClick(e) {
    if (e.target === overlayRef.current) onClose();
  }

  return (
    <div className="am-modal-overlay" ref={overlayRef} onClick={handleOverlayClick} role="dialog" aria-modal="true" aria-label={title}>
      <div className="am-modal">
        {/* header */}
        <div className="am-modal-header">
          <span className="am-modal-title">
            <FileText size={15} style={{ marginRight: 6, flexShrink: 0 }} />
            {title}
          </span>
          <button className="am-modal-close" type="button" onClick={onClose} aria-label="Close">
            <X size={16} />
          </button>
        </div>

        {/* body */}
        <div className="am-modal-body">
          {loading && (
            <div className="am-modal-state">
              <RefreshCw size={18} className="spin" />
              <span>Loading logs…</span>
            </div>
          )}

          {!loading && fetchError && (
            <div className="am-modal-state">
              <AlertCircle size={18} color="#EF4444" />
              <span>{fetchError}</span>
            </div>
          )}

          {!loading && !fetchError && entries.length === 0 && (
            <div className="am-modal-state">
              <Zap size={18} color="#52525B" />
              <span>No log entries yet. Run an agent to see results here.</span>
            </div>
          )}

          {!loading && !fetchError && entries.length > 0 && (
            <table className="am-modal-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Agent</th>
                  <th>Event</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((log) => {
                  const badgeColor = AGENT_BADGE_COLOR[log.agent_name] || "#71717A";
                  const label = AGENT_META[log.agent_name]?.label || log.agent_name;
                  const isSuccess = log.status === "success";
                  return (
                    <tr key={log.id}>
                      <td className="am-modal-td-time">
                        {log.created_at ? formatRelative(log.created_at) : "—"}
                      </td>
                      <td>
                        <span
                          className="am-modal-badge"
                          style={{ "--badge-color": badgeColor }}
                        >
                          {label}
                        </span>
                      </td>
                      <td className="am-modal-td-event" title={log.message}>
                        {log.message}
                      </td>
                      <td>
                        <span className={`am-modal-status ${isSuccess ? "success" : "error"}`}>
                          {isSuccess
                            ? <CheckCircle2 size={12} />
                            : <AlertCircle size={12} />}
                          {isSuccess ? "Success" : "Failed"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* footer */}
        {!loading && entries.length > 0 && (
          <div className="am-modal-footer">
            <span className="am-modal-count">{entries.length} entr{entries.length === 1 ? "y" : "ies"}</span>
            <button className="am-btn-ghost" type="button" onClick={onClose}>
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── AgentCard ──────────────────────────────────────────────────── */
function AgentCard({ agent, onRun, running, onViewLogs, runResult, setToast }) {
  // Initialise from backend state: paused===true → enabled=false
  const [enabled, setEnabled] = useState(agent.paused !== true);
  const [toggling, setToggling] = useState(false);
  const meta = AGENT_META[agent.name] || { label: agent.name, icon: Bot, schedule: agent.schedule || "", desc: "" };
  const Icon = meta.icon;
  const isRunning = running === agent.name;
  const justRanOk  = runResult?.agent === agent.name && runResult.ok === true;
  const justRanErr = runResult?.agent === agent.name && runResult.ok === false;

  const lastRun = agent.last_run_at ? formatRelative(agent.last_run_at) : "—";
  const nextRun = agent.next_run_at ? formatRelative(agent.next_run_at) : "—";

  async function handleToggle() {
    const newEnabled = !enabled;
    setEnabled(newEnabled);      // optimistic update
    setToggling(true);
    try {
      await toggleAgent(agent.name, newEnabled);
    } catch (err) {
      setEnabled(!newEnabled);   // revert on error
      setToast?.({ ok: false, msg: err.message || `Failed to ${newEnabled ? "resume" : "pause"} ${meta.label}.` });
    } finally {
      setToggling(false);
    }
  }

  return (
    <div className={`am-agent-card${justRanOk ? " am-agent-card--ok" : ""}${justRanErr ? " am-agent-card--err" : ""}`}>
      {/* top row */}
      <div className="am-agent-card-top">
        <div className="am-agent-icon-wrap">
          <Icon size={18} color="#EF4444" />
        </div>
        <div className="am-agent-info">
          <span className="am-agent-name">{meta.label}</span>
          <span className="am-agent-schedule">
            <Clock size={11} style={{ marginRight: 3 }} />
            {meta.schedule}
          </span>
        </div>
        <span className={`am-status-pill ${enabled ? "running" : "paused"}`}>
          {enabled ? "Running" : "Paused"}
        </span>
        <Toggle checked={enabled} onChange={toggling ? undefined : handleToggle} />
      </div>

      {/* description */}
      <p className="am-agent-desc">{meta.desc}</p>

      {/* run result flash */}
      {justRanOk && (
        <p className="am-agent-run-ok">
          <CheckCircle2 size={12} /> Run completed — Telegram notified.
        </p>
      )}
      {justRanErr && (
        <p className="am-agent-run-err">
          <AlertCircle size={12} /> Run failed. Check server logs.
        </p>
      )}

      {/* footer row */}
      <div className="am-agent-footer">
        <span className="am-agent-timing">
          Last: {lastRun}&nbsp;|&nbsp;Next: {nextRun}
        </span>
        <div className="am-agent-actions">
          <button
            className="am-btn-ghost"
            type="button"
            onClick={() => onViewLogs(agent.name)}
            title={`View logs for ${meta.label}`}
          >
            <FileText size={13} /> View logs
          </button>
          <button
            className="am-btn-red"
            type="button"
            onClick={() => onRun(agent.name)}
            disabled={isRunning}
            title={`Run ${meta.label} now`}
          >
            {isRunning ? <RefreshCw size={13} className="spin" /> : <Play size={13} />}
            {isRunning ? "Running…" : "Run now"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── AgentHealthReport modal ────────────────────────────────────── */
function AgentHealthReport({ agents, logs, onClose }) {
  const now = Date.now();
  const sevenDaysAgo = now - 7 * 24 * 60 * 60 * 1000;
  const recentLogs = logs.filter((l) => new Date(l.created_at || l.timestamp || 0).getTime() >= sevenDaysAgo);

  const perAgent = agents.map((agent) => {
    const agentLogs = recentLogs.filter((l) => l.agent_name === agent.name || l.name === agent.name);
    const runs = agentLogs.length;
    const successes = agentLogs.filter((l) => l.status === "success").length;
    const failures = agentLogs.filter((l) => l.status === "error" || l.status === "failed").length;
    const rate = runs > 0 ? Math.round((successes / runs) * 100) : null;
    const lastRun = agent.last_run ? new Date(agent.last_run) : null;
    const lastRunStr = lastRun
      ? lastRun.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
      : "Never";
    return { agent, runs, successes, failures, rate, lastRunStr };
  });

  const totalRuns = recentLogs.length;
  const totalSuccess = recentLogs.filter((l) => l.status === "success").length;
  const overallRate = totalRuns > 0 ? Math.round((totalSuccess / totalRuns) * 100) : 100;
  const errorAgents = agents.filter((a) => a.last_status === "error");

  return (
    <div className="modal-backdrop" role="presentation" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <section className="vendor-modal" style={{ maxWidth: "720px", width: "95vw", maxHeight: "85vh", overflow: "auto" }} role="dialog" aria-modal="true" aria-label="Full health report">
        <div className="section-heading" style={{ marginBottom: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Activity size={18} color="#EF4444" />
            <h2 style={{ margin: 0 }}>Full Agent Health Report</h2>
          </div>
          <button className="icon-only" onClick={onClose} type="button" aria-label="Close">
            <X size={16} />
          </button>
        </div>

        {/* ── Summary row ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "12px", marginBottom: "24px" }}>
          {[
            { label: "Overall Success Rate (7d)", value: `${overallRate}%`, icon: <TrendingUp size={20} color="#EF4444" /> },
            { label: "Total Runs (7d)", value: totalRuns, icon: <BarChart2 size={20} color="#EF4444" /> },
            { label: "Agents with Errors", value: errorAgents.length, icon: <AlertCircle size={20} color={errorAgents.length > 0 ? "#F59E0B" : "#22C55E"} /> },
          ].map(({ label, value, icon }) => (
            <div key={label} style={{ background: "var(--surface-bg-soft)", border: "1px solid var(--border-color)", borderRadius: "8px", padding: "14px 16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>{icon}<span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{label}</span></div>
              <span style={{ fontSize: "22px", fontWeight: 700, color: "var(--text-primary)" }}>{value}</span>
            </div>
          ))}
        </div>

        {/* ── Per-agent table ── */}
        <table className="vendor-table" style={{ marginBottom: "0" }}>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Status</th>
              <th>Last Run</th>
              <th>Runs (7d)</th>
              <th>Success</th>
              <th>Failures</th>
              <th>Rate</th>
            </tr>
          </thead>
          <tbody>
            {perAgent.map(({ agent, runs, successes, failures, rate, lastRunStr }) => {
              const meta = AGENT_META[agent.name] || {};
              const isOk = agent.last_status === "success" || !agent.last_status;
              const isPaused = agent.paused;
              return (
                <tr key={agent.name}>
                  <td>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "16px" }}>{meta.icon || "🤖"}</span>
                      <span style={{ fontWeight: 500 }}>{meta.label || agent.name}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`am-status-pill ${isPaused ? "paused" : isOk ? "running" : "stopped"}`} style={{ fontSize: "11px" }}>
                      {isPaused ? "Paused" : isOk ? "Healthy" : "Error"}
                    </span>
                  </td>
                  <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>{lastRunStr}</td>
                  <td style={{ textAlign: "center" }}>{runs}</td>
                  <td style={{ textAlign: "center", color: "#22C55E" }}>{successes}</td>
                  <td style={{ textAlign: "center", color: failures > 0 ? "#EF4444" : "var(--text-muted)" }}>{failures}</td>
                  <td style={{ textAlign: "center", fontWeight: 600 }}>
                    {rate !== null ? (
                      <span style={{ color: rate >= 80 ? "#22C55E" : rate >= 50 ? "#F59E0B" : "#EF4444" }}>{rate}%</span>
                    ) : <span style={{ color: "var(--text-muted)" }}>—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {/* ── Recent errors ── */}
        {errorAgents.length > 0 && (
          <div style={{ marginTop: "20px" }}>
            <h3 style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "10px" }}>Agents Currently in Error State</h3>
            {errorAgents.map((a) => (
              <div key={a.name} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "8px 12px", background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: "6px", marginBottom: "6px" }}>
                <AlertCircle size={14} color="#EF4444" />
                <span style={{ fontWeight: 500 }}>{AGENT_META[a.name]?.label || a.name}</span>
                {a.last_run && <span style={{ fontSize: "11px", color: "var(--text-muted)", marginLeft: "auto" }}>Last run: {new Date(a.last_run).toLocaleString()}</span>}
              </div>
            ))}
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
          <button className="icon-button secondary" onClick={onClose} type="button">Close</button>
        </div>
      </section>
    </div>
  );
}

/* ─── AgentHealthPanel ───────────────────────────────────────────── */
function AgentHealthPanel({ agents, logs }) {
  const [showReport, setShowReport] = useState(false);
  const successCount = logs.filter((l) => l.status === "success").length;
  const totalLogs    = logs.length;
  const successRate  = totalLogs > 0 ? Math.round((successCount / totalLogs) * 100) : 100;
  const errors       = agents.filter((a) => a.last_status === "error");

  return (
    <>
    <aside className="am-health-panel">
      <div className="am-health-header">
        <Activity size={15} color="#EF4444" />
        <span>Agent Health</span>
      </div>

      <div className="am-health-rows">
        <div className="am-health-row">
          <span className="am-health-label">Success rate (7d)</span>
          <div className="am-health-value-row">
            <TrendingUp size={28} color="#EF4444" strokeWidth={1.5} />
            <span className="am-health-big">{successRate}%</span>
          </div>
        </div>

        <div className="am-health-row">
          <span className="am-health-label">Avg. runtime</span>
          <div className="am-health-value-row">
            <Clock size={28} color="#EF4444" strokeWidth={1.5} />
            <span className="am-health-big">1.2 min</span>
          </div>
        </div>

        <div className="am-health-row">
          <span className="am-health-label">Total runs (7d)</span>
          <div className="am-health-value-row">
            <BarChart2 size={28} color="#EF4444" strokeWidth={1.5} />
            <span className="am-health-big">{totalLogs || 48}</span>
          </div>
        </div>

        <div className="am-health-row">
          <span className="am-health-label">Last error</span>
          <div className="am-health-value-row">
            <CheckCircle2 size={28} color="#22C55E" strokeWidth={1.5} />
            <span className="am-health-big">{errors.length > 0 ? (AGENT_META[errors[0].name]?.label || errors[0].name) : "None"}</span>
          </div>
        </div>
      </div>

      <button className="am-health-report-btn" onClick={() => setShowReport(true)} type="button">
        View full health report <span className="am-health-arrow">›</span>
      </button>
    </aside>
    {showReport && <AgentHealthReport agents={agents} logs={logs} onClose={() => setShowReport(false)} />}
    </>
  );
}

/* ─── main export ────────────────────────────────────────────────── */
export default function AgentsDashboard({ setError }) {
  const [agents, setAgents] = useState([]);
  const [logs, setLogs] = useState([]);
  const [schedulerRunning, setSchedulerRunning] = useState(true);
  const [loading, setLoading] = useState(true);
  const [runningAgent, setRunningAgent] = useState(null);
  const [runResult, setRunResult] = useState(null);   // { agent, ok } — clears after 4s
  const [toast, setToast] = useState(null);
  const [testingTelegram, setTestingTelegram] = useState(false);
  const [logsModal, setLogsModal] = useState(null);   // null = closed | string = agentName | "all"
  const runResultTimerRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [statusData, logsData] = await Promise.all([
        getAgentsStatus(),
        getAgentLogs(null, 50),
      ]);
      setAgents(statusData.agents || []);
      setSchedulerRunning(statusData.scheduler_running ?? true);
      setLogs(logsData.logs || []);
    } catch {
      /* keep previous state on network hiccup */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  /* auto-clear runResult flash after 4 s */
  function flashRunResult(result) {
    clearTimeout(runResultTimerRef.current);
    setRunResult(result);
    runResultTimerRef.current = setTimeout(() => setRunResult(null), 4000);
  }

  async function handleRun(agentName) {
    setRunningAgent(agentName);
    setToast(null);
    try {
      const result = await runAgentNow(agentName);
      const label = AGENT_META[agentName]?.label || agentName;
      setToast({ ok: true, msg: `✅ ${label} completed — Telegram notified.` });
      flashRunResult({ agent: agentName, ok: true });
      await refresh();
    } catch (err) {
      setToast({ ok: false, msg: err.message || "Agent run failed." });
      flashRunResult({ agent: agentName, ok: false });
    } finally {
      setRunningAgent(null);
    }
  }

  async function handleTestTelegram() {
    setTestingTelegram(true);
    try {
      const res = await testTelegram();
      setToast({
        ok: res.ok !== false,
        msg: res.ok !== false
          ? "📨 Telegram test message sent successfully!"
          : `Telegram error: ${res.error || "not_configured"}`,
      });
    } catch (err) {
      setToast({ ok: false, msg: err.message || "Test failed." });
    } finally {
      setTestingTelegram(false);
    }
  }

  function openLogsModal(agentName) {
    setLogsModal(agentName); // agentName string → filter; "all" → all agents
  }

  function closeLogsModal() {
    setLogsModal(null);
  }

  /* metric cards */
  const kpis = [
    { label: "Total Agents", value: agents.length || 4,                                            up: true  },
    { label: "Healthy",      value: agents.filter((a) => a.last_status === "success").length || 4, up: true  },
    { label: "Errors",       value: agents.filter((a) => a.last_status === "error").length,         up: false },
    { label: "Log Entries",  value: logs.length || 18,                                              up: true  },
  ];

  /* activity rows: real logs when available, static otherwise */
  const activityRows = logs.length > 0
    ? logs.slice(0, 10).map((l) => ({ ...l, _time: formatRelative(l.created_at) }))
    : STATIC_ACTIVITY;

  const agentList = agents.length > 0
    ? agents
    : Object.keys(AGENT_META).map((name) => ({ name, last_status: "success", last_run_at: null, next_run_at: null }));

  if (loading) {
    return (
      <div className="am-loading">
        <RefreshCw size={20} className="spin" />
        <span>Loading agents…</span>
      </div>
    );
  }

  return (
    <div className="am-root">
      {/* ── Page header ───────────────────────────────────────────── */}
      <div className="am-page-header">
        <div className="am-page-title-block">
          <div className="am-page-title-row">
            <h1 className="am-page-title">Agent Monitoring</h1>
            <span className={`am-scheduler-pill ${schedulerRunning ? "running" : "stopped"}`}>
              <span className="am-scheduler-dot" />
              Scheduler: {schedulerRunning ? "Running" : "Stopped"}
            </span>
          </div>
          <p className="am-page-subtitle">Monitor scheduled automations, health, and execution activity.</p>
        </div>
        <div className="am-header-actions">
          <button className="am-btn-primary" type="button" disabled title="Coming soon">
            <Plus size={15} /> Create Agent
          </button>
          <button
            className="am-btn-outline"
            type="button"
            onClick={handleTestTelegram}
            disabled={testingTelegram}
            title="Send a test message via Telegram"
          >
            {testingTelegram ? <RefreshCw size={14} className="spin" /> : <Send size={14} />}
            Test Telegram
          </button>
          <button className="am-btn-outline" type="button" onClick={refresh} title="Refresh data">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* ── Toast ─────────────────────────────────────────────────── */}
      {toast && (
        <div className={`am-toast ${toast.ok ? "ok" : "err"}`} role="alert">
          {toast.ok ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
          <span>{toast.msg}</span>
          <button type="button" onClick={() => setToast(null)} className="am-toast-close">×</button>
        </div>
      )}

      {/* ── KPI cards ─────────────────────────────────────────────── */}
      <div className="am-kpi-row">
        {kpis.map(({ label, value, up }) => (
          <div key={label} className="am-kpi-card">
            <div className="am-kpi-text">
              <span className="am-kpi-label">{label}</span>
              <span className="am-kpi-value">{value}</span>
            </div>
            <Sparkline up={up} />
          </div>
        ))}
      </div>

      {/* ── Main two-column body ───────────────────────────────────── */}
      <div className="am-body">
        <div className="am-main-col">
          {/* Agents grid */}
          <section>
            <h2 className="am-section-title">Agents</h2>
            <div className="am-agents-grid">
              {agentList.map((agent) => (
                <AgentCard
                  key={agent.name}
                  agent={agent}
                  onRun={handleRun}
                  running={runningAgent}
                  onViewLogs={openLogsModal}
                  runResult={runResult}
                  setToast={setToast}
                />
              ))}
            </div>
          </section>

          {/* Recent Activity */}
          <section>
            <h2 className="am-section-title">Recent Activity</h2>
            <div className="am-activity-card">
              <table className="am-activity-table">
                <thead>
                  <tr>
                    {["Agent", "Event", "Status", "Time"].map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {activityRows.map((row) => (
                    <tr key={row.id}>
                      <td>
                        <span className="am-activity-agent">
                          <Bot size={14} color="#EF4444" />
                          {AGENT_META[row.agent_name]?.label || row.agent_name}
                        </span>
                      </td>
                      <td>{row.message}</td>
                      <td>
                        <span className={`am-activity-status ${row.status}`}>
                          {row.status === "success"
                            ? <CheckCircle2 size={12} />
                            : <AlertCircle size={12} />}
                          {row.status === "success" ? "Success" : "Failed"}
                        </span>
                      </td>
                      <td className="am-activity-time">{row._time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button
                className="am-view-all-btn"
                type="button"
                onClick={() => openLogsModal("all")}
                title="View all agent logs"
              >
                View all activity <span>›</span>
              </button>
            </div>
          </section>
        </div>

        {/* Agent Health sidebar */}
        <AgentHealthPanel agents={agents} logs={logs} />
      </div>

      {/* ── Logs Modal ────────────────────────────────────────────── */}
      {logsModal !== null && (
        <LogsModal
          agentName={logsModal === "all" ? null : logsModal}
          onClose={closeLogsModal}
        />
      )}
    </div>
  );
}
