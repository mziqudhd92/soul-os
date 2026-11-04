"""Outbound MCP client: SSRF-safe, pinned schemas, budgets, untrusted wraps."""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("mcp_client")

SOULOS_MCP_CLIENT = os.getenv("SOULOS_MCP_CLIENT", "0").lower() in ("1", "true", "yes")
SOULOS_MCP_ALLOW_PRIVATE_NET = os.getenv("SOULOS_MCP_ALLOW_PRIVATE_NET", "0").lower() in (
    "1",
    "true",
    "yes",
)
MAX_TOOL_OUTPUT_BYTES = int(os.getenv("SOULOS_MCP_MAX_TOOL_OUTPUT_BYTES", "16384"))
MAX_TOOL_ITERATIONS = int(os.getenv("SOULOS_MCP_MAX_TOOL_ITERATIONS", "3"))
CALL_TIMEOUT_SECONDS = float(os.getenv("SOULOS_MCP_CALL_TIMEOUT_SECONDS", "8"))
CIRCUIT_OPEN_SECONDS = float(os.getenv("SOULOS_MCP_CIRCUIT_OPEN_SECONDS", "60"))

_SECRETISH = re.compile(
    r"(?i)(api[_-]?key|secret|password|bearer\s+[a-z0-9._-]{20,}|sk-[a-z0-9]{20,})"
)
_SOUL_DUMP = re.compile(r"(?i)(baseline_msv|system_prompt|\"attachment_style\")")


class AllowToolSpec(BaseModel):
    name: str
    description_override: str | None = None
    schema_sha256: str | None = None


