import { readSessionToken, writeSessionToken } from "./authStorage";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

let authToken = readSessionToken();

class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

function formatApiError(payload, status) {
  const detail = payload?.detail;
  if (status === 404 && detail === "Not Found") {
    return "The requested API endpoint was not found. Please restart the backend so it matches the current frontend.";
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => {
      const field = Array.isArray(item.loc) ? item.loc.filter((part) => part !== "body").join(".") : "";
      return field ? `${field}: ${item.msg}` : item.msg;
    }).join("; ");
  }
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }
  return `Request failed: ${status}`;
}

export function setAuthToken(token) {
  authToken = writeSessionToken(token);
}

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

function filenameFromDisposition(disposition, fallback) {
  const match = String(disposition || "").match(/filename="?([^";]+)"?/i);
  return match?.[1] || fallback;
}

async function downloadRequest(path, fallbackFilename) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {})
    }
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new ApiError(formatApiError(payload, response.status), response.status, payload);
  }
  return {
    blob: await response.blob(),
    filename: filenameFromDisposition(response.headers.get("Content-Disposition"), fallbackFilename)
  };
}

export function login(email, password) {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function logout() {
  return request("/api/auth/logout", { method: "POST" });
}

export function getCurrentUser() {
  return request("/api/auth/me");
}

export function getHealth() {
  return request("/api/health");
}

export function runCommand(message) {
  return request("/api/chat/command", {
    method: "POST",
    body: JSON.stringify({ message })
  });
}

export function routeRequest(message) {
  return request("/api/requests/route", {
    method: "POST",
    body: JSON.stringify({ message })
  });
}

export function getDashboard() {
  return request("/api/dashboard");
}

async function chatRequest(path, body) {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {})
    },
    body
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new ApiError(formatApiError(payload, response.status), response.status, payload);
  }
  return response.json();
}

export function askChatbot(message, file = null) {
  if (file) {
    const formData = new FormData();
    formData.append("message", message || "");
    formData.append("file", file, file.name || "attached-file");
    return chatRequest("/api/chat/assistant", formData);
  }
  return request("/api/chat/assistant", {
    method: "POST",
    body: JSON.stringify({ message })
  });
}

export function getTasks() {
  return request("/api/tasks");
}

export function getTask(id) {
  return request(`/api/tasks/${id}`);
}

