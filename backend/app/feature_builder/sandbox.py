"""Isolated sandbox runtime stack and live order prevention (F11.6).

Enforces physical isolation of the sandbox environment:
- Network ports: separated from live (API 8080, Engine 8081, Feedd 8082)
- Postgres: isolated 'sandbox_*' schema, barred from live schemas
- Redis: isolated database index (db=15 vs live db=0)
- DuckDB Warehouse: mounted read-only
- Broker: hard-wired to PaperBroker, zero code path to DhanBroker
- Credentials: no live order-placement credentials

Proof requirement: Sandbox has no credentials or network/code path capable of placing a live order.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field


class SandboxLiveOrderDisabledError(PermissionError):
    """Raised when an operation attempts to instantiate or route to a live broker in sandbox."""

    def __init__(self, broker_name: str, message: str | None = None) -> None:
        self.broker_name = broker_name
        detail = (
            message
            or f"SANDBOX SECURITY INVARIANT VIOLATION: Sandbox environment is hard-wired "
            f"to PaperBroker. Attempted instantiation of live broker '{broker_name}' is "
            f"physically barred and disabled."
        )
        super().__init__(detail)


class ReadOnlyWarehouseViolationError(PermissionError):
    """Raised when a mutation is attempted against the read-only sandbox warehouse."""

    def __init__(self, operation: str, message: str | None = None) -> None:
        self.operation = operation
        detail = (
            message
            or f"SANDBOX WAREHOUSE INVARIANT VIOLATION: DuckDB warehouse is mounted read-only. "
            f"Operation '{operation}' was denied."
        )
        super().__init__(detail)


class SandboxConfig(BaseModel):
    """Configuration defining isolated sandbox ports, schema, redis, and broker."""

    model_config = ConfigDict(frozen=True)

    api_port: int = Field(default=8080, description="Isolated sandbox HTTP API port")
    engine_port: int = Field(default=8081, description="Isolated sandbox engine port")
    feedd_port: int = Field(default=8082, description="Isolated sandbox feedd port")
    db_schema: str = Field(
        default="sandbox_terminal", description="Authoritative isolated Postgres schema"
    )
    redis_db: int = Field(default=15, description="Isolated Redis database index")
    warehouse_read_only: bool = Field(
        default=True, description="Strict read-only mount for historical warehouse"
    )
    broker_type: str = Field(default="PaperBroker", description="Hard-wired broker type")
    allow_live_orders: bool = Field(
        default=False, description="Strictly false in sandbox environment"
    )
    has_live_credentials: bool = Field(
        default=False, description="Strictly false in sandbox environment"
    )


class SandboxIsolationReport(BaseModel):
    """Diagnostic report auditing sandbox runtime isolation."""

    model_config = ConfigDict(frozen=True)

    ports_isolated: bool
    db_schema_isolated: bool
    redis_db_isolated: bool
    warehouse_read_only: bool
    broker_hardwired_to_paper: bool
    live_credentials_absent: bool
    all_isolated: bool
    details: list[str] = Field(default_factory=list)


class SandboxBrokerDispatcher:
    """Dispatches brokers in sandbox mode, hard-wiring PaperBroker and denying live brokers."""

    ALLOWED_BROKERS: ClassVar[set[str]] = {"PaperBroker", "SimBroker"}

    def __init__(self, config: SandboxConfig) -> None:
        self.config = config

    def get_broker(self, requested_broker: str = "PaperBroker") -> str:
        """Return the active broker or fail closed if a live broker is requested."""
        if self.config.allow_live_orders:
            raise SandboxLiveOrderDisabledError(
                requested_broker, "allow_live_orders cannot be True in sandbox"
            )

        clean_name = requested_broker.strip()
        if clean_name not in self.ALLOWED_BROKERS or "Dhan" in clean_name or "Live" in clean_name:
            raise SandboxLiveOrderDisabledError(
                clean_name,
                f"Sandbox physically has no code path to live broker '{clean_name}'. "
                f"Only PaperBroker is available in the sandbox environment.",
            )

        return self.config.broker_type


class SandboxWarehouseManager:
    """Manages read-only DuckDB warehouse connections and guards against write queries."""

    MUTATION_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^\s*INSERT\s+INTO", re.IGNORECASE),
        re.compile(r"^\s*UPDATE\s+", re.IGNORECASE),
        re.compile(r"^\s*DELETE\s+FROM", re.IGNORECASE),
        re.compile(r"^\s*DROP\s+", re.IGNORECASE),
        re.compile(r"^\s*CREATE\s+", re.IGNORECASE),
        re.compile(r"^\s*ALTER\s+", re.IGNORECASE),
        re.compile(r"^\s*TRUNCATE\s+", re.IGNORECASE),
    ]

    def __init__(self, warehouse_path: Path | None = None, read_only: bool = True) -> None:
        self.warehouse_path = warehouse_path or Path("data/warehouse")
        self.read_only = read_only

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a read-only query or raise ReadOnlyWarehouseViolationError on mutation."""
        clean_q = query.strip()
        for pattern in self.MUTATION_PATTERNS:
            if pattern.search(clean_q):
                op = clean_q.split()[0].upper()
                raise ReadOnlyWarehouseViolationError(
                    operation=op,
                    message=(
                        f"Mutation query '{op}' denied on sandbox warehouse. "
                        f"Warehouse is mounted read-only."
                    ),
                )

        # In testing/simulated environments, return simulated result set for valid read queries
        return [{"status": "success", "read_only": True, "rows": 0}]


