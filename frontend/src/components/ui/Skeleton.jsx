/**
 * Skeleton loading components used across all pages.
 * The shimmer animation is driven by the `.skeleton` CSS class in globals.css.
 * Each wrapper class (skeleton-card, skeleton-kpi-row, etc.) also lives in globals.css
 * so dark/light mode is handled automatically.
 */

/** Base shimmer block — drop-in anywhere a piece of content is expected. */
export function Skeleton({ width = "100%", height = "16px", borderRadius = "6px", className = "", style = {} }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius, display: "block", flexShrink: 0, ...style }}
    />
  );
}

/** Mimics a generic data card (e.g. Insight / Agent card). */
export function SkeletonCard({ rows = 3 }) {
  return (
    <div className="skeleton-card">
      <Skeleton height="14px" width="40%" />
      <Skeleton height="32px" width="60%" />
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} height="12px" width={`${70 + i * 10}%`} />
      ))}
    </div>
  );
}

/** Mimics a data table with a header row + N body rows. */
export function SkeletonTable({ rows = 5, cols = 5 }) {
  return (
    <div className="skeleton-table" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
      {/* Header */}
      <div className="skeleton-row skeleton-header" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {Array.from({ length: cols }, (_, i) => (
          <Skeleton key={i} height="12px" width="80%" />
        ))}
      </div>
      {/* Body rows */}
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton-row" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
          {Array.from({ length: cols }, (_, j) => (
            <Skeleton key={j} height="14px" width={j === 0 ? "60%" : "80%"} />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Mimics the KPI card row at the top of the dashboard. */
export function SkeletonKpiRow({ count = 6 }) {
  return (
    <div className="skeleton-kpi-row">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton-kpi-card">
          <Skeleton height="12px" width="50%" />
          <Skeleton height="28px" width="40%" />
        </div>
      ))}
    </div>
  );
}

/** Mimics a single chart card. */
export function SkeletonChart() {
  return (
    <div className="skeleton-chart-card">
      <Skeleton height="14px" width="30%" />
      <Skeleton height="180px" width="100%" borderRadius="8px" />
    </div>
  );
}

/** Full dashboard skeleton: KPI row + chart grid. */
export function SkeletonDashboard() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px", padding: "0" }}>
      <SkeletonKpiRow count={6} />
      <div className="skeleton-chart-grid">
        <SkeletonChart />
        <SkeletonChart />
        <SkeletonChart />
      </div>
    </div>
  );
}

/**
 * App-shell skeleton — shown during the initial checkingAuth phase.
 * Mimics the full header + nav + content layout so there's never a blank screen.
 */
export function SkeletonAppShell({ activeTab = "dashboard" }) {
  return (
    <div className="skeleton-app-shell">
      {/* Top bar */}
      <div className="skeleton-topbar">
        <div className="skeleton-brand">
          <div className="skeleton skeleton-brand-mark" />
          <Skeleton height="14px" width="120px" borderRadius="4px" />
        </div>
        <div className="skeleton-topbar-right">
          <Skeleton height="34px" width="220px" borderRadius="8px" />
          <Skeleton height="34px" width="38px"  borderRadius="10px" />
          <Skeleton height="34px" width="64px"  borderRadius="999px" />
          <Skeleton height="34px" width="120px" borderRadius="10px" />
        </div>
      </div>

      {/* Nav tabs */}
      <div className="skeleton-nav">
        {[80, 70, 60, 80, 90, 70, 80, 60, 50].map((w, i) => (
          <Skeleton key={i} height="28px" width={`${w}px`} borderRadius="8px" />
        ))}
      </div>

      {/* Page content */}
      <div className="skeleton-main">
        <SkeletonPageContent activeTab={activeTab} />
      </div>
    </div>
  );
}

/** Picks the right skeleton for each tab. */
export function SkeletonPageContent({ activeTab }) {
  switch (activeTab) {
    case "dashboard":
      return <SkeletonDashboard />;
    case "approvals":
      return <SkeletonTable rows={8} cols={6} />;
    case "tasks":
      return <SkeletonTable rows={8} cols={5} />;
    case "vendors":
      return <SkeletonTable rows={6} cols={5} />;
    case "expenses":
      return <SkeletonTable rows={8} cols={6} />;
    case "inventory":
      return <SkeletonTable rows={10} cols={6} />;
    case "travel":
      return <SkeletonTable rows={6} cols={5} />;
    case "reports":
      return <SkeletonTable rows={6} cols={4} />;
    case "agents":
      return (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" }}>
          <SkeletonCard rows={3} />
          <SkeletonCard rows={3} />
          <SkeletonCard rows={3} />
          <SkeletonCard rows={3} />
        </div>
      );
    default:
      return <SkeletonTable rows={6} cols={5} />;
  }
}
