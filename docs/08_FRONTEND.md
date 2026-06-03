# Frontend — Agent Admin-IT

---

## Key Files

| File | Purpose |
|------|---------|
| `frontend/src/App.jsx` | Main React app — all pages rendered inline here (~3500+ lines) |
| `frontend/src/api.js` | All fetch calls. Uses `request()` helper with Bearer token auth |
| `frontend/src/main.jsx` | Entry point. CSS import order matters (see below) |
| `frontend/src/styles.css` | Legacy stylesheet (~9k lines, lower specificity) |
| `frontend/src/styles/globals.css` | Override layer — wins all specificity battles via `!important` |
| `frontend/src/authStorage.js` | sessionStorage token read/write |
| `frontend/src/navigationConfig.js` | Role-based nav items |
| `frontend/src/vendorBilling.js` | Billing display helper (amount/cycle formatting) |

---

## Reusable Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `AgentsDashboard` | `components/AgentsDashboard.jsx` | Agents monitoring page — 4 cards, toggles, logs modal |
| `KpiCard` | `components/KpiCard.jsx` | Summary card (red left border, dark `#141414` bg, icon) |
| `ErrorBoundary` | `components/ErrorBoundary.jsx` | React error boundary |
| `NotFound` | `components/NotFound.jsx` | 404 page |
| `ServerError` | `components/ServerError.jsx` | 500 page |
| `CustomSelect` | `components/ui/CustomSelect.jsx` | Styled dropdown |
| `FormError` | `components/ui/FormError.jsx` | Field error display |
| `Skeleton` | `components/ui/Skeleton.jsx` | Loading placeholder |
| `useFormValidation` | `hooks/useFormValidation.js` | Form validation hook |

---

## CSS Architecture

**CSS import order in `main.jsx`:**
```js
import "./styles.css"          // 1st — legacy, lower specificity
import "./styles/globals.css"  // 2nd — !important overrides win
```

**`globals.css` key blocks (all appended at end of file):**
- `.conci-brand`, `.conci-icon`, `.conci-title`, `.conci-subtitle` — Conci AI sidebar header
- `.utility-search-form` — top navbar search bar flex layout
- `@keyframes bellRing` + notification bell animations
- `@keyframes sunSpin`, `@keyframes moonFade` — theme toggle icons
- `.toggle-slider` — pill theme toggle sliding circle
- `html.theme-transitioning *` — 350 ms smooth theme transition
- `.vendor-search-control` — all page search bars (999px radius, `#111111` bg, red glow)
- `.am-status-pill` styles — Running (green), Stopped (red), Paused (amber)
- `.am-agent-card`, `.am-toggle`, etc. — Agents dashboard CSS
- `input:focus { outline: none !important }` — removes blue focus rings globally
- `input[type="checkbox"], input[type="radio"] { accent-color: #EF4444 }` — red controls

**Light mode coverage (audited 2026-06-03):**
Light mode is fully verified. All major sections have `html:not([data-theme="dark"])` overrides. Key overrides:
- All cards, tables, inputs, modals, status pills, notification panel, login, agents dashboard — ✅ covered
- `.conci-title`/`.conci-subtitle` — CSS `!important` overrides the inline `color: #ffffff` (white text would be invisible without this)
- `.conci-icon` — red tint (`rgba(239,68,68,0.10)`) replaces dark badge in light mode
- `.metric-icon` — red tint (`rgba(239,68,68,0.08)`) replaces legacy blue (`#eef2ff`) in light mode
- `CustomSelect.jsx` — fully theme-aware via inline `isDark` branching
- Recharts axis fills — `#71717A` (dark) / `#52525B` (light) via `axisColor` variable per chart

---

## Theme & Colors

| Token | Value | Usage |
|-------|-------|-------|
| Page background | `#0A0A0A` | Dark mode body |
| Card background | `#141414` | All cards/panels |
| Border | `#1F1F1F` | Card borders |
| Red accent | `#EF4444` | Buttons, badges, focus rings, active states |
| Primary text | `#FFFFFF` | Dark mode |
| Light mode bg | `#F4F4F5` / `#FFFFFF` | Light mode surfaces |

**Theme toggle:** Sun/moon pill in the header. Stored as `admin_agent_theme` in `localStorage`. `html[data-theme="dark"]` attribute controls it. Light mode is the default.

**Purple has been fully removed.** All blue/purple accents converted to red.

---

## Design Conventions

- All search bars use `.vendor-search-control` class — 999px border-radius, dark bg, red glow
- Status pills: `.am-status-pill.running` (green) / `.am-status-pill.paused` (amber) / `.am-status-pill.stopped` (red)
- Icon library: `lucide-react` exclusively
- Charts: `recharts` (BarChart, PieChart, LineChart)
- Date display: `dd/mm/yyyy` throughout the UI
- Currency display: `₹X,XXX` (Indian rupees, formatted with `toLocaleString`)
- Pagination: 10 rows/page default, `Showing X to Y of Z` footer

---

## API Client Pattern (`api.js`)

```js
// Internal helper — adds Bearer token automatically
async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(options.headers || {})
    },
    ...options
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new ApiError(formatApiError(payload, response.status), response.status, payload);
  }
  return response.json();
}

// Example usage — all exported functions follow this pattern:
export function updateTaskStatus(id, status) {
  return request(`/api/tasks/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}
```

`ApiError` has `.status` (HTTP code) and `.payload` (response body) for error handling.

---

## Conci AI Chat Panel

- Lives in `App.jsx` as the right column on the Dashboard (35% width, sticky)
- State persisted in `sessionStorage` via `dashboardAssistantSessionKey(currentUser)`
- History payload: last 8 messages as `{role, text, source}` sent to backend on each request
- Sends to `POST /api/chat/assistant` via `askChatbot()` in `api.js`
- No `session_id` or `conversation_id` sent — backend tracks slot-filling state by `user_id` in memory
- Renders: text answers, bullet lists, compact tables (scroll inside bubble), confirmation buttons, next-question prompts
- User messages: edit-in-place on hover
- File attachment: CSV/XLSX/TXT files parsed by backend; PDF returns unsupported message

---

## Session & Auth (Frontend)

- Token: `sessionStorage["admin_agent_token"]` only (not localStorage)
- Deep links preserved: URL stays in address bar during login; user redirected back after auth if role allows
- Auth restore: `GET /api/auth/me` on load; only clears token on true 401/403, not on optional endpoint failures
- Logout: clears sessionStorage token + calls `POST /api/auth/logout`
