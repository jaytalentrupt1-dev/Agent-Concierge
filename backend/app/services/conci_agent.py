from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from typing import Any


@dataclass
class IntentResult:
    """Structured intent classification for Conci AI.

    The classifier intentionally returns only intent metadata. Data fetching and
    permission checks stay in the FastAPI layer so no hidden rows are exposed
    before the app's normal role filters run.
    """

    intent: str = "unsupported"
    confidence: float = 0.0
    entities: dict[str, Any] = field(default_factory=dict)
    required_role_scope: str = "all"
    action_type: str = "answer"
    missing_fields: list[str] = field(default_factory=list)
    confirmation_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence or 0), 3)
        return payload


class ConciAgentIntentService:
    """Meaning-first intent helper for Conci AI.

    Local classification uses normalization, typo correction, synonym phrases,
    token overlap, and sequence similarity. If the app uses OpenAI, the API
    layer can pass an OpenAI-classified intent back into ``classify`` while
    keeping app data role-filtered.
    """

    CREATE_TERMS = ("create", "raise", "add", "make", "open", "new")
    UPDATE_TERMS = ("update", "change", "mark", "resolve", "close", "reopen", "set")

    COMMON_TYPOS = {
        "aproval": "approval",
        "aprovals": "approvals",
        "approvel": "approval",
        "approvels": "approvals",
        "calender": "calendar",
        "calenders": "calendars",
        "expence": "expense",
        "expences": "expenses",
        "inventry": "inventory",
        "opentask": "open task",
        "opentasks": "open tasks",
        "panding": "pending",
        "recnt": "recent",
        "deatil": "detail",
        "deatils": "details",
        "sho": "show",
        "shoe": "show",
        "shwo": "show",
        "sumary": "summary",
        "summery": "summary",
        "tascks": "tasks",
        "tikcet": "ticket",
        "tikcets": "tickets",
        "tikets": "tickets",
        "tiket": "ticket",
        "tickts": "tickets",
        "venor": "vendor",
        "vender": "vendor",
        "vendr": "vendor",
    }

    INTENT_DEFINITIONS: dict[str, dict[str, Any]] = {
        "casual_identity": {
            "phrases": ["who are you", "what is your name", "whats your name", "are you human", "are you real"],
            "scope": "all",
            "action_type": "utility",
        },
        "help": {
            "phrases": ["help", "what can you do", "how can you help", "commands", "capabilities", "suggestions"],
            "scope": "all",
            "action_type": "utility",
        },
        "utility_date": {
            "phrases": [
                "today date",
                "todays date",
                "what is today date",
                "what date is it",
                "current date",
                "date today",
            ],
            "scope": "all",
            "action_type": "utility",
        },
        "utility_time": {
            "phrases": ["current time", "what time is it", "time now", "todays time", "today time"],
            "scope": "all",
            "action_type": "utility",
        },
        "create_ticket": {
            "phrases": [
                "create ticket",
                "raise ticket",
                "open ticket",
                "new ticket",
                "laptop not working create ticket",
                "printer not working create ticket",
                "password reset create ticket",
            ],
            "scope": "tickets",
            "action_type": "create",
            "missing_fields": ["ticket type", "category", "title", "description", "priority"],
        },
        "ticket_status": {
            "phrases": ["ticket status", "status of ticket", "check ticket", "pending ticket status", "my pending ticket"],
            "scope": "tickets",
            "action_type": "fetch",
        },
        "ticket_status_update": {
            "phrases": ["resolve ticket", "close ticket", "update ticket status", "change ticket status", "mark ticket resolved"],
            "scope": "tickets",
            "action_type": "update",
            "confirmation_required": True,
        },
        "recent_tickets": {
            "phrases": [
                "recent tickets",
                "latest tickets",
                "last tickets",
                "show recent tickets",
                "ticket history",
                "tickets history",
                "past tickets",
                "earlier tickets",
                "older tickets",
                "resolved ticket history",
                "closed ticket history",
            ],
            "scope": "tickets",
            "action_type": "fetch",
        },
        "open_tickets": {
            "phrases": ["open tickets", "pending tickets", "active tickets", "unresolved tickets"],
            "scope": "tickets",
            "action_type": "fetch",
        },
        "my_tickets": {
            "phrases": ["my tickets", "my ticket", "own tickets", "tickets assigned to me"],
            "scope": "own",
            "action_type": "fetch",
        },
        "create_task": {
            "phrases": ["create task", "create task request", "new task", "assign task", "make task"],
            "scope": "tasks",
            "action_type": "create",
            "missing_fields": ["title", "description", "category", "department", "assignee", "priority"],
        },
        "open_tasks": {
            "phrases": ["open tasks", "open task", "pending tasks", "active tasks", "incomplete tasks"],
            "scope": "tasks",
            "action_type": "fetch",
        },
        "overdue_tasks": {
            "phrases": ["overdue tasks", "late tasks", "past due tasks", "tasks overdue"],
            "scope": "tasks",
            "action_type": "fetch",
        },
        "my_tasks": {
            "phrases": ["my tasks", "my task", "tasks assigned to me", "own tasks"],
            "scope": "own",
            "action_type": "fetch",
        },
        "pending_approvals": {
            "phrases": ["pending approvals", "approval queue", "waiting approvals", "pending requests"],
            "scope": "approvals",
            "action_type": "fetch",
        },
        "vendor_billing": {
            "phrases": ["vendor billing", "vendor bills", "supplier billing", "monthly vendor billing", "vendor payment"],
            "scope": "finance",
            "action_type": "fetch",
        },
        "active_vendors": {
            "phrases": ["active vendors", "current vendors", "vendor list", "show vendors", "active suppliers"],
            "scope": "vendors",
            "action_type": "fetch",
        },
        "vendor_count": {
            "phrases": ["how many vendors", "vendor count", "count vendors", "number of vendors", "total vendors"],
            "scope": "vendors",
            "action_type": "fetch",
        },
        "vendor_details": {
            "phrases": ["vendor details", "food vendor details", "show food vendors", "details of vendors"],
            "scope": "vendors",
            "action_type": "fetch",
        },
        "create_vendor": {
            "phrases": ["add vendor", "create vendor", "new vendor", "add supplier"],
            "scope": "admin",
            "action_type": "create",
            "missing_fields": ["vendor name", "contact person", "email", "phone", "service", "billing"],
        },
        "inventory_recent_updates": {
            "phrases": ["last 5 inventory updates", "recent inventory updates", "newly created inventory", "latest inventory"],
            "scope": "it",
            "action_type": "fetch",
        },
        "inventory_summary": {
            "phrases": ["inventory summary", "inventory status", "stock summary", "device summary", "asset summary"],
            "scope": "inventory",
            "action_type": "fetch",
        },
        "inventory_in_use": {
            "phrases": ["inventory in use", "in use inventory", "devices in use", "assets in use"],
            "scope": "inventory",
            "action_type": "fetch",
        },
        "inventory_submitted_vendor": {
            "phrases": ["submitted to vendor", "devices submitted to vendor", "inventory submitted to vendor"],
            "scope": "inventory",
            "action_type": "fetch",
        },
        "expenses_by_month": {
            "phrases": [
                "expenses month wise",
                "expense month wise",
                "month wise expenses",
                "expenses by month",
                "monthly expenses",
                "expense trend by month",
            ],
            "scope": "finance",
            "action_type": "fetch",
        },
        "expenses_by_category": {
            "phrases": ["expenses by category", "expense by category", "category wise expenses", "expense categories"],
            "scope": "finance",
            "action_type": "fetch",
        },
        "pending_expenses": {
            "phrases": ["pending expenses", "pending expense", "expenses pending approval", "needs info expenses"],
            "scope": "finance",
            "action_type": "fetch",
        },
        "expenses_last_month": {
            "phrases": [
                "last month expenses",
                "previous month expenses",
                "how much expenses happened last month",
                "last month spend",
            ],
            "scope": "finance",
            "action_type": "fetch",
        },
        "expenses_this_month": {
            "phrases": ["expenses this month", "this month expenses", "current month expenses", "monthly spend"],
            "scope": "finance",
            "action_type": "fetch",
        },
        "travel_spend": {
            "phrases": ["travel spend", "travel spending", "travel expense", "travel cost", "trip spend"],
            "scope": "finance",
            "action_type": "fetch",
        },
        "travel_recent_records": {
            "phrases": ["recent travel records", "latest travel records", "travel history", "recent trips"],
            "scope": "finance",
            "action_type": "fetch",
        },
        "calendar_events": {
            "phrases": [
                "calendar events",
                "show calendar events",
                "show calender events",
                "upcoming calendar events",
                "today calendar events",
                "calendar meetings",
                "meeting events",
                "travel calendar",
            ],
            "scope": "finance",
            "action_type": "fetch",
        },
        "reports": {
            "phrases": ["reports", "show reports", "report list", "available reports", "export report", "summarize imported reports"],
            "scope": "reports",
            "action_type": "fetch",
        },
        "users_settings": {
            "phrases": ["users", "show users", "settings users", "user accounts", "roles"],
            "scope": "admin",
            "action_type": "fetch",
        },
        "file_reading": {
            "phrases": ["read file", "attached file", "summarize file", "show columns", "how many rows"],
            "scope": "all",
            "action_type": "fetch",
        },
    }

    DOMAIN_WORDS = {
        word
        for definition in INTENT_DEFINITIONS.values()
        for phrase in definition["phrases"]
        for word in re.findall(r"[a-z0-9]+", phrase)
    } | {
        "admin",
        "approval",
        "approvals",
        "asset",
        "assets",
        "billing",
        "calendar",
        "calendars",
        "category",
        "conci",
        "employee",
        "event",
        "events",
        "expense",
        "expenses",
        "finance",
        "inventory",
        "it",
        "laptop",
        "manager",
        "open",
        "pending",
        "printer",
        "recent",
        "show",
        "status",
        "task",
        "tasks",
        "ticket",
        "tickets",
        "travel",
        "vendor",
        "vendors",
    }

    STOPWORDS = {
        "a",
        "about",
        "any",
        "can",
        "for",
        "give",
        "happened",
        "how",
        "i",
        "is",
        "me",
        "much",
        "of",
        "please",
        "show",
        "tell",
        "the",
        "to",
        "what",
        "whats",
        "with",
        "you",
    }

    @classmethod
    def intent_ids(cls) -> list[str]:
        return sorted(cls.INTENT_DEFINITIONS.keys())

    @classmethod
    def normalize(cls, value: str) -> str:
        text = str(value or "").lower().strip()
        text = re.sub(r"[^a-z0-9@\s._-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        for typo, replacement in cls.COMMON_TYPOS.items():
            text = re.sub(rf"\b{re.escape(typo)}\b", replacement, text)
        corrected: list[str] = []
        for token in text.split():
            corrected.append(cls._correct_token(token))
        return re.sub(r"\s+", " ", " ".join(corrected)).strip()

    @classmethod
    def _correct_token(cls, token: str) -> str:
        if token in cls.DOMAIN_WORDS or token in cls.STOPWORDS or len(token) < 4 or re.search(r"\d", token):
            return token
        best_word = token
        best_score = 0.0
        for word in cls.DOMAIN_WORDS:
            if abs(len(word) - len(token)) > 3:
                continue
            score = SequenceMatcher(None, token, word).ratio()
            if score > best_score:
                best_score = score
                best_word = word
        return best_word if best_score >= 0.78 else token

    @classmethod
    def classify(cls, message: str, openai_intent: str | None = None, openai_entities: dict[str, Any] | None = None) -> IntentResult:
        normalized = cls.normalize(message)
        if not normalized:
            return IntentResult(intent="unsupported", confidence=0.0)

        openai_intent = cls._normalize_intent_id(openai_intent or "")
        if openai_intent in cls.INTENT_DEFINITIONS:
            return cls._result_for(openai_intent, 0.9, normalized, openai_entities or {})

        rule_intent = cls._strong_rule_intent(normalized)
        if rule_intent:
            return cls._result_for(rule_intent, 0.96, normalized)

        best_intent = "unsupported"
        best_score = 0.0
        for intent, definition in cls.INTENT_DEFINITIONS.items():
            for phrase in definition["phrases"]:
                score = cls._phrase_score(normalized, cls.normalize(phrase))
                if score > best_score:
                    best_score = score
                    best_intent = intent

        if best_score < 0.58:
            return cls._result_for("unsupported", best_score, normalized)
        return cls._result_for(best_intent, best_score, normalized)

    @staticmethod
    def _normalize_intent_id(value: str) -> str:
        return re.sub(r"[^a-z0-9_]", "", str(value or "").strip().lower().replace("-", "_").replace(" ", "_"))

    @classmethod
    def _strong_rule_intent(cls, text: str) -> str:
        tokens = set(text.split())
        if "calendar" in tokens or "calendars" in tokens or "event" in tokens or "events" in tokens:
            return "calendar_events"
        if {"date", "today"} <= tokens or "todays date" in text or "current date" in text:
            return "utility_date"
        if "what time" in text or "current time" in text or "time now" in text:
            return "utility_time"
        create_terms_without_open = {"create", "raise", "add", "make", "new"}
        if "ticket" in tokens or "tickets" in tokens:
            if tokens.intersection(cls.UPDATE_TERMS) and re.search(r"\b(?:it|adm)-\d+\b", text, re.IGNORECASE):
                return "ticket_status_update"
            if "status" in tokens:
                return "ticket_status"
            if "recent" in tokens or "latest" in tokens or "history" in tokens or "earlier" in tokens or "older" in tokens or "past" in tokens:
                return "recent_tickets"
            if "my" in tokens or "own" in tokens:
                return "my_tickets"
            if "open" in tokens or "pending" in tokens:
                return "open_tickets"
            if tokens.intersection(create_terms_without_open) and "tickets" not in tokens:
                return "create_ticket"
        if "task" in tokens or "tasks" in tokens:
            if "overdue" in tokens or "late" in tokens:
                return "overdue_tasks"
            if "my" in tokens or "own" in tokens:
                return "my_tasks"
            if "open" in tokens or "pending" in tokens:
                return "open_tasks"
            if tokens.intersection(create_terms_without_open) and "tasks" not in tokens:
                return "create_task"
        if "approval" in tokens or "approvals" in tokens or "requests" in tokens and "pending" in tokens:
            return "pending_approvals"
        if "inventory" in tokens:
            if "submitted" in tokens and "vendor" in tokens:
                return "inventory_submitted_vendor"
            if "use" in tokens or "using" in tokens:
                return "inventory_in_use"
            if "update" in tokens or "updates" in tokens or "recent" in tokens or "latest" in tokens or "newly" in tokens:
                return "inventory_recent_updates"
            return "inventory_summary"
        if "vendor" in tokens or "vendors" in tokens or "supplier" in tokens or "suppliers" in tokens:
            if tokens.intersection(cls.CREATE_TERMS):
                return "create_vendor"
            if "how many" in text or "count" in tokens or "number" in tokens or "total" in tokens:
                return "vendor_count"
            if "billing" in tokens or "bill" in tokens or "bills" in tokens:
                return "vendor_billing"
            if "detail" in tokens or "details" in tokens or "food" in tokens:
                return "vendor_details"
            return "active_vendors"
        if "expense" in tokens or "expenses" in tokens or "spend" in tokens:
            if "pending" in tokens or "approval" in tokens:
                return "pending_expenses"
            if "category" in tokens or "categories" in tokens:
                return "expenses_by_category"
            if "last" in tokens or "previous" in tokens:
                return "expenses_last_month"
            if "month" in tokens and ("wise" in tokens or "by" in tokens or "monthly" in tokens):
                return "expenses_by_month"
            if "this" in tokens or "current" in tokens or "monthly" in tokens:
                return "expenses_this_month"
        if "travel" in tokens or "trip" in tokens:
            if "recent" in tokens or "latest" in tokens or "history" in tokens or "records" in tokens:
                return "travel_recent_records"
            return "travel_spend"
        if "report" in tokens or "reports" in tokens:
            return "reports"
        if "user" in tokens or "users" in tokens or "settings" in tokens or "roles" in tokens:
            return "users_settings"
        if "file" in tokens or "attachment" in tokens or "attached" in tokens:
            return "file_reading"
        return ""

    @staticmethod
    def _phrase_score(text: str, phrase: str) -> float:
        if not phrase:
            return 0.0
        if phrase in text:
            return 1.0
        text_tokens = set(text.split())
        phrase_tokens = set(phrase.split())
        if not phrase_tokens:
            return 0.0
        important_phrase_tokens = {token for token in phrase_tokens if token not in ConciAgentIntentService.STOPWORDS}
        important_text_tokens = {token for token in text_tokens if token not in ConciAgentIntentService.STOPWORDS}
        token_score = len(important_text_tokens & important_phrase_tokens) / max(len(important_phrase_tokens), 1)
        sequence_score = SequenceMatcher(None, text, phrase).ratio()
        trigram_score = ConciAgentIntentService._ngram_score(text, phrase)
        return max(token_score, sequence_score, trigram_score)

    @staticmethod
    def _ngram_score(left: str, right: str, n: int = 3) -> float:
        def grams(value: str) -> set[str]:
            compact = re.sub(r"\s+", "", value)
            if len(compact) <= n:
                return {compact} if compact else set()
            return {compact[index:index + n] for index in range(len(compact) - n + 1)}

        left_grams = grams(left)
        right_grams = grams(right)
        if not left_grams or not right_grams:
            return 0.0
        return len(left_grams & right_grams) / len(right_grams)

    @classmethod
    def _result_for(
        cls,
        intent: str,
        confidence: float,
        normalized_text: str,
        extra_entities: dict[str, Any] | None = None,
    ) -> IntentResult:
        definition = cls.INTENT_DEFINITIONS.get(intent, {})
        entities = cls.extract_entities(normalized_text)
        if extra_entities:
            entities.update({key: value for key, value in extra_entities.items() if value not in (None, "", [])})
        return IntentResult(
            intent=intent,
            confidence=float(confidence or 0.0),
            entities=entities,
            required_role_scope=str(definition.get("scope", "all")),
            action_type=str(definition.get("action_type", "answer")),
            missing_fields=list(definition.get("missing_fields", [])),
            confirmation_required=bool(definition.get("confirmation_required", False)),
        )

    @staticmethod
    def extract_entities(normalized_text: str) -> dict[str, Any]:
        entities: dict[str, Any] = {}
        ticket_match = re.search(r"\b(?:it|adm)-\d+\b", normalized_text, re.IGNORECASE)
        if ticket_match:
            entities["ticket_id"] = ticket_match.group(0).upper()
        number_match = re.search(r"\b(\d+)\b", normalized_text)
        if number_match:
            try:
                entities["limit"] = int(number_match.group(1))
            except ValueError:
                pass
        for service in ("food", "transport", "it services", "office supplies", "security", "housekeeping", "other"):
            if service in normalized_text:
                entities["service"] = service.title() if service != "it services" else "IT Services"
                break
        if "last month" in normalized_text or "previous month" in normalized_text:
            entities["date_range"] = "last_month"
        elif "this month" in normalized_text or "current month" in normalized_text:
            entities["date_range"] = "this_month"
        return entities

    @classmethod
    def wants_create(cls, normalized_text: str) -> bool:
        return cls.classify(normalized_text).action_type == "create"

    @classmethod
    def wants_ticket_status_lookup(cls, normalized_text: str) -> bool:
        return cls.classify(normalized_text).intent == "ticket_status"

    @classmethod
    def wants_inventory_updates(cls, normalized_text: str) -> bool:
        return cls.classify(normalized_text).intent == "inventory_recent_updates"

    @classmethod
    def wants_monthly_expenses(cls, normalized_text: str) -> bool:
        return cls.classify(normalized_text).intent == "expenses_by_month"

    @classmethod
    def wants_last_month_travel_spend(cls, normalized_text: str) -> bool:
        return cls.classify(normalized_text).intent == "travel_spend" and cls.classify(normalized_text).entities.get("date_range") == "last_month"