export function createTask(payload) {
  return request("/api/tasks", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateTask(id, payload) {
  return request(`/api/tasks/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function updateTaskStatus(id, status) {
  return request(`/api/tasks/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}

export function deleteTask(id) {
  return request(`/api/tasks/${id}`, { method: "DELETE" });
}

export function getApprovals() {
  return request("/api/approvals");
}

export function getTickets() {
  return request("/api/tickets");
}

export function getNotifications() {
  return request("/api/notifications");
}

export function markNotificationRead(id) {
  return request(`/api/notifications/${id}/read`, { method: "PATCH" });
}

export function markAllNotificationsRead() {
  return request("/api/notifications/read-all", { method: "PATCH" });
}

export function createTicket(payload) {
  return request("/api/tickets", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateTicket(id, payload) {
  return request(`/api/tickets/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function updateTicketStatus(id, status) {
  return request(`/api/tickets/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}

export function getExpenses() {
  return request("/api/expenses");
}

export function createExpense(payload) {
  return request("/api/expenses", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateExpense(id, payload) {
  return request(`/api/expenses/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function updateExpenseStatus(id, status) {
  return request(`/api/expenses/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}

export function previewExpenseImport(filename, contentBase64) {
  return request("/api/expenses/import/preview", {
    method: "POST",
    body: JSON.stringify({ filename, content_base64: contentBase64 })
  });
}

export function confirmExpenseImport(filename, items) {
  return request("/api/expenses/import/confirm", {
    method: "POST",
    body: JSON.stringify({ filename, items })
  });
}

export function getTravelSummary() {
  return request("/api/travel/summary");
}

export function getTravelRecords() {
  return request("/api/travel");
}

export function createTravelRecord(payload) {
  return request("/api/travel", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateTravelRecord(id, payload) {
  return request(`/api/travel/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getCalendarEvents() {
  return request("/api/calendar-events");
}

export function createCalendarEvent(payload) {
  return request("/api/calendar-events", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateCalendarEvent(id, payload) {
  return request(`/api/calendar-events/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function getReports() {
  return request("/api/reports");
}

export function importReport(payload) {
  return request("/api/reports/import", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function downloadReport(id) {
  return downloadRequest(`/api/reports/${id}/download`, "report");
}

export function exportReports(filters = {}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "" && value !== "All") {
      params.set(key, value);
    }
  });
  const query = params.toString();
  return downloadRequest(`/api/reports/export${query ? `?${query}` : ""}`, "reports_export.csv");
}

export function deleteReport(id) {
  return request(`/api/reports/${id}`, { method: "DELETE" });
}

export function getVendors() {
  return request("/api/vendors");
}

export function createVendor(payload) {
  return request("/api/vendors", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateVendor(id, payload) {
  return request(`/api/vendors/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function closeVendor(id) {
  try {
    return await request(`/api/vendors/${id}/close`, { method: "PATCH" });
  } catch (err) {
    if (err.status === 405) {
      return request(`/api/vendors/${id}/close`, { method: "POST" });
    }
    throw err;
  }
}

export async function reopenVendor(id) {
  try {
    return await request(`/api/vendors/${id}/reopen`, { method: "PATCH" });
  } catch (err) {
    if (err.status === 405) {
      return request(`/api/vendors/${id}/reopen`, { method: "POST" });
    }
    throw err;
  }
}

export function sendVendorEmail(id, payload) {
  return request(`/api/vendors/${id}/email`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getInventoryItems() {
  return request("/api/inventory");
}

export function createInventoryItem(payload) {
  return request("/api/inventory", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function updateInventoryItem(id, payload) {
  return request(`/api/inventory/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function updateInventoryStatus(id, status) {
  return request(`/api/inventory/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  });
}

export function deleteInventoryItem(id) {
  return request(`/api/inventory/${id}`, { method: "DELETE" });
}

export function bulkDeleteInventoryItems(itemIds, metadata = {}) {
  return request("/api/inventory/bulk-delete", {
    method: "POST",
    body: JSON.stringify({ item_ids: itemIds, ...metadata })
  });
}

export function previewInventoryImport(filename, contentBase64) {
  return request("/api/inventory/import/preview", {
    method: "POST",
    body: JSON.stringify({ filename, content_base64: contentBase64 })
  });
}

export function createInventoryImport(filename, items) {
  return request("/api/inventory/imports", {
    method: "POST",
    body: JSON.stringify({ filename, items })
  });
}

export function getInventoryImports() {
  return request("/api/inventory/imports");
}

export function getInventoryImportItems(importId) {
  return request(`/api/inventory/imports/${importId}/items`);
}

export function deleteInventoryImport(importId) {
  return request(`/api/inventory/imports/${importId}`, { method: "DELETE" });
}

export function getConnectors() {
  return request("/api/connectors");
}

export function configureEmailConnector(payload) {
  return request("/api/connectors/email/configure", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function configureWhatsAppConnector(payload) {
  return request("/api/connectors/whatsapp/configure", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function testEmailConnector() {
  return request("/api/connectors/email/test", { method: "POST" });
}

export function testWhatsAppConnector() {
  return request("/api/connectors/whatsapp/test", { method: "POST" });
}

export function disconnectConnector(connectorType) {
  return request("/api/connectors/disconnect", {
    method: "POST",
    body: JSON.stringify({ connector_type: connectorType })
  });
}

export function getCommunicationLogs() {
  return request("/api/communications/logs");
}

export function sendCommunication(payload) {
  const channel = payload.channel || "email";
  const endpoint = channel === "both"
    ? "/api/communications/send-both"
    : channel === "whatsapp"
      ? "/api/communications/send-whatsapp"
      : "/api/communications/send-email";
  return request(endpoint, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function getAuditLog() {
  return request("/api/audit-log");
}

export function updateApproval(id, payload) {
  return request(`/api/approvals/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload)
  });
}

export function resetDemo() {
  return request("/api/dev/reset", { method: "POST" });
}

export function getUsers() {
  return request("/api/users");
}

export function getAssignableUsers() {
  return request("/api/users/assignable");
}

function normalizeUserRole(role) {
  const normalized = String(role || "").trim().toLowerCase().replace(/[-\s]+/g, "_");
  return {
    admin: "admin",
    it: "it_manager",
    it_manager: "it_manager",
    finance: "finance_manager",
    finance_manager: "finance_manager",
    operation: "employee",
    employee: "employee"
  }[normalized] || normalized;
}

function normalizeUserPayload(payload) {
  if (!payload || payload.role == null) return payload;
  return { ...payload, role: normalizeUserRole(payload.role) };
}

export function createUser(payload) {
  return request("/api/users", {
    method: "POST",
    body: JSON.stringify(normalizeUserPayload(payload))
  });
}

export function updateUser(id, payload) {
  return request(`/api/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(normalizeUserPayload(payload))
  });
}

export function deleteUser(id) {
  return request(`/api/users/${id}`, { method: "DELETE" });
}

export function resetUserPassword(id, password) {
  return request(`/api/users/${id}/reset-password`, {
    method: "POST",
    body: JSON.stringify({ password })
  });
}
