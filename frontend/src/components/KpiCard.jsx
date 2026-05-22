const cardStyle = {
  display: "flex",
  flexDirection: "row",
  alignItems: "center",
  height: "52px",
  minHeight: "52px",
  maxHeight: "52px",
  padding: "0 14px",
  gap: "10px",
  boxSizing: "border-box",
};

const innerStyle = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  height: "100%",
  width: "100%",
  marginTop: 0,
  marginBottom: 0,
  paddingTop: 0,
  paddingBottom: 0,
};

export default function KpiCard({ icon: Icon, label, value }) {
  return (
    <div className="kpi-card" style={cardStyle}>
      <div style={innerStyle}>
        {Icon && (
          <span className="kpi-icon">
            <Icon size={14} />
          </span>
        )}
        <div className="kpi-text" style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignSelf: "center" }}>
          <span className="kpi-label">{label}</span>
          <span className="kpi-value">{value ?? "—"}</span>
        </div>
      </div>
    </div>
  );
}
