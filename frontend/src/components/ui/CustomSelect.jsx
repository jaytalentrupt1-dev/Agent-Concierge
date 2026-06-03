import { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, Check } from "lucide-react";

/** Read the current theme from the html[data-theme] attribute. */
function readIsDark() {
  return document.documentElement.dataset.theme !== "light";
}

export default function CustomSelect({
  options = [],
  value,
  onChange,
  placeholder = "All",
  width = "160px"
}) {
  const [open, setOpen] = useState(false);
  const [dropdownStyle, setDropdownStyle] = useState({});
  const [isDark, setIsDark] = useState(readIsDark);
  const triggerRef = useRef(null);

  /* Track theme changes so the component re-renders correctly */
  useEffect(() => {
    const observer = new MutationObserver(() => setIsDark(readIsDark()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);

  /* position the portal dropdown below the trigger */
  const calcPosition = useCallback(() => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    const openUpward = spaceBelow < 200 && spaceAbove > spaceBelow;
    setDropdownStyle({
      position: "fixed",
      left: rect.left,
      width: Math.max(rect.width, 160),
      zIndex: 999999,
      ...(openUpward
        ? { bottom: window.innerHeight - rect.top + 4 }
        : { top: rect.bottom + 4 }),
    });
  }, []);

  function handleOpen() {
    calcPosition();
    setOpen((v) => !v);
  }

  /* close on outside click or scroll */
  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (triggerRef.current && !triggerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("scroll", () => setOpen(false), true);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("scroll", () => setOpen(false), true);
    };
  }, [open]);

  const selected = options.find((o) => o.value === value);

  /* ── theme-aware colour tokens ── */
  const colors = isDark
    ? {
        triggerBg:    "#141414",
        triggerBorder: open ? "rgba(239,68,68,0.6)" : "rgba(255,255,255,0.1)",
        triggerText:  selected ? "#FFFFFF" : "#71717A",
        dropBg:       "#1A1A1A",
        dropBorder:   "#2A2A2A",
        dropShadow:   "0 8px 32px rgba(0,0,0,0.6)",
        optionText:   "#A1A1AA",
        optionHoverBg:"rgba(239,68,68,0.07)",
        optionHoverText:"#FFFFFF",
      }
    : {
        triggerBg:    "#FFFFFF",
        triggerBorder: open ? "rgba(239,68,68,0.6)" : "#E4E4E7",
        triggerText:  selected ? "#0A0A0A" : "#71717A",
        dropBg:       "#FFFFFF",
        dropBorder:   "#E4E4E7",
        dropShadow:   "0 8px 24px rgba(0,0,0,0.12)",
        optionText:   "#52525B",
        optionHoverBg:"rgba(239,68,68,0.05)",
        optionHoverText:"#0A0A0A",
      };

  return (
    <div ref={triggerRef} style={{ position: "relative", width }}>
      {/* trigger */}
      <div
        onClick={handleOpen}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
          background: colors.triggerBg,
          border: `1px solid ${colors.triggerBorder}`,
          borderRadius: "8px",
          padding: "7px 12px",
          cursor: "pointer",
          fontSize: "13px",
          color: colors.triggerText,
          fontFamily: "Inter, sans-serif",
          transition: "all 0.2s ease",
          userSelect: "none",
          whiteSpace: "nowrap",
        }}
      >
        <span>{selected ? selected.label : placeholder}</span>
        <ChevronDown
          size={13}
          color={isDark ? "#71717A" : "#A1A1AA"}
          style={{
            transform: open ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.2s ease",
            flexShrink: 0,
          }}
        />
      </div>

      {/* dropdown — rendered in document.body via portal to escape overflow:hidden parents */}
      {open && createPortal(
        <div
          style={{
            ...dropdownStyle,
            background: colors.dropBg,
            border: `1px solid ${colors.dropBorder}`,
            borderRadius: "10px",
            boxShadow: colors.dropShadow,
            overflow: "hidden",
            animation: "dropdownIn 0.15s ease forwards",
          }}
        >
          {options.map((opt) => {
            const isSel = opt.value === value;
            return (
              <div
                key={opt.value}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onChange(opt.value);
                  setOpen(false);
                }}
                onMouseEnter={(e) => {
                  if (!isSel) {
                    e.currentTarget.style.background = colors.optionHoverBg;
                    e.currentTarget.style.color = colors.optionHoverText;
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSel) {
                    e.currentTarget.style.background = "transparent";
                    e.currentTarget.style.color = colors.optionText;
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
                  color: isSel ? "#EF4444" : colors.optionText,
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
        </div>,
        document.body
      )}
    </div>
  );
}
