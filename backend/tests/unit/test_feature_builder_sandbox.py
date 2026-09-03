"""Unit and acceptance tests for isolated sandbox stack (F11.6).

Proof requirement: Sandbox has no credentials or network/code path capable of placing a live order.
"""

from __future__ import annotations

import pytest
from app.feature_builder.sandbox import (
    ReadOnlyWarehouseViolationError,
    SandboxBrokerDispatcher,
    SandboxConfig,
    SandboxCredentialProvider,
    SandboxEnvironment,
    SandboxLiveOrderDisabledError,
    SandboxWarehouseManager,
)
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_sandbox_broker_dispatcher_hardwired_to_paper() -> None:
    """Proof: Sandbox has no code path to live broker and hard-wires PaperBroker."""
    config = SandboxConfig()
    dispatcher = SandboxBrokerDispatcher(config)

    # 1. PaperBroker and SimBroker are permitted and return PaperBroker
    assert dispatcher.get_broker("PaperBroker") == "PaperBroker"
    assert dispatcher.get_broker("SimBroker") == "PaperBroker"

    # 2. DhanBroker or any live broker raises SandboxLiveOrderDisabledError
    with pytest.raises(SandboxLiveOrderDisabledError) as exc_info:
        dispatcher.get_broker("DhanBroker")
    assert "no code path to live broker" in str(exc_info.value)
    assert exc_info.value.broker_name == "DhanBroker"

    with pytest.raises(SandboxLiveOrderDisabledError):
        dispatcher.get_broker("LiveExecutionBroker")


def test_sandbox_warehouse_read_only_enforcement() -> None:
    """Proof: DuckDB warehouse is mounted read-only; mutation queries are barred."""
    warehouse = SandboxWarehouseManager(read_only=True)

    # 1. SELECT query succeeds
    results = warehouse.execute_query("SELECT * FROM ohlcv_1m LIMIT 10")
    assert len(results) == 1
    assert results[0]["read_only"] is True

    # 2. Mutation queries fail closed with ReadOnlyWarehouseViolationError
    mutation_queries = [
        "INSERT INTO ohlcv_1m VALUES (1, 2, 3)",
        "UPDATE ohlcv_1m SET close = 100",
        "DELETE FROM ohlcv_1m WHERE symbol = 'NIFTY'",
        "DROP TABLE ohlcv_1m",
        "CREATE TABLE test_tbl (id INT)",
        "ALTER TABLE ohlcv_1m ADD COLUMN extra INT",
        "TRUNCATE TABLE ohlcv_1m",
    ]

    for q in mutation_queries:
        with pytest.raises(ReadOnlyWarehouseViolationError) as exc_info:
            warehouse.execute_query(q)
        assert "denied on sandbox warehouse" in str(exc_info.value)


def test_sandbox_credential_provider_no_live_keys() -> None:
    """Proof: Sandbox credential provider strips trading tokens and detects live keys."""
    config = SandboxConfig()
    provider = SandboxCredentialProvider(config)

    # 1. Returned credentials contain zero order tokens
    creds = provider.get_credentials()
    assert creds["is_live"] == "false"
    assert creds["order_placement_authorized"] == "false"
    assert "token" not in creds.get("client_id", "").lower()

    # 2. Rejection of real Dhan tokens and live trading flags
    dirty_env = {
        "DHAN_ACCESS_TOKEN": "real_jwt_live_secret_token_12345",
        "LIVE_TRADING_ENABLED": "true",
    }
    assert provider.verify_no_live_keys(dirty_env) is False

    clean_env = {
        "DHAN_ACCESS_TOKEN": "SANDBOX_MOCK_TOKEN",
        "LIVE_TRADING_ENABLED": "",
    }
    assert provider.verify_no_live_keys(clean_env) is True


def test_sandbox_environment_full_isolation_verification() -> None:
    """Proof: Sandbox self-test verifies isolation of ports, schema, redis, and warehouse."""
    env = SandboxEnvironment()
    report = env.verify_isolation(
        active_env={"DHAN_ACCESS_TOKEN": "SANDBOX_MOCK", "LIVE_TRADING_ENABLED": ""}
    )

    assert report.ports_isolated is True
    assert report.db_schema_isolated is True
    assert report.redis_db_isolated is True
    assert report.warehouse_read_only is True
    assert report.broker_hardwired_to_paper is True
    assert report.live_credentials_absent is True
    assert report.all_isolated is True
    assert len(report.details) == 6


def test_sandbox_detects_port_collision_with_live() -> None:
    """Proof: Sandbox detects and flags collision with live default ports (8000, 8001, 8002)."""
    colliding_config = SandboxConfig(api_port=8000)
    env = SandboxEnvironment(colliding_config)
    report = env.verify_isolation()

    assert report.ports_isolated is False
    assert report.all_isolated is False
    assert any("Ports collision detected" in d for d in report.details)


def test_sandbox_detects_live_schema_attempt() -> None:
    """Proof: Sandbox detects and flags attempt to point at live Postgres schemas."""
    live_schema_config = SandboxConfig(db_schema="trading_live")
    env = SandboxEnvironment(live_schema_config)
    report = env.verify_isolation()

    assert report.db_schema_isolated is False
    assert report.all_isolated is False


def test_sandbox_detects_redis_db_zero_collision() -> None:
    """Proof: Sandbox detects and flags collision with live Redis database index 0."""
    colliding_redis = SandboxConfig(redis_db=0)
    env = SandboxEnvironment(colliding_redis)
    report = env.verify_isolation()

    assert report.redis_db_isolated is False
    assert report.all_isolated is False


def test_sandbox_rest_api_lifecycle() -> None:
    """Proof: REST API endpoints for sandbox status and isolation verification."""
    # 1. GET status
    resp1 = client.get("/api/v1/feature-builder/sandbox/status")
    assert resp1.status_code == 200
    status_data = resp1.json()
    assert status_data["broker_type"] == "PaperBroker"
    assert status_data["allow_live_orders"] is False
    assert status_data["api_port"] == 8080
    assert status_data["db_schema"].startswith("sandbox_")

    # 2. POST verify-isolation
    resp2 = client.post("/api/v1/feature-builder/sandbox/verify-isolation")
    assert resp2.status_code == 200
    report_data = resp2.json()
    assert report_data["broker_hardwired_to_paper"] is True
    assert report_data["warehouse_read_only"] is True
    assert report_data["all_isolated"] is True