class OutboundServerConfig(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    url: str
    allow_tools: list[AllowToolSpec] = Field(default_factory=list)
    auth_env_key: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _name_safe(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError("server name must be alphanumeric/_/-")
        return v

    @field_validator("url")
    @classmethod
    def _url_http(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("url must be http(s)")
        if parsed.query:
            raise ValueError("url must not contain query-string secrets")
        return v


class OutboundMcpConfig(BaseModel):
    servers: list[OutboundServerConfig] = Field(default_factory=list)


@dataclass
class _Circuit:
    failures: int = 0
    open_until: float = 0.0

    def is_open(self) -> bool:
        return time.monotonic() < self.open_until

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= 2:
            self.open_until = time.monotonic() + CIRCUIT_OPEN_SECONDS

    def record_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0


@dataclass
class OutboundMcpClient:
    config: OutboundMcpConfig
    _circuits: dict[str, _Circuit] = field(default_factory=dict)
    # namespaced tool name → last tools/list entry used for schema pin checks
    _schema_cache: dict[str, dict[str, Any]] = field(default_factory=dict)

    def enabled(self) -> bool:
        return SOULOS_MCP_CLIENT and bool(self.config.servers)

    def namespaced(self, server: str, tool: str) -> str:
        return f"{server}__{tool}"

    def parse_namespaced(self, name: str) -> tuple[str, str] | None:
        if "__" not in name:
            return None
        server, tool = name.split("__", 1)
        return server, tool

    def tools_for_soul(
        self, allowed_mcp_servers: list[str] | None
    ) -> list[dict[str, Any]]:
        """Intersect global servers with per-soul allowlist.

        Schema listing works even when SOULOS_MCP_CLIENT=0 so unit tests and
        dry-runs can inspect allowlists; call_tool still requires enabled().
        """
        if not self.config.servers:
            return []
        if allowed_mcp_servers is not None and len(allowed_mcp_servers) == 0:
            return []
        out: list[dict[str, Any]] = []
        for server in self.config.servers:
            if allowed_mcp_servers is not None and server.name not in allowed_mcp_servers:
                continue
            for spec in server.allow_tools:
                desc = spec.description_override or f"Outbound tool {spec.name}"
                # Cap description length (schema sanitizer).
                desc = desc[:240]
                out.append(
                    {
                        "name": self.namespaced(server.name, spec.name),
                        "description": desc,
                        "server": server.name,
                        "tool": spec.name,
                    }
                )
        return out

    def active_tool_names(self, allowed_mcp_servers: list[str] | None) -> list[str]:
        return [t["name"] for t in self.tools_for_soul(allowed_mcp_servers)]

    def assert_url_safe(self, url: str) -> None:
        """Resolve DNS and block private/link-local unless explicitly allowed."""
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            raise ValueError("URL missing host")
        try:
            infos = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
        except socket.gaierror as e:
            raise ValueError(f"DNS resolution failed for {host}") from e
        for info in infos:
            ip_str = info[4][0]
            ip = ipaddress.ip_address(ip_str)
            if SOULOS_MCP_ALLOW_PRIVATE_NET:
                continue
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                raise ValueError(f"Blocked private/link-local address: {ip_str}")

    def wrap_untrusted_output(self, server: str, text: str) -> str:
        from runtime.memory_cognitive import strip_control_chars

        truncated = text.encode("utf-8")[:MAX_TOOL_OUTPUT_BYTES].decode(
            "utf-8", errors="ignore"
        )
        # Strip common instruction-override patterns.
        cleaned = re.sub(
            r"(?i)(ignore previous instructions|system prompt|you are now)",
            "[filtered]",
            truncated,
        )
        cleaned = strip_control_chars(cleaned)
        return (
            f'<untrusted_tool_output server="{server}">\n{cleaned}\n'
            f"</untrusted_tool_output>"
        )

    def validate_egress_args(self, arguments: dict[str, Any]) -> None:
        blob = json_dumps_safe(arguments)
        if _SECRETISH.search(blob) or _SOUL_DUMP.search(blob):
            raise ValueError(
                "Outbound tool arguments appear to contain secrets or soul dumps"
            )

    def pin_matches(self, spec: AllowToolSpec, remote_schema: dict | None) -> bool:
        if not spec.schema_sha256:
            return True
        digest = hashlib.sha256(
            json_dumps_safe(remote_schema or {}).encode("utf-8")
        ).hexdigest()
        return digest == spec.schema_sha256

    def _auth_headers(self, server: OutboundServerConfig) -> dict[str, str]:
        headers = dict(server.headers)
        if server.auth_env_key:
            token = os.environ.get(server.auth_env_key, "")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        return headers

    async def refresh_schema_cache(
        self,
        server: OutboundServerConfig,
        *,
        http_client: httpx.AsyncClient,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Fetch tools/list and cache entries for schema pin verification."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        resp = await http_client.post(
            server.url, json=payload, headers=headers or self._auth_headers(server)
        )
        if resp.is_redirect:
            raise RuntimeError("Redirects are disabled for outbound MCP (SSRF)")
        resp.raise_for_status()
        try:
            data = resp.json()
        except Exception as e:
            raise ValueError("tools/list response was not JSON") from e
        tools = (
            (data.get("result") or {}).get("tools")
            if isinstance(data, dict)
            else None
        )
        if not isinstance(tools, list):
            raise ValueError("tools/list missing result.tools")
        for entry in tools:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            if isinstance(name, str) and name:
                self._schema_cache[self.namespaced(server.name, name)] = entry

    async def _assert_schema_pin(
        self,
        server: OutboundServerConfig,
        spec: AllowToolSpec,
        *,
        http_client: httpx.AsyncClient,
        headers: dict[str, str],
    ) -> None:
        if not spec.schema_sha256:
            return
        cache_key = self.namespaced(server.name, spec.name)
        # Always re-fetch when pinned so rug-pulls after first call are caught.
        await self.refresh_schema_cache(server, http_client=http_client, headers=headers)
        remote = self._schema_cache.get(cache_key)
        if remote is None:
            raise ValueError(
                f"Pinned tool {spec.name} missing from remote tools/list "
                f"(server={server.name})"
            )
        if not self.pin_matches(spec, remote):
            raise ValueError(
                f"Tool schema pin mismatch for {cache_key} (possible rug-pull)"
            )

    async def call_tool(
        self,
        namespaced_name: str,
        arguments: dict[str, Any],
        *,
        http_client: httpx.AsyncClient | None = None,
        skip_dns_check: bool = False,
        allow_when_disabled: bool = False,
    ) -> str:
        if not SOULOS_MCP_CLIENT and not allow_when_disabled:
            raise RuntimeError("Outbound MCP client disabled (SOULOS_MCP_CLIENT=0)")
        parsed = self.parse_namespaced(namespaced_name)
        if not parsed:
            raise ValueError(f"Not a namespaced outbound tool: {namespaced_name}")
        server_name, tool_name = parsed
        server = next((s for s in self.config.servers if s.name == server_name), None)
        if server is None:
            raise ValueError(f"Unknown outbound server: {server_name}")
        spec = next((t for t in server.allow_tools if t.name == tool_name), None)
        if spec is None:
            raise ValueError(f"Tool {tool_name} not in allow_tools for {server_name}")

        circuit = self._circuits.setdefault(server_name, _Circuit())
        if circuit.is_open():
            raise RuntimeError(f"Circuit open for outbound MCP server {server_name}")

        self.validate_egress_args(arguments)
        if not skip_dns_check:
            self.assert_url_safe(server.url)

        headers = self._auth_headers(server)

        owns_client = http_client is None
        client = http_client or httpx.AsyncClient(
            timeout=CALL_TIMEOUT_SECONDS, follow_redirects=False
        )
        try:
            await self._assert_schema_pin(
                server, spec, http_client=client, headers=headers
            )
            # Minimal JSON-RPC-ish call; hosts may vary — tests mock this path.
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
            }
            resp = await client.post(server.url, json=payload, headers=headers)
            if resp.is_redirect:
                circuit.record_failure()
                raise RuntimeError("Redirects are disabled for outbound MCP (SSRF)")
            resp.raise_for_status()
            circuit.record_success()
            return self.wrap_untrusted_output(server_name, resp.text)
        except Exception:
            circuit.record_failure()
            raise
        finally:
            if owns_client:
                await client.aclose()


_client: OutboundMcpClient | None = None


def json_dumps_safe(obj: Any) -> str:
    import json

    return json.dumps(obj, sort_keys=True, default=str)


def get_outbound_client() -> OutboundMcpClient:
    global _client
    if _client is None:
        _client = OutboundMcpClient(config=OutboundMcpConfig())
    return _client


def set_outbound_client(client: OutboundMcpClient | None) -> None:
    global _client
    _client = client


def load_outbound_config_from_env() -> OutboundMcpConfig:
    """Load from SOULOS_MCP_SERVERS_JSON (Pydantic-validated; no secrets in URL)."""
    raw = os.getenv("SOULOS_MCP_SERVERS_JSON", "").strip()
    if not raw:
        return OutboundMcpConfig()
    import json

    data = json.loads(raw)
    if isinstance(data, list):
        return OutboundMcpConfig(servers=data)
    return OutboundMcpConfig.model_validate(data)
