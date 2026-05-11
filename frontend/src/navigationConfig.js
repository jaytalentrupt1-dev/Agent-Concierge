export const accessByRole = {
  admin: ["dashboard", "vendors", "tasks", "approvals", "travel", "expenses", "inventory", "reports", "settings"],
  it_manager: ["dashboard", "inventory", "tasks", "approvals", "reports", "settings"],
  finance_manager: ["dashboard", "travel", "expenses", "reports", "tasks", "approvals", "vendors", "inventory", "settings"],
  employee: ["dashboard", "approvals", "settings", "tasks"]
};

export const tabRoutes = {
  dashboard: "/dashboard",
  tasks: "/tasks",
  approvals: "/tickets",
  vendors: "/vendors",
  travel: "/travel",
  expenses: "/expenses",
  inventory: "/inventory",
  reports: "/reports",
  settings: "/settings"
};

const routeTabs = {
  ...Object.fromEntries(Object.entries(tabRoutes).map(([tab, route]) => [route, tab])),
  "/approvals": "approvals"
};

export function tabFromPath(pathname = window.location.pathname) {
  const normalized = pathname.replace(/\/+$/, "") || "/dashboard";
  return routeTabs[normalized] || null;
}

export function routeForTab(tab) {
  return tabRoutes[tab] || tabRoutes.dashboard;
}

export function canAccessTab(user, tabId) {
  if (!user) return false;
  const role = typeof user === "string" ? user : user.role;
  return (accessByRole[role] || ["dashboard"]).includes(tabId);
}

export function visibleNavItemsForRole(role, navItems) {
  const itemById = new Map(navItems.map((item) => [item.id, item]));
  return (accessByRole[role] || ["dashboard"])
    .map((tabId) => itemById.get(tabId))
    .filter(Boolean);
}
