/**
 * ChartCard — wrapper for dashboard chart sections.
 *
 * Props:
 *   title     — chart heading string
 *   period    — optional period label shown as a badge (e.g. "Last 30 days")
 *   children  — Recharts ResponsiveContainer or any chart content
 *   className — extra class names for the outer div
 */
export default function ChartCard({ title, period, children, className = "" }) {
  return (
    <div className={`chart-card ${className}`}>
      <div className="chart-card-header">
        <h3 className="chart-card-title">{title}</h3>
        {period && <span className="chart-period-badge">{period}</span>}
      </div>
      <div className="chart-card-body">{children}</div>
    </div>
  );
}
