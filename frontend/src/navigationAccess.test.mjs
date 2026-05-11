import assert from "node:assert/strict";
import {
  accessByRole,
  canAccessTab,
  tabFromPath,
  tabRoutes,
  visibleNavItemsForRole
} from "./navigationConfig.js";

const navItems = [
  { id: "dashboard" },
  { id: "vendors" },
  { id: "meetings" },
  { id: "tasks" },
  { id: "approvals" },
  { id: "travel" },
  { id: "expenses" },
  { id: "inventory" },
  { id: "reports" },
  { id: "settings" }
];

assert.deepEqual(accessByRole.admin, [
  "dashboard",
  "vendors",
  "tasks",
  "approvals",
  "travel",
  "expenses",
  "inventory",
  "reports",
  "settings"
]);
assert.deepEqual(accessByRole.it_manager, ["dashboard", "inventory", "tasks", "approvals", "reports", "settings"]);
assert.deepEqual(accessByRole.finance_manager, ["dashboard", "travel", "expenses", "reports", "tasks", "approvals", "vendors", "inventory", "settings"]);
assert.deepEqual(accessByRole.employee, ["dashboard", "approvals", "settings", "tasks"]);

for (const pages of Object.values(accessByRole)) {
  assert.equal(pages.includes("meetings"), false);
}

assert.equal(tabRoutes.meetings, undefined);
assert.equal(tabFromPath("/meetings"), null);
assert.equal(tabFromPath("/dashboard"), "dashboard");
assert.equal(tabFromPath("/approvals"), "approvals");

assert.equal(canAccessTab({ role: "admin" }, "vendors"), true);
assert.equal(canAccessTab({ role: "it_manager" }, "vendors"), false);
assert.equal(canAccessTab("it_manager", "inventory"), true);
assert.equal(canAccessTab({ role: "finance_manager" }, "inventory"), true);
assert.equal(canAccessTab({ role: "finance_manager" }, "settings"), true);
assert.equal(canAccessTab({ role: "employee" }, "inventory"), false);

assert.deepEqual(
  visibleNavItemsForRole("it_manager", navItems).map((item) => item.id),
  ["dashboard", "inventory", "tasks", "approvals", "reports", "settings"]
);
assert.deepEqual(
  visibleNavItemsForRole("employee", navItems).map((item) => item.id),
  ["dashboard", "approvals", "settings", "tasks"]
);

console.log("navigation access tests passed");
