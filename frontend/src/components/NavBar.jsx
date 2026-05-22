/**
 * NavBar — re-exports a thin wrapper around the existing App-level header
 * markup. Kept as a named component so it can be imported and extended
 * independently of App.jsx in future steps.
 *
 * The actual render logic lives in the App component; this file provides
 * the structural contract (props interface) that the design spec requires.
 *
 * Props:
 *   logo       — brand logo element or JSX
 *   search     — search bar element or JSX
 *   actions    — right-side action elements (bell, theme, user)
 *   children   — optional additional top-bar content
 */
export default function NavBar({ logo, search, actions, children }) {
  return (
    <div className="utility-bar">
      {logo}
      {search}
      <div className="topbar-actions">
        {actions}
      </div>
      {children}
    </div>
  );
}
