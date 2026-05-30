"""
Workspace & RBAC context for multi-tenant resource isolation.

Every request carries a workspace context (via X-Workspace-Id header).
Resources are scoped: global (visible everywhere) or workspace (team-only).

Roles:
  admin  — full access, can create global resources
  member — can create/edit workspace-scoped resources
  viewer — read-only within workspace
"""

from contextvars import ContextVar

# ── Request-scoped context ──────────────────────────────────────────────────

current_workspace_id: ContextVar[str] = ContextVar(
    "current_workspace_id", default="default"
)
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="system")
current_user_role: ContextVar[str] = ContextVar("current_user_role", default="admin")

VALID_SCOPES = ("global", "workspace")
VALID_ROLES = ("admin", "member", "viewer")


def get_workspace_id() -> str:
    return current_workspace_id.get()


def get_user_id() -> str:
    return current_user_id.get()


def get_user_role() -> str:
    return current_user_role.get()


def can_create_global() -> bool:
    """Only admins can create global resources."""
    return current_user_role.get() == "admin"


def can_write() -> bool:
    """Admins and members can create/edit. Viewers cannot."""
    return current_user_role.get() in ("admin", "member")


def can_read() -> bool:
    """All roles can read."""
    return True


def effective_scope(requested_scope: str | None) -> str:
    """Determine the actual scope for a new resource.

    - If admin requests 'global', grant it.
    - Otherwise, force 'workspace'.
    """
    if requested_scope == "global" and can_create_global():
        return "global"
    return "workspace"


def visibility_filter_sql(table_alias: str = "") -> str:
    """Return a SQL WHERE clause fragment for workspace-aware visibility.

    Returns rows that are either:
      - scope = 'global' (visible everywhere), OR
      - scope = 'workspace' AND workspace_id matches current workspace

    Non-admin users additionally only see their own items (created_by = user)
    plus global items.
    """
    prefix = f"{table_alias}." if table_alias else ""
    role = get_user_role()
    if role == "admin":
        return f"({prefix}scope = 'global' OR ({prefix}scope = 'workspace' AND {prefix}workspace_id = ?))"
    # Non-admin: own items in workspace + global items
    return (
        f"({prefix}scope = 'global' OR "
        f"({prefix}scope = 'workspace' AND {prefix}workspace_id = ? AND {prefix}created_by = ?))"
    )


def visibility_params() -> tuple:
    """Return the parameter tuple for visibility_filter_sql."""
    role = get_user_role()
    if role == "admin":
        return (get_workspace_id(),)
    return (get_workspace_id(), get_user_id())
