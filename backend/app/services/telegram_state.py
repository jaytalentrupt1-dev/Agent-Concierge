"""Telegram in-memory session state for guided flows (Phase C+).

Two independent state stores live here:

  TelegramSession       — multi-turn slot-filling (e.g. create_ticket C.1)
  PendingConfirmation   — single-action confirmation waiting for yes/no or
                          an inline button click (e.g. approve expense C.2)

Both are keyed by user_id (internal app ID from the linked account).
State is in-memory only — backend restart wipes all state (acceptable;
everything has a 30-minute idle timeout anyway).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
_SESSION_TIMEOUT_MINUTES = 30

# ── Session model ─────────────────────────────────────────────────────────────

@dataclass
class TelegramSession:
    """Active multi-turn slot-filling session for one Telegram user."""
    user_id: int
    intent: str                         # e.g. "create_ticket"
    collected: dict[str, str] = field(default_factory=dict)   # slot_name -> value
    awaiting_confirmation: bool = False  # all slots filled, waiting for yes/no
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_activity_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ── Module-level store ─────────────────────────────────────────────────────────
_telegram_sessions: dict[int, TelegramSession] = {}


# ── Public API ────────────────────────────────────────────────────────────────

def is_expired(session: TelegramSession) -> bool:
    """Return True if session has been idle longer than the timeout."""
    idle = datetime.now(timezone.utc) - session.last_activity_at
    return idle > timedelta(minutes=_SESSION_TIMEOUT_MINUTES)


def get_session(user_id: int) -> TelegramSession | None:
    """Return the active session for this user, or None if none/expired.

    Expired sessions are deleted on access (lazy cleanup).
    """
    session = _telegram_sessions.get(user_id)
    if session is None:
        return None
    if is_expired(session):
        logger.info(
            "Telegram session expired for user_id=%s (intent=%s, idle>%dm)",
            user_id, session.intent, _SESSION_TIMEOUT_MINUTES,
        )
        del _telegram_sessions[user_id]
        return None
    return session


def set_session(user_id: int, session: TelegramSession) -> None:
    """Store or replace the session for this user."""
    _telegram_sessions[user_id] = session


def clear_session(user_id: int) -> None:
    """Remove the session for this user (cancel / complete)."""
    _telegram_sessions.pop(user_id, None)


def update_activity(user_id: int) -> None:
    """Reset the idle timeout for an existing session."""
    session = _telegram_sessions.get(user_id)
    if session:
        session.last_activity_at = datetime.now(timezone.utc)


# ── PendingConfirmation — Phase C.2 ──────────────────────────────────────────

@dataclass
class PendingConfirmation:
    """Single-action confirmation awaiting 'yes'/'no' or an inline button.

    Stored when a bot message with inline buttons is sent to the user.
    Allows typed yes/no as a fallback if the user doesn't click a button.
    """
    user_id: int
    action: str        # "approve_expense" | "reject_expense" | "close_ticket"
    entity_id: str     # expense_id string or ticket_id string
    message_id: int    # Telegram message_id of the confirmation message (for editing)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_activity_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


_pending_confirmations: dict[int, PendingConfirmation] = {}


def get_pending_confirmation(user_id: int) -> PendingConfirmation | None:
    """Return active pending confirmation, or None if absent/expired."""
    pc = _pending_confirmations.get(user_id)
    if pc is None:
        return None
    idle = datetime.now(timezone.utc) - pc.last_activity_at
    if idle > timedelta(minutes=_SESSION_TIMEOUT_MINUTES):
        logger.info(
            "PendingConfirmation expired for user_id=%s (action=%s, idle>%dm)",
            user_id, pc.action, _SESSION_TIMEOUT_MINUTES,
        )
        del _pending_confirmations[user_id]
        return None
    return pc


def set_pending_confirmation(user_id: int, pc: PendingConfirmation) -> None:
    """Store a pending confirmation (replaces any existing one)."""
    _pending_confirmations[user_id] = pc


def clear_pending_confirmation(user_id: int) -> None:
    """Remove the pending confirmation for this user."""
    _pending_confirmations.pop(user_id, None)


# ── PendingPinEntry — Phase C.3 ───────────────────────────────────────────────

_PIN_TIMEOUT_MINUTES = 5


@dataclass
class PendingPinEntry:
    """Waiting for the user to type their PIN before executing a write action.

    intent + data encode everything needed to execute after PIN is verified.
    message_id is non-zero for C.2 flows where the confirmation message must
    be edited; 0 for slot-filling flows that send a fresh reply.
    """
    user_id: int
    intent: str    # "create_ticket", "approve_expense", "close_ticket", etc.
    data: dict     # all fields needed to execute the action
    message_id: int = 0
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_activity_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


_pending_pin_entries: dict[int, PendingPinEntry] = {}


def get_pending_pin_entry(user_id: int) -> PendingPinEntry | None:
    """Return active PIN entry, or None if absent/expired (5-min timeout)."""
    ppe = _pending_pin_entries.get(user_id)
    if ppe is None:
        return None
    idle = datetime.now(timezone.utc) - ppe.last_activity_at
    if idle > timedelta(minutes=_PIN_TIMEOUT_MINUTES):
        logger.info(
            "PendingPinEntry expired for user_id=%s (intent=%s, idle>%dm)",
            user_id, ppe.intent, _PIN_TIMEOUT_MINUTES,
        )
        del _pending_pin_entries[user_id]
        return None
    return ppe


def set_pending_pin_entry(user_id: int, ppe: PendingPinEntry) -> None:
    """Store a pending PIN entry (replaces any existing one)."""
    _pending_pin_entries[user_id] = ppe


def clear_pending_pin_entry(user_id: int) -> None:
    """Remove the pending PIN entry for this user."""
    _pending_pin_entries.pop(user_id, None)
