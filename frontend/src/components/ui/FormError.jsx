import { AlertCircle } from "lucide-react";

/**
 * FormError — inline field-level error message with icon.
 * Renders nothing when message is falsy (safe to always include).
 */
export default function FormError({ message }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "5px",
        marginTop: "4px",
      }}
    >
      <AlertCircle size={12} color="#EF4444" style={{ flexShrink: 0 }} />
      <span
        style={{
          fontSize: "12px",
          color: "#EF4444",
          fontFamily: "Inter, system-ui, sans-serif",
          lineHeight: 1.3,
        }}
      >
        {message}
      </span>
    </div>
  );
}
