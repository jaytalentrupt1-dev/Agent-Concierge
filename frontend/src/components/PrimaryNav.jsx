/**
 * PrimaryNav — the horizontal tab navigation below the top bar.
 *
 * Props:
 *   items      — array of { id, label, icon: LucideIconComponent }
 *   activeId   — currently active item id
 *   onSelect   — (id) => void
 */
export default function PrimaryNav({ items = [], activeId, onSelect }) {
  return (
    <nav className="top-nav section-nav" aria-label="Main navigation">
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = activeId === item.id;
        return (
          <button
            key={item.id}
            className={isActive ? "nav-item active" : "nav-item"}
            onClick={() => onSelect?.(item.id)}
            type="button"
            aria-current={isActive ? "page" : undefined}
          >
            {Icon && <Icon size={15} />}
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
