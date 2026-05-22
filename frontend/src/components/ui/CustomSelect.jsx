import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";

export default function CustomSelect({
  options = [],
  value,
  onChange,
  placeholder = "All",
  width = "160px"
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target))
        setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const selected = options.find((o) => o.value === value);

  return (
    <div ref={ref} style={{ position: "relative", width }}>
      <div
        onClick={() => setOpen(!open)}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
          background: "#141414",
          border: `1px solid ${open ? "rgba(239,68,68,0.6)" : "rgba(255,255,255,0.1)"}`,
          borderRadius: "8px",
          padding: "7px 12px",
          cursor: "pointer",
          fontSize: "13px",
          color: selected ? "#FFFFFF" : "#71717A",
          fontFamily: "Inter, sans-serif",
          transition: "all 0.2s ease",
          userSelect: "none",
          whiteSpace: "nowrap",
        }}
      >
        <span>{selected ? selected.label : placeholder}</span>
        <ChevronDown
          size={13}
          color="#71717A"
          style={{
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s ease",
            flexShrink: 0,
          }}
        />
      </div>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            minWidth: "100%",
            background: "#1A1A1A",
            border: "1px solid #2A2A2A",
            borderRadius: "10px",
            boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
            zIndex: 99999,
            overflow: "hidden",
            animation: "dropdownIn 0.15s ease forwards",
          }}
        >
          {options.map((opt) => {
            const isSel = opt.value === value;
            return (
              <div
                key={opt.value}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
                onMouseEnter={(e) => {
                  if (!isSel) {
                    e.currentTarget.style.background = "rgba(239,68,68,0.07)";
                    e.currentTarget.style.color = "#FFFFFF";
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSel) {
                    e.currentTarget.style.background = "transparent";
                    e.currentTarget.style.color = "#A1A1AA";
                  }
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "9px 14px",
                  fontSize: "13px",
                  fontFamily: "Inter, sans-serif",
                  cursor: "pointer",
                  background: isSel ? "rgba(239,68,68,0.12)" : "transparent",
                  color: isSel ? "#EF4444" : "#A1A1AA",
                  fontWeight: isSel ? 500 : 400,
                  transition: "all 0.15s ease",
                  whiteSpace: "nowrap",
                }}
              >
                <span>{opt.label}</span>
                {isSel && <Check size={12} color="#EF4444" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
