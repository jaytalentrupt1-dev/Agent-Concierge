# Database — Agent Admin-IT

**Engine:** SQLite · **Default path:** `backend/admin_agent.db` (override via `ADMIN_AGENT_DB` env var)
**Schema management:** `CREATE TABLE IF NOT EXISTS` in `AdminRepository.init_schema()`
**Access layer:** `backend/app/repositories/admin_repository.py`

No full migration framework. Lightweight compatibility repairs exist for columns added post-launch.

---

## Tables

### `users`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| name | TEXT | |
| email | TEXT UNIQUE | |
| password | TEXT | plain demo password |
| role | TEXT | `admin` / `it_manager` / `finance_manager` / `employee` |
| enabled | BOOLEAN | |
| is_demo | BOOLEAN | demo users hidden from User Management table |
| telegram_chat_id | INTEGER NULL | Telegram chat ID for two-way bot (Phase A) |
| telegram_registered_at | TEXT NULL | ISO datetime when Telegram was linked |
| created_at | TEXT | ISO datetime |

### `sessions`
| Column | Type | Notes |
|--------|------|-------|
| token | TEXT PK | bearer token |
| user_id | INTEGER FK → users | |
| created_at | TEXT | |

### `tickets`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| ticket_id | TEXT | human-readable e.g. `IT-1001`, `ADM-1001` |
| ticket_type | TEXT | `IT` / `Admin` |
| title | TEXT | |
| description | TEXT | |
| category | TEXT | |
| priority | TEXT | Low / Medium / High / Critical |
| status | TEXT | Open / In Progress / Waiting Approval / Resolved / Closed / Overdue |
| branch | TEXT | Pune / Ahmedabad / Vadodara / Noida |
| requester_user_id | INTEGER | |
| requester_name / email / role | TEXT | |
| assigned_role / assigned_team | TEXT | |
| due_date | TEXT | |
| approval_required | BOOLEAN | |
| created_at / updated_at | TEXT | |

### `tasks`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| task_id | TEXT | human-readable |
| title / description | TEXT | |
| category / department | TEXT | |
| assigned_to / assigned_email / assigned_role | TEXT | |
| assigned_user_id | INTEGER | |
| priority / status | TEXT | |
| due_date | TEXT | |
| branch | TEXT | |
| created_by_user_id / name / email / role | TEXT/INT | |
| source | TEXT | `manual` / `conci_ai` / `employee_request` |
| created_at / updated_at | TEXT | |

### `vendors`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| vendor_name / contact_person / email | TEXT | |
| contact_details | TEXT | phone |
| office_address | TEXT | |
| service_provided | TEXT | |
| branch | TEXT | |
| start_date / end_date | TEXT | ISO date; end_date optional |
| billing_amount | INTEGER | compat repair if missing |
| billing_cycle | TEXT | Monthly / Quarterly / Half-yearly / Yearly |
| status | TEXT | active / closed |
| created_at / updated_at | TEXT | |

### `expenses`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| expense_id | TEXT | |
| employee_name / email / role / user_id | TEXT/INT | |
| department / category | TEXT | |
| vendor_merchant | TEXT | |
| amount | REAL | |
| currency | TEXT | default INR |
| expense_date | TEXT | |
| payment_mode | TEXT | |
| receipt_status / receipt_attachment | TEXT | |
| status | TEXT | Draft / Submitted / Pending Approval / Approved / Rejected / Paid / Reimbursed / Needs Info |
| approval_required / approved_by | BOOLEAN/TEXT | |
| policy_exceptions | TEXT | JSON |
| branch | TEXT | |
| created_at / updated_at | TEXT | |

### `inventory_items`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| item_id | TEXT | |
| employee_name | TEXT | |
| serial_no / model_no | TEXT | |
| ram / disk / location | TEXT | |
| status | TEXT | In Use / Extra / Submitted to Vendor |
| notes | TEXT | |
| branch | TEXT | |
| import_batch_id | INTEGER FK → inventory_import_batches; NULL for manual |
| created_at / updated_at | TEXT | |

### `inventory_import_batches`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| filename | TEXT | |
| imported_by_user_id / name | INT/TEXT | |
| total_rows / successful_rows / failed_rows | INTEGER | |
| status | TEXT | Active / Deleted |
| notes | TEXT | |
| created_at | TEXT | |

### `travel_records`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| travel_id | TEXT | |
| employee_name / email / department | TEXT | |
| destination_from / destination_to | TEXT | |
| travel_start_date / travel_end_date | TEXT | |
| purpose / travel_mode | TEXT | |
| estimated_budget / actual_spend | REAL | |
| approval_status / policy_status / booking_status | TEXT | |
| branch | TEXT | |
| google_calendar_event_id / google_sync_status / google_last_synced_at | TEXT | placeholder, not connected |
| created_at / updated_at | TEXT | |

### `calendar_events`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| event_id | TEXT | |
| title / event_type | TEXT | |
| start_datetime / end_datetime | TEXT | |
| location / attendees | TEXT | |
| related_travel_id | TEXT | |
| reminder / notes / status | TEXT | |
| google_* fields | TEXT | placeholder, not connected |
| created_at / updated_at | TEXT | |

### `reports`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| report_id | TEXT | |
| report_name / report_type / department | TEXT | |
| uploader_user_id / name / email / role | INT/TEXT | |
| uploaded_date / file_type / original_filename | TEXT | |
| stored_file_path | TEXT | under `uploads/reports/` |
| file_size / status / notes | TEXT/INT | |
| created_at / updated_at | TEXT | |

### `notifications`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| title / message | TEXT | |
| type | TEXT | e.g. `ticket.created`, `info`, `warning`, `alert` |
| related_entity_type / related_entity_id | TEXT | |
| user_id | INTEGER | targeted user (optional) |
| target_role | TEXT | role-wide notification |
| read_user_ids | TEXT | JSON array of user IDs who read it |
| created_at | TEXT | |

### `agent_logs`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| agent_name | TEXT | `ticket_watchdog` / `expense_monitor` / etc. |
| status | TEXT | `success` / `error` / `info` |
| message | TEXT | |
| data_json | TEXT | JSON extra data |
| created_at | TEXT | |

### `audit_logs`
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | |
| action | TEXT | e.g. `ticket.created`, `vendor.updated` |
| status | TEXT | |
| actor | TEXT | email |
| details | TEXT | JSON |
| created_at | TEXT | |

### `approvals` / `routed_requests` / `agent_plans`
Supporting tables for the Vendor Review Meeting workflow and approval queue. Managed by `approval_service.py` and `workflow.py`.

### `connectors`
Per-user Email / WhatsApp connector configuration. Key: `(user_id, connector_type)`.
Secrets (tokens) are sanitised before returning to the frontend.

### `message_templates`
Seeded communication templates (vendor billing reminder, expense approval, etc.).

### `telegram_registration_codes`
| Column | Type | Notes |
|--------|------|-------|
| code | TEXT PK | 6-digit one-time code |
| user_id | INTEGER FK → users | |
| created_at | TEXT | ISO datetime |
| expires_at | TEXT | ISO datetime (10 min after creation) |
| used | INTEGER | 0 = valid, 1 = used/expired |
