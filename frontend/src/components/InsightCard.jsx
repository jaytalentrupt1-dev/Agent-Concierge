import { ArrowRight } from "lucide-react";

/**
 * InsightCard — actionable insight card for the dashboard bottom row.
 *
 * Props:
 *   icon      — lucide-react icon component
 *   title     — short heading
 *   description — one-line description
 *   ctaLabel  — CTA button text (default "View details")
 *   onCta     — click handler for the CTA button
 */
export default function InsightCard({ icon: Icon, title, description, ctaLabel = "View details", onCta }) {
  return (
    <div className="insight-card">
      {Icon && (
        <span className="insight-icon">
          <Icon size={14} />
        </span>
      )}
      <div className="insight-body">
        <p className="insight-title">{title}</p>
        <p className="insight-desc">{description}</p>
        {onCta && (
          <button className="insight-cta" onClick={onCta} type="button">
            {ctaLabel}
            <ArrowRight size={13} />
          </button>
        )}
      </div>
    </div>
  );
}
