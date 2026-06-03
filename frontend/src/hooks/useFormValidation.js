import { useState } from "react";

/**
 * useFormValidation — lightweight, rule-based form validation hook.
 *
 * Supported rule keys per field:
 *   required    — true (auto-label) | string (custom message)
 *   minLength   — number
 *   maxLength   — number
 *   email       — true
 *   min         — number (numeric value)
 *   max         — number (numeric value)
 *   pattern     — RegExp
 *   patternMessage — string (shown when pattern fails)
 *
 * Returns:
 *   errors    — { [field]: errorString }
 *   validate  — (data) => boolean  (also sets errors state)
 *   clearError — (field) => void
 *   clearAll  — () => void
 */
export function useFormValidation(rules) {
  const [errors, setErrors] = useState({});

  const validate = (data) => {
    const newErrors = {};

    for (const [field, rule] of Object.entries(rules)) {
      const value = data[field];

      // Required
      if (rule.required && !value?.toString().trim()) {
        newErrors[field] =
          rule.required === true ? `${field} is required` : rule.required;
        continue;
      }

      // Min length
      if (rule.minLength && value?.length < rule.minLength) {
        newErrors[field] = `Minimum ${rule.minLength} characters required`;
        continue;
      }

      // Max length
      if (rule.maxLength && value?.length > rule.maxLength) {
        newErrors[field] = `Maximum ${rule.maxLength} characters allowed`;
        continue;
      }

      // Email
      if (rule.email && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
          newErrors[field] = "Enter a valid email address";
          continue;
        }
      }

      // Min value
      if (rule.min !== undefined && Number(value) < rule.min) {
        newErrors[field] = `Minimum value is ${rule.min}`;
        continue;
      }

      // Max value
      if (rule.max !== undefined && Number(value) > rule.max) {
        newErrors[field] = `Maximum value is ${rule.max}`;
        continue;
      }

      // Pattern
      if (rule.pattern && !rule.pattern.test(value)) {
        newErrors[field] = rule.patternMessage || "Invalid format";
        continue;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const clearError = (field) => {
    setErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const clearAll = () => setErrors({});

  return { errors, validate, clearError, clearAll };
}
