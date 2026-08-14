"""
Content Isolation & RBAC context for user-scoped resources.

Resources are scoped:
  - global:  visible to all users (admin-created)
  - private: visible only to the creator

Roles:
  admin  — full access, can create global resources, sees all items
  member — can create private resources
  viewer — read-only (sees global + own private items)
"""

from contextvars import ContextVar

# ── Request-scoped context ──────────────────────────────────────────────────

current_workspace_id: ContextVar[str] = ContextVar(
    "current_workspace_id", default="default"
)
current_user_id: ContextVar[str] = ContextVar("current_user_id", default="system")
current_user_role: ContextVar[str] = ContextVar("current_user_role", default="admin")

VALID_SCOPES = ("global", "private")
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
    - Otherwise, force 'private'.
    """
    if requested_scope == "global" and can_create_global():
        return "global"
    return "private"


def visibility_filter_sql(table_alias: str = "") -> str:
    """Return a SQL WHERE clause fragment for content-isolation visibility.

    - Admin: sees ALL resources (global + all private from all users).
    - Non-admin: sees global resources + own private resources.
    """
    prefix = f"{table_alias}." if table_alias else ""
    role = get_user_role()
    if role == "admin":
        return "1=1"  # admin sees everything
    # Non-admin: global items + own private items
    return (
        f"({prefix}scope = 'global' OR "
        f"({prefix}scope = 'private' AND {prefix}created_by = ?) OR "
        f"({prefix}scope = 'workspace' AND {prefix}created_by = ?))"
    )


def visibility_params() -> tuple:
    """Return the parameter tuple for visibility_filter_sql."""
    role = get_user_role()
    if role == "admin":
        return ()
    return (get_user_id(), get_user_id())
