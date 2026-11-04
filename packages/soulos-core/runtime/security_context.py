"""Immutable security context for MCP and runtime calls."""

from __future__ import annotations

from dataclasses import dataclass, field

from auth import AccountContext

SCOPE_MCP_ADMIN_MSV_WRITE = "mcp:admin:msv_write"


@dataclass(frozen=True)
class SecurityContext:
    """Transport-bound principal for tenant-scoped MCP/runtime operations."""

    account: AccountContext
    scopes: frozenset[str] = field(default_factory=frozenset)
    principal_hash: str | None = None

    @property
    def account_id(self) -> str | None:
        return self.account.account_id

    @property
    def tenant_id(self) -> str | None:
        return self.account.account_id

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes

    def has_admin_msv_write(self) -> bool:
        return self.has_scope(SCOPE_MCP_ADMIN_MSV_WRITE)


def security_context_from_account(
    account: AccountContext,
    *,
    scopes: frozenset[str] | None = None,
    principal_hash: str | None = None,
    admin_tools_enabled: bool = False,
) -> SecurityContext:
    resolved = set(scopes or ())
    if admin_tools_enabled:
        resolved.add(SCOPE_MCP_ADMIN_MSV_WRITE)
    return SecurityContext(
        account=account,
        scopes=frozenset(resolved),
        principal_hash=principal_hash,
    )
