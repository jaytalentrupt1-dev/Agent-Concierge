import { useEffect, useState } from "react";
import { SearchX } from "lucide-react";

function isDarkTheme() {
  return document.documentElement.dataset.theme !== "light";
}

export default function NotFound({ onGoHome }) {
  const [dark, setDark] = useState(isDarkTheme);

  useEffect(() => {
    const observer = new MutationObserver(() => setDark(isDarkTheme()));
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100%",
      padding: "40px 24px",
      background: dark ? "#0A0A0A" : "#F8F8F8",
    }}>
      <div style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center",
        maxWidth: "400px",
        width: "100%",
        background: dark ? "#141414" : "#FFFFFF",
        border: `1px solid ${dark ? "#1F1F1F" : "#E4E4E7"}`,
        borderRadius: "16px",
        padding: "48px 40px",
        boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
        animation: "errorPageIn 0.35s cubic-bezier(0.4,0,0.2,1) forwards",
      }}>
        {/* Icon */}
        <SearchX
          size={64}
          color={dark ? "#3F3F46" : "#D4D4D8"}
          strokeWidth={1.4}
          style={{ marginBottom: "20px" }}
        />

        {/* 404 */}
        <div style={{
          fontSize: "80px",
          fontWeight: 800,
          lineHeight: 1,
          color: "#EF4444",
          marginBottom: "16px",
          fontFamily: "Inter, sans-serif",
          textShadow: "0 0 40px rgba(239,68,68,0.35)",
          letterSpacing: "-2px",
        }}>
          404
        </div>

        {/* Title */}
        <h1 style={{
          fontSize: "24px",
          fontWeight: 700,
          color: dark ? "#FFFFFF" : "#0A0A0A",
          margin: "0 0 10px",
          fontFamily: "Inter, sans-serif",
        }}>
          Page Not Found
        </h1>

        {/* Subtitle */}
        <p style={{
          fontSize: "14px",
          color: "#71717A",
          margin: "0 0 32px",
          lineHeight: 1.6,
          fontFamily: "Inter, sans-serif",
        }}>
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>

        {/* CTA */}
        <button
          onClick={onGoHome}
          type="button"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "8px",
            background: "#EF4444",
            color: "#FFFFFF",
            border: "none",
            borderRadius: "10px",
            padding: "12px 28px",
            fontSize: "14px",
            fontWeight: 600,
            fontFamily: "Inter, sans-serif",
            cursor: "pointer",
            transition: "background 0.2s ease, transform 0.15s ease",
            width: "100%",
          }}
          onMouseEnter={(e) => { e.currentTarget.style.background = "#DC2626"; }}
          onMouseLeave={(e) => { e.currentTarget.style.background = "#EF4444"; }}
          onMouseDown={(e) => { e.currentTarget.style.transform = "scale(0.98)"; }}
          onMouseUp={(e) => { e.currentTarget.style.transform = "scale(1)"; }}
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
