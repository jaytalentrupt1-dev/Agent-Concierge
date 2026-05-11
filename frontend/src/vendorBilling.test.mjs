import assert from "node:assert/strict";
import { formatVendorBilling } from "./vendorBilling.js";

assert.equal(formatVendorBilling({ billing_amount: 1000, billing_cycle: "Quarterly" }), "₹1000 / Q");
assert.equal(formatVendorBilling({ billing_amount: 4322, billing_cycle: "Quarterly" }), "₹4322 / Q");
assert.equal(formatVendorBilling({ billing_amount: 2000, billing_cycle: "Monthly" }), "₹2000 / M");
assert.equal(formatVendorBilling({ billing_amount: 43231, billing_cycle: "Monthly" }), "₹43231 / M");
assert.equal(formatVendorBilling({ billing_amount: 5232, billing_cycle: "Half-yearly" }), "₹5232 / HY");
assert.equal(formatVendorBilling({ billing_amount: 9000, billing_cycle: "Yearly" }), "₹9000 / Y");
assert.equal(formatVendorBilling({ billing_amount: "4,322", billing_cycle: "q" }), "₹4322 / Q");
assert.equal(formatVendorBilling({ billing_amount: 0, billing_cycle: "Quarterly" }), "— / Q");

console.log("vendor billing formatter tests passed");
