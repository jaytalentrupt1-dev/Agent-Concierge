export const billingCycleAbbreviations = {
  Monthly: "M",
  Quarterly: "Q",
  "Half-yearly": "HY",
  Yearly: "Y"
};

const billingCycleAliases = {
  m: "Monthly",
  monthly: "Monthly",
  q: "Quarterly",
  quarterly: "Quarterly",
  hy: "Half-yearly",
  "half-yearly": "Half-yearly",
  halfyearly: "Half-yearly",
  "half yearly": "Half-yearly",
  y: "Yearly",
  yearly: "Yearly"
};

export function normalizeBillingAmount(value) {
  const amount = Number(String(value ?? "").replace(/,/g, "").trim());
  return Number.isFinite(amount) ? amount : 0;
}

export function normalizeBillingCycle(value) {
  const normalized = String(value ?? "").trim();
  return billingCycleAliases[normalized.toLowerCase()] || normalized;
}

export function formatVendorBilling(value) {
  const amount = normalizeBillingAmount(value?.billing_amount);
  const billingCycle = normalizeBillingCycle(value?.billing_cycle);
  const cycle = billingCycleAbbreviations[billingCycle] || billingCycle || "";
  if (!amount || amount <= 0) return cycle ? `— / ${cycle}` : "—";
  return `₹${amount} / ${cycle}`;
}
