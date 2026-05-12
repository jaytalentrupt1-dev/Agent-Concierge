import { useEffect, useMemo, useRef, useState } from "react";
import {
  BarChart3,
  Bell,
  Bot,
  Building2,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Clock3,
  DollarSign,
  Download,
  ArrowRight,
  Eye,
  EyeOff,
  Filter,
  FileText,
  ListChecks,
  Lock,
  LogOut,
  Mail,
  Moon,
  MoreVertical,
  Package,
  Pencil,
  Plane,
  Plus,
  Plug,
  RefreshCw,
  Search,
  Send,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Sun,
  Upload,
  Zap,
  X,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Maximize2,
  Minimize2,
  MessageCircle,
  Phone,
  Paperclip,
  Trash2,
  UserRound,
  UsersRound
} from "lucide-react";
import {
  askChatbot,
  closeVendor,
  bulkDeleteInventoryItems,
  configureWhatsAppConnector,
  confirmExpenseImport,
  createCalendarEvent,
  createExpense,
  createInventoryImport,
  createInventoryItem,
  createTravelRecord,
  createVendor,
  createTask,
  createTicket,
  createUser,
  deleteUser,
  deleteReport,
  deleteTask,
  disconnectConnector,
  disconnectGoogleEmail,
  deleteInventoryImport,
  deleteInventoryItem,
  downloadReport,
  exportReports,
  getApprovals,
  getAuditLog,
  getCalendarEvents,
  getCommunicationLogs,
  getConnectors,
  getCurrentUser,
  getDashboard,
  getExpenses,
  getAssignableUsers,
  getHealth,
  getInventoryImportItems,
  getInventoryImports,
  getInventoryItems,
  getNotifications,
  getReports,
  getTasks,
  getTickets,
  getTravelRecords,
  getTravelSummary,
  getUsers,
  getVendors,
  login,
  logout,
  markAllNotificationsRead,
  markNotificationRead,
  importReport,
  previewExpenseImport,
  previewInventoryImport,
  resetDemo,
  resetUserPassword,
  reopenVendor,
  routeRequest,
  runCommand,
  sendCommunication,
  setAuthToken,
  startGoogleEmailConnection,
  testGoogleEmailConnector,
  testWhatsAppConnector,
  updateApproval,
  updateExpense,
  updateExpenseStatus,
  updateTask,
  updateTaskStatus,
  updateTicket,
  updateTicketStatus,
  updateCalendarEvent,
  updateInventoryItem,
  updateInventoryStatus,
  updateTravelRecord,
  updateVendor,
  updateUser
} from "./api";
import {
  canAccessTab,
  routeForTab,
  tabFromPath,
  tabRoutes,
  visibleNavItemsForRole
} from "./navigationConfig";
import { formatVendorBilling, normalizeBillingAmount, normalizeBillingCycle } from "./vendorBilling";
import {
  Bar,
  BarChart as RechartsBarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const DEFAULT_COMMAND =
  "Plan tomorrow's vendor review meeting, remind everyone, prepare files, take notes during the meeting, and follow up on action items.";

const DEFAULT_ROUTE_REQUEST = "I need approval for an invoice mismatch of ₹12,500";

const DASHBOARD_CHART_COLORS = ["#4f46e5", "#0ea5e9", "#22c55e", "#f97316", "#ec4899", "#8b5cf6"];

const DASHBOARD_SUMMARY_ICONS = {
  total_tickets: ShieldAlert,
  total_tasks: ListChecks,
  open_tasks: ListChecks,
  open_tickets: ShieldAlert,
  pending_approvals: ShieldCheck,
  active_vendors: Building2,
  inventory_items: Package,
  monthly_expenses: DollarSign,
  expenses_this_month: DollarSign,
  open_it_tickets: ShieldAlert,
  in_progress_tickets: Clock3,
  resolved_tickets: CheckCircle2,
  it_tasks: ClipboardList,
  inventory_in_use: Package,
  inventory_extra: Package,
  submitted_to_vendor: Send,
  low_stock: ShieldAlert,
  pending_expenses: DollarSign,
  approved_expenses: CheckCircle2,
  travel_spend: Plane,
  pending_finance_approvals: ShieldCheck,
  vendor_billing_followups: Building2,
  finance_tasks: ClipboardList,
  my_open_tickets: ShieldAlert,
  my_tasks: ListChecks,
  waiting_approval: Clock3,
  completed_tasks: CheckCircle2
};

const DASHBOARD_QUICK_ACTION_ICONS = {
  create_ticket: Plus,
  add_vendor: Building2,
  add_inventory_item: Package,
  import_inventory: Upload,
  import_report: FileText,
  add_user: UserRound,
  create_task: ClipboardList,
  create_task_request: ClipboardList,
  export_report: Download,
  upload_expense: Upload,
  add_travel_record: Plane
};

const ROUTE_EXAMPLES = [
  "I need approval for an invoice mismatch of ₹12,500",
  "Draft a vendor follow-up email after the supplier review",
  "Please reset my laptop password",
  "Book travel to Delhi next week",
  "Delete this confidential vendor contract",
  "Order 10 printer cartridges",
  "Remind the team about tomorrow's internal meeting"
];

const vendorServiceOptions = [
  "Transport",
  "Food",
  "Office Supplies",
  "IT Services",
  "Security",
  "Housekeeping",
  "Other"
];

const vendorServiceSignals = [
  { service: "Transport", terms: ["transport", "travels", "travel", "logistics", "taxi", "cab", "fleet", "courier", "delivery"] },
  { service: "Food", terms: ["food", "foods", "catering", "caterer", "canteen", "meal", "meals", "snack", "snacks", "kitchen", "restaurant"] },
  { service: "Office Supplies", terms: ["office supplies", "supplies", "stationery", "paper", "printer", "cartridge", "furniture"] },
  { service: "IT Services", terms: ["it", "tech", "technology", "software", "hardware", "network", "cloud", "computer", "laptop"] },
  { service: "Security", terms: ["security", "secure", "guard", "guards", "surveillance", "cctv"] },
  { service: "Housekeeping", terms: ["housekeeping", "cleaning", "cleaners", "janitorial", "facility", "facilities"] }
];

const billingCycleOptions = ["Monthly", "Quarterly", "Half-yearly", "Yearly"];
const communicationChannelOptions = [
  { value: "email", label: "Email" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "both", label: "Both" }
];
const vendorStatusFilterOptions = ["All", "Active", "Closed"];
const vendorServiceFilterOptions = ["All", ...vendorServiceOptions];
const vendorBillingCycleFilterOptions = ["All", ...billingCycleOptions];
const VENDOR_PAGE_SIZE = 10;
const ticketTypeOptions = ["IT", "Admin"];
const ticketTypeFilterOptions = ["All", ...ticketTypeOptions];
const ticketStatusOptions = ["Open", "In Progress", "Waiting Approval", "Resolved", "Closed"];
const ticketStatusFilterOptions = ["All", ...ticketStatusOptions];
const ticketPriorityOptions = ["Low", "Medium", "High", "Critical"];
const ticketPriorityFilterOptions = ["All", ...ticketPriorityOptions];
const ticketCategoryOptions = {
  IT: ["Password", "Software Access", "Printer", "Device", "Hardware", "Network", "Security", "Other"],
  Admin: ["Meeting Support", "Vendor", "Finance", "Office Supplies", "Travel", "Facilities", "Other"]
};
const TICKET_PAGE_SIZE = 10;
const taskCategoryOptions = ["Admin", "IT", "Finance", "Vendor", "Inventory", "Travel", "Expense", "Report", "Other"];
const taskCategoryFilterOptions = ["All", ...taskCategoryOptions];
const taskPriorityOptions = ["Low", "Medium", "High", "Critical"];
const taskPriorityFilterOptions = ["All", ...taskPriorityOptions];
const taskStatusOptions = ["Open", "In Progress", "Waiting Approval", "Completed", "Cancelled"];
const taskStatusFilterOptions = ["All", ...taskStatusOptions];
const taskDepartmentOptions = ["Admin", "IT", "Finance", "Operations", "HR", "Travel", "Inventory", "Reports", "Other"];
const taskDepartmentFilterOptions = ["All", ...taskDepartmentOptions];
const taskAssignedRoleOptions = ["admin", "it_manager", "finance_manager", "employee"];
const taskAssignedRoleFilterOptions = ["All", ...taskAssignedRoleOptions];
const TASK_PAGE_SIZE = 10;
const expenseCategoryOptions = [
  "Travel",
  "Food",
  "Hotel",
  "Local Conveyance",
  "Office Supplies",
  "Software",
  "Internet / Phone",
  "Vendor Payment",
  "Client Meeting",
  "Training",
  "Miscellaneous"
];
const expenseCategoryFilterOptions = ["All", ...expenseCategoryOptions];
const expenseStatusOptions = ["Draft", "Submitted", "Pending Approval", "Approved", "Rejected", "Paid", "Reimbursed", "Needs Info"];
const expenseStatusFilterOptions = ["All", ...expenseStatusOptions];
const expenseDepartmentFilterOptions = ["All", "Admin", "Finance", "IT", "Operations", "HR", "Sales", "Marketing"];
const expensePaymentModeOptions = ["Corporate Card", "Personal Card", "Cash", "UPI", "Bank Transfer", "Company Account"];
const expenseReceiptStatusOptions = ["Attached", "Missing", "Pending", "Not Required"];
const EXPENSE_PAGE_SIZE = 10;
const travelModeOptions = ["Flight", "Train", "Bus", "Cab", "Hotel", "Mixed", "Other"];
const travelModeFilterOptions = ["All", ...travelModeOptions];
const travelStatusOptions = ["Draft", "Submitted", "Pending Approval", "Approved", "Rejected", "Booked", "Completed", "Cancelled", "Needs Info"];
const travelStatusFilterOptions = ["All", ...travelStatusOptions];
const travelPolicyStatusOptions = ["Within Policy", "Over Budget", "Missing Approval", "Needs Review"];
const travelPolicyFilterOptions = ["All", ...travelPolicyStatusOptions];
const travelDepartmentFilterOptions = ["All", "Admin", "Finance", "IT", "Operations", "HR", "Sales", "Marketing"];
const calendarEventTypeOptions = ["Meeting", "Vendor Meeting", "Travel", "Reminder", "Internal Event", "Other"];
const calendarEventStatusOptions = ["Scheduled", "Completed", "Cancelled", "Tentative"];
const TRAVEL_PAGE_SIZE = 10;
const reportDepartmentOptions = ["Admin", "Finance", "IT", "Operations", "HR", "Sales", "Marketing", "General"];
const reportTypeOptions = ["Operations", "IT", "Finance", "Inventory", "Expense", "Travel", "Vendor", "Audit", "Security", "Other"];
const reportFileTypeOptions = ["CSV", "XLSX", "PDF"];
const reportStatusOptions = ["Ready", "Processing", "Archived"];
const REPORT_PAGE_SIZE = 10;
const expenseImportColumns = [
  ["expense_id", "Expense ID"],
  ["employee_name", "Employee Name"],
  ["employee_email", "Employee Email"],
  ["department", "Department"],
  ["category", "Category"],
  ["vendor_merchant", "Vendor/Merchant"],
  ["amount", "Amount"],
  ["currency", "Currency"],
  ["expense_date", "Expense Date"],
  ["payment_mode", "Payment Mode"],
  ["receipt_status", "Receipt Status"],
  ["receipt_attachment_name", "Receipt Attachment Name"],
  ["notes", "Notes"],
  ["status", "Status"],
  ["approval_required", "Approval Required"]
];
const inventoryStatusOptions = ["In Use", "Extra", "Submitted to Vendor"];
const inventoryQuickStatusOptions = ["In Use", "Extra", "Submitted to Vendor"];
const inventoryStatusFilterOptions = ["All", ...inventoryStatusOptions];
const inventoryImportTemplateHeaders = [
  "employee_name",
  "serial_no",
  "model_no",
  "ram",
  "disk",
  "location",
  "status",
  "notes"
];
const inventoryImportTemplateRows = [
  [
    "Admin User",
    "DL-5440-001",
    "Latitude 5440",
    "16 GB",
    "512 GB SSD",
    "Pune Office",
    "In Use",
    "Sample IT equipment row"
  ],
  [
    "Employee User",
    "HP-840-221",
    "EliteBook 840",
    "16 GB",
    "1 TB SSD",
    "Mumbai Office",
    "Extra",
    "Sample spare laptop row"
  ],
  [
    "IT Manager",
    "MBP14-AC-004",
    "MacBook Pro 14",
    "32 GB",
    "1 TB SSD",
    "Bengaluru Office",
    "Submitted to Vendor",
    "Sample vendor service row"
  ]
];
const INVENTORY_PAGE_SIZE = 30;
const emptyInventoryForm = {
  item_id: "",
  employee_name: "",
  serial_no: "",
  model_no: "",
  ram: "",
  disk: "",
  location: "",
  status: "In Use",
  notes: ""
};
const emptyTicketForm = {
  ticket_type: "IT",
  title: "",
  description: "",
  category: "Password",
  priority: "Medium",
  status: "Open",
  due_date: "",
  approval_required: false
};
const emptyTaskForm = {
  title: "",
  description: "",
  category: "Admin",
  department: "Admin",
  assigned_to: "",
  assigned_user_id: "",
  assigned_email: "",
  assigned_role: "admin",
  priority: "Medium",
  status: "Open",
  due_date: "",
  notes: ""
};
const emptyExpenseForm = {
  employee_name: "",
  employee_email: "",
  department: "Operations",
  category: "Travel",
  vendor_merchant: "",
  amount: "",
  currency: "INR",
  expense_date: "",
  payment_mode: "Corporate Card",
  receipt_status: "Attached",
  receipt_attachment_name: "",
  notes: "",
  status: "Draft",
  approval_required: false
};
const emptyTravelForm = {
  travel_id: "",
  employee_name: "",
  employee_email: "",
  department: "Admin",
  destination_from: "",
  destination_to: "",
  travel_start_date: "",
  travel_end_date: "",
  purpose: "",
  travel_mode: "Flight",
  estimated_budget: "",
  actual_spend: "",
  number_of_trips: "1",
  approval_status: "Draft",
  policy_status: "Within Policy",
  booking_status: "Draft",
  notes: "",
  google_calendar_event_id: "",
  google_sync_status: "Not Synced",
  google_last_synced_at: ""
};
const emptyCalendarEventForm = {
  event_id: "",
  title: "",
  event_type: "Meeting",
  start_datetime: "",
  end_datetime: "",
  location: "",
  attendees: "",
  related_travel_id: "",
  reminder: "",
  notes: "",
  status: "Scheduled",
  google_calendar_event_id: "",
  google_sync_status: "Not Synced",
  google_last_synced_at: ""
};
const emptyReportForm = {
  report_name: "",
  report_type: "Operations",
  department: "Admin",
  notes: ""
};
const emptyVendorForm = {
  vendor_name: "",
  contact_person: "",
  email: "",
  contact_details: "",
  office_address: "",
  service_provided: "",
  start_date: "",
  end_date: "",
  billing_amount: "",
  billing_cycle: "Monthly"
};

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: BarChart3 },
  { id: "vendors", label: "Vendors", icon: Building2 },
  { id: "tasks", label: "Tasks", icon: ListChecks },
  { id: "approvals", label: "Tickets", icon: ShieldAlert },
  { id: "travel", label: "Travel & Calendar", icon: Plane },
  { id: "expenses", label: "Expenses", icon: DollarSign },
  { id: "inventory", label: "Inventory", icon: Package },
  { id: "reports", label: "Reports", icon: FileText }
];
const topNavItems = [...navItems, { id: "settings", label: "Settings", icon: Settings }];

const roleOptions = ["admin", "it_manager", "finance_manager", "employee"];
const demoUserEmails = new Set([
  "admin@company.com",
  "finance@company.com",
  "it@company.com",
  "employee@company.com",
  "operation@company.com"
]);
const searchRoutes = [
  { id: "dashboard", terms: ["dashboard", "home", "overview"] },
  { id: "tasks", terms: ["task", "tasks", "deadline", "deadlines", "to do", "todo"] },
  { id: "approvals", terms: ["ticket", "tickets", "approval", "approvals", "queue", "review"] },
  { id: "vendors", terms: ["vendor", "vendors", "supplier", "suppliers"] },
  { id: "travel", terms: ["travel", "calendar", "booking", "bookings"] },
  { id: "expenses", terms: ["expense", "expenses", "payment", "payments", "invoice", "invoices"] },
  { id: "inventory", terms: ["inventory", "stock", "asset", "assets"] },
  { id: "reports", terms: ["report", "reports", "audit", "timeline", "log", "logs"] },
  { id: "settings", terms: ["setting", "settings", "users", "user management", "account"] }
];

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatDateOnly(value) {
  if (!value) return "—";
  const isoMatch = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (isoMatch) {
    return `${isoMatch[3]}/${isoMatch[2]}/${isoMatch[1]}`;
  }
  return value;
}

function formatCalendarDate(value) {
  if (!value) return "—";
  const datePart = String(value).slice(0, 10);
  return formatDateOnly(datePart);
}

function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).replace("T", " ");
  return `${formatDateOnly(date.toISOString().slice(0, 10))} ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}`;
}

function toDateTimeLocalValue(value) {
  if (!value) return "";
  return String(value).replace(" ", "T").slice(0, 16);
}

function formatCreatedDate(value) {
  if (!value) return "Created date unavailable";
  return `Created on ${new Intl.DateTimeFormat("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value))}`;
}

function isValidIsoDate(value) {
  const match = String(value || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return false;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const candidate = new Date(`${value}T00:00:00`);
  if (
    candidate.getFullYear() !== year ||
    candidate.getMonth() !== month - 1 ||
    candidate.getDate() !== day
  ) {
    return false;
  }
  return true;
}

function inferVendorService(vendorName) {
  const normalized = vendorName.toLowerCase();
  const match = vendorServiceSignals.find((item) =>
    item.terms.some((term) => normalized.includes(term))
  );
  return match?.service || "";
}

function labelize(value) {
  return (value || "")
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function roleLabel(role) {
  const normalizedRole = normalizeRoleValue(role);
  if (normalizedRole === "it_manager") return "IT Manager";
  if (normalizedRole === "finance_manager") return "Finance Manager";
  return labelize(normalizedRole);
}

function normalizeRoleValue(role) {
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

function formatRoleList(roles = []) {
  if (!roles.length) return "None";
  return roles.map(roleLabel).join("/");
}

function aiModeLabel(health) {
  return health?.agent_planner_mode?.includes("openai") ? "OpenAI Mode" : "Mock AI Mode";
}

function initials(name = "") {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0][0], parts[1][0]] : [parts[0]?.[0] || "A"];
  return letters.join("").toUpperCase();
}

function matchesSearch(item, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return JSON.stringify(item).toLowerCase().includes(normalized);
}

function inventoryMatchesLocalSearch(item, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [
    item.employee_name,
    item.serial_no,
    item.model_no,
    item.ram,
    item.disk,
    item.location,
    item.status,
    item.notes,
    item.assigned_to,
    item.serial_number,
    item.model
  ].join(" ").toLowerCase().includes(normalized);
}

function travelMatchesLocalSearch(item, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [
    item.employee_name,
    item.employee_email,
    item.department,
    item.destination_from,
    item.destination_to,
    item.purpose,
    item.title
  ].join(" ").toLowerCase().includes(normalized);
}

function reportMatchesLocalSearch(report, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [
    report.report_id,
    report.report_name,
    report.report_type,
    report.department,
    report.uploaded_by_name,
    report.uploaded_by_email,
    report.file_type,
    report.status
  ].join(" ").toLowerCase().includes(normalized);
}

function reportDepartmentsForRole(role) {
  if (role === "it_manager") return ["IT"];
  if (role === "finance_manager") return ["Finance"];
  if (role === "employee") return [];
  return reportDepartmentOptions;
}

function canManageReport(currentUser, report) {
  if (currentUser.role === "admin") return true;
  if (currentUser.role === "it_manager") return report.department === "IT";
  if (currentUser.role === "finance_manager") return report.department === "Finance";
  return false;
}

function formatFileSize(size) {
  const bytes = Number(size || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function taskMatchesLocalSearch(task, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [
    task.task_id,
    task.title,
    task.description,
    task.assigned_to,
    task.created_by_name,
    task.created_by_email,
    task.department
  ].join(" ").toLowerCase().includes(normalized);
}

function taskAssigneeMatchesUser(task, user) {
  const assignedTo = String(task?.assigned_to || "").trim().toLowerCase();
  return assignedTo === String(user?.name || "").toLowerCase() || assignedTo === String(user?.email || "").toLowerCase();
}

function taskCreatedByUser(task, user) {
  return task?.created_by_user_id === user?.id || task?.created_by_email === user?.email;
}

function isItRelatedTask(task) {
  const text = `${task?.category || ""} ${task?.department || ""} ${task?.assigned_role || ""}`.toLowerCase();
  return text.includes("it") || task?.assigned_role === "it_manager";
}

function isFinanceRelatedTask(task) {
  const text = `${task?.category || ""} ${task?.department || ""} ${task?.assigned_role || ""}`.toLowerCase();
  return ["finance", "expense", "invoice", "payment"].some((term) => text.includes(term)) || task?.assigned_role === "finance_manager";
}

function canManageTask(currentUser, task) {
  if (!currentUser || !task) return false;
  if (currentUser.role === "admin") return true;
  if (currentUser.role === "it_manager" && (isItRelatedTask(task) || taskCreatedByUser(task, currentUser))) return true;
  if (currentUser.role === "finance_manager" && (isFinanceRelatedTask(task) || taskAssigneeMatchesUser(task, currentUser) || taskCreatedByUser(task, currentUser))) return true;
  if (currentUser.role === "employee") return taskCreatedByUser(task, currentUser);
  return false;
}

function taskBadgeClass(base, value) {
  return `${base} ${String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function isTaskOverdue(task) {
  if (!task?.due_date || ["Completed", "Cancelled"].includes(task.status)) return false;
  const due = new Date(`${String(task.due_date).slice(0, 10)}T23:59:59`);
  if (Number.isNaN(due.getTime())) return false;
  return due < new Date();
}

function normalizeInventoryStatus(status) {
  const value = String(status || "").trim();
  return inventoryStatusOptions.find((option) => option.toLowerCase() === value.toLowerCase()) || value;
}

function inventoryIsLowStock(item) {
  return Number(item.quantity || 0) <= Number(item.minimum_stock_level || 0);
}

function inventoryBadgeClass(base, value) {
  return `${base} ${String(value || "").toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function inventoryImportStatusClass(status) {
  const normalized = String(status || "").toLowerCase();
  if (normalized === "completed") return "status-pill success";
  if (normalized.includes("partial") || normalized.includes("legacy")) return "status-pill warning";
  if (normalized === "failed" || normalized === "deleted") return "status-pill danger";
  return "status-pill";
}

function parseCsvText(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (char === '"' && quoted && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      quoted = !quoted;
    } else if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }
  row.push(cell);
  if (row.some((value) => value.trim())) rows.push(row);
  return rows;
}

function normalizeInventoryHeader(header) {
  return String(header || "").toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function generatedInventoryItemId(form) {
  const existing = String(form.item_id || "").trim();
  if (existing) return existing;
  const source = String(form.serial_no || form.serial_number || "").trim() || `${form.employee_name || "inventory"}-${form.model_no || "item"}`;
  const slug = source.toUpperCase().replace(/[^A-Z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return `INV-${slug || Date.now()}`;
}

function inventoryPayloadFromForm(form) {
  const employeeName = String(form.employee_name || form.assigned_to || "").trim();
  const serialNo = String(form.serial_no || form.serial_number || "").trim();
  const modelNo = String(form.model_no || form.model || "").trim();
  return {
    ...form,
    item_id: generatedInventoryItemId(form),
    item_name: employeeName || modelNo || "Inventory Item",
    category: "IT Equipment",
    subcategory: "",
    brand: "",
    model: modelNo,
    serial_number: serialNo,
    quantity: 1,
    unit: "unit",
    condition: "Good",
    location: String(form.location || "").trim(),
    assigned_to: employeeName,
    department: "",
    purchase_date: null,
    warranty_end_date: null,
    vendor: "",
    minimum_stock_level: 0,
    employee_name: employeeName,
    serial_no: serialNo,
    model_no: modelNo,
    ram: String(form.ram || "").trim(),
    disk: String(form.disk || "").trim(),
    status: normalizeInventoryStatus(form.status),
    notes: String(form.notes || "").trim()
  };
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return window.btoa(binary);
}

function csvCell(value) {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function downloadInventoryTemplate() {
  const rows = [inventoryImportTemplateHeaders, ...inventoryImportTemplateRows];
  const csv = `${rows.map((row) => row.map(csvCell).join(",")).join("\n")}\n`;
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "inventory_import_template.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function downloadBlob({ blob, filename }) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "download";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

function apiErrorMessage(err) {
  if (
    err?.status === 404 &&
    (err.payload?.detail === "Not Found" || /endpoint was not found/i.test(err.message || ""))
  ) {
    return "Some data could not load because the backend is not running the latest API. Please restart the backend and try again.";
  }
  return err?.message || "Something went wrong. Please try again.";
}

function savedTheme() {
  if (typeof window === "undefined") return "light";
  return window.localStorage.getItem("admin_agent_theme") === "dark" ? "dark" : "light";
}

function App() {
  const [activeTab, setActiveTab] = useState(() => tabFromPath() || "dashboard");
  const [command, setCommand] = useState(DEFAULT_COMMAND);
  const automationInputRef = useRef(null);
  const routingInputRef = useRef(null);
  const accountMenuRef = useRef(null);
  const [theme, setTheme] = useState(savedTheme);
  const [currentUser, setCurrentUser] = useState(null);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [approvals, setApprovals] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0);
  const [vendors, setVendors] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [travelRecords, setTravelRecords] = useState([]);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [travelSummary, setTravelSummary] = useState(null);
  const [reports, setReports] = useState([]);
  const [inventoryItems, setInventoryItems] = useState([]);
  const [inventoryImports, setInventoryImports] = useState([]);
  const [users, setUsers] = useState([]);
  const [lastRun, setLastRun] = useState(null);
  const [routeMessage, setRouteMessage] = useState(DEFAULT_ROUTE_REQUEST);
  const [lastRoute, setLastRoute] = useState(null);
  const [health, setHealth] = useState(null);
  const [search, setSearch] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [routeLoading, setRouteLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem("admin_agent_theme", theme);
  }, [theme]);

  function navigateToTab(tab, { replace = false } = {}) {
    const safeTab = tabRoutes[tab] ? tab : "dashboard";
    const nextPath = routeForTab(safeTab);
    if (window.location.pathname !== nextPath) {
      const method = replace ? "replaceState" : "pushState";
      window.history[method]({}, "", nextPath);
    }
    setActiveTab(safeTab);
  }

  async function loadTicketsSafely() {
    try {
      return await getTickets();
    } catch (err) {
      if (err.status === 404) {
        return { tickets: [] };
      }
      throw err;
    }
  }

  async function loadNotificationsSafely() {
    try {
      return await getNotifications();
    } catch (err) {
      if (err.status === 404) {
        return { notifications: [], unread_count: 0 };
      }
      throw err;
    }
  }

  async function refresh(userOverride = currentUser) {
    const canLoadVendors = canAccessTab(userOverride, "vendors");
    const canLoadExpenses = canAccessTab(userOverride, "expenses");
    const canLoadInventory = canAccessTab(userOverride, "inventory");
    const canLoadTravel = canAccessTab(userOverride, "travel");
    const canLoadReports = canAccessTab(userOverride, "reports");
    const canLoadTasks = canAccessTab(userOverride, "tasks");
    const [dash, approvalPayload, auditPayload, healthPayload, taskPayload, ticketPayload, notificationPayload, vendorPayload, expensePayload, travelPayload, calendarPayload, travelSummaryPayload, reportPayload, inventoryPayload, inventoryImportsPayload] = await Promise.all([
      getDashboard(),
      getApprovals(),
      getAuditLog(),
      getHealth(),
      canLoadTasks ? getTasks() : Promise.resolve({ tasks: [] }),
      loadTicketsSafely(),
      loadNotificationsSafely(),
      canLoadVendors ? getVendors() : Promise.resolve({ vendors: [] }),
      canLoadExpenses ? getExpenses() : Promise.resolve({ expenses: [] }),
      canLoadTravel ? getTravelRecords() : Promise.resolve({ travel_records: [] }),
      canLoadTravel ? getCalendarEvents() : Promise.resolve({ calendar_events: [] }),
      canLoadTravel ? getTravelSummary() : Promise.resolve(null),
      canLoadReports ? getReports() : Promise.resolve({ reports: [] }),
      canLoadInventory ? getInventoryItems() : Promise.resolve({ inventory_items: [] }),
      canLoadInventory ? getInventoryImports() : Promise.resolve({ imports: [] })
    ]);
    setDashboard(dash);
    setApprovals(approvalPayload.approvals);
    setAuditLogs(auditPayload.audit_logs);
    setHealth(healthPayload);
    setTasks(taskPayload.tasks || []);
    setTickets(ticketPayload.tickets);
    setNotifications(notificationPayload.notifications || []);
    setUnreadNotificationCount(notificationPayload.unread_count || 0);
    setVendors(vendorPayload.vendors);
    setExpenses(expensePayload.expenses);
    setTravelRecords(travelPayload.travel_records);
    setCalendarEvents(calendarPayload.calendar_events);
    setTravelSummary(travelSummaryPayload);
    setReports(reportPayload.reports);
    setInventoryItems(inventoryPayload.inventory_items);
    setInventoryImports(inventoryImportsPayload.imports);
    if (userOverride?.role === "admin") {
      const userPayload = await getUsers();
      setUsers(userPayload.users);
    } else {
      setUsers([]);
    }
    return {
      dashboard: dash,
      approvals: approvalPayload.approvals,
      auditLogs: auditPayload.audit_logs,
      health: healthPayload,
      tasks: taskPayload.tasks || [],
      tickets: ticketPayload.tickets,
      notifications: notificationPayload.notifications || [],
      vendors: vendorPayload.vendors,
      expenses: expensePayload.expenses,
      travelRecords: travelPayload.travel_records,
      calendarEvents: calendarPayload.calendar_events,
      travelSummary: travelSummaryPayload,
      reports: reportPayload.reports,
      inventoryItems: inventoryPayload.inventory_items,
      inventoryImports: inventoryImportsPayload.imports
    };
  }

  useEffect(() => {
    function handlePopState() {
      const nextTab = tabFromPath();
      if (nextTab) {
        setActiveTab(nextTab);
      } else {
        navigateToTab("dashboard", { replace: true });
      }
    }

    window.addEventListener("popstate", handlePopState);
    getHealth().then(setHealth).catch(() => {});
    getCurrentUser()
      .then((payload) => {
        const requestedTab = tabFromPath();
        if (!requestedTab) {
          navigateToTab("dashboard", { replace: true });
        } else {
          setActiveTab(requestedTab);
        }
        setCurrentUser(payload.user);
        return refresh(payload.user).catch((err) => {
          if (err.status === 401) {
            setAuthToken("");
            setCurrentUser(null);
            return;
          }
          setError(apiErrorMessage(err));
        });
      })
      .catch((err) => {
        if (err.status !== 401) {
          setError(apiErrorMessage(err));
        }
        setAuthToken("");
        setCurrentUser(null);
      })
      .finally(() => setCheckingAuth(false));

    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  async function handleLogin(email, password) {
    setLoading(true);
    setError("");
    try {
      const payload = await login(email, password);
      const requestedTab = tabFromPath();
      const nextTab = requestedTab && canAccessTab(payload.user, requestedTab) ? requestedTab : "dashboard";
      setAuthToken(payload.token);
      setCurrentUser(payload.user);
      navigateToTab(nextTab, { replace: true });
      await refresh(payload.user);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    setLoading(true);
    setError("");
    try {
      await logout();
    } catch {
      // Local logout should still clear the client session if the server token expired.
    } finally {
      setAuthToken("");
      setCurrentUser(null);
      setDashboard(null);
      setApprovals([]);
      setAuditLogs([]);
      setTasks([]);
      setTickets([]);
      setNotifications([]);
      setUnreadNotificationCount(0);
      setVendors([]);
      setExpenses([]);
      setTravelRecords([]);
      setCalendarEvents([]);
      setTravelSummary(null);
      setReports([]);
      setInventoryItems([]);
      setInventoryImports([]);
      setUsers([]);
      setLastRun(null);
      setLastRoute(null);
      navigateToTab("dashboard", { replace: true });
      setLoading(false);
    }
  }

  async function handleRun() {
    setLoading(true);
    setError("");
    try {
      const result = await runCommand(command);
      setLastRun(result);
      await refresh();
      navigateToTab("dashboard");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleRouteRequest() {
    setRouteLoading(true);
    setError("");
    try {
      const result = await routeRequest(routeMessage);
      setLastRoute(result);
      await refresh();
      navigateToTab("dashboard");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setRouteLoading(false);
    }
  }

  async function handleReset() {
    setLoading(true);
    setError("");
    try {
      await resetDemo();
      setLastRun(null);
      await refresh();
      navigateToTab("dashboard");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function handleNewAutomation() {
    navigateToTab("dashboard");
    window.setTimeout(() => routingInputRef.current?.focus(), 0);
  }

  function toggleTheme() {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }

  useEffect(() => {
    if (!accountOpen) return undefined;

    function handlePointerDown(event) {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setAccountOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setAccountOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [accountOpen]);

  function handleSearchSubmit(event) {
    event.preventDefault();
    const normalized = search.trim().toLowerCase();
    if (!normalized) {
      navigateToTab("dashboard");
      return;
    }

    const route = searchRoutes.find((item) =>
      item.terms.some((term) => normalized === term || normalized.includes(term))
    );
    navigateToTab(route?.id || "dashboard");
  }

  function clearSearch() {
    setSearch("");
  }

  const filteredDashboard = useMemo(() => {
    if (!dashboard) return null;
    return {
      ...dashboard,
      meetings: (dashboard.meetings || []).filter((item) => matchesSearch(item, search)),
      tasks: (dashboard.tasks || []).filter((item) => matchesSearch(item, search)),
      tickets: (dashboard.tickets || []).filter((item) => matchesSearch(item, search)),
      pending_approvals: (dashboard.pending_approvals || []).filter((item) => matchesSearch(item, search)),
      audit_logs: (dashboard.audit_logs || []).filter((item) => matchesSearch(item, search)),
      reports: (dashboard.reports || []).filter((item) => matchesSearch(item, search)),
      expenses: (dashboard.expenses || []).filter((item) => matchesSearch(item, search)),
      travel_records: (dashboard.travel_records || []).filter((item) => matchesSearch(item, search)),
      inventory_items: (dashboard.inventory_items || []).filter((item) => matchesSearch(item, search)),
      vendors: (dashboard.vendors || []).filter((item) => matchesSearch(item, search)),
      recent_notes: (dashboard.recent_notes || []).filter((item) => matchesSearch(item, search)),
      routed_requests: (dashboard.routed_requests || []).filter((item) => matchesSearch(item, search))
    };
  }, [dashboard, search]);

  const filteredApprovals = useMemo(
    () => approvals.filter((item) => matchesSearch(item, search)),
    [approvals, search]
  );

  const filteredTasks = useMemo(
    () => tasks.filter((item) => matchesSearch(item, search)),
    [tasks, search]
  );

  const filteredTickets = useMemo(
    () => tickets.filter((item) => matchesSearch(item, search)),
    [tickets, search]
  );

  const filteredExpenses = useMemo(
    () => expenses.filter((item) => matchesSearch(item, search)),
    [expenses, search]
  );

  const filteredTravelRecords = useMemo(
    () => travelRecords.filter((item) => matchesSearch(item, search)),
    [travelRecords, search]
  );

  const filteredCalendarEvents = useMemo(
    () => calendarEvents.filter((item) => matchesSearch(item, search)),
    [calendarEvents, search]
  );

  const filteredReports = useMemo(
    () => reports.filter((item) => matchesSearch(item, search)),
    [reports, search]
  );

  const filteredAuditLogs = useMemo(
    () => auditLogs.filter((item) => matchesSearch(item, search)),
    [auditLogs, search]
  );

  const notificationBadgeCount = Math.min(unreadNotificationCount, 99);

  async function handleNotificationClick(notification) {
    try {
      if (notification.unread) {
        const response = await markNotificationRead(notification.id);
        if (response?.notification) {
          setNotifications((current) =>
            current.map((item) => item.id === notification.id ? response.notification : item)
          );
          setUnreadNotificationCount((current) => Math.max(0, current - 1));
        }
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    }
    if (notification.related_entity_type === "ticket") {
      navigateToTab("approvals");
    } else if (notification.related_entity_type === "task") {
      navigateToTab("tasks");
    }
    setNotificationsOpen(false);
  }

  async function handleMarkAllNotificationsRead() {
    try {
      const response = await markAllNotificationsRead();
      setNotifications(response.notifications || []);
      setUnreadNotificationCount(response.unread_count || 0);
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  const activeLabel = useMemo(
    () => activeTab === "settings" ? "Settings" : navItems.find((item) => item.id === activeTab)?.label || "Dashboard",
    [activeTab]
  );
  const canAccessActiveTab = canAccessTab(currentUser, activeTab);

  if (checkingAuth) {
    return <div className="auth-shell"><p className="empty">Loading</p></div>;
  }

  if (!currentUser) {
    return <LoginScreen loading={loading} error={error} onLogin={handleLogin} />;
  }

  return (
    <div className={activeTab === "dashboard" ? "app-shell dashboard-shell" : "app-shell"}>
      <header className="app-header">
        <div className="utility-bar">
          <div className="brand">
            <div className="brand-mark">AC</div>
            <div>
              <strong>Agent Concierge</strong>
            </div>
          </div>
          <form className="utility-search-form" onSubmit={handleSearchSubmit} role="search">
            <div className="search-box">
              <Search size={20} />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search anything..."
              />
              {search ? (
                <button className="search-clear" onClick={clearSearch} type="button" title="Clear search" aria-label="Clear search">
                  <X size={16} />
                </button>
              ) : (
                <span className="key-hint">⌘ K</span>
              )}
            </div>
          </form>
          <div className="topbar-actions">
            <div className="notification-wrap">
              <button
                aria-expanded={notificationsOpen}
                aria-label="Open notifications"
                className="notification-button"
                onClick={() => {
                  setNotificationsOpen((open) => !open);
                  setAccountOpen(false);
                }}
                type="button"
                title="Notifications"
              >
                <Bell size={19} />
                {notificationBadgeCount > 0 && <span>{notificationBadgeCount}</span>}
              </button>
              {notificationsOpen && (
                <div className="notification-panel" role="dialog" aria-label="Notifications">
                  <div className="notification-header">
                    <div>
                      <strong>Notifications</strong>
                      {unreadNotificationCount > 0 && <span>{unreadNotificationCount} unread</span>}
                    </div>
                    {unreadNotificationCount > 0 && (
                      <button className="notification-mark-all" type="button" onClick={handleMarkAllNotificationsRead}>
                        Mark all as read
                      </button>
                    )}
                    <button type="button" onClick={() => setNotificationsOpen(false)} aria-label="Close notifications">
                      <X size={16} />
                    </button>
                  </div>
                  {notifications.length === 0 ? (
                    <p className="empty">No notifications yet.</p>
                  ) : (
                    <div className="notification-list">
                      {notifications.map((item) => (
                        <button
                          className={item.unread ? "notification-item unread" : "notification-item"}
                          key={item.id}
                          onClick={() => handleNotificationClick(item)}
                          type="button"
                        >
                          <strong>{item.title}</strong>
                          <span>{item.message}</span>
                          <small>{formatDate(item.created_at)}</small>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            <button
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              className="theme-toggle"
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              type="button"
            >
              <span className={theme === "light" ? "active" : ""}><Sun size={17} /></span>
              <span className={theme === "dark" ? "active" : ""}><Moon size={17} /></span>
            </button>
            <div className="utility-divider" aria-hidden="true" />
            <div className="account-wrap" ref={accountMenuRef}>
              <button
                aria-expanded={accountOpen}
                aria-label="Open user account menu"
                className="user-chip"
                onClick={() => {
                  setAccountOpen((open) => !open);
                  setNotificationsOpen(false);
                }}
                type="button"
              >
                <div className="user-avatar">
                  {initials(currentUser.name)}
                </div>
                <div>
                  <strong>{currentUser.name}</strong>
                  <span>{currentUser.email}</span>
                </div>
                <ChevronDown size={16} />
              </button>
              {accountOpen && (
                <div className="account-panel" role="dialog" aria-label="User account">
                  <div className="account-panel-header">
                    <div className="user-avatar">
                      {initials(currentUser.name)}
                    </div>
                    <div>
                      <strong>{currentUser.name}</strong>
                      <span>{currentUser.email}</span>
                    </div>
                  </div>
                  <button className="account-menu-item account-logout" onClick={handleLogout} type="button">
                    <LogOut size={18} />
                    <span>Logout</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
        <nav className="top-nav section-nav" aria-label="Main navigation">
          {visibleNavItemsForRole(currentUser.role, topNavItems).map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={activeTab === item.id ? "nav-item active" : "nav-item"}
                onClick={() => navigateToTab(item.id)}
                type="button"
                title={item.label}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </header>

      <main className={activeTab === "dashboard" ? "main dashboard-main" : "main"}>
        {!["dashboard", "vendors", "inventory", "settings", "expenses", "approvals", "travel", "reports", "tasks"].includes(activeTab) && (
          <div className="page-heading">
            <div className="page-title">
              <h1>{activeLabel}</h1>
              <p>Welcome back, {currentUser.name}</p>
            </div>
            {activeTab === "dashboard" && currentUser.role === "admin" && (
              <button className="icon-button secondary" onClick={handleReset} type="button" title="Reset demo">
                <RefreshCw size={18} />
                <span>Reset Demo</span>
              </button>
            )}
          </div>
        )}

        {error && <div className="alert" role="alert">{error}</div>}

        {!canAccessActiveTab && <AccessDenied activeLabel={activeLabel} currentUser={currentUser} />}

        {canAccessActiveTab && activeTab === "dashboard" && (
          <OperationsDashboard
            approvals={approvals}
            filteredApprovals={filteredApprovals}
            auditLogs={auditLogs}
            filteredAuditLogs={filteredAuditLogs}
            command={command}
            currentUser={currentUser}
            dashboard={dashboard}
            filteredDashboard={filteredDashboard}
            lastRun={lastRun}
            lastRoute={lastRoute}
            loading={loading}
            routeLoading={routeLoading}
            automationInputRef={automationInputRef}
            routingInputRef={routingInputRef}
            onCommandChange={setCommand}
            onRun={handleRun}
            onRouteRequest={handleRouteRequest}
            onRouteMessageChange={setRouteMessage}
            onUpdated={refresh}
            onNavigate={navigateToTab}
            routeMessage={routeMessage}
            search={search}
            setError={setError}
          />
        )}
        {canAccessActiveTab && activeTab === "tasks" && (
          <TasksView
            currentUser={currentUser}
            onChanged={refresh}
            onTaskDeleted={(taskId) => {
              setTasks((current) => current.filter((task) => task.id !== taskId));
            }}
            onTaskSaved={(task) => {
              setTasks((current) => {
                const existingIndex = current.findIndex((item) => item.id === task.id);
                if (existingIndex === -1) return [task, ...current];
                return current.map((item) => (item.id === task.id ? task : item));
              });
            }}
            setError={setError}
            tasks={filteredTasks}
          />
        )}
        {canAccessActiveTab && activeTab === "approvals" && (
          <TicketsView
            currentUser={currentUser}
            onTicketSaved={(ticket) => {
              setTickets((current) => {
                const existingIndex = current.findIndex((item) => item.id === ticket.id);
                if (existingIndex === -1) return [ticket, ...current];
                return current.map((item) => (item.id === ticket.id ? ticket : item));
              });
            }}
            onUpdated={refresh}
            setError={setError}
            tickets={filteredTickets}
          />
        )}
        {canAccessActiveTab && activeTab === "vendors" && (
          <VendorsView
            currentUser={currentUser}
            onChanged={refresh}
            setError={setError}
            vendors={vendors}
          />
        )}
        {canAccessActiveTab && activeTab === "travel" && (
          <TravelCalendarView
            calendarEvents={filteredCalendarEvents}
            currentUser={currentUser}
            onCalendarEventSaved={(calendarEvent) => {
              setCalendarEvents((current) => {
                const existingIndex = current.findIndex((item) => item.id === calendarEvent.id);
                if (existingIndex === -1) return [...current, calendarEvent];
                return current.map((item) => (item.id === calendarEvent.id ? calendarEvent : item));
              });
            }}
            onChanged={refresh}
            onTravelRecordSaved={(travelRecord) => {
              setTravelRecords((current) => {
                const existingIndex = current.findIndex((item) => item.id === travelRecord.id);
                if (existingIndex === -1) return [travelRecord, ...current];
                return current.map((item) => (item.id === travelRecord.id ? travelRecord : item));
              });
            }}
            setError={setError}
            summary={travelSummary}
            travelRecords={filteredTravelRecords}
          />
        )}
        {canAccessActiveTab && activeTab === "expenses" && (
          <ExpenseView
            currentUser={currentUser}
            expenses={filteredExpenses}
            onChanged={refresh}
            onExpenseSaved={(expense) => {
              setExpenses((current) => {
                const existingIndex = current.findIndex((item) => item.id === expense.id);
                if (existingIndex === -1) return [expense, ...current];
                return current.map((item) => (item.id === expense.id ? expense : item));
              });
            }}
            setError={setError}
          />
        )}
        {canAccessActiveTab && activeTab === "inventory" && (
          <InventoryView
            currentUser={currentUser}
            inventoryImports={inventoryImports}
            inventoryItems={inventoryItems}
            onChanged={refresh}
            onItemSaved={(inventoryItem) => {
              setInventoryItems((current) => {
                const existingIndex = current.findIndex((item) => item.id === inventoryItem.id);
                if (existingIndex === -1) return [inventoryItem, ...current];
                return current.map((item) => (item.id === inventoryItem.id ? inventoryItem : item));
              });
            }}
            setError={setError}
          />
        )}
        {canAccessActiveTab && activeTab === "reports" && (
          <ReportsView
            currentUser={currentUser}
            onChanged={refresh}
            onReportDeleted={(reportId) => {
              setReports((current) => current.filter((report) => report.id !== reportId));
            }}
            onReportSaved={(report) => {
              setReports((current) => [report, ...current.filter((item) => item.id !== report.id)]);
            }}
            reports={filteredReports}
            setError={setError}
          />
        )}
        {canAccessActiveTab && activeTab === "settings" && (
          <SettingsView
            currentUser={currentUser}
            health={health}
            onChanged={refresh}
            setError={setError}
            users={users}
          />
        )}
      </main>
    </div>
  );
}

function LoginScreen({ loading, error, onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

  function submit(event) {
    event.preventDefault();
    setStatusMessage("");
    onLogin(email, password);
  }

  return (
    <main className="auth-shell">
      <section className="login-split-shell" aria-label="Agent Concierge login">
        <aside className="login-brand-panel" aria-label="Agent Concierge overview">
          <div className="login-brand-row">
            <div className="login-logo">AC</div>
            <strong>Agent Concierge</strong>
          </div>
          <div className="login-copy">
            <h1>
              Power your
              <span>workflow</span>
              with automation
            </h1>
            <p>
              Secure. Reliable. Intelligent.
              <span>Built for modern teams.</span>
            </p>
          </div>
          <div className="login-feature-list">
            <LoginFeature
              icon={Zap}
              title="Lightning Fast"
              detail="Automate repetitive tasks"
            />
            <LoginFeature
              icon={ShieldCheck}
              title="Enterprise Secure"
              detail="Your data is always safe"
            />
            <LoginFeature
              icon={BarChart3}
              title="Insight Driven"
              detail="Make better decisions"
            />
          </div>
          <div className="login-dot-pattern top" aria-hidden="true" />
          <div className="login-dot-pattern bottom" aria-hidden="true" />
          <div className="login-wave" aria-hidden="true" />
        </aside>

        <section className="login-card-wrap">
          <form className="login-card" autoComplete="off" onSubmit={submit}>
            <div className="login-card-heading">
              <h2>Welcome back 👋</h2>
              <p>Sign in to your account</p>
            </div>
            {error && <div className="alert" role="alert">{error}</div>}
            {statusMessage && <div className="status-message" role="status">{statusMessage}</div>}
            <label>
              Email
              <span className="login-input-shell">
                <Mail size={20} aria-hidden="true" />
                <input
                  autoComplete="off"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="Enter your email"
                  type="email"
                />
              </span>
            </label>
            <label>
              Password
              <span className="login-input-shell">
                <Lock size={20} aria-hidden="true" />
                <input
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  type={showPassword ? "text" : "password"}
                />
                <button
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((visible) => !visible)}
                  title={showPassword ? "Hide password" : "Show password"}
                  type="button"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </span>
            </label>
            <div className="login-options">
              <label className="remember-option">
                <input
                  checked={rememberMe}
                  onChange={(event) => setRememberMe(event.target.checked)}
                  type="checkbox"
                />
                <span>Remember me</span>
              </label>
              <button
                className="inline-link"
                onClick={() => setStatusMessage("Please contact your administrator to reset your password.")}
                type="button"
              >
                Forgot password?
              </button>
            </div>
            <button className="login-submit" disabled={loading} type="submit">
              <span>{loading ? "Logging in" : "Log in"}</span>
              <ArrowRight size={22} />
            </button>
            <div className="login-divider">
              <span />
              <strong>or</strong>
              <span />
            </div>
            <button
              className="google-button"
              onClick={() => setStatusMessage("Google sign-in is not connected in demo mode.")}
              type="button"
            >
              <span className="google-mark">G</span>
              <span>Continue with Google</span>
            </button>
          </form>
          <p className="login-footer">
            Don't have an account? <button type="button" onClick={() => setStatusMessage("Please contact your administrator to create an account.")}>Contact your administrator</button>
          </p>
        </section>
      </section>
    </main>
  );
}

function LoginFeature({ icon: Icon, title, detail }) {
  return (
    <article className="login-feature">
      <span>
        <Icon size={24} />
      </span>
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
    </article>
  );
}

function OperationsDashboard({
  approvals,
  filteredApprovals,
  auditLogs,
  filteredAuditLogs,
  currentUser,
  dashboard,
  filteredDashboard,
  onUpdated,
  onNavigate,
  search,
  setError
}) {
  const role = dashboard?.role || currentUser.role;
  const dashboardData = filteredDashboard || dashboard || {};
  const tickets = dashboardData.tickets || [];
  const tasks = dashboardData.tasks || [];
  const pendingApprovals = dashboardData.pending_approvals || filteredApprovals || approvals || [];
  const auditEntries = dashboardData.audit_logs || filteredAuditLogs || auditLogs || [];
  const expenses = dashboardData.expenses || [];
  const travelRecords = dashboardData.travel_records || [];
  const inventoryItems = dashboardData.inventory_items || [];
  const vendorBillingDashboard = dashboardData.vendor_billing_dashboard;
  const assistantStorageKey = dashboardAssistantSessionKey(currentUser);
  const [assistantExpanded, setAssistantExpanded] = useState(false);
  const [assistantClosed, setAssistantClosed] = useState(false);
  const [assistantMessages, setAssistantMessages] = useState(() => readDashboardAssistantMessages(assistantStorageKey, currentUser, dashboardData));
  const [assistantDraft, setAssistantDraft] = useState(() => readDashboardAssistantDraft(assistantStorageKey));
  const [assistantAttachment, setAssistantAttachment] = useState(null);
  const [adminDashboardPanel, setAdminDashboardPanel] = useState("");
  const showCompactDashboardCards = ["admin", "it_manager", "finance_manager", "employee"].includes(role);
  const waitingTickets = tickets.filter((ticket) =>
    ticket.approval_required || ["Waiting Approval", "Pending Approval"].includes(ticket.status)
  );

  useEffect(() => {
    setAssistantMessages(readDashboardAssistantMessages(assistantStorageKey, currentUser, dashboardData));
    setAssistantDraft(readDashboardAssistantDraft(assistantStorageKey));
    setAssistantAttachment(null);
    setAssistantExpanded(false);
  }, [assistantStorageKey]);

  useEffect(() => {
    writeDashboardAssistantState(assistantStorageKey, assistantMessages, assistantDraft);
  }, [assistantStorageKey, assistantMessages, assistantDraft]);

  useEffect(() => {
    setAdminDashboardPanel("");
  }, [role]);

  function clearAssistantChat() {
    const seedMessages = createDashboardAssistantSeedMessages(currentUser, dashboardData);
    setAssistantMessages(seedMessages);
    setAssistantDraft("");
    setAssistantAttachment(null);
    writeDashboardAssistantState(assistantStorageKey, seedMessages, "");
  }

  if (!dashboard) {
    return (
      <section className="ops-dashboard command-center-dashboard">
        <EmptyState icon={BarChart3} title="Dashboard data is loading." detail="Summary cards and recent work will appear here shortly." />
      </section>
    );
  }

  return (
    <section className={`ops-dashboard command-center-dashboard dashboard-role-${String(role).replaceAll("_", "-")}`}>
      <div className={dashboardWorkspaceClassName(assistantClosed, assistantExpanded)}>
        <div className="dashboard-main-column">
          <div className="dashboard-command-header">
            <div>
              <h2>{dashboard.title || `${roleLabel(role)} Command Center`}</h2>
            </div>
            {assistantClosed && (
              <button className="icon-button secondary dashboard-ai-open-inline" onClick={() => setAssistantClosed(false)} type="button">
                <Sparkles size={16} />
                <span>Conci AI</span>
              </button>
            )}
          </div>

          <div className="ops-summary-row dashboard-summary-row">
            {(dashboard.summary_cards || []).map((card) => (
              <Metric
                icon={DASHBOARD_SUMMARY_ICONS[card.id] || BarChart3}
                key={card.id}
                label={card.label}
                value={card.value_kind === "currency" ? formatMoney(card.value) : card.value}
              />
            ))}
          </div>

          {role !== "finance_manager" && (
            <DashboardQuickActions actions={dashboard.quick_actions || []} currentUser={currentUser} onNavigate={onNavigate} />
          )}

          <DashboardCharts charts={dashboard?.charts || []} />

          {role === "admin" ? (
            <DashboardAdminActionCards
              auditEntries={auditEntries}
              currentUser={currentUser}
              pendingApprovals={pendingApprovals}
              tickets={tickets}
              vendorBillingDashboard={vendorBillingDashboard}
              waitingTickets={waitingTickets}
              onOpen={setAdminDashboardPanel}
            />
          ) : (
            <div className="ops-grid dashboard-role-grid">
              {role === "it_manager" && (
                <>
                  <DashboardTicketCard tickets={tickets} title="Recent IT Tickets" />
                  <DashboardInventoryCard items={inventoryItems} title="Inventory Status" />
                  <DashboardTaskCard tasks={tasks} title="IT Tasks" />
                </>
              )}
              {role === "finance_manager" && (
                <>
                  <DashboardExpenseExceptionsCard expenses={expenses} />
                  <DashboardApprovalCard approvals={pendingApprovals} currentUser={currentUser} onUpdated={onUpdated} setError={setError} title="Pending Finance Approvals" />
                  <DashboardTravelCard records={travelRecords} />
                </>
              )}
              {role === "employee" && (
                <>
                  <DashboardTicketCard tickets={tickets} title="My Recent Tickets" />
                  <DashboardTaskCard tasks={tasks} title="My Tasks" />
                  <DashboardTicketCard tickets={waitingTickets} title="My Requests" />
                </>
              )}
            </div>
          )}

          {role === "it_manager" && (
            <DashboardAdminActionCards
              auditEntries={auditEntries}
              currentUser={currentUser}
              pendingApprovals={pendingApprovals}
              tickets={tickets}
              vendorBillingDashboard={vendorBillingDashboard}
              waitingTickets={waitingTickets}
              onOpen={setAdminDashboardPanel}
            />
          )}

          {role === "finance_manager" && (
            <DashboardAdminActionCards
              auditEntries={auditEntries}
              currentUser={currentUser}
              pendingApprovals={pendingApprovals}
              tickets={tickets}
              vendorBillingDashboard={vendorBillingDashboard}
              waitingTickets={waitingTickets}
              onOpen={setAdminDashboardPanel}
            />
          )}

          {role === "employee" && (
            <DashboardAdminActionCards
              auditEntries={auditEntries}
              currentUser={currentUser}
              pendingApprovals={pendingApprovals}
              tickets={tickets}
              vendorBillingDashboard={vendorBillingDashboard}
              waitingTickets={waitingTickets}
              onOpen={setAdminDashboardPanel}
            />
          )}
        </div>

        {!assistantClosed && (
          <DashboardAIAssistantPanel
            attachedFile={assistantAttachment}
            currentUser={currentUser}
            dashboardData={dashboardData}
            draft={assistantDraft}
            expanded={assistantExpanded}
            messages={assistantMessages}
            onAttachmentChange={setAssistantAttachment}
            onClear={clearAssistantChat}
            onClose={() => setAssistantClosed(true)}
            onDraftChange={setAssistantDraft}
            onMessagesChange={setAssistantMessages}
            onRefreshContext={onUpdated}
            onResize={() => setAssistantExpanded((value) => !value)}
          />
        )}
      </div>
      {showCompactDashboardCards && adminDashboardPanel && (
        <DashboardAdminDetailModal
          auditEntries={auditEntries}
          currentUser={currentUser}
          panel={adminDashboardPanel}
          pendingApprovals={pendingApprovals}
          search={search}
          setError={setError}
          tickets={tickets}
          vendorBillingDashboard={vendorBillingDashboard}
          waitingTickets={waitingTickets}
          onClose={() => setAdminDashboardPanel("")}
          onUpdated={onUpdated}
        />
      )}
    </section>
  );
}

function DashboardAIAssistantPanel({
  attachedFile,
  currentUser,
  dashboardData,
  draft,
  expanded,
  messages,
  onAttachmentChange,
  onClear,
  onClose,
  onDraftChange,
  onMessagesChange,
  onRefreshContext,
  onResize
}) {
  const [sending, setSending] = useState(false);
  const [refreshingContext, setRefreshingContext] = useState(false);
  const [editingMessage, setEditingMessage] = useState(null);
  const messagesRef = useRef(null);
  const fileInputRef = useRef(null);
  const suggestions = dashboardAssistantSuggestions(currentUser);

  useEffect(() => {
    if (!messagesRef.current) return;
    messagesRef.current.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, sending, expanded]);

  async function sendMessage(messageText, options = {}) {
    const cleanMessage = messageText.trim();
    const selectedAttachment = options.attachment || attachedFile;
    const action = options.action || null;
    if ((!cleanMessage && !selectedAttachment && !action) || sending) return;
    const now = new Date();
    const requestId = `chat-${Date.now()}`;
    const history = dashboardAssistantHistoryPayload(messages);
    onMessagesChange((current) => [
      ...current,
      {
        id: `user-${Date.now()}`,
        requestId,
        role: "user",
        text: cleanMessage || "Attached file",
        attachmentName: selectedAttachment?.name || "",
        time: formatAssistantTime(now)
      }
    ]);
    onDraftChange((currentDraft) => (currentDraft.trim() === cleanMessage ? "" : currentDraft));

    setSending(true);
    try {
      const response = await askChatbot(cleanMessage, selectedAttachment?.file || null, action, history);
      const reply = response.response || response || {};
      onMessagesChange((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          requestId,
          role: "assistant",
          text: reply.answer || reply.message || "I couldn’t find matching data for your access level.",
          bullets: reply.bullets || response.bullets || [],
          table: reply.table || response.table || null,
          source: reply.source || response.source,
          nextQuestion: reply.next_question || "",
          actionRequired: reply.action_required || "",
          confirmationRequired: Boolean(reply.confirmation_required),
          action: reply.action || null,
          createdRecordId: reply.created_record_id || "",
          time: formatAssistantTime(new Date())
        }
      ]);
      if (selectedAttachment) {
        onAttachmentChange(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    } catch (err) {
      onMessagesChange((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          requestId,
          role: "assistant",
          status: "error",
          text: `I could not answer that request: ${apiErrorMessage(err)}`,
          time: formatAssistantTime(new Date())
        }
      ]);
    } finally {
      setSending(false);
    }
  }

  async function updateEditedMessage(messageText) {
    const cleanMessage = messageText.trim();
    const selectedAttachment = attachedFile;
    if (!editingMessage || (!cleanMessage && !selectedAttachment) || sending) return;
    const requestId = editingMessage.requestId || `chat-edit-${Date.now()}`;
    const history = dashboardAssistantHistoryPayload(messages.filter((message) => message.id !== editingMessage.id));
    const updatedUserMessage = {
      ...editingMessage.originalMessage,
      requestId,
      text: cleanMessage || "Attached file",
      attachmentName: selectedAttachment?.name || "",
      edited: true,
      time: formatAssistantTime(new Date())
    };
    onMessagesChange((current) => replaceEditedChatMessage(current, editingMessage, updatedUserMessage));
    onDraftChange((currentDraft) => (currentDraft.trim() === cleanMessage ? "" : currentDraft));

    setSending(true);
    try {
      const response = await askChatbot(cleanMessage, selectedAttachment?.file || null, null, history);
      const reply = response.response || response || {};
      onMessagesChange((current) => [
        ...current,
        {
          id: `assistant-${Date.now()}`,
          requestId,
          role: "assistant",
          text: reply.answer || reply.message || "I couldn’t find matching data for your access level.",
          bullets: reply.bullets || response.bullets || [],
          table: reply.table || response.table || null,
          source: reply.source || response.source,
          nextQuestion: reply.next_question || "",
          actionRequired: reply.action_required || "",
          confirmationRequired: Boolean(reply.confirmation_required),
          action: reply.action || null,
          createdRecordId: reply.created_record_id || "",
          time: formatAssistantTime(new Date())
        }
      ]);
      setEditingMessage(null);
      if (selectedAttachment) {
        onAttachmentChange(null);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    } catch (err) {
      onMessagesChange((current) => [
        ...current,
        {
          id: `assistant-error-${Date.now()}`,
          requestId,
          role: "assistant",
          status: "error",
          text: `I could not answer that request: ${apiErrorMessage(err)}`,
          time: formatAssistantTime(new Date())
        }
      ]);
    } finally {
      setSending(false);
    }
  }

  function submitMessage(event) {
    event.preventDefault();
    if (editingMessage) {
      updateEditedMessage(draft);
      return;
    }
    sendMessage(draft);
  }

  function handleComposerKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (editingMessage) {
        updateEditedMessage(draft);
        return;
      }
      sendMessage(draft);
    }
  }

  function startEditingMessage(message) {
    if (sending || message.role !== "user") return;
    setEditingMessage({
      id: message.id,
      requestId: message.requestId || "",
      attachmentName: message.attachmentName || "",
      originalMessage: message,
      preEditDraft: draft
    });
    onDraftChange(message.attachmentName && message.text === "Attached file" ? "" : message.text || "");
  }

  function cancelEditingMessage() {
    onDraftChange(editingMessage?.preEditDraft || "");
    setEditingMessage(null);
  }

  function chooseAttachment(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    onAttachmentChange({
      file,
      name: file.name,
      size: file.size,
      type: file.type
    });
  }

  function clearAttachment() {
    onAttachmentChange(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function clearDraftText() {
    onDraftChange("");
  }

  async function refreshAssistantContext() {
    if (refreshingContext || sending) return;
    setRefreshingContext(true);
    try {
      await onRefreshContext?.();
    } finally {
      setRefreshingContext(false);
    }
  }

  function confirmClearChat() {
    if (sending) return;
    const confirmed = window.confirm("Are you sure you want to clear this chat?");
    if (confirmed) {
      setEditingMessage(null);
      onClear();
    }
  }

  function confirmAssistantAction(message) {
    if (!message.action || sending) return;
    sendMessage("Confirm", { action: message.action });
  }

  function cancelAssistantAction(message) {
    if (sending) return;
    onMessagesChange((current) => [
      ...current,
      {
        id: `assistant-cancel-${Date.now()}`,
        requestId: message.requestId || "",
        role: "assistant",
        text: "Action canceled.",
        source: "Conci AI",
        time: formatAssistantTime(new Date())
      }
    ]);
  }

  return (
    <aside className={expanded ? "dashboard-ai-panel expanded" : "dashboard-ai-panel"} aria-label="Conci AI">
      <div className="dashboard-ai-header">
        <span className="dashboard-ai-icon"><Sparkles size={18} /></span>
        <div>
          <h2>Conci AI</h2>
          <p>Your smart concierge</p>
        </div>
        <button className="dashboard-ai-icon-button" onClick={refreshAssistantContext} type="button" aria-label="Refresh Conci AI context" disabled={sending || refreshingContext}>
          <RefreshCw size={16} />
        </button>
        <button className="dashboard-ai-icon-button" onClick={onResize} type="button" aria-label={expanded ? "Return Conci AI to normal size" : "Expand Conci AI"}>
          {expanded ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
        </button>
        <button className="dashboard-ai-icon-button" onClick={confirmClearChat} type="button" aria-label="Clear Conci AI chat" disabled={sending} title="Clear chat">
          <Trash2 size={16} />
        </button>
        <button className="dashboard-ai-icon-button" onClick={onClose} type="button" aria-label="Close Conci AI">
          <X size={17} />
        </button>
      </div>

      <div className="dashboard-ai-messages" ref={messagesRef}>
        {messages.map((message) => (
          <article className={`dashboard-ai-message ${message.role}${message.status ? ` ${message.status}` : ""}`} key={message.id}>
            {message.role === "user" && (
              <div className="dashboard-ai-message-actions">
                <button
                  aria-label="Edit message"
                  disabled={sending}
                  onClick={() => startEditingMessage(message)}
                  title="Edit message"
                  type="button"
                >
                  <Pencil size={13} />
                </button>
              </div>
            )}
            {String(message.text || "").split("\n").map((line, lineIndex) => (
              <p key={`${message.id}-${lineIndex}`}>{line}</p>
            ))}
            {message.attachmentName && (
              <span className="dashboard-ai-attachment">
                <Paperclip size={13} />
                {message.attachmentName}
              </span>
            )}
            {message.bullets?.length > 0 && (
              <ul>
                {message.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}
              </ul>
            )}
            <DashboardAIMessageTable table={message.table} />
            {message.nextQuestion && (
              <div className="dashboard-ai-followup">
                <strong>Next question</strong>
                <span>{message.nextQuestion}</span>
              </div>
            )}
            {message.createdRecordId && (
              <span className="dashboard-ai-record-link">Created: {message.createdRecordId}</span>
            )}
            {message.confirmationRequired && message.action && (
              <div className="dashboard-ai-confirm-actions">
                <button type="button" onClick={() => confirmAssistantAction(message)} disabled={sending}>Confirm</button>
                <button type="button" onClick={() => cancelAssistantAction(message)} disabled={sending}>Cancel</button>
              </div>
            )}
            {message.source && <span className="dashboard-ai-source">{message.source}</span>}
            <time>{message.time}</time>
          </article>
        ))}
        {sending && (
          <article className="dashboard-ai-typing" aria-live="polite">
            <span className="dashboard-ai-typing-icon"><Sparkles size={15} /></span>
            <span className="dashboard-ai-typing-dots" aria-label="Conci AI is typing">
              <i />
              <i />
              <i />
            </span>
          </article>
        )}
      </div>

      <div className="dashboard-ai-suggestions" aria-label="Conci AI suggestions">
        {suggestions.map((suggestion) => (
          <button key={suggestion} onClick={() => sendMessage(suggestion)} type="button" disabled={sending || Boolean(editingMessage)}>
            <span className="dashboard-ai-chip-icon">{dashboardAssistantSuggestionIcon(suggestion)}</span>
            <span>{suggestion}</span>
          </button>
        ))}
      </div>

      {editingMessage && (
        <div className="dashboard-ai-edit-banner">
          <Pencil size={14} />
          <div>
            <strong>Editing message</strong>
            {editingMessage.attachmentName && !attachedFile && (
              <span>Attachment will not be resent unless selected again.</span>
            )}
          </div>
          <button onClick={cancelEditingMessage} type="button" disabled={sending}>
            Cancel
          </button>
        </div>
      )}

      {attachedFile && (
        <div className="dashboard-ai-attachment-draft">
          <Paperclip size={14} />
          <span>{attachedFile.name}</span>
          <button onClick={clearAttachment} type="button" aria-label="Remove attached file">
            <X size={14} />
          </button>
        </div>
      )}

      <form className="dashboard-ai-input" onSubmit={submitMessage}>
        <input
          accept="*/*"
          className="sr-only"
          onChange={chooseAttachment}
          ref={fileInputRef}
          type="file"
        />
        <button
          className="dashboard-ai-attach-button"
          disabled={sending}
          onClick={() => fileInputRef.current?.click()}
          type="button"
          aria-label="Attach file"
        >
          <Paperclip size={17} />
        </button>
        <textarea
          aria-label="Ask Conci AI"
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={handleComposerKeyDown}
          placeholder={editingMessage ? "Edit your message..." : "Ask anything..."}
          rows={2}
          value={draft}
        />
        <button
          className="dashboard-ai-clear-draft-button"
          disabled={sending || !draft}
          onClick={clearDraftText}
          type="button"
          aria-label="Clear current input"
          title="Clear input"
        >
          <X size={15} />
        </button>
        <button type="submit" aria-label={editingMessage ? "Update message" : "Send message"} disabled={sending || (!draft.trim() && !attachedFile)}>
          {editingMessage ? <CheckCircle2 size={17} /> : <Send size={17} />}
        </button>
      </form>
    </aside>
  );
}

function DashboardAIMessageTable({ table }) {
  if (!table || !Array.isArray(table.columns) || !Array.isArray(table.rows) || table.rows.length === 0) return null;
  const columns = table.columns.map((column) => String(column || "").trim()).filter(Boolean);
  if (!columns.length) return null;
  return (
    <div className="dashboard-ai-table-wrap">
      <table className="dashboard-ai-table">
        <thead>
          <tr>
            {columns.map((column) => <th key={column}>{dashboardAIColumnLabel(column)}</th>)}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${columns.join("-")}`}>
              {columns.map((column, columnIndex) => (
                <td key={column}>
                  {Array.isArray(row) ? row[columnIndex] : row?.[column]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function dashboardAssistantHistoryPayload(messages) {
  return (Array.isArray(messages) ? messages : [])
    .slice(-8)
    .map((message) => ({
      role: message.role || "",
      text: String(message.text || "").slice(0, 500),
      source: message.source || ""
    }))
    .filter((message) => message.text || message.source);
}

function dashboardAIColumnLabel(column) {
  const normalized = String(column || "").trim().toLowerCase();
  const labels = {
    service: "Category/Service",
    category: "Category/Service",
    contact: "Contact Person",
    "contact person": "Contact Person",
    phone: "Contact Number",
    "contact number": "Contact Number",
    billing: "Billing",
    status: "Status",
    "vendor name": "Vendor Name"
  };
  return labels[normalized] || column;
}

function dashboardAssistantSuggestionIcon(suggestion) {
  const text = String(suggestion || "").toLowerCase();
  if (text.includes("approval")) return <ClipboardList size={16} />;
  if (text.includes("vendor")) return <Building2 size={16} />;
  if (text.includes("ticket")) return <ShieldCheck size={16} />;
  if (text.includes("inventory") || text.includes("device")) return <Package size={16} />;
  if (text.includes("expense") || text.includes("billing") || text.includes("spend")) return <DollarSign size={16} />;
  if (text.includes("task")) return <ListChecks size={16} />;
  return <Sparkles size={16} />;
}

function replaceEditedChatMessage(messages, editingMessage, updatedUserMessage) {
  const userIndex = messages.findIndex((message) => message.id === editingMessage.id);
  if (userIndex === -1) return messages;
  const requestId = editingMessage.requestId;
  let reachedNextUser = false;

  return messages.flatMap((message, index) => {
    if (index === userIndex) return [updatedUserMessage];
    if (index <= userIndex) return [message];
    if (requestId && message.role === "assistant" && message.requestId === requestId) return [];
    if (!requestId) {
      if (message.role === "user") reachedNextUser = true;
      if (!reachedNextUser && message.role === "assistant") return [];
    }
    return [message];
  });
}

function createDashboardAssistantSeedMessages(currentUser, dashboardData) {
  const role = normalizeRoleValue(currentUser?.role);
  const greetingName = String(currentUser?.name || roleLabel(role) || "there").split(" ")[0] || "there";
  return [
    {
      id: "assistant-hello",
      role: "assistant",
      text: `Hello ${greetingName}! 👋\nI’m Conci AI. How can I help you today?`,
      time: formatAssistantTime(new Date())
    }
  ];
}

function dashboardAssistantSessionKey(currentUser) {
  return `conci-ai-chat:${currentUser?.id || currentUser?.email || "guest"}`;
}

function dashboardWorkspaceClassName(assistantClosed, assistantExpanded) {
  const classes = ["dashboard-workspace"];
  if (assistantClosed) classes.push("assistant-closed");
  if (assistantExpanded) classes.push("assistant-expanded");
  return classes.join(" ");
}

function readDashboardAssistantMessages(storageKey, currentUser, dashboardData) {
  if (typeof window === "undefined") return createDashboardAssistantSeedMessages(currentUser, dashboardData);
  try {
    const saved = window.sessionStorage.getItem(`${storageKey}:messages`);
    const parsed = saved ? JSON.parse(saved) : null;
    if (Array.isArray(parsed) && parsed.length > 0) return parsed;
  } catch {
    // Ignore malformed session data and start a fresh chat.
  }
  return createDashboardAssistantSeedMessages(currentUser, dashboardData);
}

function readDashboardAssistantDraft(storageKey) {
  if (typeof window === "undefined") return "";
  try {
    return window.sessionStorage.getItem(`${storageKey}:draft`) || "";
  } catch {
    return "";
  }
}

function writeDashboardAssistantState(storageKey, messages, draft) {
  if (typeof window === "undefined") return;
  try {
    window.sessionStorage.setItem(`${storageKey}:messages`, JSON.stringify(messages));
    window.sessionStorage.setItem(`${storageKey}:draft`, draft || "");
  } catch {
    // Session persistence is a convenience; chat should still work if storage is unavailable.
  }
}

function dashboardAssistantSuggestions(currentUser) {
  const role = normalizeRoleValue(currentUser?.role);
  if (role === "finance_manager") {
    return ["Show monthly expenses", "Show vendor billing", "Show travel spend", "Show pending finance approvals"];
  }
  if (role === "it_manager") {
    return ["Show IT tickets", "Show inventory in use", "Show devices submitted to vendor", "Show IT tasks"];
  }
  if (role === "employee") {
    return ["Show my tickets", "Show my tasks", "Show my pending requests"];
  }
  return ["Show pending approvals", "Show vendor billing", "Show open tickets", "Show inventory summary", "Show monthly expenses"];
}

function formatAssistantTime(date = new Date()) {
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function DashboardQuickActions({ actions = [], currentUser, onNavigate }) {
  if (!actions.length) return null;
  return (
    <div className="dashboard-quick-actions" aria-label="Dashboard quick actions">
      {actions.map((action) => {
        const Icon = DASHBOARD_QUICK_ACTION_ICONS[action.id] || ArrowRight;
        const allowed = canAccessTab(currentUser, action.target_tab);
        return (
          <button
            className="icon-button secondary"
            disabled={!allowed}
            key={action.id}
            onClick={() => allowed && onNavigate?.(action.target_tab)}
            title={allowed ? action.label : "Access denied"}
            type="button"
          >
            <Icon size={16} />
            <span>{action.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function DashboardAdminActionCards({ auditEntries, currentUser, pendingApprovals, tickets, vendorBillingDashboard, waitingTickets = [], onOpen }) {
  const role = normalizeRoleValue(currentUser?.role);
  const pendingCount = pendingApprovals.filter((item) => item.status === "pending").length;
  const vendorCount = vendorBillingDashboard?.current_vendors?.length || 0;
  const cards = [
    {
      id: "recentTickets",
      icon: ShieldAlert,
      title: "Recent Tickets",
      detail: "Open the latest ticket activity.",
      count: tickets.length
    },
    {
      id: "pendingApprovals",
      icon: ShieldCheck,
      title: "Pending Approvals",
      detail: role === "employee" ? "Check your approval status." : "Review approval requests.",
      count: pendingCount
    },
    {
      id: "recentActivity",
      icon: Clock3,
      title: "Recent Activity",
      detail: "View recent audit events.",
      count: auditEntries.length
    }
  ];
  cards.push(role === "employee" ? {
    id: "myPendingRequests",
    icon: Clock3,
    title: "My Pending Requests",
    detail: "Track your pending requests.",
    count: waitingTickets.length
  } : {
      id: "vendorBilling",
      icon: Building2,
      title: "Vendor Billing Dashboard",
      detail: "Open vendor services and billing.",
      count: vendorCount
    });

  return (
    <section className="dashboard-admin-actions" aria-label="Admin dashboard sections">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <button className="dashboard-admin-action-card" key={card.id} onClick={() => onOpen(card.id)} type="button">
            <span className="dashboard-admin-action-icon"><Icon size={18} /></span>
            <span>
              <strong>{card.title}</strong>
              <small>{card.detail}</small>
            </span>
            <span className="count-badge">{card.count}</span>
            <ChevronRight size={16} />
          </button>
        );
      })}
    </section>
  );
}

function DashboardAdminDetailModal({
  auditEntries,
  currentUser,
  panel,
  pendingApprovals,
  search,
  setError,
  tickets,
  vendorBillingDashboard,
  waitingTickets = [],
  onClose,
  onUpdated
}) {
  const pendingOnly = pendingApprovals.filter((item) => item.status === "pending");
  const config = {
    recentTickets: {
      title: "Recent Tickets",
      detail: normalizeRoleValue(currentUser?.role) === "it_manager"
        ? "Latest IT ticket activity available to your role."
        : normalizeRoleValue(currentUser?.role) === "finance_manager"
          ? "Latest finance ticket activity available to your role."
          : "Latest ticket activity across the organization.",
      content: <DashboardAdminTicketsTable tickets={tickets} />
    },
    pendingApprovals: {
      title: "Pending Approvals",
      detail: normalizeRoleValue(currentUser?.role) === "it_manager"
        ? "Approval queue items waiting for IT Manager action."
        : normalizeRoleValue(currentUser?.role) === "finance_manager"
          ? "Approval queue items waiting for Finance Manager action."
          : normalizeRoleValue(currentUser?.role) === "employee"
            ? "Your requests currently waiting for approval."
            : "Approval queue items waiting for Admin action.",
      content: (
        <ApprovalQueue
          approvals={pendingOnly}
          currentUser={currentUser}
          onUpdated={onUpdated}
          setError={setError}
        />
      )
    },
    recentActivity: {
      title: "Recent Activity",
      detail: "Recent audit and operational activity.",
      content: (
        <>
          {search && <span className="dashboard-filter-chip">{search}</span>}
          <AutomationTimeline logs={auditEntries} />
        </>
      )
    },
    vendorBilling: {
      title: "Vendor Billing Dashboard",
      detail: normalizeRoleValue(currentUser?.role) === "it_manager"
        ? "Vendor service summary available to IT Manager."
        : "Current vendors, service mix, billing summary, and expected billing.",
      content: <DashboardVendorBillingSection data={vendorBillingDashboard} />
    },
    myPendingRequests: {
      title: "My Pending Requests",
      detail: "Tickets and requests waiting for approval or follow-up.",
      content: <DashboardAdminTicketsTable tickets={waitingTickets} />
    }
  }[panel];

  if (!config) return null;

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="vendor-modal dashboard-detail-modal" role="dialog" aria-modal="true" aria-label={config.title}>
        <div className="section-heading dashboard-detail-heading">
          <div>
            <h2>{config.title}</h2>
            <p>{config.detail}</p>
          </div>
          <button className="icon-only" onClick={onClose} type="button" aria-label={`Close ${config.title}`}>
            <X size={18} />
          </button>
        </div>
        <div className="dashboard-detail-body">
          {config.content}
        </div>
      </section>
    </div>
  );
}

function DashboardAdminTicketsTable({ tickets }) {
  if (!tickets.length) {
    return <EmptyState icon={ShieldAlert} title="No recent tickets." detail="Recent ticket activity will appear here." />;
  }

  return (
    <div className="dashboard-detail-table-wrap">
      <table className="vendor-table dashboard-detail-table">
        <thead>
          <tr>
            <th>Ticket ID</th>
            <th>Title</th>
            <th>Type</th>
            <th>Status</th>
            <th>Requested by</th>
            <th>Created date</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr key={ticket.id}>
              <td><strong>{ticket.ticket_id}</strong></td>
              <td className="ticket-title-cell">
                <strong>{ticket.title}</strong>
                {ticket.category && <p>{ticket.category}</p>}
              </td>
              <td>{ticket.ticket_type}</td>
              <td>{ticket.status}</td>
              <td className="ticket-person-cell">
                <strong>{ticket.requester_name}</strong>
                <span>{ticket.requester_email}</span>
              </td>
              <td>{formatCalendarDate(ticket.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DashboardCardShell({ children, count, title }) {
  return (
    <section className="dashboard-card command-section-card">
      <div className="section-heading">
        <h2>{title}</h2>
        {typeof count === "number" && <span className="count-badge">{count}</span>}
      </div>
      {children}
    </section>
  );
}

function DashboardApprovalCard({ approvals, currentUser, onUpdated, setError, title }) {
  return (
    <DashboardCardShell count={approvals.filter((item) => item.status === "pending").length} title={title}>
      <ApprovalQueue approvals={approvals.slice(0, 3)} currentUser={currentUser} onUpdated={onUpdated} setError={setError} compact />
    </DashboardCardShell>
  );
}

function DashboardTaskCard({ tasks, title }) {
  return (
    <DashboardCardShell count={tasks.length} title={title}>
      <TaskList tasks={tasks.slice(0, 5)} />
    </DashboardCardShell>
  );
}

function DashboardTicketCard({ tickets, title }) {
  return (
    <DashboardCardShell count={tickets.length} title={title}>
      <DashboardTicketList tickets={tickets.slice(0, 5)} />
    </DashboardCardShell>
  );
}

function DashboardActivityCard({ logs, search, title }) {
  return (
    <DashboardCardShell count={logs.length} title={title}>
      {search && <span className="dashboard-filter-chip">{search}</span>}
      <AutomationTimeline logs={logs.slice(0, 8)} />
    </DashboardCardShell>
  );
}

function DashboardReportsCard({ reports }) {
  return (
    <DashboardCardShell count={reports.length} title="Reports Snapshot">
      <DashboardReportList reports={reports.slice(0, 5)} />
    </DashboardCardShell>
  );
}

function DashboardInventoryCard({ items, title }) {
  const counts = inventoryQuickStatusOptions.map((status) => ({
    status,
    count: items.filter((item) => normalizeInventoryStatus(item.status) === status).length
  }));
  return (
    <DashboardCardShell count={items.length} title={title}>
      {items.length ? (
        <div className="dashboard-mini-list">
          {counts.map((item) => (
            <article className="dashboard-mini-row" key={item.status}>
              <Package size={16} />
              <div>
                <strong>{item.status}</strong>
                <span>{item.count} inventory items</span>
              </div>
              <span className="status-pill">{item.count}</span>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState icon={Package} title="No inventory yet." detail="Inventory status will appear here when items are available." />
      )}
    </DashboardCardShell>
  );
}

function DashboardExpenseExceptionsCard({ expenses }) {
  const exceptions = expenses.filter((expense) =>
    (expense.policy_exceptions || []).length || ["Rejected", "Needs Info"].includes(expense.status)
  );
  return (
    <DashboardCardShell count={exceptions.length} title="Expense Exceptions">
      {exceptions.length ? (
        <div className="dashboard-mini-list">
          {exceptions.slice(0, 5).map((expense) => (
            <article className="dashboard-mini-row" key={expense.id}>
              <DollarSign size={16} />
              <div>
                <strong>{expense.expense_id || expense.category}</strong>
                <span>{expense.employee_name} · {formatMoney(expense.amount, expense.currency)}</span>
              </div>
              <span className="status-pill">{expense.status}</span>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState icon={DollarSign} title="No exceptions." detail="Policy exceptions and finance follow-ups will appear here." />
      )}
    </DashboardCardShell>
  );
}

function DashboardTravelCard({ records }) {
  return (
    <DashboardCardShell count={records.length} title="Recent Travel Records">
      {records.length ? (
        <div className="dashboard-mini-list">
          {records.slice(0, 5).map((record) => (
            <article className="dashboard-mini-row" key={record.id}>
              <Plane size={16} />
              <div>
                <strong>{record.employee_name}</strong>
                <span>{record.destination_from} to {record.destination_to} · {formatCalendarDate(record.travel_start_date)}</span>
              </div>
              <span className="status-pill">{record.approval_status}</span>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState icon={Plane} title="No travel records." detail="Recent travel schedules will appear here." />
      )}
    </DashboardCardShell>
  );
}

function DashboardVendorBillingSection({ data }) {
  if (!data?.visible) return null;
  const canViewBilling = Boolean(data.can_view_billing);
  const vendors = data.current_vendors || [];
  const serviceSummary = data.service_summary || [];
  const billingRows = data.current_billing?.rows || [];
  const expectedBilling = data.expected_billing || [];
  const closingSoon = data.closing_soon || [];
  const expectedThisMonth = expectedBilling.find((item) => item.label === "This month");
  const totalMonthly = data.current_billing?.total_monthly_equivalent || 0;

  return (
    <section className="dashboard-card dashboard-vendor-billing-section">
      <div className="section-heading vendor-billing-heading">
        <div>
          <h2><Building2 size={18} />Vendor Billing Dashboard</h2>
          <p>Current vendors, services, billing outlook, and local Conci AI support.</p>
        </div>
      </div>

      <div className="vendor-billing-summary-grid">
        <Metric icon={Building2} label="Active Vendors" value={vendors.length} />
        {canViewBilling && (
          <>
            <Metric icon={DollarSign} label="Monthly Equivalent" value={formatMoney(totalMonthly)} />
            <Metric icon={CalendarDays} label="Expected This Month" value={formatMoney(expectedThisMonth?.value || 0)} />
          </>
        )}
        <Metric icon={Clock3} label="Closing Soon" value={closingSoon.length} />
      </div>

      <div className="vendor-service-summary" aria-label="Vendor services summary">
        {serviceSummary.map((item) => (
          <article className="vendor-service-card" key={item.service}>
            <span>{item.service}</span>
            <strong>{item.count}</strong>
          </article>
        ))}
      </div>

      <div className="vendor-billing-layout">
        <section className="vendor-billing-panel">
          <div className="vendor-billing-panel-heading">
            <h3>Current Vendors</h3>
            <span className="count-badge">{vendors.length}</span>
          </div>
          {vendors.length ? (
            <div className="vendor-billing-table-wrap">
              <table className="vendor-table vendor-billing-table">
                <thead>
                  <tr>
                    <th>Vendor</th>
                    <th>Service</th>
                    {canViewBilling && <th>Billing</th>}
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {vendors.map((vendor) => (
                    <tr key={vendor.id}>
                      <td><strong>{vendor.vendor_name}</strong></td>
                      <td>{vendor.service_provided || "Other"}</td>
                      {canViewBilling && <td>{formatVendorBilling(vendor)}</td>}
                      <td>{labelize(vendor.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState icon={Building2} title="No current vendors." detail="Active vendor information will appear here." />
          )}
        </section>

        <section className="vendor-billing-panel">
          <div className="vendor-billing-panel-heading">
            <h3>Current Billing</h3>
            {canViewBilling && <span>{formatMoney(totalMonthly)} / month</span>}
          </div>
          {canViewBilling ? (
            billingRows.length ? (
              <div className="vendor-billing-table-wrap">
                <table className="vendor-table vendor-billing-table">
                  <thead>
                    <tr>
                      <th>Vendor</th>
                      <th>Cycle Billing</th>
                      <th>Monthly Eq.</th>
                    </tr>
                  </thead>
                  <tbody>
                    {billingRows.map((row) => (
                      <tr key={row.id}>
                        <td><strong>{row.vendor_name}</strong></td>
                        <td>{formatVendorBilling(row)}</td>
                        <td>{formatMoney(row.monthly_equivalent)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState icon={DollarSign} title="No billing data." detail="Billing will appear after active vendors are added." />
            )
          ) : (
            <EmptyState icon={ShieldAlert} title="Billing restricted." detail="Your role can view vendor service summary only." />
          )}
        </section>
      </div>

      {canViewBilling && (
        <div className="vendor-expected-grid" aria-label="Expected vendor billing">
          {expectedBilling.map((item) => (
            <article className="vendor-expected-card" key={item.label}>
              <span>{item.label}</span>
              <strong>{formatMoney(item.value || 0)}</strong>
            </article>
          ))}
        </div>
      )}

      <VendorBillingChatbot data={data} />
    </section>
  );
}

function VendorBillingChatbot({ data }) {
  const examples = [
    "Which vendors are active?",
    "Show food vendors.",
    "What is total monthly vendor billing?",
    "Which vendor has the highest billing?",
    "What is expected billing this month?",
    "Which vendors are closing soon?"
  ];
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Ask about active vendors, services, monthly billing, expected billing, or vendors closing soon."
    }
  ]);

  function askVendorBot(nextQuestion) {
    const cleanQuestion = nextQuestion.trim();
    if (!cleanQuestion) return;
    const answer = answerVendorBillingQuestion(cleanQuestion, data);
    setMessages((current) => [
      ...current,
      { role: "user", text: cleanQuestion },
      { role: "assistant", text: answer }
    ]);
    setQuestion("");
  }

  function submitQuestion(event) {
    event.preventDefault();
    askVendorBot(question);
  }

  return (
    <section className="vendor-chatbot" aria-label="Conci AI vendor billing">
      <div className="vendor-chatbot-heading">
        <Bot size={18} />
        <div>
          <h3>Conci AI</h3>
          <p>Local demo answers from the vendor data already loaded in Agent Concierge.</p>
        </div>
      </div>
      <div className="vendor-chatbot-examples">
        {examples.map((example) => (
          <button key={example} onClick={() => askVendorBot(example)} type="button">
            {example}
          </button>
        ))}
      </div>
      <div className="vendor-chatbot-messages">
        {messages.slice(-6).map((message, index) => (
          <article className={`vendor-chat-message ${message.role}`} key={`${message.role}-${index}-${message.text}`}>
            {message.text}
          </article>
        ))}
      </div>
      <form className="vendor-chatbot-input" onSubmit={submitQuestion}>
        <input
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about vendors..."
          value={question}
        />
        <button className="primary-button" type="submit">
          <Send size={15} />
          Ask
        </button>
      </form>
    </section>
  );
}

function answerVendorBillingQuestion(question, data) {
  const normalized = question.toLowerCase();
  const vendors = data?.current_vendors || [];
  const billingRows = data?.current_billing?.rows || [];
  const expectedBilling = data?.expected_billing || [];
  const closingSoon = data?.closing_soon || [];
  const canViewBilling = Boolean(data?.can_view_billing);
  const listNames = (items) => items.map((item) => item.vendor_name).filter(Boolean).join(", ");

  if (normalized.includes("active")) {
    return vendors.length
      ? `${vendors.length} active vendors: ${vendors.map((vendor) => `${vendor.vendor_name} (${vendor.service_provided || "Other"})`).join(", ")}.`
      : "There are no active vendors in the current dashboard data.";
  }

  if (normalized.includes("food")) {
    const foodVendors = vendors.filter((vendor) => String(vendor.service_provided || "").toLowerCase() === "food");
    return foodVendors.length ? `Food vendors: ${listNames(foodVendors)}.` : "No active food vendors are visible in the current dashboard data.";
  }

  if (normalized.includes("monthly") || normalized.includes("total billing")) {
    if (!canViewBilling) return "Billing amounts are restricted for your role. You can view vendor service summary only.";
    return `Total current monthly equivalent vendor billing is ${formatMoney(data?.current_billing?.total_monthly_equivalent || 0)}.`;
  }

  if (normalized.includes("highest")) {
    if (!canViewBilling) return "Billing amounts are restricted for your role.";
    const highest = [...billingRows].sort((a, b) => Number(b.monthly_equivalent || 0) - Number(a.monthly_equivalent || 0))[0];
    return highest
      ? `${highest.vendor_name} has the highest monthly equivalent billing at ${formatMoney(highest.monthly_equivalent)}.`
      : "No vendor billing rows are available yet.";
  }

  if (normalized.includes("expected") || normalized.includes("this month")) {
    if (!canViewBilling) return "Expected billing amounts are restricted for your role.";
    const thisMonth = expectedBilling.find((item) => item.label === "This month");
    return `Expected vendor billing this month is ${formatMoney(thisMonth?.value || 0)}.`;
  }

  if (normalized.includes("closing") || normalized.includes("close soon")) {
    return closingSoon.length
      ? `Vendors closing soon: ${closingSoon.map((vendor) => `${vendor.vendor_name} on ${formatDateOnly(vendor.end_date)}`).join(", ")}.`
      : "No visible active vendors are closing in the next 60 days.";
  }

  if (normalized.includes("service")) {
    const summary = (data?.service_summary || []).map((item) => `${item.service}: ${item.count}`).join(", ");
    return summary ? `Vendor services summary: ${summary}.` : "No service summary is available yet.";
  }

  return "I can answer vendor questions about active vendors, service types, current monthly billing, highest billing, expected billing, and closing-soon vendors.";
}

function DashboardTicketList({ tickets }) {
  if (!tickets.length) {
    return <EmptyState icon={ShieldAlert} title="No tickets yet." detail="You're all caught up." />;
  }
  return (
    <div className="dashboard-mini-list">
      {tickets.map((ticket) => (
        <article className="dashboard-mini-row" key={ticket.id}>
          <ShieldAlert size={16} />
          <div>
            <strong>{ticket.title}</strong>
            <span>{ticket.ticket_type} · {ticket.category} · due {formatCalendarDate(ticket.due_date)}</span>
          </div>
          <span className="status-pill">{ticket.status}</span>
        </article>
      ))}
    </div>
  );
}

function DashboardReportList({ reports }) {
  if (!reports.length) {
    return <EmptyState icon={FileText} title="No reports yet." detail="Reports will appear here when available." />;
  }
  return (
    <div className="dashboard-mini-list">
      {reports.map((report) => (
        <article className="dashboard-mini-row" key={report.id}>
          <FileText size={16} />
          <div>
            <strong>{report.report_name}</strong>
            <span>{report.department} · {report.file_type} · {formatDateTime(report.uploaded_at)}</span>
          </div>
          <span className="status-pill">{report.status}</span>
        </article>
      ))}
    </div>
  );
}

function DashboardCharts({ charts = [] }) {
  if (!charts.length) return null;
  return (
    <section className="dashboard-chart-grid" aria-label="Dashboard charts">
      {charts.map((chart) => <DashboardChartCard chart={chart} key={chart.id || chart.title} />)}
    </section>
  );
}

function DashboardChartCard({ chart }) {
  const data = Array.isArray(chart.data) ? chart.data.filter((item) => Number(item.value || 0) >= 0) : [];
  const hasData = data.some((item) => Number(item.value || 0) > 0);
  const valueKind = chart.value_kind || "count";
  return (
    <section className="dashboard-card dashboard-chart-card">
      <div className="section-heading">
        <h2>{chart.title}</h2>
      </div>
      {hasData ? (
        <div className="dashboard-chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            {chart.chart_type === "pie"
              ? <DashboardPieChart data={data} valueKind={valueKind} />
              : chart.chart_type === "line"
                ? <DashboardLineChart data={data} valueKind={valueKind} />
                : <DashboardBarChart data={data} valueKind={valueKind} />}
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="dashboard-chart-empty">
          <BarChart3 size={22} />
          <span>No chart data yet.</span>
        </div>
      )}
    </section>
  );
}

function DashboardTooltip({ active, payload, label, valueKind }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="dashboard-chart-tooltip">
      <strong>{label || payload[0]?.name}</strong>
      <span>{formatChartValue(payload[0]?.value, valueKind)}</span>
    </div>
  );
}

function DashboardBarChart({ data, valueKind }) {
  return (
    <RechartsBarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
      <CartesianGrid strokeDasharray="3 3" vertical={false} />
      <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} height={44} tickLine={false} axisLine={false} />
      <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={42} />
      <Tooltip content={(props) => <DashboardTooltip {...props} valueKind={valueKind} />} />
      <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#4f46e5" />
    </RechartsBarChart>
  );
}

function DashboardLineChart({ data, valueKind }) {
  return (
    <LineChart data={data} margin={{ top: 8, right: 10, left: 0, bottom: 0 }}>
      <CartesianGrid strokeDasharray="3 3" vertical={false} />
      <XAxis dataKey="name" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
      <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={42} />
      <Tooltip content={(props) => <DashboardTooltip {...props} valueKind={valueKind} />} />
      <Line type="monotone" dataKey="value" stroke="#4f46e5" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
    </LineChart>
  );
}

function DashboardPieChart({ data, valueKind }) {
  return (
    <PieChart margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
      <Tooltip content={(props) => <DashboardTooltip {...props} valueKind={valueKind} />} />
      <Pie data={data} dataKey="value" nameKey="name" innerRadius="48%" outerRadius="76%" paddingAngle={2}>
        {data.map((entry, index) => (
          <Cell key={entry.name} fill={DASHBOARD_CHART_COLORS[index % DASHBOARD_CHART_COLORS.length]} />
        ))}
      </Pie>
    </PieChart>
  );
}

function Metric({ label, value, icon: Icon }) {
  return (
    <div className="metric">
      <span className="metric-icon"><Icon size={18} /></span>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TaskSummaryPill({ label, value, icon: Icon }) {
  return (
    <div className="task-summary-pill">
      <Icon size={15} />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AutomationSchedule({ latestPlan, meetings, approvals }) {
  const pendingApproval = approvals.find((item) => item.status === "pending");
  const meeting = meetings[0];
  const rows = [
    {
      time: "09:00 AM",
      status: "success",
      icon: CheckCircle2,
      title: meeting ? `${meeting.title} scheduled` : "Vendor Review - ABC Supplies scheduled",
      detail: "Automated by Vendor Bot"
    },
    {
      time: "09:30 AM",
      status: "info",
      icon: CalendarDays,
      title: "Meeting notes generated",
      detail: "Automated by Meeting Bot"
    },
    {
      time: "10:15 AM",
      status: "warning",
      icon: ShieldAlert,
      title: pendingApproval ? pendingApproval.subject : "Approval check ready",
      detail: latestPlan ? `Classified as ${labelize(latestPlan.task_type)}` : "Awaiting next automation"
    },
    {
      time: "11:00 AM",
      status: "success",
      icon: CheckCircle2,
      title: "Vendor follow-up routed to review",
      detail: "External email requires approval"
    },
    {
      time: "12:30 PM",
      status: "info",
      icon: CalendarDays,
      title: "Task deadlines updated",
      detail: "Automated by Task Bot"
    }
  ];

  return (
    <div className="automation-schedule">
      {rows.map((row) => {
        const Icon = row.icon;
        return (
          <article className="automation-row" key={`${row.time}-${row.title}`}>
            <time>{row.time}</time>
            <span className={`automation-icon ${row.status}`}>
              <Icon size={15} />
            </span>
            <div>
              <strong>{row.title}</strong>
              <span>{row.detail}</span>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function AgentPlanPanel({ plan, record }) {
  return (
    <div className="agent-plan-panel">
      <div className="section-heading">
        <h2>Agent Decision</h2>
        <span className={plan.approval_required ? "status-pill warning" : "status-pill success"}>
          {labelize(plan.automation_level)}
        </span>
      </div>
      <div className="plan-grid">
        <div>
          <span>Task Type</span>
          <strong>{labelize(plan.task_type)}</strong>
        </div>
        <div>
          <span>Risk</span>
          <strong>{labelize(plan.risk_level)}</strong>
        </div>
        <div>
          <span>Planner</span>
          <strong>{labelize(record.planner_mode)}</strong>
        </div>
      </div>
      <p>{plan.summary}</p>
      {plan.approval_reason && <p className="risk-line">{plan.approval_reason}</p>}
      <div className="file-list">
        {(plan.required_tools || []).map((tool) => (
          <span key={tool}>{labelize(tool)}</span>
        ))}
      </div>
    </div>
  );
}

function RequestRoutingPanel({
  lastRoute,
  loading,
  onMessageChange,
  onSubmit,
  requestRef,
  routedRequests,
  value
}) {
  const route = lastRoute?.route;

  return (
    <div className="request-routing-panel">
      <label>
        New admin or IT request
        <textarea
          ref={requestRef}
          value={value}
          onChange={(event) => onMessageChange(event.target.value)}
          rows={4}
          placeholder="Describe the admin request you want routed..."
        />
      </label>
      <div className="example-chip-row" aria-label="Example requests">
        {ROUTE_EXAMPLES.map((example) => (
          <button
            key={example}
            onClick={() => onMessageChange(example)}
            type="button"
          >
            {example}
          </button>
        ))}
      </div>
      <div className="button-row">
        <button className="primary-button" disabled={loading || !value.trim()} onClick={onSubmit} type="button">
          <Bot size={17} />
          <span>{loading ? "Routing" : "Route Request"}</span>
        </button>
      </div>
      {route ? (
        <section className="route-result" aria-label="Routed request result">
          <div className="route-result-header">
            <strong>Backend route</strong>
            <span className={route.approval_required ? "status-pill warning" : "status-pill success"}>
              {route.approval_required ? "Approval Required" : "Automatic"}
            </span>
          </div>
          <div className="plan-grid route-grid">
            <div><span>Task Type</span><strong>{labelize(route.task_type)}</strong></div>
            <div><span>Assigned Role</span><strong>{roleLabel(route.assigned_role)}</strong></div>
            <div><span>Approval Roles</span><strong>{formatRoleList(route.required_approval_roles)}</strong></div>
            <div><span>Risk</span><strong>{labelize(route.risk_level)}</strong></div>
            <div><span>Priority</span><strong>{labelize(route.priority)}</strong></div>
            <div><span>Status</span><strong>{labelize(route.status)}</strong></div>
          </div>
          {route.approval_required ? (
            <p className="approval-route-message">
              This request requires {formatRoleList(route.required_approval_roles)} approval.
            </p>
          ) : (
            <p className="approval-route-message success">No human approval is required for this routed request.</p>
          )}
          {route.approval_reason && <p className="risk-line">{route.approval_reason}</p>}
        </section>
      ) : (
        <EmptyState
          icon={Bot}
          title="No request routed yet."
          detail="Submit a request to see task type, risk, priority, and approver routing."
        />
      )}
      <RecentRoutes routes={routedRequests} />
    </div>
  );
}

function RecentRoutes({ routes }) {
  if (!routes?.length) {
    return (
      <div className="recent-routes">
        <div className="section-subheading">
          <strong>Recent Requests</strong>
        </div>
        <p className="empty">No routed requests yet.</p>
      </div>
    );
  }

  return (
    <div className="recent-routes">
      <div className="section-subheading">
        <strong>Recent Requests</strong>
      </div>
      <div className="mini-list">
        {routes.slice(0, 4).map((request) => (
          <article className="mini-row route-mini-row" key={request.id}>
            <Bot size={16} />
            <div>
              <strong>{labelize(request.task_type)}</strong>
              <span>
                {labelize(request.status)} - {roleLabel(request.assigned_role)}
                {request.approval_required ? ` - ${request.required_role_label}` : " - No approval required"}
              </span>
            </div>
            <span className={`priority-pill ${request.priority === "critical" ? "high" : request.priority}`}>
              {request.priority}
            </span>
          </article>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, title, detail }) {
  return (
    <div className="empty-state polished-empty">
      <span className="empty-icon"><Icon size={20} /></span>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}

function approvalPriority(approval) {
  if (approval.risk_reason?.toLowerCase().includes("payment")) return "high";
  if (approval.approval_type === "external_vendor_email") return "medium";
  return "low";
}

function ApprovalQueue({ approvals, currentUser, onUpdated, setError, compact = false }) {
  const [drafts, setDrafts] = useState({});

  useEffect(() => {
    const nextDrafts = {};
    approvals.forEach((approval) => {
      nextDrafts[approval.id] = {
        subject: approval.subject,
        body: approval.body,
        reason: approval.cancelled_reason || ""
      };
    });
    setDrafts(nextDrafts);
  }, [approvals]);

  async function submit(id, action) {
    setError("");
    try {
      await updateApproval(id, { action, ...(drafts[id] || {}) });
      await onUpdated();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  if (approvals.length === 0) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="No tickets yet."
        detail="You're all caught up!"
      />
    );
  }

  return (
    <section className={compact ? "approval-list compact-approvals" : "approval-list"}>
      {approvals.map((approval) => {
        const draft = drafts[approval.id] || { subject: approval.subject, body: approval.body };
        const canApprove = approval.required_roles?.includes(currentUser.role);
        const priority = approvalPriority(approval);
        return (
          <article className="approval-item" key={approval.id}>
            <div className="approval-meta">
              <span className={approval.status === "pending" ? "status-pill warning" : "status-pill"}>
                {approval.status}
              </span>
              <span className={`priority-pill ${priority}`}>{priority}</span>
              <strong>{approval.recipient_name}</strong>
              <span>{approval.recipient_email}</span>
            </div>
            <p className="risk-line">{approval.required_role_label}</p>
            {!compact && (
              <>
                <label>
                  Subject
                  <input
                    value={draft.subject}
                    disabled={approval.status !== "pending"}
                    onChange={(event) =>
                      setDrafts({
                        ...drafts,
                        [approval.id]: { ...draft, subject: event.target.value }
                      })
                    }
                  />
                </label>
                <label>
                  Email Draft
                  <textarea
                    value={draft.body}
                    disabled={approval.status !== "pending"}
                    rows={8}
                    onChange={(event) =>
                      setDrafts({
                        ...drafts,
                        [approval.id]: { ...draft, body: event.target.value }
                      })
                    }
                  />
                </label>
              </>
            )}
            {approval.status === "pending" && (
              <div className="button-row">
                <button
                  className="primary-button"
                  disabled={!canApprove}
                  onClick={() => submit(approval.id, "approve_send")}
                  type="button"
                  title={canApprove ? "Approve and send" : approval.required_role_label}
                >
                  <Mail size={17} />
                  <span>Approve Send</span>
                </button>
                {!compact && (
                  <>
                    <button
                      className="icon-button secondary"
                      disabled={!canApprove}
                      onClick={() => submit(approval.id, "edit")}
                      type="button"
                      title={canApprove ? "Save edit" : approval.required_role_label}
                    >
                      <Pencil size={17} />
                      <span>Save Edit</span>
                    </button>
                    <button
                      className="icon-button danger"
                      disabled={!canApprove}
                      onClick={() => submit(approval.id, "cancel")}
                      type="button"
                      title={canApprove ? "Cancel approval" : approval.required_role_label}
                    >
                      <X size={17} />
                      <span>Cancel</span>
                    </button>
                  </>
                )}
                {!canApprove && <span className="permission-note">{approval.required_role_label}</span>}
              </div>
            )}
          </article>
        );
      })}
    </section>
  );
}

function TaskList({ tasks }) {
  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={ListChecks}
        title="No action items yet."
        detail="You're all set for now!"
      />
    );
  }
  return (
    <div className="task-list">
      {tasks.map((task) => (
        <article className="task-row" key={task.id}>
          <ListChecks size={17} />
          <div>
            <strong>{task.title}</strong>
            <span>{task.assigned_to || task.owner_name || "Unassigned"} · due {formatCalendarDate(task.due_date)}</span>
          </div>
          <span className="status-pill">{task.status}</span>
        </article>
      ))}
    </div>
  );
}

function VendorFollowups({ approvals, meetings }) {
  const vendorApprovals = approvals.filter((item) => item.approval_type === "external_vendor_email");
  if (vendorApprovals.length === 0 && meetings.length === 0) {
    return (
      <EmptyState
        icon={Mail}
        title="No vendor follow-ups queued."
        detail="Vendor drafts will appear here after a meeting workflow."
      />
    );
  }
  return (
    <div className="mini-list">
      {vendorApprovals.map((approval) => (
        <article className="mini-row" key={approval.id}>
          <Mail size={16} />
          <div>
            <strong>{approval.subject}</strong>
            <span>{approval.status} - {approval.recipient_email}</span>
          </div>
        </article>
      ))}
      {meetings.slice(0, 1).map((meeting) => (
        <article className="mini-row" key={meeting.id}>
          <Building2 size={16} />
          <div>
            <strong>{meeting.vendor_name}</strong>
            <span>{formatDate(meeting.scheduled_for)}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function ExpenseExceptions({ approvals }) {
  const expenseItems = approvals.filter((item) => ["expense_approval", "payment"].includes(item.approval_type));
  if (expenseItems.length === 0) {
    return (
      <EmptyState
        icon={DollarSign}
        title="No expense exceptions pending."
        detail="Finance exceptions will be routed here for review."
      />
    );
  }
  return <VendorFollowups approvals={expenseItems} meetings={[]} />;
}

function AutomationTimeline({ logs }) {
  if (logs.length === 0) return <p className="empty">No audit events yet.</p>;
  return (
    <div className="timeline">
      {logs.map((log) => (
        <article className="timeline-row" key={log.id}>
          <Clock3 size={15} />
          <div>
            <strong>{log.action}</strong>
            <span>{formatDate(log.timestamp)} - {log.actor}</span>
          </div>
          <span className="status-pill">{log.status}</span>
        </article>
      ))}
    </div>
  );
}

function TasksView({ currentUser, onChanged, onTaskDeleted, onTaskSaved, setError, tasks }) {
  const [taskSearch, setTaskSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [assignableUsers, setAssignableUsers] = useState([]);
  const [assignableLoading, setAssignableLoading] = useState(false);
  const [assigneeSearch, setAssigneeSearch] = useState("");
  const [taskFilters, setTaskFilters] = useState({
    status: "All",
    priority: "All",
    category: "All",
    department: "All",
    assignedRole: "All",
    dueDate: "",
    myTasksOnly: false,
    overdueOnly: false
  });
  const [taskPage, setTaskPage] = useState(1);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const [formOpen, setFormOpen] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [viewingTask, setViewingTask] = useState(null);
  const [statusTask, setStatusTask] = useState(null);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [statusValue, setStatusValue] = useState("Open");
  const [form, setForm] = useState(emptyTaskForm);
  const [formErrors, setFormErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const activeFilterCount = Object.entries(taskFilters).filter(([key, value]) => {
    if (key === "dueDate") return Boolean(value);
    if (typeof value === "boolean") return value;
    return value !== "All";
  }).length;
  const summary = useMemo(() => ({
    total: tasks.length,
    open: tasks.filter((task) => task.status === "Open").length,
    inProgress: tasks.filter((task) => task.status === "In Progress").length,
    overdue: tasks.filter(isTaskOverdue).length,
    completed: tasks.filter((task) => task.status === "Completed").length
  }), [tasks]);
  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      const matchesQuery = taskMatchesLocalSearch(task, taskSearch);
      const matchesStatus = taskFilters.status === "All" || task.status === taskFilters.status;
      const matchesPriority = taskFilters.priority === "All" || task.priority === taskFilters.priority;
      const matchesCategory = taskFilters.category === "All" || task.category === taskFilters.category;
      const matchesDepartment = taskFilters.department === "All" || task.department === taskFilters.department;
      const matchesAssignedRole = taskFilters.assignedRole === "All" || task.assigned_role === taskFilters.assignedRole;
      const matchesDueDate = !taskFilters.dueDate || String(task.due_date || "").slice(0, 10) === taskFilters.dueDate;
      const matchesMyTasks = !taskFilters.myTasksOnly || taskAssigneeMatchesUser(task, currentUser) || taskCreatedByUser(task, currentUser);
      const matchesOverdue = !taskFilters.overdueOnly || isTaskOverdue(task);
      return (
        matchesQuery &&
        matchesStatus &&
        matchesPriority &&
        matchesCategory &&
        matchesDepartment &&
        matchesAssignedRole &&
        matchesDueDate &&
        matchesMyTasks &&
        matchesOverdue
      );
    });
  }, [currentUser, taskFilters, taskSearch, tasks]);
  const taskPageCount = Math.max(1, Math.ceil(filteredTasks.length / TASK_PAGE_SIZE));
  const currentTaskPage = Math.min(taskPage, taskPageCount);
  const taskStartIndex = filteredTasks.length ? (currentTaskPage - 1) * TASK_PAGE_SIZE : 0;
  const taskEndIndex = Math.min(taskStartIndex + TASK_PAGE_SIZE, filteredTasks.length);
  const pagedTasks = filteredTasks.slice(taskStartIndex, taskEndIndex);
  const firstPaginationPage = Math.min(
    Math.max(1, currentTaskPage - 1),
    Math.max(1, taskPageCount - 2)
  );
  const taskPaginationPages = Array.from(
    { length: Math.min(3, taskPageCount) },
    (_, index) => firstPaginationPage + index
  );
  const filteredAssignableUsers = useMemo(() => {
    const query = assigneeSearch.trim().toLowerCase();
    return assignableUsers
      .filter((user) => Number(user.id) !== Number(currentUser.id))
      .filter((user) => {
        if (!query) return true;
        return `${user.name || ""} ${user.email || ""} ${roleLabel(user.role || "")}`.toLowerCase().includes(query);
      });
  }, [assigneeSearch, assignableUsers, currentUser.id]);
  const selectedAssigneeValue = Number(form.assigned_user_id) === Number(currentUser.id)
    ? "self"
    : String(form.assigned_user_id || "");

  useEffect(() => {
    setTaskPage(1);
  }, [taskFilters, taskSearch, tasks.length]);

  useEffect(() => {
    let active = true;
    setAssignableLoading(true);
    getAssignableUsers()
      .then((response) => {
        if (active) setAssignableUsers(response.users || []);
      })
      .catch((err) => {
        if (active) {
          setAssignableUsers([currentUser]);
          setError(apiErrorMessage(err));
        }
      })
      .finally(() => {
        if (active) setAssignableLoading(false);
      });
    return () => {
      active = false;
    };
  }, [currentUser, setError]);

  useEffect(() => {
    if (taskPage > taskPageCount) {
      setTaskPage(taskPageCount);
    }
  }, [taskPage, taskPageCount]);

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = window.setTimeout(() => setToastMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  function updateTaskFilter(field, value) {
    setTaskFilters((current) => ({ ...current, [field]: value }));
  }

  function clearTaskFilters() {
    setTaskFilters({
      status: "All",
      priority: "All",
      category: "All",
      department: "All",
      assignedRole: "All",
      dueDate: "",
      myTasksOnly: false,
      overdueOnly: false
    });
  }

  function updateTaskField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function taskAssigneeOptionLabel(user) {
    return `${user.name || "Unnamed User"} - ${user.email || "No email"}`;
  }

  function findAssignableUserForTask(task) {
    if (task.assigned_user_id) {
      const byId = assignableUsers.find((user) => Number(user.id) === Number(task.assigned_user_id));
      if (byId) return byId;
    }
    const assignedEmail = String(task.assigned_email || task.owner_email || "").toLowerCase();
    const assignedTo = String(task.assigned_to || "").toLowerCase();
    return assignableUsers.find((user) => (
      (assignedEmail && String(user.email || "").toLowerCase() === assignedEmail) ||
      (assignedTo && [String(user.name || "").toLowerCase(), String(user.email || "").toLowerCase()].includes(assignedTo))
    ));
  }

  function updateTaskAssignee(value) {
    const selectedUser = value === "self"
      ? currentUser
      : assignableUsers.find((user) => String(user.id) === String(value));
    setForm((current) => ({
      ...current,
      assigned_user_id: selectedUser?.id ? String(selectedUser.id) : "",
      assigned_to: selectedUser?.name || "",
      assigned_email: selectedUser?.email || "",
      assigned_role: selectedUser?.role || current.assigned_role
    }));
    setFormErrors((current) => ({ ...current, assigned_to: "" }));
  }

  function validateTaskForm() {
    const errors = {};
    if (!form.title.trim()) errors.title = "Required";
    if (form.title.trim().length > 0 && form.title.trim().length < 3) errors.title = "Enter at least 3 characters";
    if (!form.description.trim()) errors.description = "Required";
    if (form.description.trim().length > 0 && form.description.trim().length < 3) errors.description = "Enter at least 3 characters";
    if (!form.department.trim()) errors.department = "Choose a department";
    if (!form.assigned_user_id && !form.assigned_to.trim()) errors.assigned_to = "Choose an assignee";
    if (form.due_date && !isValidIsoDate(form.due_date)) errors.due_date = "Choose a valid due date";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function openCreateTask() {
    setToastMessage("");
    setToastType("success");
    setEditingTask(null);
    setFormErrors({});
    setForm({
      ...emptyTaskForm,
      assigned_user_id: currentUser.role === "employee" ? String(currentUser.id) : "",
      assigned_to: currentUser.role === "employee" ? currentUser.name : "",
      assigned_email: currentUser.role === "employee" ? currentUser.email : "",
      assigned_role: currentUser.role === "employee" ? "employee" : "admin"
    });
    setAssigneeSearch("");
    setFormOpen(true);
  }

  function openEditTask(task) {
    if (!canManageTask(currentUser, task)) return;
    setToastMessage("");
    setToastType("success");
    setEditingTask(task);
    setFormErrors({});
    const assignedUser = findAssignableUserForTask(task);
    setForm({
      title: task.title || "",
      description: task.description || "",
      category: task.category || "Admin",
      department: task.department || "Admin",
      assigned_user_id: assignedUser?.id ? String(assignedUser.id) : String(task.assigned_user_id || ""),
      assigned_to: assignedUser?.name || task.assigned_to || "",
      assigned_email: assignedUser?.email || task.assigned_email || "",
      assigned_role: assignedUser?.role || task.assigned_role || "admin",
      priority: task.priority || "Medium",
      status: task.status || "Open",
      due_date: String(task.due_date || "").slice(0, 10),
      notes: task.notes || ""
    });
    setAssigneeSearch("");
    setFormOpen(true);
  }

  function closeTaskForm() {
    setFormOpen(false);
    setEditingTask(null);
    setForm(emptyTaskForm);
    setFormErrors({});
  }

  function openStatusModal(task) {
    if (!canManageTask(currentUser, task)) return;
    setStatusTask(task);
    setStatusValue(task.status || "Open");
  }

  async function submitTask(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    if (!validateTaskForm()) return;
    setSaving(true);
    try {
      const payload = {
        ...form,
        title: form.title.trim(),
        description: form.description.trim(),
        department: form.department.trim(),
        assigned_to: form.assigned_to.trim(),
        assigned_user_id: form.assigned_user_id ? Number(form.assigned_user_id) : null,
        assigned_email: form.assigned_email.trim(),
        due_date: form.due_date || null,
        notes: form.notes.trim()
      };
      const response = editingTask
        ? await updateTask(editingTask.id, payload)
        : await createTask(payload);
      if (response?.task) {
        onTaskSaved(response.task);
      }
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      closeTaskForm();
      setToastType("success");
      setToastMessage(editingTask ? "Task updated successfully" : "Task created successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not save task: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function submitTaskStatus(event) {
    event.preventDefault();
    if (!statusTask) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      const response = await updateTaskStatus(statusTask.id, statusValue);
      if (response?.task) {
        onTaskSaved(response.task);
      }
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setStatusTask(null);
      setToastType("success");
      setToastMessage("Task status updated successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not update task status: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function confirmDeleteTask() {
    if (!deleteCandidate) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      await deleteTask(deleteCandidate.id);
      onTaskDeleted(deleteCandidate.id);
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setDeleteCandidate(null);
      setToastType("success");
      setToastMessage("Task deleted successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not delete task: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="tasks-page screen-stack">
      {toastMessage && <div className={toastType === "error" ? "toast-notification error" : "toast-notification"} role="status">{toastMessage}</div>}
      <div className="tasks-page-header">
        <div className="page-title tasks-title">
          <h1>Tasks</h1>
        </div>
        <div className="task-summary-row" aria-label="Task summary">
          <TaskSummaryPill label="Total" value={summary.total} icon={ClipboardList} />
          <TaskSummaryPill label="Open" value={summary.open} icon={ListChecks} />
          <TaskSummaryPill label="In Progress" value={summary.inProgress} icon={RefreshCw} />
          <TaskSummaryPill label="Overdue" value={summary.overdue} icon={Clock3} />
          <TaskSummaryPill label="Completed" value={summary.completed} icon={CheckCircle2} />
        </div>
      </div>
      <section className="dashboard-card vendor-directory-card task-directory-card">
        <div className="vendor-directory-header task-directory-header">
          <div className="vendor-directory-title">
            <span className="vendor-directory-icon"><ClipboardList size={20} /></span>
            <div>
              <div className="directory-title-row">
                <h2>Task Directory</h2>
                <span className="vendor-count-badge">{filteredTasks.length} Tasks</span>
              </div>
              <p>Create, assign, and track Admin/IT tasks</p>
            </div>
          </div>
          <div className="task-action-row">
            <label className="vendor-search-control task-search-control" aria-label="Search tasks">
              <Search size={17} />
              <input
                onChange={(event) => setTaskSearch(event.target.value)}
                placeholder="Search tasks..."
                value={taskSearch}
              />
              {taskSearch && (
                <button
                  aria-label="Clear task search"
                  onClick={() => setTaskSearch("")}
                  title="Clear task search"
                  type="button"
                >
                  <X size={15} />
                </button>
              )}
            </label>
            <div className="vendor-filter-wrap">
              <button
                aria-expanded={filtersOpen}
                aria-label="Filter tasks"
                className="icon-button secondary vendor-filter-button inventory-icon-action"
                onClick={() => setFiltersOpen((open) => !open)}
                title="Filter tasks"
                type="button"
              >
                <Filter size={17} />
                {activeFilterCount > 0 && <strong>{activeFilterCount}</strong>}
              </button>
              {filtersOpen && (
                <div className="vendor-filter-panel task-filter-panel" role="dialog" aria-label="Task filters">
                  <label>
                    Status
                    <select value={taskFilters.status} onChange={(event) => updateTaskFilter("status", event.target.value)}>
                      {taskStatusFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Priority
                    <select value={taskFilters.priority} onChange={(event) => updateTaskFilter("priority", event.target.value)}>
                      {taskPriorityFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Category
                    <select value={taskFilters.category} onChange={(event) => updateTaskFilter("category", event.target.value)}>
                      {taskCategoryFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Department
                    <select value={taskFilters.department} onChange={(event) => updateTaskFilter("department", event.target.value)}>
                      {taskDepartmentFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Assigned Role
                    <select value={taskFilters.assignedRole} onChange={(event) => updateTaskFilter("assignedRole", event.target.value)}>
                      {taskAssignedRoleFilterOptions.map((option) => <option key={option} value={option}>{option === "All" ? option : roleLabel(option)}</option>)}
                    </select>
                  </label>
                  <label>
                    Due Date
                    <input value={taskFilters.dueDate} onChange={(event) => updateTaskFilter("dueDate", event.target.value)} type="date" />
                  </label>
                  <label className="ticket-checkbox">
                    <input
                      checked={taskFilters.myTasksOnly}
                      onChange={(event) => updateTaskFilter("myTasksOnly", event.target.checked)}
                      type="checkbox"
                    />
                    <span>My Tasks only</span>
                  </label>
                  <label className="ticket-checkbox">
                    <input
                      checked={taskFilters.overdueOnly}
                      onChange={(event) => updateTaskFilter("overdueOnly", event.target.checked)}
                      type="checkbox"
                    />
                    <span>Overdue only</span>
                  </label>
                  <button className="table-action-button" onClick={clearTaskFilters} type="button">Clear</button>
                </div>
              )}
            </div>
            <button className="primary-button vendor-add-button task-create-button" onClick={openCreateTask} type="button">
              <Plus size={18} />
              <span>Create Task</span>
            </button>
          </div>
        </div>
        <TaskTable
          currentUser={currentUser}
          emptyDetail={tasks.length ? "Adjust search or filters to show more tasks." : "Create a task request or assignment to get started."}
          emptyTitle={tasks.length ? "No tasks match." : "No tasks yet."}
          from={filteredTasks.length ? taskStartIndex + 1 : 0}
          onDelete={setDeleteCandidate}
          onEdit={openEditTask}
          onPageChange={setTaskPage}
          onStatus={openStatusModal}
          onView={setViewingTask}
          page={currentTaskPage}
          pageCount={taskPageCount}
          pageNumbers={taskPaginationPages}
          tasks={pagedTasks}
          to={taskEndIndex}
          total={filteredTasks.length}
        />
      </section>
      {viewingTask && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal task-view-modal" role="dialog" aria-modal="true" aria-label="View task">
            <div className="section-heading">
              <h2>{viewingTask.task_id}</h2>
              <button className="icon-only" onClick={() => setViewingTask(null)} type="button" aria-label="Close task details">
                <X size={16} />
              </button>
            </div>
            <div className="ticket-detail-grid">
              <div><span>Title</span><strong>{viewingTask.title}</strong></div>
              <div><span>Category</span><strong>{viewingTask.category}</strong></div>
              <div><span>Department</span><strong>{viewingTask.department}</strong></div>
              <div><span>Priority</span><strong>{viewingTask.priority}</strong></div>
              <div><span>Status</span><strong>{viewingTask.status}</strong></div>
              <div><span>Assigned to</span><strong>{viewingTask.assigned_to}</strong></div>
              <div><span>Assigned role</span><strong>{roleLabel(viewingTask.assigned_role)}</strong></div>
              <div><span>Due date</span><strong>{formatCalendarDate(viewingTask.due_date)}</strong></div>
              <div><span>Created by</span><strong>{viewingTask.created_by_name}</strong></div>
              <div><span>Created date</span><strong>{formatCalendarDate(viewingTask.created_at)}</strong></div>
              <div className="ticket-detail-wide"><span>Description</span><p>{viewingTask.description || "No description provided."}</p></div>
              {viewingTask.notes && <div className="ticket-detail-wide"><span>Notes</span><p>{viewingTask.notes}</p></div>}
            </div>
            <div className="modal-actions">
              <button className="primary-button" onClick={() => setViewingTask(null)} type="button">Done</button>
            </div>
          </section>
        </div>
      )}
      {statusTask && (
        <div className="modal-backdrop" role="presentation">
          <form className="confirm-modal" onSubmit={submitTaskStatus} role="dialog" aria-modal="true" aria-label="Change task status">
            <div className="section-heading">
              <h2>Change Status</h2>
              <button className="icon-only" onClick={() => setStatusTask(null)} type="button" aria-label="Close status form">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-body">
              <p>{statusTask.task_id}</p>
              <strong>{statusTask.title}</strong>
              <label className="vendor-field">
                Status
                <select value={statusValue} onChange={(event) => setStatusValue(event.target.value)}>
                  {taskStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={() => setStatusTask(null)} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Saving..." : "Update Status"}
              </button>
            </div>
          </form>
        </div>
      )}
      {deleteCandidate && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-label="Delete task confirmation">
            <div className="section-heading">
              <h2>Delete Task</h2>
              <button className="icon-only" onClick={() => setDeleteCandidate(null)} type="button" aria-label="Cancel delete task">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-body">
              <p>Are you sure you want to delete this task?</p>
              <strong>{deleteCandidate.title}</strong>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={() => setDeleteCandidate(null)} type="button">Cancel</button>
              <button className="primary-button danger-action" disabled={saving} onClick={confirmDeleteTask} type="button">
                Delete
              </button>
            </div>
          </section>
        </div>
      )}
      {formOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal task-modal" onSubmit={submitTask} role="dialog" aria-modal="true" aria-label={editingTask ? "Edit task" : "Create task"}>
            <div className="section-heading">
              <h2>{editingTask ? "Edit Task" : "Create Task"}</h2>
              <button className="icon-only" onClick={closeTaskForm} type="button" aria-label="Close task form">
                <X size={16} />
              </button>
            </div>
            <div className="vendor-form-grid">
              <VendorField
                error={formErrors.title}
                label="Title"
                onChange={(value) => updateTaskField("title", value)}
                value={form.title}
              />
              <label className="vendor-field">
                Category
                <select onChange={(event) => updateTaskField("category", event.target.value)} value={form.category}>
                  {taskCategoryOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="vendor-field">
                Department
                <select onChange={(event) => updateTaskField("department", event.target.value)} value={form.department}>
                  {taskDepartmentOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                {formErrors.department && <span>{formErrors.department}</span>}
              </label>
              <label className="vendor-field task-assignee-field">
                Assigned To
                <input
                  aria-label="Search assignees"
                  onChange={(event) => setAssigneeSearch(event.target.value)}
                  placeholder="Search users..."
                  type="search"
                  value={assigneeSearch}
                />
                <select
                  aria-label="Assigned To"
                  disabled={assignableLoading}
                  onChange={(event) => updateTaskAssignee(event.target.value)}
                  value={selectedAssigneeValue}
                >
                  <option value="">{assignableLoading ? "Loading users..." : "Choose assignee"}</option>
                  <option value="self">Myself</option>
                  {filteredAssignableUsers.map((user) => (
                    <option key={user.id} value={user.id}>
                      {taskAssigneeOptionLabel(user)}
                    </option>
                  ))}
                </select>
                {form.assigned_email && <small>{roleLabel(form.assigned_role)} · {form.assigned_email}</small>}
                {formErrors.assigned_to && <span>{formErrors.assigned_to}</span>}
              </label>
              <label className="vendor-field">
                Assigned Role
                <select onChange={(event) => updateTaskField("assigned_role", event.target.value)} value={form.assigned_role}>
                  {taskAssignedRoleOptions.map((option) => <option key={option} value={option}>{roleLabel(option)}</option>)}
                </select>
              </label>
              <label className="vendor-field">
                Priority
                <select onChange={(event) => updateTaskField("priority", event.target.value)} value={form.priority}>
                  {taskPriorityOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              {editingTask && (
                <label className="vendor-field">
                  Status
                  <select onChange={(event) => updateTaskField("status", event.target.value)} value={form.status}>
                    {taskStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
              )}
              <VendorField
                error={formErrors.due_date}
                helper={form.due_date ? `Selected: ${formatCalendarDate(form.due_date)}` : "Optional - choose due date from calendar"}
                label="Due Date"
                onChange={(value) => updateTaskField("due_date", value)}
                type="date"
                value={form.due_date}
              />
              <label className="vendor-field wide">
                Description
                <textarea onChange={(event) => updateTaskField("description", event.target.value)} rows={4} value={form.description} />
                {formErrors.description && <span>{formErrors.description}</span>}
              </label>
              <label className="vendor-field wide">
                Notes
                <textarea onChange={(event) => updateTaskField("notes", event.target.value)} rows={3} value={form.notes} />
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={closeTaskForm} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Saving..." : editingTask ? "Update Task" : "Create Task"}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

function TaskTable({
  currentUser,
  emptyDetail,
  emptyTitle,
  from = 0,
  onDelete,
  onEdit,
  onPageChange,
  onStatus,
  page = 1,
  pageCount = 1,
  pageNumbers = [1],
  tasks,
  to = 0,
  total = 0
}) {
  if (!tasks.length) {
    return (
      <EmptyState
        icon={ClipboardList}
        title={emptyTitle}
        detail={emptyDetail}
      />
    );
  }

  return (
    <div className="vendor-table-wrap task-table-wrap">
      <table className="vendor-table task-table">
        <thead>
          <tr>
            <th>Task ID</th>
            <th>Title</th>
            <th>Description</th>
            <th>Category</th>
            <th>Department</th>
            <th>Assigned To</th>
            <th>Assigned Role</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Due Date</th>
            <th>Created By</th>
            <th>Created Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((task) => {
            const canManage = canManageTask(currentUser, task);
            return (
              <tr key={task.id}>
                <td><strong>{task.task_id}</strong></td>
                <td className="ticket-title-cell"><strong>{task.title}</strong></td>
                <td className="task-description-cell">{task.description}</td>
                <td>{task.category}</td>
                <td>{task.department}</td>
                <td>{task.assigned_to}</td>
                <td>{roleLabel(task.assigned_role)}</td>
                <td>{task.priority}</td>
                <td>{task.status}</td>
                <td>{formatCalendarDate(task.due_date)}</td>
                <td className="ticket-person-cell">
                  <strong>{task.created_by_name || "Agent Concierge"}</strong>
                  <span>{task.created_by_email || "system@agent.local"}</span>
                </td>
                <td>{formatCalendarDate(task.created_at)}</td>
                <td>
                  <div className="table-actions task-actions">
                    <button
                      className="table-action-button vendor-row-icon-button task-action-icon action-edit"
                      disabled={!canManage}
                      onClick={() => onEdit(task)}
                      type="button"
                      aria-label="Edit task"
                      title={canManage ? "Edit task" : "Requires task manager access"}
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      className="table-action-button vendor-row-icon-button task-action-icon action-status"
                      disabled={!canManage}
                      onClick={() => onStatus(task)}
                      type="button"
                      aria-label="Change task status"
                      title={canManage ? "Change task status" : "Requires task manager access"}
                    >
                      <RefreshCw size={16} />
                    </button>
                    <button
                      className="table-action-button vendor-row-icon-button task-action-icon action-close"
                      disabled={!canManage}
                      onClick={() => onDelete(task)}
                      type="button"
                      aria-label="Delete task"
                      title={canManage ? "Delete task" : "Requires task manager access"}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="vendor-table-footer task-table-footer">
        <span>Showing {from} to {to} of {total} tasks</span>
        <div className="pagination-controls" aria-label="Task pagination">
          <button
            disabled={page <= 1}
            onClick={() => onPageChange?.(Math.max(1, page - 1))}
            type="button"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          {pageNumbers.map((pageNumber) => (
            <button
              className={pageNumber === page ? "active" : ""}
              key={pageNumber}
              onClick={() => onPageChange?.(pageNumber)}
              type="button"
            >
              {pageNumber}
            </button>
          ))}
          <button
            disabled={page >= pageCount}
            onClick={() => onPageChange?.(Math.min(pageCount, page + 1))}
            type="button"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ticketAssignedLabel(ticket) {
  return ticket.assigned_team || roleLabel(ticket.assigned_role || "");
}

function isFinanceRelatedTicket(ticket) {
  const text = `${ticket.category || ""} ${ticket.assigned_role || ""}`.toLowerCase();
  return ticket.ticket_type === "Admin" && ["finance", "invoice", "payment", "expense", "reimbursement"].some((term) => text.includes(term));
}

function canManageTicket(user, ticket) {
  if (!user || !ticket) return false;
  if (user.role === "admin") return true;
  if (user.role === "it_manager" && ticket.ticket_type === "IT") return true;
  if (user.role === "finance_manager" && isFinanceRelatedTicket(ticket)) return true;
  return false;
}

function canUpdateTicketStatus(user, ticket) {
  if (!user || !ticket) return false;
  if (user.role === "admin") return true;
  if (user.role === "it_manager" && ticket.ticket_type === "IT") return true;
  return false;
}

function isItRelatedExpense(expense) {
  const text = `${expense.department || ""} ${expense.category || ""}`.toLowerCase();
  return text.includes("it") || text.includes("software") || text.includes("internet");
}

function canManageExpense(user, expense) {
  if (!user || !expense) return false;
  if (user.role === "admin" || user.role === "finance_manager") return true;
  if (user.role === "employee") {
    return expense.employee_email === user.email && ["Draft", "Needs Info"].includes(expense.status);
  }
  return false;
}

function canApproveExpense(user) {
  return user?.role === "admin" || user?.role === "finance_manager";
}

function expenseMatchesLocalSearch(expense, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [
    expense.expense_id,
    expense.employee_name,
    expense.employee_email,
    expense.department,
    expense.category,
    expense.vendor_merchant,
    expense.payment_mode,
    expense.receipt_attachment_name,
    expense.notes,
    expense.status
  ].join(" ").toLowerCase().includes(normalized);
}

function formatMoney(amount, currency = "INR") {
  const numeric = Number(amount || 0);
  if (currency === "INR") {
    return `₹${numeric.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
  }
  return `${currency} ${numeric.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatChartValue(value, valueKind = "count") {
  if (valueKind === "currency") return formatMoney(value);
  return Number(value || 0).toLocaleString("en-IN");
}

function ticketMatchesLocalSearch(ticket, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return [
    ticket.ticket_id,
    ticket.title,
    ticket.requester_name,
    ticket.requester_email,
    ticket.category,
    ticket.assigned_role,
    ticket.assigned_team
  ].join(" ").toLowerCase().includes(normalized);
}

function ticketBadgeClass(base, value) {
  return `${base} ${String(value || "").toLowerCase().replace(/\s+/g, "-")}`;
}

function TicketsView({ currentUser, onTicketSaved, onUpdated, setError, tickets }) {
  const [ticketSearch, setTicketSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [ticketFilters, setTicketFilters] = useState({ type: "All", status: "All", priority: "All" });
  const [ticketPage, setTicketPage] = useState(1);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const [formOpen, setFormOpen] = useState(false);
  const [editingTicket, setEditingTicket] = useState(null);
  const [viewingTicket, setViewingTicket] = useState(null);
  const [ticketMessage, setTicketMessage] = useState(null);
  const [statusTicket, setStatusTicket] = useState(null);
  const [statusValue, setStatusValue] = useState("Open");
  const [form, setForm] = useState(emptyTicketForm);
  const [formErrors, setFormErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const activeFilterCount = Object.values(ticketFilters).filter((value) => value !== "All").length;
  const filteredTickets = useMemo(() => {
    return tickets.filter((ticket) => {
      const matchesQuery = ticketMatchesLocalSearch(ticket, ticketSearch);
      const matchesType = ticketFilters.type === "All" || ticket.ticket_type === ticketFilters.type;
      const matchesStatus = ticketFilters.status === "All" || ticket.status === ticketFilters.status;
      const matchesPriority = ticketFilters.priority === "All" || ticket.priority === ticketFilters.priority;
      return matchesQuery && matchesType && matchesStatus && matchesPriority;
    });
  }, [ticketFilters, ticketSearch, tickets]);
  const ticketPageCount = Math.max(1, Math.ceil(filteredTickets.length / TICKET_PAGE_SIZE));
  const currentTicketPage = Math.min(ticketPage, ticketPageCount);
  const ticketStartIndex = filteredTickets.length ? (currentTicketPage - 1) * TICKET_PAGE_SIZE : 0;
  const ticketEndIndex = Math.min(ticketStartIndex + TICKET_PAGE_SIZE, filteredTickets.length);
  const pagedTickets = filteredTickets.slice(ticketStartIndex, ticketEndIndex);
  const firstPaginationPage = Math.min(
    Math.max(1, currentTicketPage - 1),
    Math.max(1, ticketPageCount - 2)
  );
  const ticketPaginationPages = Array.from(
    { length: Math.min(3, ticketPageCount) },
    (_, index) => firstPaginationPage + index
  );

  useEffect(() => {
    setTicketPage(1);
  }, [ticketFilters, ticketSearch, tickets.length]);

  useEffect(() => {
    if (ticketPage > ticketPageCount) {
      setTicketPage(ticketPageCount);
    }
  }, [ticketPage, ticketPageCount]);

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = window.setTimeout(() => setToastMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  function updateTicketFilter(field, value) {
    setTicketFilters((current) => ({ ...current, [field]: value }));
  }

  function clearTicketFilters() {
    setTicketFilters({ type: "All", status: "All", priority: "All" });
  }

  function updateTicketField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function updateTicketType(value) {
    const firstCategory = ticketCategoryOptions[value]?.[0] || "Other";
    setForm((current) => ({
      ...current,
      ticket_type: value,
      category: firstCategory
    }));
    setFormErrors((current) => ({ ...current, ticket_type: "", category: "" }));
  }

  function validateTicketForm() {
    const errors = {};
    if (!form.title.trim()) errors.title = "Required";
    if (form.title.trim().length > 0 && form.title.trim().length < 3) errors.title = "Enter at least 3 characters";
    if (!form.description.trim()) errors.description = "Required";
    if (form.description.trim().length > 0 && form.description.trim().length < 3) errors.description = "Enter at least 3 characters";
    if (!form.category.trim()) errors.category = "Choose a category";
    if (form.due_date && !isValidIsoDate(form.due_date)) errors.due_date = "Choose a valid due date";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function openCreateTicket() {
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingTicket(null);
    setForm(emptyTicketForm);
    setFormOpen(true);
  }

  function openEditTicket(ticket) {
    if (!canManageTicket(currentUser, ticket)) return;
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingTicket(ticket);
    setForm({
      ticket_type: ticket.ticket_type || "IT",
      title: ticket.title || "",
      description: ticket.description || "",
      category: ticket.category || ticketCategoryOptions[ticket.ticket_type]?.[0] || "Other",
      priority: ticket.priority || "Medium",
      status: ticket.status || "Open",
      due_date: String(ticket.due_date || "").slice(0, 10),
      approval_required: Boolean(ticket.approval_required)
    });
    setFormOpen(true);
  }

  function closeTicketForm() {
    setFormOpen(false);
    setEditingTicket(null);
    setForm(emptyTicketForm);
    setFormErrors({});
  }

  function openStatusModal(ticket) {
    if (!canUpdateTicketStatus(currentUser, ticket)) return;
    setToastMessage("");
    setToastType("success");
    setStatusTicket(ticket);
    setStatusValue(ticket.status || "Open");
  }

  function openTicketMessage(ticket) {
    setTicketMessage({
      detail: "Send a ticket update by Email, WhatsApp, or both.",
      recipient_name: ticket.requester_name || "",
      recipient_email: ticket.requester_email || "",
      recipient_phone: "",
      subject: `Ticket update: ${ticket.ticket_id}`,
      message_body: `Hello ${ticket.requester_name || "there"},\n\nYour ticket "${ticket.title}" is currently ${ticket.status}.\n\nRegards,\nAgent Concierge`,
      related_module: "tickets",
      related_record_id: ticket.ticket_id || ticket.id
    });
  }

  async function submitTicket(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    if (!validateTicketForm()) return;
    setSaving(true);
    try {
      const payload = {
        ...form,
        title: form.title.trim(),
        description: form.description.trim(),
        category: form.category.trim(),
        due_date: form.due_date || null
      };
      let response;
      if (editingTicket) {
        response = await updateTicket(editingTicket.id, payload);
      } else {
        response = await createTicket(payload);
      }
      if (response?.ticket) {
        onTicketSaved(response.ticket);
      }
      try {
        await onUpdated();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      closeTicketForm();
      setToastType("success");
      setToastMessage(editingTicket ? "Ticket updated successfully" : "Ticket created successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not save ticket: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function submitTicketStatus(event) {
    event.preventDefault();
    if (!statusTicket) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      const response = await updateTicketStatus(statusTicket.id, statusValue);
      if (response?.ticket) {
        onTicketSaved(response.ticket);
      }
      try {
        await onUpdated();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setStatusTicket(null);
      setToastType("success");
      setToastMessage("Ticket status updated successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not update ticket status: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  const categoryOptions = ticketCategoryOptions[form.ticket_type] || ["Other"];
  const categoryList = form.category && !categoryOptions.includes(form.category) ? [...categoryOptions, form.category] : categoryOptions;

  return (
    <section className="tickets-page screen-stack">
      {toastMessage && <div className={toastType === "error" ? "toast-notification error" : "toast-notification"} role="status">{toastMessage}</div>}
      <section className="dashboard-card vendor-directory-card ticket-directory-card">
        <div className="vendor-directory-header ticket-directory-header">
          <div className="vendor-directory-title">
            <span className="vendor-directory-icon"><ClipboardList size={20} /></span>
            <div>
              <div className="directory-title-row">
                <h2>Ticket Directory</h2>
                <span className="vendor-count-badge">{filteredTickets.length} Tickets</span>
              </div>
              <p>Manage IT and Admin tickets in one queue</p>
            </div>
          </div>
          <div className="ticket-action-row">
            <label className="vendor-search-control ticket-search-control" aria-label="Search tickets">
              <Search size={17} />
              <input
                onChange={(event) => setTicketSearch(event.target.value)}
                placeholder="Search tickets..."
                value={ticketSearch}
              />
              {ticketSearch && (
                <button
                  aria-label="Clear ticket search"
                  onClick={() => setTicketSearch("")}
                  title="Clear ticket search"
                  type="button"
                >
                  <X size={15} />
                </button>
              )}
            </label>
            <div className="vendor-filter-wrap">
              <button
                aria-expanded={filtersOpen}
                aria-label="Filter tickets"
                className="icon-button secondary vendor-filter-button inventory-icon-action"
                onClick={() => setFiltersOpen((open) => !open)}
                title="Filter tickets"
                type="button"
              >
                <Filter size={17} />
                {activeFilterCount > 0 && <strong>{activeFilterCount}</strong>}
              </button>
              {filtersOpen && (
                <div className="vendor-filter-panel" role="dialog" aria-label="Ticket filters">
                  <label>
                    Type
                    <select value={ticketFilters.type} onChange={(event) => updateTicketFilter("type", event.target.value)}>
                      {ticketTypeFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Status
                    <select value={ticketFilters.status} onChange={(event) => updateTicketFilter("status", event.target.value)}>
                      {ticketStatusFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Priority
                    <select value={ticketFilters.priority} onChange={(event) => updateTicketFilter("priority", event.target.value)}>
                      {ticketPriorityFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <button className="table-action-button" onClick={clearTicketFilters} type="button">Clear</button>
                </div>
              )}
            </div>
            <button className="primary-button vendor-add-button ticket-create-button" onClick={openCreateTicket} type="button">
              <Plus size={18} />
              <span>Create Ticket</span>
            </button>
          </div>
        </div>
        <TicketTable
          currentUser={currentUser}
          emptyDetail={tickets.length ? "Adjust search or filters to show more tickets." : "Create IT or Admin tickets for the current workflow."}
          emptyTitle={tickets.length ? "No tickets match." : "No tickets yet."}
          from={filteredTickets.length ? ticketStartIndex + 1 : 0}
          onEdit={openEditTicket}
          onPageChange={setTicketPage}
          onStatus={openStatusModal}
          onView={setViewingTicket}
          page={currentTicketPage}
          pageCount={ticketPageCount}
          pageNumbers={ticketPaginationPages}
          tickets={pagedTickets}
          to={ticketEndIndex}
          total={filteredTickets.length}
        />
      </section>
      {viewingTicket && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal ticket-view-modal" role="dialog" aria-modal="true" aria-label="View ticket">
            <div className="section-heading">
              <h2>{viewingTicket.ticket_id}</h2>
              <button className="icon-only" onClick={() => setViewingTicket(null)} type="button" aria-label="Close ticket details">
                <X size={16} />
              </button>
            </div>
            <div className="ticket-detail-grid">
              <div><span>Title</span><strong>{viewingTicket.title}</strong></div>
              <div><span>Type</span><strong>{viewingTicket.ticket_type}</strong></div>
              <div><span>Category</span><strong>{viewingTicket.category}</strong></div>
              <div><span>Priority</span><strong>{viewingTicket.priority}</strong></div>
              <div><span>Status</span><strong>{viewingTicket.status}</strong></div>
              <div><span>Requested by</span><strong>{viewingTicket.requester_name}</strong></div>
              <div><span>Assigned to</span><strong>{ticketAssignedLabel(viewingTicket)}</strong></div>
              <div><span>Due date</span><strong>{formatCalendarDate(viewingTicket.due_date)}</strong></div>
              <div><span>Approval required</span><strong>{viewingTicket.approval_required ? "Yes" : "No"}</strong></div>
              <div className="ticket-detail-wide"><span>Description</span><p>{viewingTicket.description || "No description provided."}</p></div>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={() => openTicketMessage(viewingTicket)} type="button">
                <Send size={16} />
                <span>Send Update</span>
              </button>
              <button className="primary-button" onClick={() => setViewingTicket(null)} type="button">Done</button>
            </div>
          </section>
        </div>
      )}
      {ticketMessage && (
        <CommunicationSendModal
          context={ticketMessage}
          onClose={() => setTicketMessage(null)}
          onSent={(response) => {
            setToastType("success");
            setToastMessage(response?.message || "Message sent");
          }}
          setError={setError}
        />
      )}
      {statusTicket && (
        <div className="modal-backdrop" role="presentation">
          <form className="confirm-modal" onSubmit={submitTicketStatus} role="dialog" aria-modal="true" aria-label="Change ticket status">
            <div className="section-heading">
              <h2>Change Status</h2>
              <button className="icon-only" onClick={() => setStatusTicket(null)} type="button" aria-label="Close status form">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-body">
              <p>{statusTicket.ticket_id}</p>
              <strong>{statusTicket.title}</strong>
              <label className="vendor-field">
                Status
                <select value={statusValue} onChange={(event) => setStatusValue(event.target.value)}>
                  {ticketStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={() => setStatusTicket(null)} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Saving..." : "Update Status"}
              </button>
            </div>
          </form>
        </div>
      )}
      {formOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal ticket-modal" onSubmit={submitTicket} role="dialog" aria-modal="true" aria-label="Create ticket">
            <div className="section-heading">
              <h2>{editingTicket ? "Edit Ticket" : "Create Ticket"}</h2>
              <button className="icon-only" onClick={closeTicketForm} type="button" aria-label="Close ticket form">
                <X size={16} />
              </button>
            </div>
            <div className="vendor-form-grid">
              <label className="vendor-field">
                Type
                <select onChange={(event) => updateTicketType(event.target.value)} value={form.ticket_type}>
                  {ticketTypeOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="vendor-field">
                Category
                <select onChange={(event) => updateTicketField("category", event.target.value)} value={form.category}>
                  {categoryList.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                {formErrors.category && <span>{formErrors.category}</span>}
              </label>
              <VendorField
                error={formErrors.title}
                label="Title"
                onChange={(value) => updateTicketField("title", value)}
                value={form.title}
              />
              <label className="vendor-field">
                Priority
                <select onChange={(event) => updateTicketField("priority", event.target.value)} value={form.priority}>
                  {ticketPriorityOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              {editingTicket && canUpdateTicketStatus(currentUser, editingTicket) && (
                <label className="vendor-field">
                  Status
                  <select onChange={(event) => updateTicketField("status", event.target.value)} value={form.status}>
                    {ticketStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
              )}
              <VendorField
                error={formErrors.due_date}
                helper={form.due_date ? `Selected: ${formatCalendarDate(form.due_date)}` : "Optional - choose due date from calendar"}
                label="Due date"
                onChange={(value) => updateTicketField("due_date", value)}
                type="date"
                value={form.due_date}
              />
              <label className="vendor-field wide">
                Description
                <textarea
                  onChange={(event) => updateTicketField("description", event.target.value)}
                  rows={4}
                  value={form.description}
                />
                {formErrors.description && <span>{formErrors.description}</span>}
              </label>
              <label className="ticket-checkbox wide">
                <input
                  checked={form.approval_required}
                  onChange={(event) => updateTicketField("approval_required", event.target.checked)}
                  type="checkbox"
                />
                <span>Approval required</span>
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={closeTicketForm} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Saving..." : editingTicket ? "Update Ticket" : "Create Ticket"}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

function TicketTable({
  currentUser,
  emptyDetail,
  emptyTitle,
  from = 0,
  onEdit,
  onPageChange,
  onStatus,
  onView,
  page = 1,
  pageCount = 1,
  pageNumbers = [1],
  tickets,
  to = 0,
  total = 0
}) {
  if (!tickets.length) {
    return (
      <EmptyState
        icon={ClipboardList}
        title={emptyTitle}
        detail={emptyDetail}
      />
    );
  }

  return (
    <div className="vendor-table-wrap ticket-table-wrap">
      <table className="vendor-table ticket-table">
        <thead>
          <tr>
            <th>Ticket ID</th>
            <th>Title</th>
            <th>Type</th>
            <th>Category</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Requested by</th>
            <th>Assigned to / Assigned role</th>
            <th>Created date</th>
            <th>Due date</th>
            <th>Approval required</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => {
            const canManage = canManageTicket(currentUser, ticket);
            const canChangeStatus = canUpdateTicketStatus(currentUser, ticket);
            return (
              <tr key={ticket.id}>
                <td><strong>{ticket.ticket_id}</strong></td>
                <td className="ticket-title-cell">
                  <strong>{ticket.title}</strong>
                  {ticket.description && <p>{ticket.description}</p>}
                </td>
                <td>{ticket.ticket_type}</td>
                <td>{ticket.category}</td>
                <td>{ticket.priority}</td>
                <td>{ticket.status}</td>
                <td className="ticket-person-cell">
                  <strong>{ticket.requester_name}</strong>
                  <span>{ticket.requester_email}</span>
                </td>
                <td className="ticket-person-cell">
                  <strong>{ticketAssignedLabel(ticket)}</strong>
                  <span>{roleLabel(ticket.assigned_role)}</span>
                </td>
                <td>{formatCalendarDate(ticket.created_at)}</td>
                <td>{formatCalendarDate(ticket.due_date)}</td>
                <td>{ticket.approval_required ? "Yes" : "No"}</td>
                <td>
                  <div className="table-actions ticket-actions">
                    <button
                      aria-label="View ticket"
                      className="table-action-button ticket-icon-action action-view"
                      onClick={() => onView(ticket)}
                      title="View ticket"
                      type="button"
                    >
                      <Eye size={16} />
                    </button>
                    <button
                      aria-label="Edit ticket"
                      className="table-action-button ticket-icon-action action-edit"
                      disabled={!canManage}
                      onClick={() => onEdit(ticket)}
                      title={canManage ? "Edit ticket" : "Requires ticket manager access"}
                      type="button"
                    >
                      <Pencil size={16} />
                    </button>
                    {currentUser?.role !== "finance_manager" && (
                      <button
                        aria-label="Change ticket status"
                        className="table-action-button ticket-icon-action action-status"
                        disabled={!canChangeStatus}
                        onClick={() => onStatus(ticket)}
                        title={canChangeStatus ? "Change status" : "Requires ticket status access"}
                        type="button"
                      >
                        <RefreshCw size={16} />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="vendor-table-footer ticket-table-footer">
        <span>Showing {from} to {to} of {total} tickets</span>
        <div className="pagination-controls" aria-label="Ticket pagination">
          <button
            disabled={page <= 1}
            onClick={() => onPageChange?.(Math.max(1, page - 1))}
            type="button"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          {pageNumbers.map((pageNumber) => (
            <button
              className={pageNumber === page ? "active" : ""}
              key={pageNumber}
              onClick={() => onPageChange?.(pageNumber)}
              type="button"
            >
              {pageNumber}
            </button>
          ))}
          <button
            disabled={page >= pageCount}
            onClick={() => onPageChange?.(Math.min(pageCount, page + 1))}
            type="button"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function CommunicationSendModal({ context, onClose, onSent, setError }) {
  const [form, setForm] = useState({
    channel: context?.channel || "email",
    recipient_name: context?.recipient_name || "",
    recipient_email: context?.recipient_email || "",
    recipient_phone: context?.recipient_phone || "",
    subject: context?.subject || "",
    message_body: context?.message_body || "",
    attachments: context?.attachments || []
  });
  const [previewing, setPreviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [localError, setLocalError] = useState("");
  const sendsEmail = form.channel === "email" || form.channel === "both";
  const sendsWhatsApp = form.channel === "whatsapp" || form.channel === "both";
  const showSubject = sendsEmail;

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setLocalError("");
  }

  function validateCommunication() {
    if ((form.channel === "email" || form.channel === "both") && !form.recipient_email.trim()) {
      return "Recipient email is required for Email.";
    }
    if ((form.channel === "whatsapp" || form.channel === "both") && !form.recipient_phone.trim()) {
      return "Recipient phone is required for WhatsApp.";
    }
    if (!form.message_body.trim()) {
      return "Message body is required.";
    }
    if ((form.channel === "email" || form.channel === "both") && !form.subject.trim()) {
      return "Subject is required for Email.";
    }
    return "";
  }

  function handlePreview(event) {
    event.preventDefault();
    const error = validateCommunication();
    if (error) {
      setLocalError(error);
      return;
    }
    setPreviewing(true);
  }

  async function confirmSend() {
    const error = validateCommunication();
    if (error) {
      setLocalError(error);
      return;
    }
    setSaving(true);
    setError?.("");
    setLocalError("");
    try {
      const response = await sendCommunication({
        ...form,
        recipient_name: form.recipient_name.trim(),
        recipient_email: sendsEmail ? form.recipient_email.trim() : "",
        recipient_phone: sendsWhatsApp ? form.recipient_phone.trim() : "",
        subject: showSubject ? form.subject.trim() : "",
        message_body: form.message_body.trim(),
        related_module: context?.related_module || "general",
        related_record_id: String(context?.related_record_id || ""),
        attachments: form.attachments || []
      });
      onSent?.(response);
      onClose?.();
    } catch (err) {
      const message = apiErrorMessage(err);
      setLocalError(message);
      setError?.(message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <form className="vendor-modal communication-modal" onSubmit={handlePreview} role="dialog" aria-modal="true" aria-label="Send message">
        <div className="section-heading">
          <div>
            <h2>{previewing ? "Preview Message" : "Send Message"}</h2>
            <p>{context?.detail || "Choose a channel and preview before sending."}</p>
          </div>
          <button className="icon-only" onClick={onClose} type="button" aria-label="Close send message">
            <X size={16} />
          </button>
        </div>
        {localError && <div className="import-inline-error">{localError}</div>}
        <div className="vendor-form-grid">
          <label className="vendor-field">
            Channel
            <select disabled={previewing} value={form.channel} onChange={(event) => updateField("channel", event.target.value)}>
              {communicationChannelOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="vendor-field">
            Recipient name
            <input readOnly={previewing} value={form.recipient_name} onChange={(event) => updateField("recipient_name", event.target.value)} />
          </label>
          {sendsEmail && (
            <label className="vendor-field">
              Recipient email
              <input readOnly={previewing} value={form.recipient_email} onChange={(event) => updateField("recipient_email", event.target.value)} />
            </label>
          )}
          {sendsWhatsApp && (
            <label className="vendor-field">
              Recipient phone
              <input readOnly={previewing} value={form.recipient_phone} onChange={(event) => updateField("recipient_phone", event.target.value)} />
            </label>
          )}
          {showSubject && (
            <label className="vendor-field wide">
              Subject
              <input readOnly={previewing} value={form.subject} onChange={(event) => updateField("subject", event.target.value)} />
            </label>
          )}
          <label className="vendor-field wide">
            Message body
            <textarea readOnly={previewing} rows={7} value={form.message_body} onChange={(event) => updateField("message_body", event.target.value)} />
          </label>
          {Boolean(form.attachments?.length) && (
            <div className="communication-preview wide">
              <span>Attachments</span>
              {form.attachments.map((attachment) => <strong key={attachment}>{attachment}</strong>)}
            </div>
          )}
        </div>
        {previewing && (
          <div className="communication-preview">
            <span>Preview</span>
            <strong>{communicationChannelOptions.find((option) => option.value === form.channel)?.label}</strong>
            <dl className="communication-preview-meta">
              {form.recipient_name && (
                <>
                  <dt>Recipient</dt>
                  <dd>{form.recipient_name}</dd>
                </>
              )}
              {sendsEmail && (
                <>
                  <dt>Email</dt>
                  <dd>{form.recipient_email}</dd>
                </>
              )}
              {sendsWhatsApp && (
                <>
                  <dt>Phone</dt>
                  <dd>{form.recipient_phone}</dd>
                </>
              )}
              {showSubject && (
                <>
                  <dt>Subject</dt>
                  <dd>{form.subject}</dd>
                </>
              )}
            </dl>
            <p>{form.message_body}</p>
          </div>
        )}
        <div className="modal-actions">
          {previewing ? (
            <>
              <button className="icon-button secondary" disabled={saving} onClick={() => setPreviewing(false)} type="button">Edit</button>
              <button className="primary-button" disabled={saving} onClick={confirmSend} type="button">
                <Send size={17} />
                <span>{saving ? "Sending..." : "Confirm Send"}</span>
              </button>
            </>
          ) : (
            <>
              <button className="icon-button secondary" onClick={onClose} type="button">Cancel</button>
              <button className="primary-button" type="submit">Preview</button>
            </>
          )}
        </div>
      </form>
    </div>
  );
}

function VendorsView({ currentUser, onChanged, setError, vendors }) {
  const canAddVendor = currentUser.role === "admin";
  const canSendVendorMessage = ["admin", "finance_manager"].includes(currentUser.role);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState(emptyVendorForm);
  const [formErrors, setFormErrors] = useState({});
  const [closingVendor, setClosingVendor] = useState(null);
  const [editingVendor, setEditingVendor] = useState(null);
  const [emailVendor, setEmailVendor] = useState(null);
  const [emailForm, setEmailForm] = useState({ subject: "", body: "" });
  const [vendorSearch, setVendorSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const vendorFilterRef = useRef(null);
  const [vendorPage, setVendorPage] = useState(1);
  const [vendorFilters, setVendorFilters] = useState({
    status: "All",
    service: "All",
    billingCycle: "All"
  });
  const [vendorFilterDraft, setVendorFilterDraft] = useState({
    status: "All",
    service: "All",
    billingCycle: "All"
  });
  const [saving, setSaving] = useState(false);
  const filteredVendors = useMemo(() => {
    const query = vendorSearch.trim().toLowerCase();
    return vendors.filter((vendor) => {
      const searchText = [
        vendor.vendor_name,
        vendor.contact_person,
        vendor.email,
        vendor.contact_details,
        vendor.service_provided
      ].join(" ").toLowerCase();
      const matchesQuery = !query || searchText.includes(query);
      const matchesStatus =
        vendorFilters.status === "All" ||
        String(vendor.status || "").toLowerCase() === vendorFilters.status.toLowerCase();
      const matchesService =
        vendorFilters.service === "All" ||
        vendor.service_provided === vendorFilters.service;
      const matchesBillingCycle =
        vendorFilters.billingCycle === "All" ||
        normalizeBillingCycle(vendor.billing_cycle) === vendorFilters.billingCycle;
      return matchesQuery && matchesStatus && matchesService && matchesBillingCycle;
    });
  }, [vendorFilters, vendorSearch, vendors]);
  const vendorPageCount = Math.max(1, Math.ceil(filteredVendors.length / VENDOR_PAGE_SIZE));
  const currentVendorPage = Math.min(vendorPage, vendorPageCount);
  const vendorStartIndex = filteredVendors.length ? (currentVendorPage - 1) * VENDOR_PAGE_SIZE : 0;
  const vendorEndIndex = Math.min(vendorStartIndex + VENDOR_PAGE_SIZE, filteredVendors.length);
  const pagedVendors = filteredVendors.slice(vendorStartIndex, vendorEndIndex);
  const firstPaginationPage = Math.min(
    Math.max(1, currentVendorPage - 1),
    Math.max(1, vendorPageCount - 2)
  );
  const vendorPaginationPages = Array.from(
    { length: Math.min(3, vendorPageCount) },
    (_, index) => firstPaginationPage + index
  );

  useEffect(() => {
    setVendorPage(1);
  }, [vendorFilters, vendorSearch, vendors.length]);

  useEffect(() => {
    if (vendorPage > vendorPageCount) {
      setVendorPage(vendorPageCount);
    }
  }, [vendorPage, vendorPageCount]);

  useEffect(() => {
    if (!filtersOpen) return undefined;
    function handlePointerDown(event) {
      if (vendorFilterRef.current && !vendorFilterRef.current.contains(event.target)) {
        setFiltersOpen(false);
      }
    }
    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setFiltersOpen(false);
      }
    }
    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [filtersOpen]);

  function toggleVendorFilters() {
    setFiltersOpen((open) => {
      if (!open) {
        setVendorFilterDraft(vendorFilters);
      }
      return !open;
    });
  }

  function updateVendorFilterDraft(field, value) {
    setVendorFilterDraft((current) => ({ ...current, [field]: value }));
  }

  function applyVendorFilters() {
    setVendorFilters(vendorFilterDraft);
    setFiltersOpen(false);
  }

  function clearVendorFilters() {
    const clearedFilters = { status: "All", service: "All", billingCycle: "All" };
    setVendorFilterDraft(clearedFilters);
    setVendorFilters(clearedFilters);
    setFiltersOpen(false);
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function updateVendorName(value) {
    setForm((current) => ({
      ...current,
      vendor_name: value,
      service_provided: inferVendorService(value)
    }));
    setFormErrors((current) => ({ ...current, vendor_name: "", service_provided: "" }));
  }

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = window.setTimeout(() => setToastMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  function validateVendorForm() {
    const errors = {};
    Object.entries(form).forEach(([key, value]) => {
      if (key === "end_date") return;
      if (!String(value || "").trim()) {
        errors[key] = "Required";
      }
    });
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      errors.email = "Enter a valid email";
    }
    if (form.office_address && form.office_address.trim().length < 5) {
      errors.office_address = "Enter at least 5 characters";
    }
    if (!form.service_provided) {
      errors.service_provided = "Choose a service";
    }
    if (!/^\d+$/.test(String(form.billing_amount || "").trim())) {
      errors.billing_amount = "Enter numbers only";
    } else if (Number(form.billing_amount) <= 0) {
      errors.billing_amount = "Amount must be greater than 0";
    }
    if (!form.billing_cycle) {
      errors.billing_cycle = "Choose a billing cycle";
    }
    const startDate = String(form.start_date || "").trim();
    const endDate = String(form.end_date || "").trim();
    if (startDate && !isValidIsoDate(startDate)) {
      errors.start_date = "Choose a valid start date";
    }
    if (endDate && !isValidIsoDate(endDate)) {
      errors.end_date = "Choose a valid end date or leave blank";
    }
    if (startDate && endDate && isValidIsoDate(startDate) && isValidIsoDate(endDate) && endDate < startDate) {
      errors.end_date = "End date must be on or after start date";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0 ? { startDate, endDate } : null;
  }

  function openForm() {
    if (!canAddVendor) return;
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingVendor(null);
    setForm(emptyVendorForm);
    setFormOpen(true);
  }

  function openEdit(vendor) {
    if (!canAddVendor) return;
    const billingAmount = normalizeBillingAmount(vendor.billing_amount);
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingVendor(vendor);
    setForm({
      vendor_name: vendor.vendor_name || "",
      contact_person: vendor.contact_person || "",
      email: vendor.email || "",
      contact_details: vendor.contact_details || "",
      office_address: vendor.office_address || "",
      service_provided: vendor.service_provided || "",
      start_date: vendor.start_date || "",
      end_date: vendor.end_date || "",
      billing_amount: billingAmount > 0 ? String(billingAmount) : "",
      billing_cycle: normalizeBillingCycle(vendor.billing_cycle) || "Monthly"
    });
    setFormOpen(true);
  }

  function openCloseConfirmation(vendor) {
    if (!canAddVendor) return;
    setToastMessage("");
    setToastType("success");
    setClosingVendor(vendor);
  }

  function openEmailModal(vendor) {
    if (!canSendVendorMessage) return;
    setToastMessage("");
    setToastType("success");
    setEmailVendor(vendor);
    setEmailForm({
      subject: `Follow-up for ${vendor.vendor_name}`,
      body: `Hello ${vendor.contact_person || "there"},\n\nSharing a quick vendor update from Agent Concierge.\n\nRegards,\nAgent Concierge`
    });
  }

  function vendorPhoneForSend(vendor) {
    return vendor.contact_details
      || vendor.contactDetails
      || vendor.phone
      || vendor.contact_number
      || vendor.contactNumber
      || "";
  }

  function closeForm() {
    setFormOpen(false);
    setFormErrors({});
    setEditingVendor(null);
    setForm(emptyVendorForm);
  }

  function closeEmailModal() {
    setEmailVendor(null);
    setEmailForm({ subject: "", body: "" });
  }

  async function confirmCloseVendor() {
    if (!closingVendor) return;
    setError("");
    setToastMessage("");
    if (!closingVendor.id) {
      setToastType("error");
      setToastMessage("Vendor could not be found. Please refresh and try again.");
      return;
    }
    setSaving(true);
    try {
      await closeVendor(closingVendor.id);
      await onChanged();
      setClosingVendor(null);
      setToastType("success");
      setToastMessage("Vendor closed successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(
        err.status === 404 || /not found/i.test(err.message)
          ? "Vendor could not be found. Please refresh and try again."
          : `Could not close vendor: ${apiErrorMessage(err)}`
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleReopenVendor(vendor) {
    if (!canAddVendor) return;
    setError("");
    setToastMessage("");
    if (!vendor.id) {
      setToastType("error");
      setToastMessage("Vendor could not be found. Please refresh and try again.");
      return;
    }
    setSaving(true);
    try {
      await reopenVendor(vendor.id);
      await onChanged();
      setToastType("success");
      setToastMessage("Vendor reopened successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(
        err.status === 404 || /not found/i.test(err.message)
          ? "Vendor could not be found. Please refresh and try again."
          : `Could not reopen vendor: ${apiErrorMessage(err)}`
      );
    } finally {
      setSaving(false);
    }
  }

  async function submitVendor(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    const validated = validateVendorForm();
    if (!validated) return;
    setSaving(true);
    try {
      const payload = Object.fromEntries(
        Object.entries(form).map(([key, value]) => [key, typeof value === "string" ? value.trim() : value])
      );
      payload.start_date = validated.startDate;
      payload.end_date = validated.endDate || null;
      payload.billing_amount = normalizeBillingAmount(payload.billing_amount);
      payload.billing_cycle = normalizeBillingCycle(payload.billing_cycle);
      const response = editingVendor
        ? await updateVendor(editingVendor.id, payload)
        : await createVendor(payload);
      const refreshed = await onChanged();
      const refreshedVendor = refreshed?.vendors?.find((vendor) => vendor.id === response.vendor?.id);
      const savedVendor = refreshedVendor || response.vendor;
      if (!savedVendor || normalizeBillingAmount(savedVendor.billing_amount) !== payload.billing_amount) {
        throw new Error("Billing amount was not saved. Please try again.");
      }
      if (normalizeBillingCycle(savedVendor.billing_cycle) !== payload.billing_cycle) {
        throw new Error("Billing cycle was not saved. Please try again.");
      }
      closeForm();
      setToastType("success");
      setToastMessage(editingVendor ? "Vendor updated successfully" : "Vendor added successfully");
    } catch (err) {
      if (err.message.toLowerCase().includes("end_date")) {
        setFormErrors((current) => ({ ...current, end_date: "Choose a valid end date or leave it blank" }));
      } else if (err.message.toLowerCase().includes("start_date")) {
        setFormErrors((current) => ({ ...current, start_date: "Choose a valid start date" }));
      } else if (err.message.toLowerCase().includes("billing")) {
        setToastType("error");
        setToastMessage(err.message);
      } else {
        setError(apiErrorMessage(err));
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="vendors-page">
      <div className="vendors-page-header">
        <div className="page-title vendors-title">
          <div className="directory-title-row">
            <h1>Vendors</h1>
            <span className="vendor-count-badge">{filteredVendors.length} Vendors</span>
          </div>
        </div>
        <div className="vendors-top-action">
          <label className="vendor-search-control" aria-label="Search vendors">
            <Search size={17} />
            <input
              onChange={(event) => setVendorSearch(event.target.value)}
              placeholder="Search vendors..."
              value={vendorSearch}
            />
            {vendorSearch && (
              <button
                aria-label="Clear vendor search"
                onClick={() => setVendorSearch("")}
                title="Clear vendor search"
                type="button"
              >
                <X size={15} />
              </button>
            )}
          </label>
          <div className="vendor-filter-wrap" ref={vendorFilterRef}>
            <button
              aria-expanded={filtersOpen}
              className="icon-button secondary vendor-filter-button vendor-filter-trigger"
              onClick={toggleVendorFilters}
              type="button"
            >
              <Filter size={17} />
              <span>Filter</span>
              <ChevronDown size={16} />
            </button>
            {filtersOpen && (
              <div className="vendor-filter-panel" role="dialog" aria-label="Vendor filters">
                <label>
                  Status
                  <select value={vendorFilterDraft.status} onChange={(event) => updateVendorFilterDraft("status", event.target.value)}>
                    {vendorStatusFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>
                  Service
                  <select value={vendorFilterDraft.service} onChange={(event) => updateVendorFilterDraft("service", event.target.value)}>
                    {vendorServiceFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>
                  Billing cycle
                  <select value={vendorFilterDraft.billingCycle} onChange={(event) => updateVendorFilterDraft("billingCycle", event.target.value)}>
                    {vendorBillingCycleFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <div className="vendor-filter-actions">
                  <button className="vendor-filter-reset" onClick={clearVendorFilters} type="button">
                    <RefreshCw size={15} />
                    <span>Reset</span>
                  </button>
                  <button className="vendor-filter-apply" onClick={applyVendorFilters} type="button">
                    <Filter size={15} />
                    <span>Apply</span>
                  </button>
                </div>
              </div>
            )}
          </div>
          <button
            aria-label="Add vendor"
            className="primary-button vendor-add-button vendor-icon-action"
            disabled={!canAddVendor}
            onClick={openForm}
            type="button"
            title={canAddVendor ? "Add vendor" : "Requires Admin access"}
          >
            <Plus size={18} />
          </button>
        </div>
      </div>
      {toastMessage && <div className={toastType === "error" ? "toast-notification error" : "toast-notification"} role="status">{toastMessage}</div>}
      {!canAddVendor && (
        <div className="status-message vendor-status-message" role="status">
          Requires Admin access to add vendors.
        </div>
      )}
      <section className="dashboard-card vendor-directory-card">
        <VendorTable
          canManage={canAddVendor}
          canSend={canSendVendorMessage}
          emptyDetail={vendors.length ? "Adjust search or filters to show more vendors." : "Add approved business vendors here for the manager demo."}
          emptyTitle={vendors.length ? "No vendors match." : "No vendors added yet."}
          from={filteredVendors.length ? vendorStartIndex + 1 : 0}
          onClose={openCloseConfirmation}
          onEdit={openEdit}
          onPageChange={setVendorPage}
          onReopen={handleReopenVendor}
          onSend={openEmailModal}
          page={currentVendorPage}
          pageCount={vendorPageCount}
          pageNumbers={vendorPaginationPages}
          to={vendorEndIndex}
          total={filteredVendors.length}
          vendors={pagedVendors}
        />
      </section>
      {closingVendor && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-label="Close vendor confirmation">
            <div className="section-heading">
              <h2>Close Vendor</h2>
              <button className="icon-only" onClick={() => setClosingVendor(null)} type="button" aria-label="Cancel close vendor">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-body">
              <p>Are you sure you want to close this vendor?</p>
              <strong>{closingVendor.vendor_name}</strong>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={() => setClosingVendor(null)} type="button">Cancel</button>
              <button className="primary-button danger-action" disabled={saving} onClick={confirmCloseVendor} type="button">
                Close
              </button>
            </div>
          </section>
        </div>
      )}
      {emailVendor && (
        <CommunicationSendModal
          context={{
            detail: "Send a vendor message by Email, WhatsApp, or both.",
            recipient_name: emailVendor.contact_person || emailVendor.vendor_name || "",
            recipient_email: emailVendor.email || "",
            recipient_phone: vendorPhoneForSend(emailVendor),
            subject: emailForm.subject,
            message_body: emailForm.body,
            related_module: "vendors",
            related_record_id: emailVendor.id
          }}
          onClose={closeEmailModal}
          onSent={(response) => {
            setToastType("success");
            setToastMessage(response?.message || "Message sent");
            onChanged();
          }}
          setError={setError}
        />
      )}
      {formOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal" onSubmit={submitVendor} role="dialog" aria-modal="true" aria-label="Add vendor">
            <div className="section-heading">
              <h2>{editingVendor ? "Edit Vendor" : "Add Vendor"}</h2>
              <button className="icon-only" onClick={closeForm} type="button" aria-label="Close add vendor form">
                <X size={16} />
              </button>
            </div>
            <div className="vendor-form-grid">
              <VendorField
                error={formErrors.vendor_name}
                label="Vendor name"
                onChange={updateVendorName}
                value={form.vendor_name}
              />
              <VendorField
                error={formErrors.contact_person}
                label="Contact person"
                onChange={(value) => updateField("contact_person", value)}
                value={form.contact_person}
              />
              <VendorField
                error={formErrors.email}
                label="Email"
                onChange={(value) => updateField("email", value)}
                type="email"
                value={form.email}
              />
              <VendorField
                error={formErrors.contact_details}
                label="Contact details / phone number"
                onChange={(value) => updateField("contact_details", value)}
                value={form.contact_details}
              />
              <label className="vendor-field wide">
                Office address
                <textarea
                  onChange={(event) => updateField("office_address", event.target.value)}
                  rows={3}
                  value={form.office_address}
                />
                {formErrors.office_address && <span>{formErrors.office_address}</span>}
              </label>
              <label className="vendor-field">
                Service provided
                <select
                  onChange={(event) => updateField("service_provided", event.target.value)}
                  value={form.service_provided}
                >
                  <option value="">Choose</option>
                  {vendorServiceOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                {formErrors.service_provided && <span>{formErrors.service_provided}</span>}
              </label>
              <VendorField
                error={formErrors.start_date}
                helper={form.start_date ? `Selected: ${formatDateOnly(form.start_date)}` : "Choose date from calendar"}
                label="Vendor start date"
                onChange={(value) => updateField("start_date", value)}
                type="date"
                value={form.start_date}
              />
              <VendorField
                error={formErrors.end_date}
                helper={form.end_date ? `Selected: ${formatDateOnly(form.end_date)}` : "Optional - choose date from calendar"}
                label="Vendor end date (optional)"
                min={form.start_date || undefined}
                onChange={(value) => updateField("end_date", value)}
                type="date"
                value={form.end_date}
              />
              <VendorField
                error={formErrors.billing_amount}
                inputMode="numeric"
                label="Billing amount"
                onChange={(value) => updateField("billing_amount", value.replace(/\D/g, ""))}
                placeholder="Enter amount"
                value={form.billing_amount}
              />
              <label className="vendor-field">
                Billing cycle
                <select
                  onChange={(event) => updateField("billing_cycle", event.target.value)}
                  value={form.billing_cycle}
                >
                  {billingCycleOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                {formErrors.billing_cycle && <span>{formErrors.billing_cycle}</span>}
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={closeForm} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Saving..." : editingVendor ? "Update Vendor" : "Save Vendor"}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

function VendorField({ error, helper, inputMode, label, maxLength, min, onChange, placeholder = "", type = "text", value }) {
  return (
    <label className="vendor-field">
      {label}
      <input
        inputMode={inputMode}
        maxLength={maxLength}
        min={min}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        type={type}
        value={value}
      />
      {error && <span>{error}</span>}
      {!error && helper && <small>{helper}</small>}
    </label>
  );
}

function VendorTable({
  canManage,
  canSend = canManage,
  emptyDetail = "Add approved business vendors here for the manager demo.",
  emptyTitle = "No vendors added yet.",
  from = 0,
  onClose,
  onEdit,
  onPageChange,
  onReopen,
  onSend,
  page = 1,
  pageCount = 1,
  pageNumbers = [1],
  to = 0,
  total = 0,
  vendors
}) {
  if (!vendors.length) {
    return (
      <EmptyState
        icon={Building2}
        title={emptyTitle}
        detail={emptyDetail}
      />
    );
  }

  return (
    <div className="vendor-table-shell">
      <div className="vendor-table-wrap vendor-list-scroll">
        <table className="vendor-table">
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Contact</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Service</th>
              <th>Start</th>
              <th>End</th>
              <th>Billing</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {vendors.map((vendor) => (
              <tr key={vendor.id}>
                <td><strong>{vendor.vendor_name}</strong></td>
                <td>{vendor.contact_person}</td>
                <td>{vendor.email}</td>
                <td>{vendor.contact_details}</td>
                <td>{vendor.service_provided}</td>
                <td>{formatDateOnly(vendor.start_date)}</td>
                <td>{formatDateOnly(vendor.end_date)}</td>
                <td>{formatVendorBilling(vendor)}</td>
                <td>{labelize(vendor.status).toUpperCase()}</td>
                <td>
                  <div className="table-actions vendor-row-actions">
                    <button
                      aria-label="Edit vendor"
                      className="table-action-button vendor-row-icon-button vendor-action-icon action-edit"
                      disabled={!canManage}
                      onClick={() => onEdit(vendor)}
                      title="Edit vendor"
                      type="button"
                    >
                      <Pencil size={16} />
                    </button>
                    {vendor.status === "closed" ? (
                      <button
                        aria-label="Reopen vendor"
                        className="table-action-button vendor-row-icon-button vendor-action-icon action-reopen"
                        disabled={!canManage}
                        onClick={() => onReopen(vendor)}
                        title="Reopen vendor"
                        type="button"
                      >
                        <RefreshCw size={16} />
                      </button>
                    ) : (
                      <button
                        aria-label="Close vendor"
                        className="table-action-button vendor-row-icon-button vendor-action-icon action-close"
                        disabled={!canManage}
                        onClick={() => onClose(vendor)}
                        title="Close vendor"
                        type="button"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                    <button
                      aria-label="Send message to vendor"
                      className="table-action-button vendor-row-icon-button vendor-action-icon action-send"
                      disabled={!canSend}
                      onClick={() => onSend(vendor)}
                      title={canSend ? "Send message to vendor" : "Requires communication access"}
                      type="button"
                    >
                      <Send size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="vendor-mobile-list">
          {vendors.map((vendor) => (
            <article className="item-card vendor-mobile-card" key={vendor.id}>
              <div className="item-card-header">
                <Building2 size={18} />
                <div>
                  <strong>{vendor.vendor_name}</strong>
                  <p>{vendor.service_provided} • {formatVendorBilling(vendor)}</p>
                </div>
                <span className={vendor.status === "closed" ? "vendor-status-pill closed" : "vendor-status-pill active"}>
                  {labelize(vendor.status).toUpperCase()}
                </span>
              </div>
              <div className="vendor-mobile-meta">
                <span><Mail size={14} />{vendor.email}</span>
                <span><Phone size={14} />{vendor.contact_details}</span>
                <span><MapPin size={14} />{vendor.office_address || "—"}</span>
                <span>{formatDateOnly(vendor.start_date)} - {formatDateOnly(vendor.end_date)}</span>
              </div>
              <button
                aria-label="Edit vendor"
                className="table-action-button vendor-row-icon-button vendor-action-icon action-edit"
                disabled={!canManage}
                onClick={() => onEdit(vendor)}
                title="Edit vendor"
                type="button"
              >
                <Pencil size={16} />
              </button>
              {vendor.status === "closed" ? (
                <button
                  aria-label="Reopen vendor"
                  className="table-action-button vendor-row-icon-button vendor-action-icon action-reopen"
                  disabled={!canManage}
                  onClick={() => onReopen(vendor)}
                  title="Reopen vendor"
                  type="button"
                >
                  <RefreshCw size={16} />
                </button>
              ) : (
                <button
                  aria-label="Close vendor"
                  className="table-action-button vendor-row-icon-button vendor-action-icon action-close"
                  disabled={!canManage}
                  onClick={() => onClose(vendor)}
                  title="Close vendor"
                  type="button"
                >
                  <Trash2 size={16} />
                </button>
              )}
              <button
                aria-label="Send message to vendor"
                className="table-action-button vendor-row-icon-button vendor-action-icon action-send"
                disabled={!canSend}
                onClick={() => onSend(vendor)}
                title={canSend ? "Send message to vendor" : "Requires communication access"}
                type="button"
              >
                <Send size={16} />
              </button>
            </article>
          ))}
        </div>
      </div>
      <div className="vendor-table-footer vendor-list-footer">
        <span>Showing {from} to {to} of {total} vendors</span>
        <div className="pagination-controls" aria-label="Vendor pagination">
          <button
            disabled={page <= 1}
            onClick={() => onPageChange?.(Math.max(1, page - 1))}
            type="button"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          {pageNumbers.map((pageNumber) => (
            <button
              className={pageNumber === page ? "active" : ""}
              key={pageNumber}
              onClick={() => onPageChange?.(pageNumber)}
              type="button"
            >
              {pageNumber}
            </button>
          ))}
          <button
            disabled={page >= pageCount}
            onClick={() => onPageChange?.(Math.min(pageCount, page + 1))}
            type="button"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function InventoryView({ currentUser, inventoryImports, inventoryItems, onChanged, onItemSaved, setError }) {
  const canManageInventory = ["admin", "it_manager"].includes(currentUser.role);
  const fileInputRef = useRef(null);
  const [inventorySearch, setInventorySearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [inventoryFilters, setInventoryFilters] = useState({
    status: "All",
    location: "All"
  });
  const [inventoryPage, setInventoryPage] = useState(1);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const [formOpen, setFormOpen] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [form, setForm] = useState(emptyInventoryForm);
  const [formErrors, setFormErrors] = useState({});
  const [importOpen, setImportOpen] = useState(false);
  const [importPreview, setImportPreview] = useState(null);
  const [selectedImportFileName, setSelectedImportFileName] = useState("");
  const [importError, setImportError] = useState("");
  const [selectedInventoryIds, setSelectedInventoryIds] = useState([]);
  const [inventorySelectionMode, setInventorySelectionMode] = useState("manual");
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [importHistoryOpen, setImportHistoryOpen] = useState(false);
  const [viewingImport, setViewingImport] = useState(null);
  const [viewingImportItems, setViewingImportItems] = useState([]);
  const [deleteImportTarget, setDeleteImportTarget] = useState(null);
  const [saving, setSaving] = useState(false);

  const locationOptions = useMemo(() => {
    const values = Array.from(new Set(inventoryItems.map((item) => item.location).filter(Boolean))).sort();
    return ["All", ...values];
  }, [inventoryItems]);
  const activeFilterCount = Object.values(inventoryFilters).filter((value) => value !== "All").length;
  const filteredInventory = useMemo(() => {
    return inventoryItems.filter((item) => {
      const matchesQuery = inventoryMatchesLocalSearch(item, inventorySearch);
      const matchesStatus = inventoryFilters.status === "All" || normalizeInventoryStatus(item.status) === inventoryFilters.status;
      const matchesLocation = inventoryFilters.location === "All" || item.location === inventoryFilters.location;
      return matchesQuery && matchesStatus && matchesLocation;
    });
  }, [inventoryFilters, inventoryItems, inventorySearch]);
  const inventoryPageCount = Math.max(1, Math.ceil(filteredInventory.length / INVENTORY_PAGE_SIZE));
  const currentInventoryPage = Math.min(inventoryPage, inventoryPageCount);
  const inventoryStartIndex = filteredInventory.length ? (currentInventoryPage - 1) * INVENTORY_PAGE_SIZE : 0;
  const inventoryEndIndex = Math.min(inventoryStartIndex + INVENTORY_PAGE_SIZE, filteredInventory.length);
  const pagedInventory = filteredInventory.slice(inventoryStartIndex, inventoryEndIndex);
  const firstPaginationPage = Math.min(
    Math.max(1, currentInventoryPage - 1),
    Math.max(1, inventoryPageCount - 2)
  );
  const inventoryPaginationPages = Array.from(
    { length: Math.min(3, inventoryPageCount) },
    (_, index) => firstPaginationPage + index
  );
  const filteredInventoryIds = useMemo(() => filteredInventory.map((item) => item.id), [filteredInventory]);
  const selectedInventoryIdSet = useMemo(() => new Set(selectedInventoryIds), [selectedInventoryIds]);
  const filteredInventoryIdSet = useMemo(() => new Set(filteredInventoryIds), [filteredInventoryIds]);
  const selectedVisibleCount = selectedInventoryIds.filter((id) => filteredInventoryIdSet.has(id)).length;
  const currentPageIds = pagedInventory.map((item) => item.id);
  const allCurrentPageSelected = currentPageIds.length > 0 && currentPageIds.every((id) => selectedInventoryIdSet.has(id));
  const allFilteredSelected = filteredInventoryIds.length > 0 && filteredInventoryIds.every((id) => selectedInventoryIdSet.has(id));
  const showSelectAllFilteredPrompt =
    allCurrentPageSelected && filteredInventoryIds.length > currentPageIds.length && !allFilteredSelected;
  const selectedCountLabel = allFilteredSelected && filteredInventoryIds.length > currentPageIds.length
    ? `All ${filteredInventoryIds.length} selected`
    : `${selectedInventoryIds.length} selected`;
  const inventoryStatusSummary = useMemo(() => {
    const summarySource = inventoryItems.filter((item) => {
      const matchesQuery = inventoryMatchesLocalSearch(item, inventorySearch);
      const matchesLocation = inventoryFilters.location === "All" || item.location === inventoryFilters.location;
      return matchesQuery && matchesLocation;
    });

    return inventoryQuickStatusOptions.map((status) => ({
      status,
      count: summarySource.filter((item) => normalizeInventoryStatus(item.status) === status).length
    }));
  }, [inventoryFilters.location, inventoryItems, inventorySearch]);

  useEffect(() => {
    setInventoryPage(1);
    setSelectedInventoryIds([]);
  }, [inventoryFilters, inventorySearch, inventoryItems.length]);

  useEffect(() => {
    const availableIds = new Set(inventoryItems.map((item) => item.id));
    setSelectedInventoryIds((current) => current.filter((id) => availableIds.has(id)));
  }, [inventoryItems]);

  useEffect(() => {
    if (inventoryPage > inventoryPageCount) {
      setInventoryPage(inventoryPageCount);
    }
  }, [inventoryPage, inventoryPageCount]);

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = window.setTimeout(() => setToastMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  function updateInventoryFilter(field, value) {
    setInventoryFilters((current) => ({ ...current, [field]: value }));
  }

  function clearInventoryFilters() {
    setInventoryFilters({
      status: "All",
      location: "All"
    });
  }

  function updateInventoryField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function validateInventoryForm(currentForm = form) {
    const errors = {};
    const required = {
      employee_name: "Employee name",
      serial_no: "Serial No.",
      model_no: "Model No.",
      ram: "RAM",
      disk: "Disk",
      location: "Location",
      status: "Status"
    };
    Object.entries(required).forEach(([key, label]) => {
      if (!String(currentForm[key] ?? "").trim()) {
        errors[key] = `${label} is required`;
      }
    });
    if (currentForm.status && !inventoryStatusOptions.includes(currentForm.status)) {
      errors.status = "Choose a supported status";
    }
    return errors;
  }

  function openAddItem() {
    if (!canManageInventory) return;
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingItem(null);
    setForm(emptyInventoryForm);
    setFormOpen(true);
  }

  function openEditItem(item) {
    if (!canManageInventory) return;
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingItem(item);
    setForm({
      item_id: item.item_id || "",
      employee_name: item.employee_name || item.assigned_to || "",
      serial_no: item.serial_no || item.serial_number || "",
      model_no: item.model_no || item.model || "",
      ram: item.ram || "",
      disk: item.disk || "",
      location: item.location || "",
      status: inventoryStatusOptions.includes(normalizeInventoryStatus(item.status)) ? normalizeInventoryStatus(item.status) : "In Use",
      notes: item.notes || ""
    });
    setFormOpen(true);
  }

  function closeInventoryForm() {
    setFormOpen(false);
    setEditingItem(null);
    setForm(emptyInventoryForm);
    setFormErrors({});
  }

  function toggleInventorySelection(itemId, checked) {
    setInventorySelectionMode("manual");
    setSelectedInventoryIds((current) => {
      if (checked) {
        return current.includes(itemId) ? current : [...current, itemId];
      }
      return current.filter((id) => id !== itemId);
    });
  }

  function toggleCurrentPageSelection(checked) {
    setInventorySelectionMode(checked ? "current_page" : "manual");
    setSelectedInventoryIds((current) => {
      const pageIdSet = new Set(currentPageIds);
      if (!checked) {
        return current.filter((id) => !pageIdSet.has(id));
      }
      return Array.from(new Set([...current, ...currentPageIds]));
    });
  }

  function selectInventoryRange(mode) {
    if (!canManageInventory || !mode) return;
    const limits = {
      current_page: currentPageIds.length,
      first_50: 50,
      first_100: 100,
      all_filtered: filteredInventoryIds.length
    };
    const sourceIds = mode === "current_page" ? currentPageIds : filteredInventoryIds;
    const nextIds = sourceIds.slice(0, limits[mode] || 0);
    setInventorySelectionMode(mode);
    setSelectedInventoryIds(nextIds);
  }

  function selectAllFilteredInventory() {
    setInventorySelectionMode("all_filtered");
    setSelectedInventoryIds(filteredInventoryIds);
  }

  function clearInventorySelection() {
    setInventorySelectionMode("manual");
    setSelectedInventoryIds([]);
  }

  function openDeleteItem(item) {
    if (!canManageInventory) return;
    setToastMessage("");
    setToastType("success");
    setDeleteTarget({ type: "single", item, itemIds: [item.id] });
  }

  function openBulkDelete() {
    if (!canManageInventory || selectedInventoryIds.length === 0) return;
    setToastMessage("");
    setToastType("success");
    setDeleteTarget({
      type: "bulk",
      item: null,
      itemIds: [...selectedInventoryIds],
      selectionMode: inventorySelectionMode,
      search: inventorySearch.trim(),
      filters: { ...inventoryFilters }
    });
  }

  function closeDeleteConfirmation() {
    if (saving) return;
    setDeleteTarget(null);
  }

  async function viewImportItems(batch) {
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      const response = await getInventoryImportItems(batch.id);
      setViewingImport(response.import || batch);
      setViewingImportItems(response.inventory_items || []);
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not load import items: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  function openDeleteImport(batch) {
    if (!canManageInventory) return;
    setToastMessage("");
    setToastType("success");
    setDeleteImportTarget(batch);
  }

  function closeDeleteImportConfirmation() {
    if (saving) return;
    setDeleteImportTarget(null);
  }

  async function confirmDeleteImport() {
    if (!deleteImportTarget) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      await deleteInventoryImport(deleteImportTarget.id);
      await onChanged();
      setViewingImport(null);
      setViewingImportItems([]);
      setDeleteImportTarget(null);
      setSelectedInventoryIds([]);
      setToastType("success");
      setToastMessage("Import batch deleted successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not delete import batch: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function confirmDeleteInventory() {
    if (!deleteTarget) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      if (deleteTarget.type === "single") {
        await deleteInventoryItem(deleteTarget.item.id);
        setSelectedInventoryIds((current) => current.filter((id) => id !== deleteTarget.item.id));
        setToastMessage("Inventory item deleted successfully");
      } else {
        await bulkDeleteInventoryItems(deleteTarget.itemIds, {
          selection_mode: deleteTarget.selectionMode,
          search: deleteTarget.search,
          filters: deleteTarget.filters
        });
        setSelectedInventoryIds([]);
        setInventorySelectionMode("manual");
        setToastMessage("Inventory items deleted successfully");
      }
      await onChanged();
      setDeleteTarget(null);
      setToastType("success");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not delete inventory ${deleteTarget.type === "bulk" ? "items" : "item"}: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function submitInventoryItem(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    const errors = validateInventoryForm();
    setFormErrors(errors);
    if (Object.keys(errors).length) return;
    setSaving(true);
    try {
      const payload = inventoryPayloadFromForm(form);
      const response = editingItem
        ? await updateInventoryItem(editingItem.id, payload)
        : await createInventoryItem(payload);
      if (response?.inventory_item) {
        onItemSaved(response.inventory_item);
      }
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      closeInventoryForm();
      setToastType("success");
      setToastMessage(editingItem ? "Inventory item updated successfully" : "Inventory item added successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not save inventory item: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function updateItemStatus(item, status) {
    if (!canManageInventory) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      const response = await updateInventoryStatus(item.id, status);
      if (response?.inventory_item) {
        onItemSaved(response.inventory_item);
      }
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setToastType("success");
      setToastMessage("Inventory status updated");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not update inventory status: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  function startImport() {
    if (!canManageInventory) return;
    setToastMessage("");
    setToastType("success");
    setSelectedImportFileName("");
    setImportError("");
    setImportPreview(null);
    setImportOpen(true);
  }

  function closeImportModal() {
    if (saving) return;
    setImportOpen(false);
    setSelectedImportFileName("");
    setImportError("");
    setImportPreview(null);
  }

  function chooseImportFile() {
    if (!canManageInventory) return;
    fileInputRef.current?.click();
  }

  async function handleImportFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setToastMessage("");
    setToastType("success");
    setImportError("");
    setImportPreview(null);
    setSelectedImportFileName(file.name);
    const fileName = file.name.toLowerCase();
    const isCsv = fileName.endsWith(".csv");
    const isXlsx = fileName.endsWith(".xlsx");
    const isXls = fileName.endsWith(".xls");
    if (!isCsv && !isXlsx && !isXls) {
      setImportError("Unsupported file type. Please upload a CSV or .xlsx file.");
      return;
    }
    if (isXls) {
      setImportError("Legacy .xls import is not enabled yet. Please use CSV or .xlsx.");
      return;
    }
    if (file.size === 0) {
      setImportError("Selected file is empty.");
      return;
    }
    setSaving(true);
    try {
      const contentBase64 = arrayBufferToBase64(await file.arrayBuffer());
      const preview = await previewInventoryImport(file.name, contentBase64);
      setImportPreview(preview);
      if (preview.errors?.length) {
        const templateError = preview.errors.find((message) => message.includes("does not match the inventory template"));
        setImportError(templateError || "Some rows need attention before import can continue.");
      }
    } catch (err) {
      setImportError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function confirmImport() {
    if (!importPreview || importPreview.errors.length) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      const response = await createInventoryImport(
        selectedImportFileName || importPreview.file_name || "inventory_import.csv",
        importPreview.rows.map((row) => inventoryPayloadFromForm(row.item))
      );
      (response.inventory_items || []).forEach((item) => onItemSaved(item));
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setImportOpen(false);
      setImportPreview(null);
      setImportError("");
      setSelectedImportFileName("");
      setToastType("success");
      const failedRows = response.import?.failed_rows || 0;
      setToastMessage(
        failedRows
          ? `${response.import.successful_rows} inventory items imported; ${failedRows} rows failed`
          : `${response.import?.successful_rows || 0} inventory items imported successfully`
      );
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not import inventory: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="inventory-page vendors-page">
      <div className="vendors-page-header inventory-page-header">
        <div className="page-title inventory-title-block">
          <span className="vendor-directory-icon inventory-page-icon"><Package size={20} /></span>
          <div>
            <div className="inventory-title-row">
              <h1>Inventory</h1>
            </div>
          </div>
        </div>
        <div className="inventory-status-summary" aria-label="Inventory status summary">
          {inventoryStatusSummary.map(({ status, count }) => (
            <button
              aria-label={`Show ${status} inventory items`}
              className={`${inventoryBadgeClass("inventory-summary-card", status)}${inventoryFilters.status === status ? " active" : ""}`}
              key={status}
              onClick={() => updateInventoryFilter("status", status)}
              title={`Show ${status} inventory items`}
              type="button"
            >
              <span className={inventoryBadgeClass("inventory-summary-dot", status)} />
              <span>{status}</span>
              <strong>{count}</strong>
            </button>
          ))}
        </div>
        <div className="vendors-top-action inventory-top-action">
          <label className="vendor-search-control inventory-search-control" aria-label="Search inventory">
            <Search size={17} />
            <input
              onChange={(event) => setInventorySearch(event.target.value)}
              placeholder="Search inventory..."
              value={inventorySearch}
            />
            {inventorySearch && (
              <button aria-label="Clear inventory search" onClick={() => setInventorySearch("")} title="Clear inventory search" type="button">
                <X size={15} />
              </button>
            )}
          </label>
          <div className="vendor-filter-wrap">
            <button
              aria-expanded={filtersOpen}
              className="icon-button secondary vendor-filter-button"
              onClick={() => setFiltersOpen((open) => !open)}
              type="button"
            >
              <Filter size={17} />
              <span>Filter</span>
              {activeFilterCount > 0 && <strong>{activeFilterCount}</strong>}
            </button>
            {filtersOpen && (
              <div className="vendor-filter-panel inventory-filter-panel" role="dialog" aria-label="Inventory filters">
                <label>
                  Status
                  <select value={inventoryFilters.status} onChange={(event) => updateInventoryFilter("status", event.target.value)}>
                    {inventoryStatusFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>
                  Location
                  <select value={inventoryFilters.location} onChange={(event) => updateInventoryFilter("location", event.target.value)}>
                    {locationOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <button className="table-action-button" onClick={clearInventoryFilters} type="button">Clear</button>
              </div>
            )}
          </div>
          <input
            accept=".csv,.xlsx,.xls,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
            className="visually-hidden"
            onChange={handleImportFile}
            ref={fileInputRef}
            type="file"
          />
          <label className="inventory-select-dropdown" aria-label="Bulk select inventory rows">
            <select
              disabled={!canManageInventory || filteredInventory.length === 0}
              onChange={(event) => {
                selectInventoryRange(event.target.value);
                event.target.value = "";
              }}
              value=""
            >
              <option value="">Select</option>
              <option value="current_page">Select current page</option>
              <option value="first_50">Select 50 rows</option>
              <option value="first_100">Select 100 rows</option>
              <option value="all_filtered">Select all rows</option>
            </select>
          </label>
          {selectedInventoryIds.length > 0 && (
            <span className="inventory-selected-count">{selectedCountLabel}</span>
          )}
          {selectedInventoryIds.length > 0 && (
            <button
              aria-label="Delete selected inventory items"
              className="icon-button secondary inventory-delete-selected-button inventory-icon-action"
              disabled={!canManageInventory || saving}
              onClick={openBulkDelete}
              title="Delete selected inventory items"
              type="button"
            >
              <Trash2 size={18} />
            </button>
          )}
          <button
            aria-label="View inventory import history"
            className="icon-button secondary inventory-import-button inventory-icon-action"
            disabled={!canManageInventory}
            onClick={() => setImportHistoryOpen((open) => !open)}
            title="View inventory import history"
            type="button"
          >
            <Clock3 size={18} />
          </button>
          <button
            aria-label="Import inventory"
            className="icon-button secondary inventory-import-button inventory-icon-action"
            disabled={!canManageInventory}
            onClick={startImport}
            title={canManageInventory ? "Import inventory file" : "Requires Admin or IT Manager access"}
            type="button"
          >
            <Upload size={18} />
          </button>
          <button
            aria-label="Add inventory item"
            className="primary-button vendor-add-button inventory-icon-action inventory-add-icon-button"
            disabled={!canManageInventory}
            onClick={openAddItem}
            title={canManageInventory ? "Add inventory item" : "Requires Admin or IT Manager access"}
            type="button"
          >
            <Plus size={18} />
          </button>
        </div>
      </div>
      {toastMessage && <div className={toastType === "error" ? "toast-notification error" : "toast-notification"} role="status">{toastMessage}</div>}
      <section className="dashboard-card vendor-directory-card inventory-directory-card">
        {selectedInventoryIds.length > 0 && (
          <div className="inventory-selection-summary">
            <span>{selectedVisibleCount} selected</span>
            {showSelectAllFilteredPrompt && (
              <button onClick={selectAllFilteredInventory} type="button">
                Select all {filteredInventory.length} inventory items
              </button>
            )}
            {allFilteredSelected && filteredInventory.length > currentPageIds.length && (
              <strong>All {filteredInventory.length} inventory items selected</strong>
            )}
            <button onClick={clearInventorySelection} type="button">Clear selection</button>
          </div>
        )}
        <InventoryTable
          allCurrentPageSelected={allCurrentPageSelected}
          canManage={canManageInventory}
          emptyDetail={inventoryItems.length ? "Adjust search or filters to show more inventory items." : "Add or import inventory items to begin tracking stock."}
          emptyTitle={inventoryItems.length ? "No inventory items match." : "No inventory items yet."}
          from={filteredInventory.length ? inventoryStartIndex + 1 : 0}
          inventoryItems={pagedInventory}
          onDelete={openDeleteItem}
          onEdit={openEditItem}
          onPageChange={setInventoryPage}
          onSelect={toggleInventorySelection}
          onSelectPage={toggleCurrentPageSelection}
          onStatusUpdate={updateItemStatus}
          page={currentInventoryPage}
          pageCount={inventoryPageCount}
          pageNumbers={inventoryPaginationPages}
          selectedIds={selectedInventoryIdSet}
          to={inventoryEndIndex}
          total={filteredInventory.length}
        />
      </section>
      {importHistoryOpen && (
        <section className="dashboard-card vendor-directory-card inventory-history-card">
          <div className="vendor-directory-header">
            <div className="vendor-directory-title">
              <span className="vendor-directory-icon"><Clock3 size={20} /></span>
              <div>
                <h2>Import History</h2>
                <p>Manage uploaded inventory files and remove a full import batch</p>
              </div>
            </div>
            <span className="vendor-count-badge">{inventoryImports.length} Imports</span>
          </div>
          <InventoryImportHistory
            batches={inventoryImports}
            canManage={canManageInventory}
            currentUser={currentUser}
            onDelete={openDeleteImport}
            onViewItems={viewImportItems}
          />
        </section>
      )}
      {formOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal inventory-modal" onSubmit={submitInventoryItem} role="dialog" aria-modal="true" aria-label={editingItem ? "Edit inventory item" : "Add inventory item"}>
            <div className="section-heading">
              <h2>{editingItem ? "Edit Inventory Item" : "Add Inventory Item"}</h2>
              <button className="icon-only" onClick={closeInventoryForm} type="button" aria-label="Close inventory form">
                <X size={16} />
              </button>
            </div>
            <InventoryFormFields form={form} formErrors={formErrors} onChange={updateInventoryField} />
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={closeInventoryForm} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Saving..." : editingItem ? "Update Item" : "Save Item"}
              </button>
            </div>
          </form>
        </div>
      )}
      {deleteTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-label="Delete inventory confirmation">
            <div className="section-heading">
              <h2>{deleteTarget.type === "bulk" ? "Delete Selected Items" : "Delete Inventory Item"}</h2>
              <button className="icon-only" onClick={closeDeleteConfirmation} type="button" aria-label="Cancel inventory delete">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-body">
              <p>
                {deleteTarget.type === "bulk"
                  ? "Are you sure you want to delete selected inventory items?"
                  : "Are you sure you want to delete this inventory item?"}
              </p>
              {deleteTarget.type === "single" && (
                <strong>{deleteTarget.item.employee_name || deleteTarget.item.assigned_to || deleteTarget.item.serial_no || deleteTarget.item.item_name}</strong>
              )}
              {deleteTarget.type === "bulk" && <strong>This will delete {deleteTarget.itemIds.length} inventory items.</strong>}
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" disabled={saving} onClick={closeDeleteConfirmation} type="button">Cancel</button>
              <button className="primary-button danger-action" disabled={saving} onClick={confirmDeleteInventory} type="button">
                {saving ? "Deleting..." : "Delete"}
              </button>
            </div>
          </section>
        </div>
      )}
      {deleteImportTarget && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal import-delete-modal" role="dialog" aria-modal="true" aria-label="Delete inventory import confirmation">
            <div className="section-heading">
              <h2>Delete Import</h2>
              <button className="icon-only" onClick={closeDeleteImportConfirmation} type="button" aria-label="Cancel import delete">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-body">
              <p>Are you sure you want to delete all inventory items imported from this file?</p>
              <strong>{deleteImportTarget.file_name}</strong>
              {deleteImportTarget.is_legacy_unbatched && (
                <p className="import-warning">Legacy unbatched inventory can include manually added items created before batch tracking.</p>
              )}
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" disabled={saving} onClick={closeDeleteImportConfirmation} type="button">Cancel</button>
              <button className="primary-button danger-action" disabled={saving} onClick={confirmDeleteImport} type="button">
                {saving ? "Deleting..." : "Delete Import"}
              </button>
            </div>
          </section>
        </div>
      )}
      {viewingImport && (
        <div className="modal-backdrop" role="presentation">
          <section className="vendor-modal inventory-preview-modal" role="dialog" aria-modal="true" aria-label="Imported inventory items">
            <div className="section-heading">
              <h2>{viewingImport.file_name}</h2>
              <button className="icon-only" onClick={() => { setViewingImport(null); setViewingImportItems([]); }} type="button" aria-label="Close imported items">
                <X size={16} />
              </button>
            </div>
            <div className="import-summary">
              <span className="status-pill success">{viewingImportItems.length} items</span>
              <span className="status-pill">{viewingImport.status}</span>
            </div>
            <InventoryImportedItemsTable items={viewingImportItems} />
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={() => { setViewingImport(null); setViewingImportItems([]); }} type="button">Close</button>
            </div>
          </section>
        </div>
      )}
      {importOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="vendor-modal inventory-preview-modal inventory-import-modal" role="dialog" aria-modal="true" aria-label="Import inventory">
            <div className="section-heading">
              <h2>Import Inventory</h2>
              <button className="icon-only" onClick={closeImportModal} type="button" aria-label="Close import inventory">
                <X size={16} />
              </button>
            </div>
            <div className="inventory-upload-area">
              <div>
                <strong>{selectedImportFileName || "No file selected"}</strong>
                <span>Supported formats: CSV and .xlsx. Legacy .xls can be selected but is not enabled yet.</span>
                <p>Use the sample template to avoid import errors.</p>
              </div>
              <div className="inventory-upload-actions">
                <button className="icon-button secondary inventory-choose-file-button" disabled={saving} onClick={chooseImportFile} type="button">
                  <Upload size={17} />
                  <span>{selectedImportFileName ? "Replace File" : "Choose File"}</span>
                </button>
                <button className="table-action-button inventory-template-button" onClick={downloadInventoryTemplate} type="button">
                  <FileText size={15} />
                  <span>Download Sample Template</span>
                </button>
              </div>
            </div>
            {importError && <div className="import-inline-error" role="alert">{importError}</div>}
            {saving && !importPreview && <p className="empty import-loading">Parsing selected file...</p>}
            {importPreview && (
              <>
                <div className="import-summary">
                  <span className="status-pill success">{importPreview.rows.length} rows</span>
                  <span className={importPreview.errors.length ? "status-pill danger" : "status-pill success"}>{importPreview.errors.length} errors</span>
                  <span className={importPreview.warnings.length ? "status-pill warning" : "status-pill success"}>{importPreview.warnings.length} warnings</span>
                </div>
                {importPreview.detected_columns?.length > 0 && (
                  <div className="import-detected-columns">
                    <strong>Detected columns:</strong>
                    <span>{importPreview.detected_columns.join(", ")}</span>
                    {importPreview.header_row_number && <em>Header row {importPreview.header_row_number}</em>}
                  </div>
                )}
                {(importPreview.errors.length > 0 || importPreview.warnings.length > 0) && (
                  <div className="import-messages">
                    {importPreview.errors.map((message) => <p className="import-error" key={message}>{message}</p>)}
                    {importPreview.warnings.map((message) => <p className="import-warning" key={message}>{message}</p>)}
                  </div>
                )}
                <div className="vendor-table-wrap inventory-preview-wrap">
                  <table className="vendor-table inventory-preview-table">
                    <thead>
                      <tr>
                        <th>Employee Name</th>
                        <th>Serial No.</th>
                        <th>Model No.</th>
                        <th>RAM</th>
                        <th>Disk</th>
                        <th>Location</th>
                        <th>Status</th>
                        <th>Notes</th>
                        <th>Validation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {importPreview.rows.map((row) => (
                        <tr key={row.rowNumber}>
                          <td><strong>{row.item.employee_name || row.item.assigned_to || "—"}</strong></td>
                          <td>{row.item.serial_no || row.item.serial_number || "—"}</td>
                          <td>{row.item.model_no || row.item.model || "—"}</td>
                          <td>{row.item.ram || "—"}</td>
                          <td>{row.item.disk || "—"}</td>
                          <td>{row.item.location || "—"}</td>
                          <td>{row.item.status || "In Use"}</td>
                          <td className="inventory-notes-cell">{row.item.notes || "—"}</td>
                          <td>
                            <span className={row.errors.length ? "status-pill danger" : row.warnings.length ? "status-pill warning" : "status-pill success"}>
                              {row.errors.length ? "Error" : row.warnings.length ? "Warning" : "Ready"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            <div className="modal-actions">
              <button className="icon-button secondary" disabled={saving} onClick={closeImportModal} type="button">Cancel</button>
              <button className="primary-button" disabled={saving || !importPreview || importPreview.errors.length > 0 || importPreview.rows.length === 0} onClick={confirmImport} type="button">
                {saving ? "Importing..." : "Confirm Import"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

function InventoryFormFields({ form, formErrors, onChange }) {
  return (
    <div className="vendor-form-grid inventory-form-grid">
      <VendorField error={formErrors.employee_name} label="Employee Name" onChange={(value) => onChange("employee_name", value)} value={form.employee_name} />
      <VendorField error={formErrors.serial_no} label="Serial No." onChange={(value) => onChange("serial_no", value)} value={form.serial_no} />
      <VendorField error={formErrors.model_no} label="Model No." onChange={(value) => onChange("model_no", value)} value={form.model_no} />
      <VendorField error={formErrors.ram} label="RAM" onChange={(value) => onChange("ram", value)} value={form.ram} />
      <VendorField error={formErrors.disk} label="Disk" onChange={(value) => onChange("disk", value)} value={form.disk} />
      <VendorField error={formErrors.location} label="Location" onChange={(value) => onChange("location", value)} value={form.location} />
      <label className="vendor-field">
        Status
        <select value={form.status} onChange={(event) => onChange("status", event.target.value)}>
          {inventoryStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
        {formErrors.status && <span>{formErrors.status}</span>}
      </label>
      <label className="vendor-field wide">
        Notes
        <textarea rows={3} value={form.notes} onChange={(event) => onChange("notes", event.target.value)} />
        {formErrors.notes && <span>{formErrors.notes}</span>}
      </label>
    </div>
  );
}

function InventoryImportHistory({ batches, canManage, currentUser, onDelete, onViewItems }) {
  if (!batches.length) {
    return <EmptyState icon={Clock3} title="No imports yet." detail="Uploaded CSV and .xlsx inventory files will appear here." />;
  }
  return (
    <div className="vendor-table-wrap inventory-import-history-wrap">
      <table className="vendor-table inventory-import-history-table">
        <thead>
          <tr>
            <th>File name</th>
            <th>Imported by</th>
            <th>Imported date</th>
            <th>Items imported</th>
            <th>Failed rows</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {batches.map((batch) => {
            const canDeleteBatch = canManage && (!batch.is_legacy_unbatched || currentUser.role === "admin");
            return (
              <tr key={batch.id}>
                <td>
                  <strong>{batch.file_name}</strong>
                  {batch.notes && <p className="import-history-note">{batch.notes}</p>}
                </td>
                <td>{batch.imported_by_name || "—"}</td>
                <td>{batch.imported_at ? formatDate(batch.imported_at) : "—"}</td>
                <td>{batch.successful_rows}</td>
                <td>{batch.failed_rows}</td>
                <td><span className={inventoryImportStatusClass(batch.status)}>{batch.status}</span></td>
                <td>
                  <div className="table-actions">
                    <button className="table-action-button action-view" onClick={() => onViewItems(batch)} type="button">
                      <Eye size={14} />
                      <span>View Items</span>
                    </button>
                    <button
                      className="table-action-button action-close"
                      disabled={!canDeleteBatch || batch.status === "Deleted"}
                      onClick={() => onDelete(batch)}
                      title={canDeleteBatch ? "Delete import batch" : "Legacy cleanup requires Admin access"}
                      type="button"
                    >
                      <Trash2 size={14} />
                      <span>{batch.is_legacy_unbatched ? "Delete Unbatched" : "Delete Import"}</span>
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function InventoryImportedItemsTable({ items }) {
  if (!items.length) {
    return <EmptyState icon={Package} title="No items in this import." detail="This import batch has no active inventory items." />;
  }
  return (
    <div className="vendor-table-wrap inventory-preview-wrap">
      <table className="vendor-table inventory-preview-table">
        <thead>
          <tr>
            <th>Employee Name</th>
            <th>Serial No.</th>
            <th>Model No.</th>
            <th>RAM</th>
            <th>Disk</th>
            <th>Location</th>
            <th>Status</th>
            <th>Notes</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td><strong>{item.employee_name || item.assigned_to || "—"}</strong></td>
              <td>{item.serial_no || item.serial_number || "—"}</td>
              <td>{item.model_no || item.model || "—"}</td>
              <td>{item.ram || "—"}</td>
              <td>{item.disk || "—"}</td>
              <td>{item.location}</td>
              <td>{item.status}</td>
              <td className="inventory-notes-cell">{item.notes || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InventoryTable({
  allCurrentPageSelected = false,
  canManage,
  emptyDetail,
  emptyTitle,
  from = 0,
  inventoryItems,
  onDelete,
  onEdit,
  onPageChange,
  onSelect,
  onSelectPage,
  onStatusUpdate,
  page = 1,
  pageCount = 1,
  pageNumbers = [1],
  selectedIds = new Set(),
  to = 0,
  total = 0
}) {
  const [pageJumpValue, setPageJumpValue] = useState("");
  const [pageJumpError, setPageJumpError] = useState("");
  const [statusMenuItemId, setStatusMenuItemId] = useState(null);

  function submitPageJump(event) {
    event.preventDefault();
    const targetPage = Number.parseInt(String(pageJumpValue).trim(), 10);
    if (!Number.isInteger(targetPage) || targetPage < 1 || targetPage > pageCount) {
      setPageJumpError("Page not found");
      return;
    }
    setPageJumpError("");
    onPageChange?.(targetPage);
    setPageJumpValue("");
  }

  if (!inventoryItems.length) {
    return <EmptyState icon={Package} title={emptyTitle} detail={emptyDetail} />;
  }
  return (
    <div className="inventory-table-shell">
      <div className="vendor-table-wrap inventory-table-wrap">
        <table className="vendor-table inventory-table">
          <thead>
            <tr>
              <th className="inventory-select-column">
                <input
                  aria-label="Select current inventory page"
                  checked={allCurrentPageSelected}
                  disabled={!canManage}
                  onChange={(event) => onSelectPage?.(event.target.checked)}
                  type="checkbox"
                />
              </th>
              <th>Employee Name</th>
              <th>Serial No.</th>
              <th>Model No.</th>
              <th>RAM</th>
              <th>Disk</th>
              <th>Location</th>
              <th>Status</th>
              <th>Notes</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {inventoryItems.map((item) => (
              <tr key={item.id}>
                <td className="inventory-select-column">
                  <input
                    aria-label={`Select ${item.employee_name || item.assigned_to || item.item_name}`}
                    checked={selectedIds.has(item.id)}
                    disabled={!canManage}
                    onChange={(event) => onSelect?.(item.id, event.target.checked)}
                    type="checkbox"
                  />
                </td>
                <td><strong>{item.employee_name || item.assigned_to || "—"}</strong></td>
                <td>{item.serial_no || item.serial_number || "—"}</td>
                <td>{item.model_no || item.model || "—"}</td>
                <td>{item.ram || "—"}</td>
                <td>{item.disk || "—"}</td>
                <td>{item.location}</td>
                <td><span className="inventory-status-text">{item.status}</span></td>
                <td className="inventory-notes-cell">{item.notes || "—"}</td>
                <td>
                  <div className="table-actions inventory-row-actions">
                    <button
                      aria-label="Edit item"
                      className="table-action-button inventory-row-icon-button inventory-action-icon inventory-row-edit-button"
                      disabled={!canManage}
                      onClick={() => onEdit(item)}
                      title={canManage ? "Edit item" : "Requires Admin or IT Manager access"}
                      type="button"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      aria-label="Delete item"
                      className="table-action-button inventory-row-icon-button inventory-action-icon inventory-row-delete-button"
                      disabled={!canManage}
                      onClick={() => onDelete(item)}
                      title={canManage ? "Delete item" : "Requires Admin or IT Manager access"}
                      type="button"
                    >
                      <Trash2 size={16} />
                    </button>
                    <div className="inventory-status-action-wrap">
                      <button
                        aria-expanded={statusMenuItemId === item.id}
                        aria-label="Update status"
                        className="table-action-button inventory-row-icon-button inventory-action-icon inventory-row-status-button"
                        disabled={!canManage}
                        onClick={() => setStatusMenuItemId((current) => current === item.id ? null : item.id)}
                        title={canManage ? "Update status" : "Requires Admin or IT Manager access"}
                        type="button"
                      >
                        <RefreshCw size={16} />
                      </button>
                      {statusMenuItemId === item.id && (
                        <div className="inventory-status-menu" role="menu" aria-label={`Update ${item.employee_name || item.assigned_to || item.item_name} status`}>
                          {inventoryQuickStatusOptions.map((status) => (
                            <button
                              key={status}
                              onClick={() => {
                                onStatusUpdate?.(item, status);
                                setStatusMenuItemId(null);
                              }}
                              role="menuitem"
                              type="button"
                            >
                              {status}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="vendor-table-footer inventory-table-footer">
        <div className="inventory-page-info">
          <span>Showing {from} to {to} of {total} items</span>
        </div>
        <form className="inventory-pagination-controls" onSubmit={submitPageJump} aria-label="Inventory pagination">
          <strong className="inventory-current-page">Page {page} of {pageCount}</strong>
          <button disabled={page <= 1} onClick={() => onPageChange?.(Math.max(1, page - 1))} type="button" aria-label="Previous page">
            <ChevronLeft size={16} />
          </button>
          <label>
            <span className="visually-hidden">Go to inventory page</span>
            <input
              aria-label="Go to inventory page"
              inputMode="numeric"
              min="1"
              onChange={(event) => {
                setPageJumpValue(event.target.value.replace(/\D/g, ""));
                setPageJumpError("");
              }}
              placeholder="Go to page..."
              type="text"
              value={pageJumpValue}
            />
          </label>
          <button type="submit" aria-label="Go to page">
            <Search size={16} />
          </button>
          <button disabled={page >= pageCount} onClick={() => onPageChange?.(Math.min(pageCount, page + 1))} type="button" aria-label="Next page">
            <ChevronRight size={16} />
          </button>
          {pageJumpError && <span className="inventory-page-error" role="alert">{pageJumpError}</span>}
        </form>
      </div>
    </div>
  );
}

function TravelCalendarView({
  calendarEvents,
  currentUser,
  onCalendarEventSaved,
  onChanged,
  onTravelRecordSaved,
  setError,
  summary,
  travelRecords
}) {
  const [travelSearch, setTravelSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState({
    department: "All",
    approvalStatus: "All",
    policyStatus: "All",
    travelMode: "All",
    startDate: "",
    endDate: ""
  });
  const [travelPage, setTravelPage] = useState(1);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const [travelFormOpen, setTravelFormOpen] = useState(false);
  const [eventFormOpen, setEventFormOpen] = useState(false);
  const [editingTravel, setEditingTravel] = useState(null);
  const [editingEvent, setEditingEvent] = useState(null);
  const [travelForm, setTravelForm] = useState(emptyTravelForm);
  const [eventForm, setEventForm] = useState(emptyCalendarEventForm);
  const [formErrors, setFormErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const activeFilterCount = Object.values(filters).filter((value) => value && value !== "All").length;

  const filteredTravel = useMemo(() => {
    return travelRecords.filter((record) => {
      const matchesQuery = travelMatchesLocalSearch(record, travelSearch);
      const matchesDepartment = filters.department === "All" || record.department === filters.department;
      const matchesApproval = filters.approvalStatus === "All" || record.approval_status === filters.approvalStatus;
      const matchesPolicy = filters.policyStatus === "All" || record.policy_status === filters.policyStatus;
      const matchesMode = filters.travelMode === "All" || record.travel_mode === filters.travelMode;
      const start = String(record.travel_start_date || "").slice(0, 10);
      const matchesStart = !filters.startDate || start >= filters.startDate;
      const matchesEnd = !filters.endDate || start <= filters.endDate;
      return matchesQuery && matchesDepartment && matchesApproval && matchesPolicy && matchesMode && matchesStart && matchesEnd;
    });
  }, [filters, travelRecords, travelSearch]);

  const travelByTravelId = useMemo(() => {
    const lookup = new Map();
    travelRecords.forEach((record) => lookup.set(record.travel_id, record));
    return lookup;
  }, [travelRecords]);

  const filteredEvents = useMemo(() => {
    return calendarEvents.filter((event) => {
      const relatedTravel = travelByTravelId.get(event.related_travel_id) || {};
      const matchesQuery = travelMatchesLocalSearch({ ...relatedTravel, ...event }, travelSearch);
      const matchesDepartment = filters.department === "All" || relatedTravel.department === filters.department;
      const matchesApproval = filters.approvalStatus === "All" || relatedTravel.approval_status === filters.approvalStatus;
      const matchesPolicy = filters.policyStatus === "All" || relatedTravel.policy_status === filters.policyStatus;
      const matchesMode = filters.travelMode === "All" || relatedTravel.travel_mode === filters.travelMode;
      const start = String(event.start_datetime || "").slice(0, 10);
      const matchesStart = !filters.startDate || start >= filters.startDate;
      const matchesEnd = !filters.endDate || start <= filters.endDate;
      return matchesQuery && matchesDepartment && matchesApproval && matchesPolicy && matchesMode && matchesStart && matchesEnd;
    });
  }, [calendarEvents, filters, travelByTravelId, travelSearch]);

  const travelPageCount = Math.max(1, Math.ceil(filteredTravel.length / TRAVEL_PAGE_SIZE));
  const currentTravelPage = Math.min(travelPage, travelPageCount);
  const travelStartIndex = filteredTravel.length ? (currentTravelPage - 1) * TRAVEL_PAGE_SIZE : 0;
  const travelEndIndex = Math.min(travelStartIndex + TRAVEL_PAGE_SIZE, filteredTravel.length);
  const pagedTravel = filteredTravel.slice(travelStartIndex, travelEndIndex);

  useEffect(() => {
    setTravelPage(1);
  }, [filters, travelSearch, travelRecords.length]);

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = window.setTimeout(() => setToastMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({
      department: "All",
      approvalStatus: "All",
      policyStatus: "All",
      travelMode: "All",
      startDate: "",
      endDate: ""
    });
  }

  function updateTravelField(field, value) {
    setTravelForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function updateEventField(field, value) {
    setEventForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function openTravelForm(record = null) {
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingTravel(record);
    setTravelForm(record ? {
      travel_id: record.travel_id || "",
      employee_name: record.employee_name || "",
      employee_email: record.employee_email || "",
      department: record.department || "Admin",
      destination_from: record.destination_from || "",
      destination_to: record.destination_to || "",
      travel_start_date: String(record.travel_start_date || "").slice(0, 10),
      travel_end_date: String(record.travel_end_date || "").slice(0, 10),
      purpose: record.purpose || "",
      travel_mode: record.travel_mode || "Flight",
      estimated_budget: String(record.estimated_budget ?? ""),
      actual_spend: String(record.actual_spend ?? ""),
      number_of_trips: String(record.number_of_trips || 1),
      approval_status: record.approval_status || "Draft",
      policy_status: record.policy_status || "Within Policy",
      booking_status: record.booking_status || "Draft",
      notes: record.notes || "",
      google_calendar_event_id: record.google_calendar_event_id || "",
      google_sync_status: record.google_sync_status || "Not Synced",
      google_last_synced_at: toDateTimeLocalValue(record.google_last_synced_at)
    } : {
      ...emptyTravelForm,
      employee_name: currentUser.name,
      employee_email: currentUser.email,
      department: currentUser.role === "finance_manager" ? "Finance" : "Admin",
      travel_start_date: new Date().toISOString().slice(0, 10),
      travel_end_date: new Date().toISOString().slice(0, 10)
    });
    setTravelFormOpen(true);
  }

  function closeTravelForm() {
    setTravelFormOpen(false);
    setEditingTravel(null);
    setTravelForm(emptyTravelForm);
    setFormErrors({});
  }

  function openEventForm(event = null) {
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingEvent(event);
    const now = new Date();
    const later = new Date(now.getTime() + 60 * 60 * 1000);
    setEventForm(event ? {
      event_id: event.event_id || "",
      title: event.title || "",
      event_type: event.event_type || "Meeting",
      start_datetime: toDateTimeLocalValue(event.start_datetime),
      end_datetime: toDateTimeLocalValue(event.end_datetime),
      location: event.location || "",
      attendees: event.attendees || "",
      related_travel_id: event.related_travel_id || "",
      reminder: event.reminder || "",
      notes: event.notes || "",
      status: event.status || "Scheduled",
      google_calendar_event_id: event.google_calendar_event_id || "",
      google_sync_status: event.google_sync_status || "Not Synced",
      google_last_synced_at: toDateTimeLocalValue(event.google_last_synced_at)
    } : {
      ...emptyCalendarEventForm,
      start_datetime: now.toISOString().slice(0, 16),
      end_datetime: later.toISOString().slice(0, 16)
    });
    setEventFormOpen(true);
  }

  function closeEventForm() {
    setEventFormOpen(false);
    setEditingEvent(null);
    setEventForm(emptyCalendarEventForm);
    setFormErrors({});
  }

  function validateTravelForm() {
    const errors = {};
    if (!travelForm.employee_name.trim()) errors.employee_name = "Required";
    if (!travelForm.employee_email.trim()) errors.employee_email = "Required";
    if (travelForm.employee_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(travelForm.employee_email)) errors.employee_email = "Enter a valid email";
    if (!travelForm.department.trim()) errors.department = "Required";
    if (!travelForm.destination_from.trim()) errors.destination_from = "Required";
    if (!travelForm.destination_to.trim()) errors.destination_to = "Required";
    if (!travelForm.travel_start_date || !isValidIsoDate(travelForm.travel_start_date)) errors.travel_start_date = "Choose a valid start date";
    if (!travelForm.travel_end_date || !isValidIsoDate(travelForm.travel_end_date)) errors.travel_end_date = "Choose a valid end date";
    if (travelForm.travel_start_date && travelForm.travel_end_date && travelForm.travel_end_date < travelForm.travel_start_date) errors.travel_end_date = "End date must be after start";
    if (!travelForm.purpose.trim()) errors.purpose = "Required";
    if (Number(travelForm.estimated_budget) < 0) errors.estimated_budget = "Budget cannot be negative";
    if (Number(travelForm.actual_spend) < 0) errors.actual_spend = "Spend cannot be negative";
    if (Number(travelForm.number_of_trips) < 1) errors.number_of_trips = "At least 1 trip";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  function validateEventForm() {
    const errors = {};
    if (!eventForm.title.trim()) errors.title = "Required";
    if (!eventForm.start_datetime) errors.start_datetime = "Required";
    if (!eventForm.end_datetime) errors.end_datetime = "Required";
    if (eventForm.start_datetime && eventForm.end_datetime && eventForm.end_datetime < eventForm.start_datetime) errors.end_datetime = "End time must be after start";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function submitTravelForm(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    if (!validateTravelForm()) return;
    setSaving(true);
    try {
      const payload = {
        ...travelForm,
        travel_id: travelForm.travel_id.trim(),
        employee_name: travelForm.employee_name.trim(),
        employee_email: travelForm.employee_email.trim().toLowerCase(),
        department: travelForm.department.trim(),
        destination_from: travelForm.destination_from.trim(),
        destination_to: travelForm.destination_to.trim(),
        purpose: travelForm.purpose.trim(),
        estimated_budget: Number(travelForm.estimated_budget || 0),
        actual_spend: Number(travelForm.actual_spend || 0),
        number_of_trips: Number(travelForm.number_of_trips || 1),
        notes: travelForm.notes.trim(),
        google_calendar_event_id: travelForm.google_calendar_event_id.trim(),
        google_sync_status: travelForm.google_sync_status.trim() || "Not Synced",
        google_last_synced_at: travelForm.google_last_synced_at || null
      };
      const response = editingTravel
        ? await updateTravelRecord(editingTravel.id, payload)
        : await createTravelRecord(payload);
      if (response?.travel_record) onTravelRecordSaved(response.travel_record);
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      closeTravelForm();
      setToastType("success");
      setToastMessage(editingTravel ? "Travel record updated successfully" : "Travel record created successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not save travel record: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function submitEventForm(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    if (!validateEventForm()) return;
    setSaving(true);
    try {
      const payload = {
        ...eventForm,
        event_id: eventForm.event_id.trim(),
        title: eventForm.title.trim(),
        location: eventForm.location.trim(),
        attendees: eventForm.attendees.trim(),
        related_travel_id: eventForm.related_travel_id.trim(),
        reminder: eventForm.reminder.trim(),
        notes: eventForm.notes.trim(),
        google_calendar_event_id: eventForm.google_calendar_event_id.trim(),
        google_sync_status: eventForm.google_sync_status.trim() || "Not Synced",
        google_last_synced_at: eventForm.google_last_synced_at || null
      };
      const response = editingEvent
        ? await updateCalendarEvent(editingEvent.id, payload)
        : await createCalendarEvent(payload);
      if (response?.calendar_event) onCalendarEventSaved(response.calendar_event);
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      closeEventForm();
      setToastType("success");
      setToastMessage(editingEvent ? "Calendar event updated successfully" : "Calendar event created successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not save calendar event: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  const cards = summary?.cards || {};
  const reports = summary || {};

  return (
    <section className="travel-page screen-stack">
      {toastMessage && <div className={toastType === "error" ? "toast-notification error" : "toast-notification"} role="status">{toastMessage}</div>}
      <div className="travel-page-header">
        <div className="vendor-directory-title">
          <span className="vendor-directory-icon"><Plane size={20} /></span>
          <div>
            <h1>Travel & Calendar</h1>
            <p>Internal travel records and calendar coordination, ready for future Google API sync.</p>
          </div>
        </div>
        <div className="ticket-action-row travel-action-row">
          <label className="vendor-search-control ticket-search-control" aria-label="Search travel and calendar">
            <Search size={17} />
            <input
              onChange={(event) => setTravelSearch(event.target.value)}
              placeholder="Search travel..."
              value={travelSearch}
            />
            {travelSearch && (
              <button aria-label="Clear travel search" onClick={() => setTravelSearch("")} title="Clear travel search" type="button">
                <X size={15} />
              </button>
            )}
          </label>
          <div className="vendor-filter-wrap">
            <button
              aria-expanded={filtersOpen}
              className="icon-button secondary vendor-filter-button"
              onClick={() => setFiltersOpen((open) => !open)}
              type="button"
            >
              <Filter size={17} />
              <span>Filter</span>
              {activeFilterCount > 0 && <strong>{activeFilterCount}</strong>}
            </button>
            {filtersOpen && (
              <div className="vendor-filter-panel travel-filter-panel" role="dialog" aria-label="Travel filters">
                <label>
                  Department
                  <select value={filters.department} onChange={(event) => updateFilter("department", event.target.value)}>
                    {travelDepartmentFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>
                  Travel status
                  <select value={filters.approvalStatus} onChange={(event) => updateFilter("approvalStatus", event.target.value)}>
                    {travelStatusFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>
                  Policy status
                  <select value={filters.policyStatus} onChange={(event) => updateFilter("policyStatus", event.target.value)}>
                    {travelPolicyFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label>
                  Travel mode
                  <select value={filters.travelMode} onChange={(event) => updateFilter("travelMode", event.target.value)}>
                    {travelModeFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <VendorField label="From date" onChange={(value) => updateFilter("startDate", value)} type="date" value={filters.startDate} />
                <VendorField label="To date" onChange={(value) => updateFilter("endDate", value)} type="date" value={filters.endDate} />
                <button className="table-action-button" onClick={clearFilters} type="button">Clear</button>
              </div>
            )}
          </div>
          <button className="icon-button secondary" onClick={() => openEventForm()} type="button">
            <CalendarDays size={17} />
            <span>Add Calendar Event</span>
          </button>
          <button className="primary-button vendor-add-button" onClick={() => openTravelForm()} type="button">
            <Plus size={18} />
            <span>Add Travel Record</span>
          </button>
        </div>
      </div>

      <div className="ops-summary-row travel-summary-row">
        <Metric label="Total travel spend" value={formatMoney(cards.total_travel_spend || 0)} icon={DollarSign} />
        <Metric label="Upcoming trips" value={cards.upcoming_trips || 0} icon={Plane} />
        <Metric label="Currently traveling" value={cards.currently_traveling_employees || 0} icon={MapPin} />
        <Metric label="Pending approvals" value={cards.pending_travel_approvals || 0} icon={ShieldAlert} />
        <Metric label="Over-budget travel" value={cards.over_budget_travel || 0} icon={ShieldCheck} />
        <Metric label="Today's events" value={cards.todays_calendar_events || 0} icon={CalendarDays} />
      </div>

      <section className="dashboard-card vendor-directory-card">
        <div className="vendor-directory-header">
          <div className="vendor-directory-title">
            <span className="vendor-directory-icon"><Plane size={20} /></span>
            <div>
              <h2>Travel Records</h2>
              <p>Who is traveling, where they are going, and what is being spent</p>
            </div>
          </div>
          <span className="vendor-count-badge">{filteredTravel.length} Records</span>
        </div>
        <TravelRecordsTable
          from={filteredTravel.length ? travelStartIndex + 1 : 0}
          onEdit={openTravelForm}
          onPageChange={setTravelPage}
          page={currentTravelPage}
          pageCount={travelPageCount}
          records={pagedTravel}
          to={travelEndIndex}
          total={filteredTravel.length}
        />
      </section>

      <section className="dashboard-card vendor-directory-card">
        <div className="vendor-directory-header">
          <div className="vendor-directory-title">
            <span className="vendor-directory-icon"><CalendarDays size={20} /></span>
            <div>
              <h2>Calendar Events</h2>
              <p>Internal meetings, reminders, and travel-linked events</p>
            </div>
          </div>
          <span className="vendor-count-badge">{filteredEvents.length} Events</span>
        </div>
        <CalendarEventsTable events={filteredEvents} onEdit={openEventForm} />
      </section>

      <TravelReports summary={reports} />

      {travelFormOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal travel-modal" onSubmit={submitTravelForm} role="dialog" aria-modal="true" aria-label="Travel record">
            <div className="section-heading">
              <h2>{editingTravel ? "Edit Travel Record" : "Add Travel Record"}</h2>
              <button className="icon-only" onClick={closeTravelForm} type="button" aria-label="Close travel form">
                <X size={16} />
              </button>
            </div>
            <div className="vendor-form-grid">
              <VendorField label="Travel ID" onChange={(value) => updateTravelField("travel_id", value)} placeholder="Auto-generated if blank" value={travelForm.travel_id} />
              <VendorField error={formErrors.employee_name} label="Employee name" onChange={(value) => updateTravelField("employee_name", value)} value={travelForm.employee_name} />
              <VendorField error={formErrors.employee_email} label="Employee email" onChange={(value) => updateTravelField("employee_email", value)} type="email" value={travelForm.employee_email} />
              <VendorField error={formErrors.department} label="Department" onChange={(value) => updateTravelField("department", value)} value={travelForm.department} />
              <VendorField error={formErrors.destination_from} label="Destination from" onChange={(value) => updateTravelField("destination_from", value)} value={travelForm.destination_from} />
              <VendorField error={formErrors.destination_to} label="Destination to" onChange={(value) => updateTravelField("destination_to", value)} value={travelForm.destination_to} />
              <VendorField error={formErrors.travel_start_date} helper={travelForm.travel_start_date ? `Selected: ${formatDateOnly(travelForm.travel_start_date)}` : "Choose start date"} label="Travel start date" onChange={(value) => updateTravelField("travel_start_date", value)} type="date" value={travelForm.travel_start_date} />
              <VendorField error={formErrors.travel_end_date} helper={travelForm.travel_end_date ? `Selected: ${formatDateOnly(travelForm.travel_end_date)}` : "Choose end date"} label="Travel end date" onChange={(value) => updateTravelField("travel_end_date", value)} type="date" value={travelForm.travel_end_date} />
              <VendorField error={formErrors.purpose} label="Purpose" onChange={(value) => updateTravelField("purpose", value)} value={travelForm.purpose} />
              <label className="vendor-field">
                Travel mode
                <select onChange={(event) => updateTravelField("travel_mode", event.target.value)} value={travelForm.travel_mode}>
                  {travelModeOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <VendorField error={formErrors.estimated_budget} label="Estimated budget" onChange={(value) => updateTravelField("estimated_budget", value.replace(/[^\d.]/g, ""))} value={travelForm.estimated_budget} />
              <VendorField error={formErrors.actual_spend} label="Actual spend" onChange={(value) => updateTravelField("actual_spend", value.replace(/[^\d.]/g, ""))} value={travelForm.actual_spend} />
              <VendorField error={formErrors.number_of_trips} inputMode="numeric" label="Number of trips" onChange={(value) => updateTravelField("number_of_trips", value.replace(/\D/g, ""))} value={travelForm.number_of_trips} />
              <label className="vendor-field">
                Approval status
                <select onChange={(event) => updateTravelField("approval_status", event.target.value)} value={travelForm.approval_status}>
                  {travelStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="vendor-field">
                Policy status
                <select onChange={(event) => updateTravelField("policy_status", event.target.value)} value={travelForm.policy_status}>
                  {travelPolicyStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="vendor-field">
                Booking status
                <select onChange={(event) => updateTravelField("booking_status", event.target.value)} value={travelForm.booking_status}>
                  {travelStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <VendorField label="Google Calendar event ID" onChange={(value) => updateTravelField("google_calendar_event_id", value)} value={travelForm.google_calendar_event_id} />
              <VendorField label="Google sync status" onChange={(value) => updateTravelField("google_sync_status", value)} value={travelForm.google_sync_status} />
              <VendorField label="Google last synced at" onChange={(value) => updateTravelField("google_last_synced_at", value)} type="datetime-local" value={travelForm.google_last_synced_at} />
              <label className="vendor-field wide">
                Notes
                <textarea onChange={(event) => updateTravelField("notes", event.target.value)} rows={4} value={travelForm.notes} />
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={closeTravelForm} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">{saving ? "Saving..." : editingTravel ? "Update Travel Record" : "Add Travel Record"}</button>
            </div>
          </form>
        </div>
      )}

      {eventFormOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal travel-modal" onSubmit={submitEventForm} role="dialog" aria-modal="true" aria-label="Calendar event">
            <div className="section-heading">
              <h2>{editingEvent ? "Edit Calendar Event" : "Add Calendar Event"}</h2>
              <button className="icon-only" onClick={closeEventForm} type="button" aria-label="Close calendar event form">
                <X size={16} />
              </button>
            </div>
            <div className="vendor-form-grid">
              <VendorField label="Event ID" onChange={(value) => updateEventField("event_id", value)} placeholder="Auto-generated if blank" value={eventForm.event_id} />
              <VendorField error={formErrors.title} label="Title" onChange={(value) => updateEventField("title", value)} value={eventForm.title} />
              <label className="vendor-field">
                Event type
                <select onChange={(event) => updateEventField("event_type", event.target.value)} value={eventForm.event_type}>
                  {calendarEventTypeOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <VendorField error={formErrors.start_datetime} label="Start date/time" onChange={(value) => updateEventField("start_datetime", value)} type="datetime-local" value={eventForm.start_datetime} />
              <VendorField error={formErrors.end_datetime} label="End date/time" onChange={(value) => updateEventField("end_datetime", value)} type="datetime-local" value={eventForm.end_datetime} />
              <VendorField label="Location" onChange={(value) => updateEventField("location", value)} value={eventForm.location} />
              <VendorField label="Attendees" onChange={(value) => updateEventField("attendees", value)} value={eventForm.attendees} />
              <VendorField label="Related travel ID" onChange={(value) => updateEventField("related_travel_id", value)} value={eventForm.related_travel_id} />
              <VendorField label="Reminder" onChange={(value) => updateEventField("reminder", value)} value={eventForm.reminder} />
              <label className="vendor-field">
                Status
                <select onChange={(event) => updateEventField("status", event.target.value)} value={eventForm.status}>
                  {calendarEventStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <VendorField label="Google Calendar event ID" onChange={(value) => updateEventField("google_calendar_event_id", value)} value={eventForm.google_calendar_event_id} />
              <VendorField label="Google sync status" onChange={(value) => updateEventField("google_sync_status", value)} value={eventForm.google_sync_status} />
              <VendorField label="Google last synced at" onChange={(value) => updateEventField("google_last_synced_at", value)} type="datetime-local" value={eventForm.google_last_synced_at} />
              <label className="vendor-field wide">
                Notes
                <textarea onChange={(event) => updateEventField("notes", event.target.value)} rows={4} value={eventForm.notes} />
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={closeEventForm} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">{saving ? "Saving..." : editingEvent ? "Update Calendar Event" : "Add Calendar Event"}</button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

function TravelRecordsTable({ from, onEdit, onPageChange, page, pageCount, records, to, total }) {
  if (!records.length) {
    return <EmptyState icon={Plane} title="No travel records match." detail="Add travel records or adjust search and filters." />;
  }
  return (
    <div className="vendor-table-wrap travel-table-wrap">
      <table className="vendor-table travel-table">
        <thead>
          <tr>
            <th>Travel ID</th>
            <th>Employee</th>
            <th>Department</th>
            <th>From</th>
            <th>To</th>
            <th>Dates</th>
            <th>Purpose</th>
            <th>Mode</th>
            <th>Budget</th>
            <th>Spend</th>
            <th>Trips</th>
            <th>Approval</th>
            <th>Policy</th>
            <th>Booking</th>
            <th>Google Sync</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={record.id}>
              <td><strong>{record.travel_id}</strong></td>
              <td className="ticket-person-cell"><strong>{record.employee_name}</strong><span>{record.employee_email}</span></td>
              <td>{record.department}</td>
              <td>{record.destination_from}</td>
              <td>{record.destination_to}</td>
              <td>{formatDateOnly(record.travel_start_date)} - {formatDateOnly(record.travel_end_date)}</td>
              <td>{record.purpose}</td>
              <td>{record.travel_mode}</td>
              <td>{formatMoney(record.estimated_budget)}</td>
              <td><strong>{formatMoney(record.actual_spend)}</strong></td>
              <td>{record.number_of_trips}</td>
              <td><span className={ticketBadgeClass("ticket-status-pill", record.approval_status)}>{record.approval_status}</span></td>
              <td><span className={ticketBadgeClass("ticket-status-pill", record.policy_status)}>{record.policy_status}</span></td>
              <td><span className={ticketBadgeClass("ticket-status-pill", record.booking_status)}>{record.booking_status}</span></td>
              <td className="ticket-person-cell"><strong>{record.google_sync_status || "Not Synced"}</strong><span>{record.google_calendar_event_id || "Google ID pending"}</span></td>
              <td>
                <div className="table-actions ticket-actions">
                  <button className="icon-only table-icon-button action-edit" onClick={() => onEdit(record)} title="Edit travel record" type="button" aria-label="Edit travel record">
                    <Pencil size={15} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="vendor-table-footer">
        <span>Showing {from} to {to} of {total} travel records</span>
        <div className="pagination-controls" aria-label="Travel pagination">
          <button disabled={page <= 1} onClick={() => onPageChange(Math.max(1, page - 1))} type="button" aria-label="Previous page">
            <ChevronLeft size={16} />
          </button>
          <span>Page {page} of {pageCount}</span>
          <button disabled={page >= pageCount} onClick={() => onPageChange(Math.min(pageCount, page + 1))} type="button" aria-label="Next page">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function CalendarEventsTable({ events, onEdit }) {
  if (!events.length) {
    return <EmptyState icon={CalendarDays} title="No calendar events match." detail="Add calendar events or adjust search and filters." />;
  }
  return (
    <div className="vendor-table-wrap travel-table-wrap">
      <table className="vendor-table travel-table">
        <thead>
          <tr>
            <th>Event ID</th>
            <th>Title</th>
            <th>Type</th>
            <th>Start</th>
            <th>End</th>
            <th>Location</th>
            <th>Attendees</th>
            <th>Related Travel</th>
            <th>Reminder</th>
            <th>Status</th>
            <th>Google Sync</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td><strong>{event.event_id}</strong></td>
              <td>{event.title}</td>
              <td>{event.event_type}</td>
              <td>{formatDateTime(event.start_datetime)}</td>
              <td>{formatDateTime(event.end_datetime)}</td>
              <td>{event.location || "—"}</td>
              <td>{event.attendees || "—"}</td>
              <td>{event.related_travel_id || "—"}</td>
              <td>{event.reminder || "—"}</td>
              <td><span className={ticketBadgeClass("ticket-status-pill", event.status)}>{event.status}</span></td>
              <td className="ticket-person-cell"><strong>{event.google_sync_status || "Not Synced"}</strong><span>{event.google_calendar_event_id || "Google ID pending"}</span></td>
              <td>
                <div className="table-actions ticket-actions">
                  <button className="icon-only table-icon-button action-edit" onClick={() => onEdit(event)} title="Edit calendar event" type="button" aria-label="Edit calendar event">
                    <Pencil size={15} />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TravelReports({ summary }) {
  const countByEmployee = summary.travel_count_by_employee || [];
  const spendByEmployee = summary.travel_spend_by_employee || [];
  const spendByDepartment = summary.travel_spend_by_department || [];
  const topDestinations = summary.top_destinations || [];
  const monthlySpend = summary.monthly_travel_spend || [];
  return (
    <section className="travel-reports-grid">
      <TravelReportCard title="Travel count by employee" rows={countByEmployee.slice(0, 5)} columns={[
        ["employee_name", "Employee"],
        ["travel_count", "Records"],
        ["trip_count", "Trips"]
      ]} />
      <TravelReportCard title="Travel spend by employee" rows={spendByEmployee.slice(0, 5)} columns={[
        ["employee_name", "Employee"],
        ["department", "Department"],
        ["actual_spend", "Spend", formatMoney]
      ]} />
      <TravelReportCard title="Travel spend by department" rows={spendByDepartment.slice(0, 5)} columns={[
        ["department", "Department"],
        ["actual_spend", "Spend", formatMoney]
      ]} />
      <TravelReportCard title="Top destinations" rows={topDestinations.slice(0, 5)} columns={[
        ["destination", "Destination"],
        ["travel_count", "Trips"],
        ["actual_spend", "Spend", formatMoney]
      ]} />
      <TravelReportCard title="Monthly travel spend" rows={monthlySpend.slice(-6)} columns={[
        ["month", "Month"],
        ["actual_spend", "Spend", formatMoney]
      ]} />
    </section>
  );
}

function TravelReportCard({ columns, rows, title }) {
  return (
    <section className="dashboard-card travel-report-card">
      <div className="section-heading"><h2>{title}</h2></div>
      {!rows.length ? (
        <p className="empty">No data yet.</p>
      ) : (
        <table className="mini-report-table">
          <thead>
            <tr>{columns.map(([, label]) => <th key={label}>{label}</th>)}</tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={`${title}-${index}`}>
                {columns.map(([key, , formatter]) => (
                  <td key={key}>{formatter ? formatter(row[key]) : row[key]}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

function ExpenseView({ currentUser, expenses, onChanged, onExpenseSaved, setError }) {
  const [expenseSearch, setExpenseSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [expenseFilters, setExpenseFilters] = useState({ category: "All", status: "All", department: "All" });
  const [expensePage, setExpensePage] = useState(1);
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const [formOpen, setFormOpen] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [form, setForm] = useState(emptyExpenseForm);
  const [formErrors, setFormErrors] = useState({});
  const [importOpen, setImportOpen] = useState(false);
  const [selectedImportFileName, setSelectedImportFileName] = useState("");
  const [importPreview, setImportPreview] = useState(null);
  const [importError, setImportError] = useState("");
  const [expenseMessage, setExpenseMessage] = useState(null);
  const [saving, setSaving] = useState(false);
  const expenseImportFileInputRef = useRef(null);
  const activeFilterCount = Object.values(expenseFilters).filter((value) => value !== "All").length;
  const canCreateExpense = ["admin", "finance_manager", "employee", "it_manager"].includes(currentUser.role);
  const canImportExpenses = ["admin", "finance_manager"].includes(currentUser.role);
  const canSendExpenseMessage = ["admin", "finance_manager"].includes(currentUser.role);
  const filteredExpenses = useMemo(() => {
    return expenses.filter((expense) => {
      const matchesQuery = expenseMatchesLocalSearch(expense, expenseSearch);
      const matchesCategory = expenseFilters.category === "All" || expense.category === expenseFilters.category;
      const matchesStatus = expenseFilters.status === "All" || expense.status === expenseFilters.status;
      const matchesDepartment = expenseFilters.department === "All" || expense.department === expenseFilters.department;
      return matchesQuery && matchesCategory && matchesStatus && matchesDepartment;
    });
  }, [expenseFilters, expenseSearch, expenses]);
  const expensePageCount = Math.max(1, Math.ceil(filteredExpenses.length / EXPENSE_PAGE_SIZE));
  const currentExpensePage = Math.min(expensePage, expensePageCount);
  const expenseStartIndex = filteredExpenses.length ? (currentExpensePage - 1) * EXPENSE_PAGE_SIZE : 0;
  const expenseEndIndex = Math.min(expenseStartIndex + EXPENSE_PAGE_SIZE, filteredExpenses.length);
  const pagedExpenses = filteredExpenses.slice(expenseStartIndex, expenseEndIndex);
  const firstPaginationPage = Math.min(
    Math.max(1, currentExpensePage - 1),
    Math.max(1, expensePageCount - 2)
  );
  const expensePaginationPages = Array.from(
    { length: Math.min(3, expensePageCount) },
    (_, index) => firstPaginationPage + index
  );
  useEffect(() => {
    setExpensePage(1);
  }, [expenseFilters, expenseSearch, expenses.length]);

  useEffect(() => {
    if (expensePage > expensePageCount) {
      setExpensePage(expensePageCount);
    }
  }, [expensePage, expensePageCount]);

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = window.setTimeout(() => setToastMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  function updateExpenseFilter(field, value) {
    setExpenseFilters((current) => ({ ...current, [field]: value }));
  }

  function clearExpenseFilters() {
    setExpenseFilters({ category: "All", status: "All", department: "All" });
  }

  function updateExpenseField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function openExpenseForm(expense = null) {
    if (expense && !canManageExpense(currentUser, expense)) return;
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setEditingExpense(expense);
    setForm(expense ? {
      employee_name: expense.employee_name || "",
      employee_email: expense.employee_email || "",
      department: expense.department || "Operations",
      category: expense.category || "Travel",
      vendor_merchant: expense.vendor_merchant || "",
      amount: String(expense.amount || ""),
      currency: expense.currency || "INR",
      expense_date: String(expense.expense_date || "").slice(0, 10),
      payment_mode: expense.payment_mode || "Corporate Card",
      receipt_status: expense.receipt_status || "Attached",
      receipt_attachment_name: expense.receipt_attachment_name || "",
      notes: expense.notes || "",
      status: expense.status || "Draft",
      approval_required: Boolean(expense.approval_required)
    } : {
      ...emptyExpenseForm,
      employee_name: currentUser.name,
      employee_email: currentUser.email,
      department: currentUser.role === "it_manager" ? "IT" : currentUser.role === "finance_manager" ? "Finance" : "Operations",
      expense_date: new Date().toISOString().slice(0, 10)
    });
    setFormOpen(true);
  }

  function closeExpenseForm() {
    setFormOpen(false);
    setEditingExpense(null);
    setForm(emptyExpenseForm);
    setFormErrors({});
  }

  function validateExpenseForm() {
    const errors = {};
    if (!form.employee_name.trim()) errors.employee_name = "Required";
    if (!form.employee_email.trim()) errors.employee_email = "Required";
    if (form.employee_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.employee_email)) errors.employee_email = "Enter a valid email";
    if (!form.department.trim()) errors.department = "Required";
    if (!form.vendor_merchant.trim()) errors.vendor_merchant = "Required";
    if (!String(form.amount || "").trim()) errors.amount = "Required";
    if (Number(form.amount) <= 0) errors.amount = "Amount must be greater than 0";
    if (!form.expense_date || !isValidIsoDate(form.expense_date)) errors.expense_date = "Choose a valid expense date";
    if (!form.payment_mode.trim()) errors.payment_mode = "Required";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function submitExpense(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    if (!validateExpenseForm()) return;
    setSaving(true);
    try {
      const payload = {
        ...form,
        employee_name: form.employee_name.trim(),
        employee_email: form.employee_email.trim().toLowerCase(),
        department: form.department.trim(),
        vendor_merchant: form.vendor_merchant.trim(),
        amount: Number(form.amount),
        currency: form.currency.trim().toUpperCase(),
        payment_mode: form.payment_mode.trim(),
        receipt_attachment_name: form.receipt_attachment_name.trim(),
        notes: form.notes.trim()
      };
      const response = editingExpense
        ? await updateExpense(editingExpense.id, payload)
        : await createExpense(payload);
      if (response?.expense) onExpenseSaved(response.expense);
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      closeExpenseForm();
      setToastType("success");
      setToastMessage(editingExpense ? "Expense updated successfully" : "Expense created successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not save expense: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function changeExpenseStatus(expense, status) {
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      const response = await updateExpenseStatus(expense.id, status);
      if (response?.expense) onExpenseSaved(response.expense);
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setToastType("success");
      setToastMessage(`Expense ${status.toLowerCase()} successfully`);
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not update expense: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  function openExpenseMessage(expense) {
    if (!canSendExpenseMessage) return;
    setToastMessage("");
    setToastType("success");
    setExpenseMessage({
      detail: "Send an expense update by Email, WhatsApp, or both.",
      recipient_name: expense.employee_name || "",
      recipient_email: expense.employee_email || "",
      recipient_phone: "",
      subject: `Expense update: ${expense.expense_id || "expense"}`,
      message_body: `Hello ${expense.employee_name || "there"},\n\nYour expense ${expense.expense_id || ""} is currently ${expense.status || "updated"}.\n\nRegards,\nAgent Concierge`,
      related_module: "expenses",
      related_record_id: expense.id
    });
  }

  function startExpenseImport() {
    if (!canImportExpenses) return;
    setToastMessage("");
    setToastType("success");
    setSelectedImportFileName("");
    setImportPreview(null);
    setImportError("");
    setImportOpen(true);
  }

  function closeExpenseImport() {
    if (saving) return;
    setImportOpen(false);
    setSelectedImportFileName("");
    setImportPreview(null);
    setImportError("");
  }

  function chooseExpenseImportFile() {
    if (!canImportExpenses) return;
    expenseImportFileInputRef.current?.click();
  }

  async function handleExpenseImportFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setToastMessage("");
    setToastType("success");
    setImportError("");
    setImportPreview(null);
    setSelectedImportFileName(file.name);
    const fileName = file.name.toLowerCase();
    const isCsv = fileName.endsWith(".csv");
    const isXlsx = fileName.endsWith(".xlsx");
    const isXls = fileName.endsWith(".xls");
    if (!isCsv && !isXlsx && !isXls) {
      setImportError("Unsupported file type. Please upload a CSV or .xlsx file.");
      return;
    }
    if (isXls) {
      setImportError("Legacy .xls import is not enabled yet. Please use CSV or .xlsx.");
      return;
    }
    if (file.size === 0) {
      setImportError("Selected file is empty.");
      return;
    }
    setSaving(true);
    try {
      const contentBase64 = arrayBufferToBase64(await file.arrayBuffer());
      const preview = await previewExpenseImport(file.name, contentBase64);
      setImportPreview(preview);
      if (preview.errors?.length) {
        const templateError = preview.errors.find((message) => message.includes("does not match the expense import template"));
        setImportError(templateError || "Some rows need attention before import can continue.");
      }
    } catch (err) {
      setImportError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function confirmExpenseUpload() {
    if (!importPreview || importPreview.errors.length) return;
    setError("");
    setToastMessage("");
    setSaving(true);
    try {
      const response = await confirmExpenseImport(
        selectedImportFileName || importPreview.file_name || "expenses_import.csv",
        importPreview.rows.map((row) => row.expense)
      );
      (response.expenses || []).forEach((expense) => onExpenseSaved(expense));
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setImportOpen(false);
      setImportPreview(null);
      setImportError("");
      setSelectedImportFileName("");
      setToastType("success");
      setToastMessage(`${response.import?.successful_rows || 0} expenses imported successfully`);
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not import expenses: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="expenses-page screen-stack">
      {toastMessage && <div className={toastType === "error" ? "toast-notification error" : "toast-notification"} role="status">{toastMessage}</div>}
      <section className="dashboard-card vendor-directory-card expense-directory-card">
        <div className="vendor-directory-header expense-directory-header">
          <div className="vendor-directory-title">
            <span className="vendor-directory-icon"><DollarSign size={20} /></span>
            <div>
              <h2>All Expenses</h2>
              <p>Manage company expenses and reports</p>
            </div>
          </div>
          <div className="ticket-action-row expense-action-row">
            <label className="vendor-search-control ticket-search-control expense-search-control" aria-label="Search expenses">
              <Search size={17} />
              <input
                onChange={(event) => setExpenseSearch(event.target.value)}
                placeholder="Search expenses..."
                value={expenseSearch}
              />
              {expenseSearch && (
                <button aria-label="Clear expense search" onClick={() => setExpenseSearch("")} title="Clear expense search" type="button">
                  <X size={15} />
                </button>
              )}
            </label>
            <div className="vendor-filter-wrap">
              <button
                aria-expanded={filtersOpen}
                aria-label="Filter expenses"
                className="icon-button secondary vendor-filter-button inventory-icon-action"
                onClick={() => setFiltersOpen((open) => !open)}
                title="Filter expenses"
                type="button"
              >
                <Filter size={17} />
                {activeFilterCount > 0 && <strong>{activeFilterCount}</strong>}
              </button>
              {filtersOpen && (
                <div className="vendor-filter-panel" role="dialog" aria-label="Expense filters">
                  <label>
                    Category
                    <select value={expenseFilters.category} onChange={(event) => updateExpenseFilter("category", event.target.value)}>
                      {expenseCategoryFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Status
                    <select value={expenseFilters.status} onChange={(event) => updateExpenseFilter("status", event.target.value)}>
                      {expenseStatusFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Department
                    <select value={expenseFilters.department} onChange={(event) => updateExpenseFilter("department", event.target.value)}>
                      {expenseDepartmentFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <button className="table-action-button" onClick={clearExpenseFilters} type="button">Clear</button>
                </div>
              )}
            </div>
            <input
              accept=".csv,.xlsx,.xls,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
              className="visually-hidden"
              onChange={handleExpenseImportFile}
              ref={expenseImportFileInputRef}
              type="file"
            />
            {canImportExpenses && (
              <button
                className="icon-button secondary inventory-import-button expense-upload-button"
                disabled={saving}
                onClick={startExpenseImport}
                title="Upload expenses"
                type="button"
              >
                <Upload size={17} />
                <span>Upload Expenses</span>
              </button>
            )}
            <button className="primary-button vendor-add-button ticket-create-button" disabled={!canCreateExpense} onClick={() => openExpenseForm()} type="button">
              <Plus size={18} />
              <span>Add Expense</span>
            </button>
          </div>
        </div>
        <ExpenseTable
          currentUser={currentUser}
          emptyDetail={expenses.length ? "Adjust search or filters to show more expenses." : "Add expenses to begin tracking reimbursements and finance approvals."}
          emptyTitle={expenses.length ? "No expenses match." : "No expenses yet."}
          expenses={pagedExpenses}
          from={filteredExpenses.length ? expenseStartIndex + 1 : 0}
          onApprove={(expense) => changeExpenseStatus(expense, "Approved")}
          onEdit={openExpenseForm}
          onPageChange={setExpensePage}
          onReject={(expense) => changeExpenseStatus(expense, "Rejected")}
          page={currentExpensePage}
          pageCount={expensePageCount}
          pageNumbers={expensePaginationPages}
          to={expenseEndIndex}
          total={filteredExpenses.length}
        />
      </section>

      {importOpen && (
        <div className="modal-backdrop" role="presentation">
          <section className="vendor-modal inventory-preview-modal inventory-import-modal expense-import-modal" role="dialog" aria-modal="true" aria-label="Upload expenses">
            <div className="section-heading">
              <h2>Upload Expenses</h2>
              <button className="icon-only" onClick={closeExpenseImport} type="button" aria-label="Close upload expenses">
                <X size={16} />
              </button>
            </div>
            <div className="inventory-upload-area">
              <div>
                <strong>{selectedImportFileName || "No file selected"}</strong>
                <span>Supported formats: CSV and .xlsx. Legacy .xls can be selected but is not enabled yet.</span>
                <p>Preview and validate expenses before saving them.</p>
              </div>
              <div className="inventory-upload-actions">
                <button className="icon-button secondary inventory-choose-file-button" disabled={saving} onClick={chooseExpenseImportFile} type="button">
                  <Upload size={17} />
                  <span>{selectedImportFileName ? "Replace File" : "Choose File"}</span>
                </button>
              </div>
            </div>
            {importError && <div className="import-inline-error" role="alert">{importError}</div>}
            {saving && !importPreview && <p className="empty import-loading">Parsing selected file...</p>}
            {importPreview && (
              <>
                <div className="import-summary">
                  <span className="status-pill success">{importPreview.rows.length} rows</span>
                  <span className={importPreview.errors.length ? "status-pill danger" : "status-pill success"}>{importPreview.errors.length} errors</span>
                  <span className={importPreview.warnings.length ? "status-pill warning" : "status-pill success"}>{importPreview.warnings.length} warnings</span>
                </div>
                {(importPreview.errors.length > 0 || importPreview.warnings.length > 0) && (
                  <div className="import-messages">
                    {importPreview.errors.map((message) => <p className="import-error" key={message}>{message}</p>)}
                    {importPreview.warnings.map((message) => <p className="import-warning" key={message}>{message}</p>)}
                  </div>
                )}
                <div className="vendor-table-wrap inventory-preview-wrap">
                  <table className="vendor-table inventory-preview-table expense-import-preview-table">
                    <thead>
                      <tr>
                        {expenseImportColumns.map(([, label]) => <th key={label}>{label}</th>)}
                        <th>Validation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {importPreview.rows.map((row) => (
                        <tr key={row.rowNumber}>
                          {expenseImportColumns.map(([key]) => (
                            <td key={key}>
                              {key === "expense_date"
                                ? formatDateOnly(row.expense[key])
                                : key === "amount"
                                  ? row.expense[key] || "—"
                                  : String(row.expense[key] ?? "") || "—"}
                            </td>
                          ))}
                          <td className="ticket-person-cell">
                            <span className={row.errors.length ? "status-pill danger" : row.warnings.length ? "status-pill warning" : "status-pill success"}>
                              {row.errors.length ? "Error" : row.warnings.length ? "Warning" : "Ready"}
                            </span>
                            <span>{[...(row.errors || []), ...(row.warnings || [])].join("; ") || "Ready to import"}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
            <div className="modal-actions">
              <button className="icon-button secondary" disabled={saving} onClick={closeExpenseImport} type="button">Cancel</button>
              <button className="primary-button" disabled={saving || !importPreview || importPreview.errors.length > 0 || importPreview.rows.length === 0} onClick={confirmExpenseUpload} type="button">
                {saving ? "Importing..." : "Confirm Import"}
              </button>
            </div>
          </section>
        </div>
      )}

      {formOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal expense-modal" onSubmit={submitExpense} role="dialog" aria-modal="true" aria-label="Add expense">
            <div className="section-heading">
              <h2>{editingExpense ? "Edit Expense" : "Add Expense"}</h2>
              <button className="icon-only" onClick={closeExpenseForm} type="button" aria-label="Close expense form">
                <X size={16} />
              </button>
            </div>
            <div className="vendor-form-grid">
              <VendorField error={formErrors.employee_name} label="Employee name" onChange={(value) => updateExpenseField("employee_name", value)} value={form.employee_name} />
              <VendorField error={formErrors.employee_email} label="Employee email" onChange={(value) => updateExpenseField("employee_email", value)} type="email" value={form.employee_email} />
              <label className="vendor-field">
                Department
                <input onChange={(event) => updateExpenseField("department", event.target.value)} value={form.department} />
                {formErrors.department && <span>{formErrors.department}</span>}
              </label>
              <label className="vendor-field">
                Category
                <select onChange={(event) => updateExpenseField("category", event.target.value)} value={form.category}>
                  {expenseCategoryOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <VendorField error={formErrors.vendor_merchant} label="Vendor/Merchant" onChange={(value) => updateExpenseField("vendor_merchant", value)} value={form.vendor_merchant} />
              <VendorField error={formErrors.amount} label="Amount" onChange={(value) => updateExpenseField("amount", value.replace(/[^\d.]/g, ""))} value={form.amount} />
              <VendorField label="Currency" onChange={(value) => updateExpenseField("currency", value)} value={form.currency} />
              <VendorField error={formErrors.expense_date} helper={form.expense_date ? `Selected: ${formatCalendarDate(form.expense_date)}` : "Choose expense date"} label="Expense date" onChange={(value) => updateExpenseField("expense_date", value)} type="date" value={form.expense_date} />
              <label className="vendor-field">
                Payment mode
                <select onChange={(event) => updateExpenseField("payment_mode", event.target.value)} value={form.payment_mode}>
                  {expensePaymentModeOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="vendor-field">
                Receipt status
                <select onChange={(event) => updateExpenseField("receipt_status", event.target.value)} value={form.receipt_status}>
                  {expenseReceiptStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <VendorField label="Receipt attachment name" onChange={(value) => updateExpenseField("receipt_attachment_name", value)} value={form.receipt_attachment_name} />
              <label className="vendor-field">
                Status
                <select onChange={(event) => updateExpenseField("status", event.target.value)} value={form.status}>
                  {expenseStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="ticket-checkbox wide">
                <input checked={form.approval_required} onChange={(event) => updateExpenseField("approval_required", event.target.checked)} type="checkbox" />
                <span>Approval required</span>
              </label>
              <label className="vendor-field wide">
                Notes
                <textarea onChange={(event) => updateExpenseField("notes", event.target.value)} rows={4} value={form.notes} />
              </label>
            </div>
            <div className="modal-actions">
              {editingExpense && canSendExpenseMessage && (
                <button className="icon-button secondary" onClick={() => openExpenseMessage(editingExpense)} type="button">
                  <Send size={16} />
                  <span>Send Update</span>
                </button>
              )}
              <button className="icon-button secondary" onClick={closeExpenseForm} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Saving..." : editingExpense ? "Update Expense" : "Add Expense"}
              </button>
            </div>
          </form>
        </div>
      )}
      {expenseMessage && (
        <CommunicationSendModal
          context={expenseMessage}
          onClose={() => setExpenseMessage(null)}
          onSent={(response) => {
            setToastType("success");
            setToastMessage(response?.message || "Message sent");
          }}
          setError={setError}
        />
      )}
    </section>
  );
}

function ExpenseTable({
  currentUser,
  emptyDetail,
  emptyTitle,
  expenses,
  from = 0,
  onApprove,
  onEdit,
  onPageChange,
  onReject,
  page = 1,
  pageCount = 1,
  pageNumbers = [1],
  to = 0,
  total = 0
}) {
  if (!expenses.length) {
    return <EmptyState icon={DollarSign} title={emptyTitle} detail={emptyDetail} />;
  }

  return (
    <div className="vendor-table-wrap expense-table-wrap">
      <table className="vendor-table expense-table">
        <thead>
          <tr>
            <th>Expense ID</th>
            <th>Employee</th>
            <th>Department</th>
            <th>Category</th>
            <th>Vendor/Merchant</th>
            <th>Amount</th>
            <th>Expense date</th>
            <th>Payment mode</th>
            <th>Receipt</th>
            <th>Status</th>
            <th>Approval required</th>
            <th>Approved by</th>
            <th>Created date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {expenses.map((expense) => {
            const canManage = canManageExpense(currentUser, expense);
            const canApprove = canApproveExpense(currentUser);
            return (
              <tr key={expense.id}>
                <td><strong>{expense.expense_id}</strong></td>
                <td className="ticket-person-cell">
                  <strong>{expense.employee_name}</strong>
                  <span>{expense.employee_email}</span>
                </td>
                <td>{expense.department}</td>
                <td>{expense.category}</td>
                <td>{expense.vendor_merchant}</td>
                <td><strong>{formatMoney(expense.amount, expense.currency)}</strong></td>
                <td>{formatCalendarDate(expense.expense_date)}</td>
                <td>{expense.payment_mode}</td>
                <td className="ticket-person-cell">
                  <strong>{expense.receipt_status}</strong>
                  <span>{expense.receipt_attachment_name || "—"}</span>
                </td>
                <td>{expense.status}</td>
                <td>{expense.approval_required ? "Yes" : "No"}</td>
                <td>{expense.approved_by || "—"}</td>
                <td>{formatCalendarDate(expense.created_at)}</td>
                <td>
                  <div className="table-actions expense-row-actions">
                    <button
                      aria-label="Edit expense"
                      className="table-action-button expense-icon-action action-edit"
                      disabled={!canManage}
                      onClick={() => onEdit(expense)}
                      title={canManage ? "Edit expense" : "Only Finance/Admin or owner draft expenses can be edited"}
                      type="button"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      aria-label="Approve expense"
                      className="table-action-button expense-icon-action action-reopen"
                      disabled={!canApprove || expense.status === "Approved"}
                      onClick={() => onApprove(expense)}
                      title={canApprove ? "Approve expense" : "Requires Finance Manager/Admin access"}
                      type="button"
                    >
                      <CheckCircle2 size={16} />
                    </button>
                    <button
                      aria-label="Reject expense"
                      className="table-action-button expense-icon-action action-close"
                      disabled={!canApprove || expense.status === "Rejected"}
                      onClick={() => onReject(expense)}
                      title={canApprove ? "Reject expense" : "Requires Finance Manager/Admin access"}
                      type="button"
                    >
                      <X size={16} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="vendor-table-footer expense-table-footer">
        <span>Showing {from} to {to} of {total} expenses</span>
        <div className="pagination-controls" aria-label="Expense pagination">
          <button
            disabled={page <= 1}
            onClick={() => onPageChange?.(Math.max(1, page - 1))}
            type="button"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          {pageNumbers.map((pageNumber) => (
            <button
              className={pageNumber === page ? "active" : ""}
              key={pageNumber}
              onClick={() => onPageChange?.(pageNumber)}
              type="button"
            >
              {pageNumber}
            </button>
          ))}
          <button
            disabled={page >= pageCount}
            onClick={() => onPageChange?.(Math.min(pageCount, page + 1))}
            type="button"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ReportsView({ currentUser, onChanged, onReportDeleted, onReportSaved, reports, setError }) {
  const [reportSearch, setReportSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [filters, setFilters] = useState({
    department: "All",
    reportType: "All",
    fileType: "All",
    status: "All",
    uploadedDate: ""
  });
  const [reportPage, setReportPage] = useState(1);
  const [importOpen, setImportOpen] = useState(false);
  const [viewingReport, setViewingReport] = useState(null);
  const [reportMessage, setReportMessage] = useState(null);
  const [form, setForm] = useState(() => ({
    ...emptyReportForm,
    department: reportDepartmentsForRole(currentUser.role)[0] || "Admin",
    report_type: currentUser.role === "it_manager" ? "IT" : currentUser.role === "finance_manager" ? "Finance" : "Operations"
  }));
  const [formErrors, setFormErrors] = useState({});
  const [selectedFile, setSelectedFile] = useState(null);
  const [selectedFileName, setSelectedFileName] = useState("");
  const [fileError, setFileError] = useState("");
  const [toastMessage, setToastMessage] = useState("");
  const [toastType, setToastType] = useState("success");
  const [saving, setSaving] = useState(false);
  const reportFileInputRef = useRef(null);
  const canImportExport = ["admin", "it_manager", "finance_manager"].includes(currentUser.role);
  const allowedDepartments = reportDepartmentsForRole(currentUser.role);
  const activeFilterCount = Object.values(filters).filter((value) => value && value !== "All").length;

  const filteredReports = useMemo(() => {
    return reports.filter((report) => {
      const matchesQuery = reportMatchesLocalSearch(report, reportSearch);
      const matchesDepartment = filters.department === "All" || report.department === filters.department;
      const matchesType = filters.reportType === "All" || report.report_type === filters.reportType;
      const matchesFileType = filters.fileType === "All" || report.file_type === filters.fileType;
      const matchesStatus = filters.status === "All" || report.status === filters.status;
      const matchesDate = !filters.uploadedDate || String(report.uploaded_at || "").slice(0, 10) === filters.uploadedDate;
      return matchesQuery && matchesDepartment && matchesType && matchesFileType && matchesStatus && matchesDate;
    });
  }, [filters, reportSearch, reports]);

  const reportPageCount = Math.max(1, Math.ceil(filteredReports.length / REPORT_PAGE_SIZE));
  const currentReportPage = Math.min(reportPage, reportPageCount);
  const reportStartIndex = filteredReports.length ? (currentReportPage - 1) * REPORT_PAGE_SIZE : 0;
  const reportEndIndex = Math.min(reportStartIndex + REPORT_PAGE_SIZE, filteredReports.length);
  const pagedReports = filteredReports.slice(reportStartIndex, reportEndIndex);

  useEffect(() => {
    setReportPage(1);
  }, [filters, reportSearch, reports.length]);

  useEffect(() => {
    if (!toastMessage) return undefined;
    const timer = window.setTimeout(() => setToastMessage(""), 3000);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  function updateFilter(field, value) {
    setFilters((current) => ({ ...current, [field]: value }));
  }

  function clearFilters() {
    setFilters({ department: "All", reportType: "All", fileType: "All", status: "All", uploadedDate: "" });
  }

  function updateReportField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function openImportModal() {
    if (!canImportExport) return;
    setToastMessage("");
    setToastType("success");
    setFormErrors({});
    setFileError("");
    setSelectedFile(null);
    setSelectedFileName("");
    setForm({
      ...emptyReportForm,
      department: allowedDepartments[0] || "Admin",
      report_type: currentUser.role === "it_manager" ? "IT" : currentUser.role === "finance_manager" ? "Finance" : "Operations"
    });
    setImportOpen(true);
  }

  function closeImportModal() {
    if (saving) return;
    setImportOpen(false);
    setSelectedFile(null);
    setSelectedFileName("");
    setFileError("");
    setFormErrors({});
  }

  function chooseReportFile() {
    reportFileInputRef.current?.click();
  }

  function handleReportFile(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    setFileError("");
    setSelectedFile(null);
    setSelectedFileName("");
    if (!file) return;
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith(".csv") && !fileName.endsWith(".xlsx") && !fileName.endsWith(".pdf")) {
      setFileError("Unsupported file type. Please upload CSV, XLSX, or PDF.");
      return;
    }
    if (file.size === 0) {
      setFileError("Selected file is empty.");
      return;
    }
    setSelectedFile(file);
    setSelectedFileName(file.name);
  }

  function validateReportForm() {
    const errors = {};
    if (!form.report_name.trim()) errors.report_name = "Required";
    if (!form.report_type.trim()) errors.report_type = "Required";
    if (!form.department.trim()) errors.department = "Required";
    if (!selectedFile) errors.file = "Choose a report file";
    if (allowedDepartments.length && !allowedDepartments.includes(form.department)) {
      errors.department = "This role cannot import reports for that department";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function submitReportImport(event) {
    event.preventDefault();
    setError("");
    setToastMessage("");
    if (!validateReportForm()) return;
    setSaving(true);
    try {
      const response = await importReport({
        ...form,
        report_name: form.report_name.trim(),
        report_type: form.report_type.trim(),
        department: form.department.trim(),
        notes: form.notes.trim(),
        filename: selectedFile.name,
        content_base64: arrayBufferToBase64(await selectedFile.arrayBuffer())
      });
      if (response?.report) onReportSaved(response.report);
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      closeImportModal();
      setToastType("success");
      setToastMessage("Report imported successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not import report: ${apiErrorMessage(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleDownload(report) {
    setToastMessage("");
    try {
      const download = await downloadReport(report.id);
      downloadBlob(download);
      setToastType("success");
      setToastMessage("Report exported successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not export report: ${apiErrorMessage(err)}`);
    }
  }

  async function handleExportFiltered() {
    if (!canImportExport) return;
    setToastMessage("");
    try {
      const download = await exportReports({
        search: reportSearch,
        department: filters.department,
        report_type: filters.reportType,
        file_type: filters.fileType,
        status: filters.status,
        uploaded_date: filters.uploadedDate
      });
      downloadBlob(download);
      setToastType("success");
      setToastMessage("Filtered reports exported successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not export reports: ${apiErrorMessage(err)}`);
    }
  }

  async function handleDelete(report) {
    if (!canManageReport(currentUser, report)) return;
    if (!window.confirm("Are you sure you want to delete this report?")) return;
    setToastMessage("");
    try {
      await deleteReport(report.id);
      onReportDeleted(report.id);
      try {
        await onChanged();
      } catch (refreshErr) {
        setError(apiErrorMessage(refreshErr));
      }
      setToastType("success");
      setToastMessage("Report deleted successfully");
    } catch (err) {
      setToastType("error");
      setToastMessage(`Could not delete report: ${apiErrorMessage(err)}`);
    }
  }

  function openReportMessage(report) {
    if (!canImportExport) return;
    setToastMessage("");
    setToastType("success");
    setReportMessage({
      detail: "Send a report summary by Email, WhatsApp, or both.",
      recipient_name: "",
      recipient_email: "",
      recipient_phone: "",
      subject: `Report shared: ${report.report_name}`,
      message_body: `Hello,\n\nSharing the ${report.report_name} report from Agent Concierge.\n\nReport type: ${report.report_type}\nDepartment: ${report.department}\n\nRegards,\nAgent Concierge`,
      attachments: report.file_name ? [report.file_name] : [],
      related_module: "reports",
      related_record_id: report.id
    });
  }

  const departmentFilterOptions = ["All", ...new Set([...reportDepartmentOptions, ...reports.map((report) => report.department)].filter(Boolean))];
  const reportTypeFilterOptions = ["All", ...new Set([...reportTypeOptions, ...reports.map((report) => report.report_type)].filter(Boolean))];
  const fileTypeFilterOptions = ["All", ...reportFileTypeOptions];
  const statusFilterOptions = ["All", ...new Set([...reportStatusOptions, ...reports.map((report) => report.status)].filter(Boolean))];

  return (
    <section className="reports-page screen-stack">
      {toastMessage && <div className={toastType === "error" ? "toast-notification error" : "toast-notification"} role="status">{toastMessage}</div>}
      <section className="dashboard-card vendor-directory-card report-directory-card">
        <div className="vendor-directory-header report-directory-header">
          <div className="vendor-directory-title">
            <span className="vendor-directory-icon"><FileText size={20} /></span>
            <div>
              <h2>Reports</h2>
              <p>Import, export, and manage report files</p>
            </div>
          </div>
          <div className="ticket-action-row report-action-row">
            <label className="vendor-search-control ticket-search-control report-search-control" aria-label="Search reports">
              <Search size={17} />
              <input
                onChange={(event) => setReportSearch(event.target.value)}
                placeholder="Search reports..."
                value={reportSearch}
              />
              {reportSearch && (
                <button aria-label="Clear report search" onClick={() => setReportSearch("")} title="Clear report search" type="button">
                  <X size={15} />
                </button>
              )}
            </label>
            <div className="vendor-filter-wrap">
              <button
                aria-expanded={filtersOpen}
                className="icon-button secondary vendor-filter-button"
                onClick={() => setFiltersOpen((open) => !open)}
                type="button"
              >
                <Filter size={17} />
                <span>Filter</span>
                {activeFilterCount > 0 && <strong>{activeFilterCount}</strong>}
              </button>
              {filtersOpen && (
                <div className="vendor-filter-panel report-filter-panel" role="dialog" aria-label="Report filters">
                  <label>
                    Department
                    <select value={filters.department} onChange={(event) => updateFilter("department", event.target.value)}>
                      {departmentFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Report Type
                    <select value={filters.reportType} onChange={(event) => updateFilter("reportType", event.target.value)}>
                      {reportTypeFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    File Type
                    <select value={filters.fileType} onChange={(event) => updateFilter("fileType", event.target.value)}>
                      {fileTypeFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <label>
                    Status
                    <select value={filters.status} onChange={(event) => updateFilter("status", event.target.value)}>
                      {statusFilterOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                  </label>
                  <VendorField label="Uploaded Date" onChange={(value) => updateFilter("uploadedDate", value)} type="date" value={filters.uploadedDate} />
                  <button className="table-action-button" onClick={clearFilters} type="button">Clear</button>
                </div>
              )}
            </div>
            <button className="icon-button secondary" disabled={!canImportExport} onClick={handleExportFiltered} type="button" title="Export filtered reports">
              <Download size={17} />
              <span>Export Reports</span>
            </button>
            {canImportExport && (
              <button className="primary-button vendor-add-button" onClick={openImportModal} type="button">
                <Plus size={18} />
                <span>Import Report</span>
              </button>
            )}
          </div>
        </div>
        <ReportsTable
          currentUser={currentUser}
          from={filteredReports.length ? reportStartIndex + 1 : 0}
          onDelete={handleDelete}
          onDownload={handleDownload}
          onPageChange={setReportPage}
          onView={setViewingReport}
          page={currentReportPage}
          pageCount={reportPageCount}
          reports={pagedReports}
          to={reportEndIndex}
          total={filteredReports.length}
        />
      </section>

      {importOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal report-modal" onSubmit={submitReportImport} role="dialog" aria-modal="true" aria-label="Import report">
            <div className="section-heading">
              <h2>Import Report</h2>
              <button className="icon-only" onClick={closeImportModal} type="button" aria-label="Close import report">
                <X size={16} />
              </button>
            </div>
            <div className="inventory-upload-area report-upload-area">
              <div>
                <strong>{selectedFileName || "No file selected"}</strong>
                <span>Supported formats: CSV, XLSX, and PDF.</span>
                <p>Select a file, add report metadata, then import it into local report storage.</p>
              </div>
              <div className="inventory-upload-actions">
                <input
                  accept=".csv,.xlsx,.pdf,text/csv,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                  className="visually-hidden"
                  onChange={handleReportFile}
                  ref={reportFileInputRef}
                  type="file"
                />
                <button className="icon-button secondary inventory-choose-file-button" disabled={saving} onClick={chooseReportFile} type="button">
                  <Upload size={17} />
                  <span>{selectedFileName ? "Replace File" : "Choose File"}</span>
                </button>
              </div>
            </div>
            {(fileError || formErrors.file) && <div className="import-inline-error" role="alert">{fileError || formErrors.file}</div>}
            <div className="vendor-form-grid">
              <VendorField error={formErrors.report_name} label="Report Name" onChange={(value) => updateReportField("report_name", value)} value={form.report_name} />
              <label className="vendor-field">
                Report Type
                <select onChange={(event) => updateReportField("report_type", event.target.value)} value={form.report_type}>
                  {reportTypeOptions.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
              </label>
              <label className="vendor-field">
                Department
                <select onChange={(event) => updateReportField("department", event.target.value)} value={form.department}>
                  {(allowedDepartments.length ? allowedDepartments : reportDepartmentOptions).map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                {formErrors.department && <span>{formErrors.department}</span>}
              </label>
              <label className="vendor-field wide">
                Notes
                <textarea onChange={(event) => updateReportField("notes", event.target.value)} rows={4} value={form.notes} />
              </label>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" disabled={saving} onClick={closeImportModal} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">{saving ? "Importing..." : "Import Report"}</button>
            </div>
          </form>
        </div>
      )}

      {viewingReport && (
        <div className="modal-backdrop" role="presentation">
          <section className="vendor-modal report-modal" role="dialog" aria-modal="true" aria-label="Report details">
            <div className="section-heading">
              <h2>Report Details</h2>
              <button className="icon-only" onClick={() => setViewingReport(null)} type="button" aria-label="Close report details">
                <X size={16} />
              </button>
            </div>
            <div className="report-detail-grid">
              <span>Report ID<strong>{viewingReport.report_id}</strong></span>
              <span>Name<strong>{viewingReport.report_name}</strong></span>
              <span>Type<strong>{viewingReport.report_type}</strong></span>
              <span>Department<strong>{viewingReport.department}</strong></span>
              <span>Uploaded By<strong>{viewingReport.uploaded_by_name}</strong></span>
              <span>Uploaded Date<strong>{formatDate(viewingReport.uploaded_at)}</strong></span>
              <span>File<strong>{viewingReport.file_name}</strong></span>
              <span>Size<strong>{formatFileSize(viewingReport.file_size)}</strong></span>
              <span>Status<strong>{viewingReport.status}</strong></span>
              <span className="wide">Notes<strong>{viewingReport.notes || "—"}</strong></span>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" onClick={() => setViewingReport(null)} type="button">Close</button>
              {canImportExport && (
                <button className="icon-button secondary" onClick={() => openReportMessage(viewingReport)} type="button">
                  <Send size={16} />
                  <span>Send Report</span>
                </button>
              )}
              <button className="primary-button" onClick={() => handleDownload(viewingReport)} type="button">
                <Download size={17} />
                <span>Download</span>
              </button>
            </div>
          </section>
        </div>
      )}
      {reportMessage && (
        <CommunicationSendModal
          context={reportMessage}
          onClose={() => setReportMessage(null)}
          onSent={(response) => {
            setToastType("success");
            setToastMessage(response?.message || "Message sent");
          }}
          setError={setError}
        />
      )}
    </section>
  );
}

function ReportsTable({ currentUser, from, onDelete, onDownload, onPageChange, onView, page, pageCount, reports, to, total }) {
  if (!reports.length) {
    return <EmptyState icon={FileText} title="No reports match." detail="Import reports or adjust search and filters." />;
  }

  return (
    <div className="vendor-table-wrap report-table-wrap">
      <table className="vendor-table report-table">
        <thead>
          <tr>
            <th>Report ID</th>
            <th>Report Name</th>
            <th>Report Type</th>
            <th>Department</th>
            <th>Uploaded By</th>
            <th>Uploaded Date</th>
            <th>File Type</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((report) => {
            const canManage = canManageReport(currentUser, report);
            return (
              <tr key={report.id}>
                <td><strong>{report.report_id}</strong></td>
                <td className="ticket-person-cell">
                  <strong>{report.report_name}</strong>
                  <span>{report.file_name} · {formatFileSize(report.file_size)}</span>
                </td>
                <td>{report.report_type}</td>
                <td>{report.department}</td>
                <td className="ticket-person-cell">
                  <strong>{report.uploaded_by_name}</strong>
                  <span>{report.uploaded_by_email}</span>
                </td>
                <td>{formatDate(report.uploaded_at)}</td>
                <td><span className={ticketBadgeClass("ticket-type-pill", report.file_type)}>{report.file_type}</span></td>
                <td><span className={ticketBadgeClass("ticket-status-pill", report.status)}>{report.status}</span></td>
                <td>
                  <div className="table-actions ticket-actions">
                    <button className="icon-only table-icon-button action-edit" onClick={() => onView(report)} title="View report" type="button" aria-label="View report">
                      <Eye size={15} />
                    </button>
                    <button className="icon-only table-icon-button action-send" onClick={() => onDownload(report)} title="Download report" type="button" aria-label="Download report">
                      <Download size={15} />
                    </button>
                    <button
                      className="icon-only table-icon-button action-close"
                      disabled={!canManage}
                      onClick={() => onDelete(report)}
                      title={canManage ? "Delete report" : "Delete not permitted"}
                      type="button"
                      aria-label="Delete report"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="vendor-table-footer">
        <span>Showing {from} to {to} of {total} reports</span>
        <div className="pagination-controls" aria-label="Report pagination">
          <button disabled={page <= 1} onClick={() => onPageChange(Math.max(1, page - 1))} type="button" aria-label="Previous page">
            <ChevronLeft size={16} />
          </button>
          <span>Page {page} of {pageCount}</span>
          <button disabled={page >= pageCount} onClick={() => onPageChange(Math.min(pageCount, page + 1))} type="button" aria-label="Next page">
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

function ModulePlaceholder({ title, icon: Icon, copy }) {
  return (
    <section className="dashboard-card module-placeholder">
      <Icon size={28} />
      <h2>{title}</h2>
      <p>{copy}</p>
    </section>
  );
}

function AccessDenied({ activeLabel, currentUser }) {
  return (
    <section className="dashboard-card module-placeholder access-denied">
      <ShieldAlert size={28} />
      <h2>Access denied</h2>
      <p>{activeLabel} is not available for the {roleLabel(currentUser.role)} role.</p>
    </section>
  );
}

function connectorStatusLabel(status) {
  if (status === "connected") return "Connected";
  if (status === "not_connected") return "Not Connected";
  return "Mock Mode";
}

function ConnectorsPanel({ connectors, googleEmailConfigured, logs, onConfigure, onDisconnect, onSendTest, onTest }) {
  const [cardErrors, setCardErrors] = useState({});
  const [activeMenu, setActiveMenu] = useState("");
  const [selectedType, setSelectedType] = useState("email");
  const [detailsConnector, setDetailsConnector] = useState(null);
  const [logsOpen, setLogsOpen] = useState(false);
  const byType = Object.fromEntries((connectors || []).map((connector) => [connector.connector_type, connector]));
  const cards = [
    byType.email || { connector_type: "email", display_name: "Email", provider: "Mock Email", status: "mock_mode", last_tested_at: "", config: {} },
    byType.whatsapp || { connector_type: "whatsapp", display_name: "WhatsApp", provider: "Mock WhatsApp", status: "mock_mode", last_tested_at: "" }
  ];
  const selectedConnector = cards.find((connector) => connector.connector_type === selectedType) || cards[0];

  function setConnectorError(connectorType, message) {
    setCardErrors((current) => ({ ...current, [connectorType]: message }));
  }

  function clearConnectorError(connectorType) {
    setCardErrors((current) => {
      const next = { ...current };
      delete next[connectorType];
      return next;
    });
  }

  async function handleConfigure(connector) {
    const isEmail = connector.connector_type === "email";
    setSelectedType(connector.connector_type);
    setActiveMenu("");
    clearConnectorError(connector.connector_type);
    if (isEmail && !googleEmailConfigured) {
      setConnectorError("email", "Google email connection is not configured yet.");
      return;
    }
    const payload = await onConfigure(connector);
    if (isEmail && payload && payload.configured === false) {
      setConnectorError("email", payload.message || "Google email connection is not configured yet.");
    }
  }

  async function handleDisconnect(connector) {
    setSelectedType(connector.connector_type);
    setActiveMenu("");
    if (connector.status !== "connected") return;
    const confirmed = window.confirm(`Are you sure you want to disconnect ${connector.display_name || connector.connector_type}?`);
    if (!confirmed) return;
    clearConnectorError(connector.connector_type);
    await onDisconnect(connector.connector_type);
  }

  async function handleTest(connector) {
    setSelectedType(connector.connector_type);
    setActiveMenu("");
    clearConnectorError(connector.connector_type);
    await onTest(connector.connector_type);
  }

  function handleViewDetails(connector) {
    setSelectedType(connector.connector_type);
    setActiveMenu("");
    setDetailsConnector(connector);
  }

  function connectorMeta(connector) {
    const isEmail = connector.connector_type === "email";
    const isConnected = connector.status === "connected";
    const connectedEmail = connector.config?.connected_email || connector.config?.email || "";
    const connectedAt = connector.config?.connected_at || (isConnected ? connector.updated_at : "");
    const provider = connector.provider || (isEmail ? "Mock Email" : "Mock WhatsApp");
    const oauthStatus = !googleEmailConfigured
      ? "Google email connection is not configured yet."
      : connectedEmail
        ? `Connected as ${connectedEmail}`
        : "Configured, ready to connect";
    const whatsappConfigStatus = connector.config?.business_phone_number
      || connector.config?.twilio_whatsapp_sender_number
      || connector.config?.whatsapp_phone_number_id
      ? "Configured"
      : "Mock or not configured";
    return {
      connectedAt,
      provider,
      subtext: isEmail ? "Gmail OAuth" : whatsappConfigStatus,
      serviceStatus: isEmail ? oauthStatus : whatsappConfigStatus
    };
  }

  const selectedIsConnected = selectedConnector?.status === "connected";

  return (
    <section className="dashboard-card connectors-card">
      <div className="connector-section-heading">
        <div className="connector-title-group">
          <span className="connector-section-icon"><Plug size={30} /></span>
          <div>
            <h2>Connectors</h2>
            <p>Configure Email and WhatsApp accounts for bills, reports, reminders, approvals, and vendor messages.</p>
          </div>
        </div>
        <button
          className="connector-logs-button"
          onClick={() => setLogsOpen(true)}
          type="button"
          aria-label="Open communication logs"
        >
          <span className="count-badge"><FileText size={16} /> {logs.length} Logs</span>
          <ChevronRight size={22} />
        </button>
      </div>
      <div className="connector-table-card">
        <table className="connector-table">
          <thead>
            <tr>
              <th>Connector</th>
              <th>Provider</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {cards.map((connector) => {
              const isEmail = connector.connector_type === "email";
              const Icon = isEmail ? Mail : MessageCircle;
              const meta = connectorMeta(connector);
              return (
                <tr
                  className={selectedType === connector.connector_type ? "connector-row selected" : "connector-row"}
                  key={connector.connector_type}
                  onClick={() => setSelectedType(connector.connector_type)}
                >
                  <td>
                    <div className="connector-table-identity">
                      <span className={`connector-table-icon ${connector.connector_type}`}><Icon size={25} /></span>
                      <div>
                        <strong>{connector.display_name || (isEmail ? "Email" : "WhatsApp")}</strong>
                        <span className="connector-provider-badge">{meta.provider}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="connector-provider-cell">
                      <strong>{meta.provider}</strong>
                      <span>{meta.subtext}</span>
                    </div>
                  </td>
                  <td>
                    <span className={`connector-status ${connector.status}`}>{connectorStatusLabel(connector.status)}</span>
                  </td>
                  <td>
                    <div className="connector-menu-cell">
                      <button
                        className="connector-gear-button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedType(connector.connector_type);
                          setActiveMenu((current) => current === connector.connector_type ? "" : connector.connector_type);
                        }}
                        type="button"
                        aria-label={`${connector.display_name || connector.connector_type} actions`}
                      >
                        <Settings size={20} />
                      </button>
                      {activeMenu === connector.connector_type && (
                        <div className="connector-action-menu" onClick={(event) => event.stopPropagation()} role="menu">
                          <button onClick={() => handleConfigure(connector)} type="button" role="menuitem">
                            <Plus size={20} />
                            Connect / Configure
                          </button>
                          <button onClick={() => handleTest(connector)} type="button" role="menuitem">
                            <Send size={20} />
                            Send Test
                          </button>
                          <button onClick={() => handleViewDetails(connector)} type="button" role="menuitem">
                            <Eye size={20} />
                            View Details
                          </button>
                          <span className="connector-action-divider" />
                          <button
                            className="danger"
                            disabled={connector.status !== "connected"}
                            onClick={() => handleDisconnect(connector)}
                            type="button"
                            role="menuitem"
                          >
                            <Trash2 size={20} />
                            Disconnect
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {cards.map((connector) => (
        cardErrors[connector.connector_type] ? (
          <div className="connector-card-error" key={`${connector.connector_type}-error`} role="alert">{cardErrors[connector.connector_type]}</div>
        ) : null
      ))}
      <div className="connector-actions">
        <button className="icon-button primary" onClick={() => handleConfigure(selectedConnector)} type="button">
          <Plus size={18} />
          Connect / Configure
        </button>
        <button className="icon-button secondary" onClick={() => handleTest(selectedConnector)} type="button">
          <Send size={18} />
          Send Test
        </button>
        <button
          className="icon-button secondary danger-inline"
          disabled={!selectedIsConnected}
          onClick={() => handleDisconnect(selectedConnector)}
          type="button"
        >
          <Trash2 size={18} />
          Disconnect
        </button>
      </div>
      {detailsConnector && (
        <div className="modal-backdrop">
          <section className="vendor-modal connector-details-dialog" role="dialog" aria-modal="true" aria-label="Connector details">
            <div className="section-heading">
              <div>
                <h2>{detailsConnector.display_name || connectorStatusLabel(detailsConnector.connector_type)} Details</h2>
                <p>{connectorMeta(detailsConnector).provider}</p>
              </div>
              <button className="icon-only" onClick={() => setDetailsConnector(null)} type="button" aria-label="Close connector details">
                <X size={18} />
              </button>
            </div>
            <dl className="connector-detail-grid">
              <div><dt>Provider</dt><dd>{connectorMeta(detailsConnector).provider}</dd></div>
              <div><dt>Status</dt><dd>{connectorStatusLabel(detailsConnector.status)}</dd></div>
              <div><dt>{detailsConnector.connector_type === "email" ? "Gmail OAuth" : "WhatsApp provider"}</dt><dd>{connectorMeta(detailsConnector).serviceStatus}</dd></div>
              <div><dt>Last connected</dt><dd>{connectorMeta(detailsConnector).connectedAt ? formatCreatedDate(connectorMeta(detailsConnector).connectedAt) : "Never"}</dd></div>
              <div><dt>Last tested</dt><dd>{detailsConnector.last_tested_at ? formatCreatedDate(detailsConnector.last_tested_at) : "Never"}</dd></div>
              <div><dt>Connector owner</dt><dd>Your account</dd></div>
            </dl>
            <div className="vendor-modal-actions">
              <button className="icon-button secondary" onClick={() => setDetailsConnector(null)} type="button">Close</button>
            </div>
          </section>
        </div>
      )}
      {logsOpen && (
        <div className="modal-backdrop">
          <section className="vendor-modal connector-details-dialog" role="dialog" aria-modal="true" aria-label="Communication logs">
            <div className="section-heading">
              <div>
                <h2>Communication Logs</h2>
                <p>{logs.length} recent connector log{logs.length === 1 ? "" : "s"}</p>
              </div>
              <button className="icon-only" onClick={() => setLogsOpen(false)} type="button" aria-label="Close communication logs">
                <X size={18} />
              </button>
            </div>
            <div className="connector-log-list">
              {logs.length === 0 ? (
                <p className="empty">No communication logs yet.</p>
              ) : (
                logs.slice(0, 12).map((log) => (
                  <div className="connector-log-row" key={log.id || `${log.channel}-${log.sent_at}`}>
                    <strong>{log.subject || log.related_module || log.channel || "Message"}</strong>
                    <span>{log.channel || "channel"} · {log.status || "status unavailable"} · {log.sent_at ? formatCreatedDate(log.sent_at) : "Date unavailable"}</span>
                  </div>
                ))
              )}
            </div>
            <div className="vendor-modal-actions">
              <button className="icon-button secondary" onClick={() => setLogsOpen(false)} type="button">Close</button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

function ConnectorConfigModal({ connector, currentUser, onClose, onSaved, setError }) {
  const connectorType = connector.connector_type;
  const isEmail = connectorType === "email";
  const config = connector.config || {};
  const [form, setForm] = useState(() => isEmail ? {
    provider: connector.provider || "Mock Email",
    from_name: config.from_name || "Agent Concierge",
    from_email: config.from_email || "",
    smtp_host: config.smtp_host || "",
    smtp_port: config.smtp_port || "",
    smtp_username: config.smtp_username || "",
    smtp_password: "",
    sendgrid_api_key: "",
    reply_to_email: config.reply_to_email || ""
  } : {
    provider: connector.provider || "Mock WhatsApp",
    business_phone_number: config.business_phone_number || "",
    twilio_account_sid: "",
    twilio_auth_token: "",
    twilio_whatsapp_sender_number: config.twilio_whatsapp_sender_number || "",
    whatsapp_cloud_api_access_token: "",
    whatsapp_phone_number_id: config.whatsapp_phone_number_id || "",
    whatsapp_business_account_id: config.whatsapp_business_account_id || ""
  });
  const [saving, setSaving] = useState(false);

  if (connector.sendTest) {
    return (
      <CommunicationSendModal
        context={{
          channel: connectorType === "whatsapp" ? "whatsapp" : "email",
          detail: `Send a test ${connector.display_name || connectorType} message.`,
          recipient_name: currentUser?.name || "Connector Test",
          recipient_email: connectorType === "email" ? currentUser?.email || "" : "",
          recipient_phone: connectorType === "whatsapp" ? connector.config?.business_phone_number || "+910000000000" : "",
          subject: `${connector.display_name || connectorType} test message`,
          message_body: "This is a test message from Agent Concierge.",
          related_module: "settings",
          related_record_id: `${connectorType}-send-test`
        }}
        onClose={onClose}
        onSent={() => onSaved("Test message sent")}
        setError={setError}
      />
    );
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    if (isEmail) {
      setError("Email is connected with Google OAuth. Use Connect Gmail from the connector card.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await configureWhatsAppConnector(form);
      await onSaved("WhatsApp connector saved");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <form className="vendor-modal connector-modal" onSubmit={submit} role="dialog" aria-modal="true" aria-label="Configure connector">
        <div className="section-heading">
          <div>
            <h2>Configure {isEmail ? "Gmail" : "WhatsApp"}</h2>
            <p>{isEmail ? "Email connects through Google OAuth. Gmail passwords are never entered in Agent Concierge." : "Secrets are read from .env in real mode. Values here are stored only as non-secret display settings."}</p>
          </div>
          <button className="icon-only" onClick={onClose} type="button" aria-label="Close connector form">
            <X size={16} />
          </button>
        </div>
        <div className="vendor-form-grid">
          <label className="vendor-field wide">
            Provider
            <select value={form.provider} onChange={(event) => updateField("provider", event.target.value)}>
              {(isEmail ? ["SMTP", "SendGrid", "Mock Email"] : ["Twilio WhatsApp", "WhatsApp Cloud API", "Mock WhatsApp"]).map((provider) => (
                <option key={provider} value={provider}>{provider}</option>
              ))}
            </select>
          </label>
          {isEmail ? (
            <div className="connector-oauth-note wide">
              <strong>Use Connect Gmail from the connector card.</strong>
              <span>Google will handle login and consent, then return you to Agent Concierge.</span>
            </div>
          ) : (
            <>
              <VendorField label="Business phone number" onChange={(value) => updateField("business_phone_number", value)} value={form.business_phone_number} />
              <VendorField label="Twilio Account SID" onChange={(value) => updateField("twilio_account_sid", value)} value={form.twilio_account_sid} />
              <VendorField label="Twilio Auth Token" onChange={(value) => updateField("twilio_auth_token", value)} type="password" value={form.twilio_auth_token} />
              <VendorField label="Twilio WhatsApp sender number" onChange={(value) => updateField("twilio_whatsapp_sender_number", value)} value={form.twilio_whatsapp_sender_number} />
              <VendorField label="WhatsApp Cloud API access token" onChange={(value) => updateField("whatsapp_cloud_api_access_token", value)} type="password" value={form.whatsapp_cloud_api_access_token} />
              <VendorField label="WhatsApp phone number ID" onChange={(value) => updateField("whatsapp_phone_number_id", value)} value={form.whatsapp_phone_number_id} />
              <VendorField label="WhatsApp business account ID" onChange={(value) => updateField("whatsapp_business_account_id", value)} value={form.whatsapp_business_account_id} />
            </>
          )}
        </div>
        <div className="modal-actions">
          <button className="icon-button secondary" onClick={onClose} type="button">Cancel</button>
          <button className="primary-button" disabled={saving || isEmail} type="submit">{saving ? "Saving..." : "Save Connector"}</button>
        </div>
      </form>
    </div>
  );
}

function ProfileSettingsCard({ currentUser, health }) {
  return (
    <section className="dashboard-card settings-account-card">
      <div className="section-heading">
        <h2>Profile Settings</h2>
        <span className={health?.agent_planner_mode?.includes("openai") ? "mode-badge openai" : "mode-badge"}>
          {aiModeLabel(health)}
        </span>
      </div>
      <div className="plan-grid">
        <div><span>Name</span><strong>{currentUser.name}</strong></div>
        <div><span>Email</span><strong>{currentUser.email}</strong></div>
        <div><span>Role</span><strong>{roleLabel(currentUser.role)}</strong></div>
      </div>
    </section>
  );
}

function SettingsView({ currentUser, health, onChanged, setError, users }) {
  const isAdmin = currentUser.role === "admin";
  const [createOpen, setCreateOpen] = useState(false);
  const [connectors, setConnectors] = useState([]);
  const [googleEmailConfigured, setGoogleEmailConfigured] = useState(false);
  const [communicationLogs, setCommunicationLogs] = useState([]);
  const [connectorModal, setConnectorModal] = useState(null);
  const [connectorToast, setConnectorToast] = useState("");
  const [form, setForm] = useState({ name: "", email: "", password: "", confirmPassword: "", role: "employee" });
  const [formErrors, setFormErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [userSearch, setUserSearch] = useState("");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [userFilters, setUserFilters] = useState({ role: "All" });
  const activeFilterCount = Object.values(userFilters).filter((value) => value !== "All").length;
  const createdUsers = useMemo(
    () => users
      .filter((user) => !user.is_demo && !demoUserEmails.has(String(user.email || "").toLowerCase()))
      .toSorted((first, second) => {
        const secondCreated = new Date(second.created_at || 0).getTime();
        const firstCreated = new Date(first.created_at || 0).getTime();
        return secondCreated - firstCreated || Number(second.id || 0) - Number(first.id || 0);
      }),
    [users]
  );

  const filteredUsers = useMemo(() => {
    const query = userSearch.trim().toLowerCase();
    return createdUsers.filter((user) => {
      const editRole = normalizeRoleValue(user.role || "");
      const matchesQuery = !query || [
        user.name,
        user.email,
        editRole,
        roleLabel(editRole)
      ].join(" ").toLowerCase().includes(query);
      const matchesRole = userFilters.role === "All" || editRole === userFilters.role;
      return matchesQuery && matchesRole;
    });
  }, [createdUsers, userFilters, userSearch]);

  useEffect(() => {
    let cancelled = false;
    async function loadConnectors() {
      try {
        const [connectorPayload, logPayload] = await Promise.all([
          getConnectors(),
          getCommunicationLogs()
        ]);
        if (!cancelled) {
          setConnectors(connectorPayload.connectors || []);
          setGoogleEmailConfigured(Boolean(connectorPayload.google_email_configured));
          setCommunicationLogs(logPayload.logs || []);
        }
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err));
      }
    }
    loadConnectors();
    return () => {
      cancelled = true;
    };
  }, [setError]);

  async function refreshConnectors(message = "") {
    const [connectorPayload, logPayload] = await Promise.all([
      getConnectors(),
      getCommunicationLogs()
    ]);
    setConnectors(connectorPayload.connectors || []);
    setGoogleEmailConfigured(Boolean(connectorPayload.google_email_configured));
    setCommunicationLogs(logPayload.logs || []);
    setConnectorToast(message);
  }

  function updateCreateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormErrors((current) => ({ ...current, [field]: "" }));
  }

  function openCreateUser() {
    if (!isAdmin) return;
    setError("");
    setFormErrors({});
    setForm({ name: "", email: "", password: "", confirmPassword: "", role: "employee" });
    setCreateOpen(true);
  }

  function closeCreateUser() {
    setCreateOpen(false);
    setFormErrors({});
    setForm({ name: "", email: "", password: "", confirmPassword: "", role: "employee" });
  }

  function validateCreateUser() {
    const errors = {};
    if (!form.name.trim()) errors.name = "Required";
    if (!form.email.trim()) {
      errors.email = "Required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email.trim())) {
      errors.email = "Enter a valid email";
    }
    if (!form.password) {
      errors.password = "Required";
    } else if (form.password.length < 6) {
      errors.password = "Use at least 6 characters";
    }
    if (!form.confirmPassword) {
      errors.confirmPassword = "Required";
    } else if (form.password !== form.confirmPassword) {
      errors.confirmPassword = "Passwords do not match";
    }
    if (!roleOptions.includes(normalizeRoleValue(form.role))) {
      errors.role = "Choose a role";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function submitCreate(event) {
    event.preventDefault();
    if (!isAdmin || !validateCreateUser()) return;
    setError("");
    setSaving(true);
    try {
      await createUser({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        role: normalizeRoleValue(form.role)
      });
      closeCreateUser();
      await onChanged();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="settings-page screen-stack">
      {!isAdmin && (
        <div className="vendors-page-header settings-page-header">
          <div className="page-title">
            <div className="directory-title-row">
              <h1>Settings</h1>
            </div>
            <p>Manage your profile and communication connectors.</p>
          </div>
        </div>
      )}
      <ConnectorsPanel
        connectors={connectors}
        googleEmailConfigured={googleEmailConfigured}
        logs={communicationLogs}
        onConfigure={async (connector) => {
          setError("");
          if (connector.connector_type !== "email") {
            setConnectorModal(connector);
            return null;
          }
          try {
            const payload = await startGoogleEmailConnection();
            if (!payload.configured) {
              return payload;
            }
            if (payload.authorization_url) {
              window.location.href = payload.authorization_url;
            }
            return payload;
          } catch (err) {
            setError(apiErrorMessage(err));
            return null;
          }
        }}
        onDisconnect={async (connectorType) => {
          setError("");
          try {
            await (connectorType === "email" ? disconnectGoogleEmail() : disconnectConnector(connectorType));
            await refreshConnectors("Connector disconnected");
          } catch (err) {
            setError(apiErrorMessage(err));
          }
        }}
        onTest={async (connectorType) => {
          setError("");
          try {
            await (connectorType === "email" ? testGoogleEmailConnector() : testWhatsAppConnector());
            await refreshConnectors("Connector test completed");
          } catch (err) {
            setError(apiErrorMessage(err));
          }
        }}
        onSendTest={(connector) => setConnectorModal({ ...connector, sendTest: true })}
      />
      {connectorToast && <div className="toast-notification" role="status">{connectorToast}</div>}
      {isAdmin && (
        <>
          <div className="vendors-page-header settings-page-header user-management-top">
            <div className="page-title">
              <div className="directory-title-row">
                <h1>Users</h1>
                <span className="user-count-badge">
                  <UserRound size={17} />
                  <strong>{createdUsers.length} Users</strong>
                </span>
              </div>
              <p>View and manage all created user accounts.</p>
            </div>
            <div className="vendors-top-action settings-top-action">
              <label className="vendor-search-control user-search-control" aria-label="Search users">
                <Search size={17} />
                <input
                  onChange={(event) => setUserSearch(event.target.value)}
                  placeholder="Search users..."
                  value={userSearch}
                />
                {userSearch && (
                  <button
                    aria-label="Clear user search"
                    onClick={() => setUserSearch("")}
                    title="Clear user search"
                    type="button"
                  >
                    <X size={15} />
                  </button>
                )}
              </label>
              <div className="vendor-filter-wrap">
                <button
                  aria-expanded={filtersOpen}
                  className="icon-button secondary vendor-filter-button"
                  onClick={() => setFiltersOpen((open) => !open)}
                  type="button"
                >
                  <Filter size={17} />
                  <span>Filter</span>
                  {activeFilterCount > 0 && <strong>{activeFilterCount}</strong>}
                </button>
                {filtersOpen && (
                  <div className="vendor-filter-panel user-filter-panel" role="dialog" aria-label="User filters">
                    <label>
                      Role
                      <select value={userFilters.role} onChange={(event) => setUserFilters((current) => ({ ...current, role: event.target.value }))}>
                        <option value="All">All</option>
                        {roleOptions.map((role) => <option key={role} value={role}>{roleLabel(role)}</option>)}
                      </select>
                    </label>
                    <button className="table-action-button" onClick={() => setUserFilters({ role: "All" })} type="button">Clear</button>
                  </div>
                )}
              </div>
              <button className="primary-button vendor-add-button" onClick={openCreateUser} type="button">
                <Plus size={18} />
                <span>Add User</span>
              </button>
            </div>
          </div>
          <UserManagement currentUser={currentUser} filteredUsers={filteredUsers} onChanged={onChanged} setError={setError} totalUsers={createdUsers.length} users={createdUsers} />
        </>
      )}
      {connectorModal && (
        <ConnectorConfigModal
          connector={connectorModal}
          currentUser={currentUser}
          onClose={() => setConnectorModal(null)}
          onSaved={async (message) => {
            setConnectorModal(null);
            await refreshConnectors(message);
          }}
          setError={setError}
        />
      )}
      {createOpen && (
        <div className="modal-backdrop" role="presentation">
          <form className="vendor-modal user-create-modal" onSubmit={submitCreate} role="dialog" aria-modal="true" aria-label="Create user">
            <div className="section-heading">
              <h2>Create User</h2>
              <button className="icon-only" onClick={closeCreateUser} type="button" aria-label="Close create user form">
                <X size={16} />
              </button>
            </div>
            <div className="vendor-form-grid">
              <label className="vendor-field">
                Name
                <input value={form.name} onChange={(event) => updateCreateField("name", event.target.value)} />
                {formErrors.name && <span>{formErrors.name}</span>}
              </label>
              <label className="vendor-field">
                Email
                <input type="email" value={form.email} onChange={(event) => updateCreateField("email", event.target.value)} />
                {formErrors.email && <span>{formErrors.email}</span>}
              </label>
              <label className="vendor-field">
                Password
                <input type="password" value={form.password} onChange={(event) => updateCreateField("password", event.target.value)} />
                {formErrors.password && <span>{formErrors.password}</span>}
              </label>
              <label className="vendor-field">
                Confirm password
                <input type="password" value={form.confirmPassword} onChange={(event) => updateCreateField("confirmPassword", event.target.value)} />
                {formErrors.confirmPassword && <span>{formErrors.confirmPassword}</span>}
              </label>
              <label className="vendor-field wide">
                Role
                <select value={form.role} onChange={(event) => updateCreateField("role", event.target.value)}>
                  {roleOptions.map((role) => <option key={role} value={role}>{roleLabel(role)}</option>)}
                </select>
                {formErrors.role && <span>{formErrors.role}</span>}
              </label>
            </div>
            <div className="vendor-modal-actions">
              <button className="icon-button secondary" onClick={closeCreateUser} type="button">Cancel</button>
              <button className="primary-button" disabled={saving} type="submit">
                {saving ? "Creating..." : "Create User"}
              </button>
            </div>
          </form>
        </div>
      )}
    </section>
  );
}

function UserManagement({ currentUser, filteredUsers, onChanged, setError, totalUsers, users }) {
  const [edits, setEdits] = useState({});
  const [passwords, setPasswords] = useState({});
  const [openMenuUserId, setOpenMenuUserId] = useState(null);
  const [deletingUser, setDeletingUser] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [userPage, setUserPage] = useState(1);
  const USER_PAGE_SIZE = 10;
  const userPageCount = Math.max(1, Math.ceil(filteredUsers.length / USER_PAGE_SIZE));
  const currentUserPage = Math.min(userPage, userPageCount);
  const userStartIndex = filteredUsers.length ? (currentUserPage - 1) * USER_PAGE_SIZE : 0;
  const userEndIndex = Math.min(userStartIndex + USER_PAGE_SIZE, filteredUsers.length);
  const pagedUsers = filteredUsers.slice(userStartIndex, userEndIndex);

  useEffect(() => {
    const next = {};
    users.forEach((user) => {
      next[user.id] = { name: user.name, email: user.email, role: normalizeRoleValue(user.role) };
    });
    setEdits(next);
  }, [users]);

  useEffect(() => {
    setUserPage(1);
  }, [filteredUsers.length]);

  useEffect(() => {
    if (userPage > userPageCount) {
      setUserPage(userPageCount);
    }
  }, [userPage, userPageCount]);

  async function saveUser(userId) {
    setError("");
    try {
      const edit = edits[userId] || {};
      await updateUser(userId, { ...edit, role: normalizeRoleValue(edit.role) });
      await onChanged();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function confirmDeleteUser() {
    if (!deletingUser || deletingUser.id === currentUser.id) return;
    setError("");
    setDeleting(true);
    try {
      await deleteUser(deletingUser.id);
      setDeletingUser(null);
      await onChanged();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setDeleting(false);
    }
  }

  async function resetPassword(userId) {
    setError("");
    try {
      await resetUserPassword(userId, passwords[userId] || "");
      setPasswords({ ...passwords, [userId]: "" });
      setOpenMenuUserId(null);
      await onChanged();
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <section className="dashboard-card user-management-card">
      <div className="vendor-table-wrap user-table-wrap">
        <table className="vendor-table user-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
          {pagedUsers.length === 0 && (
            <tr>
              <td colSpan="5">
                <EmptyState icon={UserRound} title="No users match." detail="Adjust search or filters to show more users." />
              </td>
            </tr>
          )}
          {pagedUsers.map((user) => {
            const edit = edits[user.id] || { name: user.name, email: user.email, role: user.role };
            const isCurrentUser = user.id === currentUser.id;
            const avatarClass = `user-avatar avatar-${user.id % 4}`;
            return (
              <tr key={user.id}>
                <td>
                  <div className="user-identity-cell">
                    <span className={avatarClass}>{initials(user.name || user.email)}</span>
                    <div>
                      <strong>{user.email}</strong>
                      <span>{formatCreatedDate(user.created_at)}</span>
                    </div>
                  </div>
                </td>
                <td>
                  <input className="user-table-input" aria-label={`Name for ${user.email}`} value={edit.name} onChange={(event) => setEdits({ ...edits, [user.id]: { ...edit, name: event.target.value } })} />
                </td>
                <td>
                  <input className="user-table-input" aria-label={`Email for ${user.email}`} type="email" value={edit.email} onChange={(event) => setEdits({ ...edits, [user.id]: { ...edit, email: event.target.value } })} />
                </td>
                <td>
                  <select value={edit.role} onChange={(event) => setEdits({ ...edits, [user.id]: { ...edit, role: event.target.value } })}>
                    {roleOptions.map((role) => <option key={role} value={role}>{roleLabel(role)}</option>)}
                  </select>
                </td>
                <td>
                  <div className="user-actions-cell">
                    <button
                      aria-label={`Edit ${user.email}`}
                      className="table-action-button user-action-icon user-edit-button"
                      onClick={() => saveUser(user.id)}
                      title="Edit user"
                      type="button"
                    >
                      <Pencil size={16} />
                    </button>
                    <button
                      className="table-action-button user-action-icon user-delete-button"
                      disabled={isCurrentUser}
                      onClick={() => setDeletingUser(user)}
                      title={isCurrentUser ? "You cannot delete your own account" : "Delete user"}
                      type="button"
                      aria-label={`Delete ${user.email}`}
                    >
                      <Trash2 size={16} />
                    </button>
                    <div className="user-more-wrap">
                      <button
                        className="table-action-button user-action-icon user-more-button"
                        onClick={() => setOpenMenuUserId((current) => current === user.id ? null : user.id)}
                        type="button"
                        aria-label={`More actions for ${user.email}`}
                        aria-expanded={openMenuUserId === user.id}
                        title="More actions"
                      >
                        <MoreVertical size={16} />
                      </button>
                    </div>
                    {openMenuUserId === user.id && (
                      <div className="user-more-panel" role="dialog" aria-label="User more actions">
                        <label>
                          Reset password
                          <input type="password" value={passwords[user.id] || ""} onChange={(event) => setPasswords({ ...passwords, [user.id]: event.target.value })} />
                        </label>
                        <button className="icon-button secondary" onClick={() => resetPassword(user.id)} type="button">Reset Password</button>
                      </div>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
          </tbody>
        </table>
      </div>
      <div className="vendor-table-footer user-table-footer">
        <p>Showing {filteredUsers.length ? userStartIndex + 1 : 0} to {userEndIndex} of {filteredUsers.length} users</p>
        <div className="pagination-controls" aria-label="User pagination">
          <button
            disabled={currentUserPage === 1}
            onClick={() => setUserPage((page) => Math.max(1, page - 1))}
            type="button"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <button className="active" type="button">{currentUserPage}</button>
          <button
            disabled={currentUserPage === userPageCount}
            onClick={() => setUserPage((page) => Math.min(userPageCount, page + 1))}
            type="button"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      </div>
      {deletingUser && (
        <div className="modal-backdrop" role="presentation">
          <section className="confirm-modal" role="dialog" aria-modal="true" aria-label="Delete user confirmation">
            <div className="section-heading">
              <h2>Delete User</h2>
              <button className="icon-only" onClick={() => setDeletingUser(null)} type="button" aria-label="Cancel delete user">
                <X size={16} />
              </button>
            </div>
            <div className="confirm-body">
              <p>Are you sure you want to delete this user?</p>
              <strong>{deletingUser.email}</strong>
            </div>
            <div className="modal-actions">
              <button className="icon-button secondary" disabled={deleting} onClick={() => setDeletingUser(null)} type="button">
                Cancel
              </button>
              <button className="primary-button danger-action" disabled={deleting} onClick={confirmDeleteUser} type="button">
                {deleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </section>
        </div>
      )}
    </section>
  );
}

export default App;