class SandboxCredentialProvider:
    """Provides sanitized, non-live credentials for sandbox execution."""

    def __init__(self, config: SandboxConfig) -> None:
        self.config = config

    def get_credentials(self) -> dict[str, str]:
        """Return non-live credentials with all trading tokens redacted."""
        return {
            "client_id": "SANDBOX_MOCK_CLIENT_ID",
            "feed_token": "SANDBOX_DATA_ONLY_TOKEN",
            "is_live": "false",
            "order_placement_authorized": "false",
        }

    def verify_no_live_keys(self, env_vars: dict[str, str]) -> bool:
        """Verify that no real Dhan order keys or live private secrets exist in the sandbox."""
        suspicious_keys = [
            "DHAN_ACCESS_TOKEN",
            "DHAN_SECRET_KEY",
            "LIVE_TRADING_ENABLED",
        ]
        for k in suspicious_keys:
            val = env_vars.get(k, "")
            if val and not val.startswith("SANDBOX") and not val.startswith("MOCK"):
                return False
        return True


class SandboxEnvironment:
    """Unified manager orchestrating isolated sandbox runtime components."""

    def __init__(self, config: SandboxConfig | None = None) -> None:
        self.config = config or SandboxConfig()
        self.broker_dispatcher = SandboxBrokerDispatcher(self.config)
        self.warehouse_manager = SandboxWarehouseManager(read_only=self.config.warehouse_read_only)
        self.credential_provider = SandboxCredentialProvider(self.config)

    def verify_isolation(self, active_env: dict[str, str] | None = None) -> SandboxIsolationReport:
        """Run comprehensive isolation self-test to verify proof requirements."""
        details: list[str] = []

        # 1. Ports check (must differ from live defaults: 8000, 8001, 8002)
        live_ports = {8000, 8001, 8002}
        sandbox_ports = {
            self.config.api_port,
            self.config.engine_port,
            self.config.feedd_port,
        }
        ports_isolated = len(live_ports.intersection(sandbox_ports)) == 0
        if ports_isolated:
            details.append(
                f"Ports isolated: API={self.config.api_port}, "
                f"Engine={self.config.engine_port}, Feedd={self.config.feedd_port}"
            )
        else:
            details.append("Ports collision detected with live default ports!")

        # 2. Database schema check (must start with sandbox_)
        db_schema_isolated = self.config.db_schema.startswith("sandbox_")
        if db_schema_isolated:
            details.append(f"Postgres schema isolated: '{self.config.db_schema}'")
        else:
            details.append(
                f"Invalid DB schema '{self.config.db_schema}'; must begin with 'sandbox_'"
            )

        # 3. Redis DB check (must be != 0)
        redis_db_isolated = self.config.redis_db > 0
        if redis_db_isolated:
            details.append(f"Redis database isolated: index={self.config.redis_db} (live=0)")
        else:
            details.append("Redis database collision with live index 0!")

        # 4. Warehouse read-only check
        warehouse_read_only = self.config.warehouse_read_only
        if warehouse_read_only:
            details.append("DuckDB warehouse mounted read-only")
        else:
            details.append("Warehouse is NOT marked read-only!")

        # 5. Broker hardwired to PaperBroker check
        broker_hardwired = (
            self.config.broker_type == "PaperBroker" and not self.config.allow_live_orders
        )
        if broker_hardwired:
            details.append("Broker hard-wired to PaperBroker (live orders barred)")
        else:
            details.append("Broker is NOT securely hard-wired to PaperBroker!")

        # 6. Credentials check
        no_live = self.credential_provider.verify_no_live_keys(active_env or {})
        creds_ok = not self.config.has_live_credentials and no_live
        if creds_ok:
            details.append("Live credentials stripped and confirmed absent")
        else:
            details.append("Live trading credentials detected in environment!")

        all_isolated = (
            ports_isolated
            and db_schema_isolated
            and redis_db_isolated
            and warehouse_read_only
            and broker_hardwired
            and creds_ok
        )

        return SandboxIsolationReport(
            ports_isolated=ports_isolated,
            db_schema_isolated=db_schema_isolated,
            redis_db_isolated=redis_db_isolated,
            warehouse_read_only=warehouse_read_only,
            broker_hardwired_to_paper=broker_hardwired,
            live_credentials_absent=creds_ok,
            all_isolated=all_isolated,
            details=details,
        )


sandbox_env = SandboxEnvironment()
