from __future__ import annotations

import secrets

from app.services.audit_service import AuditService


ROLES = {"admin", "it_manager", "finance_manager", "employee"}
PRIVILEGED_ROLES = {"admin", "it_manager", "finance_manager"}
LEGACY_ROLE_MAP = {
    "it": "it_manager",
    "finance": "finance_manager",
    "operation": "employee",
}


def public_user(user: dict) -> dict:
    return {key: value for key, value in user.items() if key != "password"}


def normalize_role(role: str) -> str:
    normalized = str(role or "").strip().lower().replace("-", "_").replace(" ", "_")
    return {
        **LEGACY_ROLE_MAP,
        "admin": "admin",
        "it_manager": "it_manager",
        "finance_manager": "finance_manager",
        "employee": "employee",
    }.get(normalized, role)


def can_view_all(user: dict) -> bool:
    return normalize_role(user.get("role", "")) == "admin"


def can_manage_users(user: dict) -> bool:
    return can_view_all(user)


def can_manage_it(user: dict) -> bool:
    return normalize_role(user.get("role", "")) in {"admin", "it_manager"}


def can_manage_finance(user: dict) -> bool:
    return normalize_role(user.get("role", "")) in {"admin", "finance_manager"}


def can_view_own_only(user: dict) -> bool:
    return normalize_role(user.get("role", "")) == "employee"


def can_approve_request(user: dict, approval: dict) -> bool:
    role = normalize_role(user.get("role", ""))
    return role == "admin" or role in approval.get("required_roles", ["admin"])


def can_approve(user: dict, approval: dict) -> bool:
    return can_approve_request(user, approval)


class AuthService:
    def __init__(self, repository, audit: AuditService):
        self.repository = repository
        self.audit = audit

    def login(self, *, email: str, password: str) -> dict:
        user = self.repository.get_user_by_email(email)
        if not user or not user["enabled"] or user["password"] != password:
            raise ValueError("Invalid email or password")

        token = secrets.token_urlsafe(32)
        self.repository.add_session(token=token, user_id=user["id"])
        self.audit.record(
            "auth.login",
            "completed",
            actor=user["email"],
            details={"user_id": user["id"], "role": user["role"]},
        )
        return {"token": token, "user": public_user(user)}

    def logout(self, *, token: str, user: dict) -> None:
        self.repository.delete_session(token)
        self.audit.record(
            "auth.logout",
            "completed",
            actor=user["email"],
            details={"user_id": user["id"], "role": user["role"]},
        )

    def user_for_token(self, token: str) -> dict:
        session = self.repository.get_session(token)
        if not session:
            return {}
        user = self.repository.get_user(session["user_id"])
        if not user or not user["enabled"]:
            return {}
        return user

    def list_users(self) -> list[dict]:
        return [public_user(user) for user in self.repository.list_users()]

    def create_user(self, *, actor: dict, payload: dict) -> dict:
        self._require_admin(actor)
        role = normalize_role(payload["role"])
        if role not in ROLES:
            raise ValueError("Unsupported role")
        if role in PRIVILEGED_ROLES and not can_manage_users(actor):
            raise ValueError("Only admins can create privileged users")
        if self.repository.get_user_by_email(payload["email"]):
            raise ValueError("User already exists")

        user = self.repository.add_user(
            {
                "email": payload["email"].strip().lower(),
                "password": payload["password"],
                "name": payload["name"],
                "role": role,
                "enabled": True,
            }
        )
        self.audit.record(
            "user.created",
            "completed",
            actor=actor["email"],
            details={
                "actor_user_id": actor["id"],
                "actor_role": actor["role"],
                "target_user_id": user["id"],
                "target_role": user["role"],
            },
        )
        return public_user(user)

    def update_user(self, *, actor: dict, user_id: int, payload: dict) -> dict:
        self._require_admin(actor)
        updates = {}
        if payload.get("name") is not None:
            updates["name"] = payload["name"]
        if payload.get("email") is not None:
            email = payload["email"].strip().lower()
            existing = self.repository.get_user_by_email(email)
            if existing and existing["id"] != user_id:
                raise ValueError("User already exists")
            updates["email"] = email
        if payload.get("role") is not None:
            role = normalize_role(payload["role"])
            if role not in ROLES:
                raise ValueError("Unsupported role")
            updates["role"] = role
        if payload.get("enabled") is not None:
            updates["enabled"] = payload["enabled"]

        user = self.repository.update_user(user_id, **updates)
        if not user:
            raise ValueError("User not found")
        self.audit.record(
            "user.updated",
            "completed",
            actor=actor["email"],
            details={
                "actor_user_id": actor["id"],
                "actor_role": actor["role"],
                "target_user_id": user_id,
                "updates": {key: value for key, value in updates.items() if key != "password"},
            },
        )
        return public_user(user)

    def reset_password(self, *, actor: dict, user_id: int, password: str) -> dict:
        self._require_admin(actor)
        user = self.repository.update_user(user_id, password=password)
        if not user:
            raise ValueError("User not found")
        self.audit.record(
            "user.password_reset",
            "completed",
            actor=actor["email"],
            details={
                "actor_user_id": actor["id"],
                "actor_role": actor["role"],
                "target_user_id": user_id,
            },
        )
        return public_user(user)

    def delete_user(self, *, actor: dict, user_id: int) -> dict:
        self._require_admin(actor)
        if actor["id"] == user_id:
            raise ValueError("You cannot delete your own account")
        user = self.repository.delete_user(user_id)
        if not user:
            raise ValueError("User not found")
        self.audit.record(
            "user.deleted",
            "completed",
            actor=actor["email"],
            details={
                "actor_user_id": actor["id"],
                "actor_role": actor["role"],
                "target_user_id": user_id,
                "target_email": user["email"],
                "target_role": user["role"],
            },
        )
        return public_user(user)

    def _require_admin(self, actor: dict) -> None:
        if not can_manage_users(actor):
            raise PermissionError("Admin role required")
