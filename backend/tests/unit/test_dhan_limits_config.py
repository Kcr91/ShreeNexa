"""Unit tests for Dhan API rate limits configuration and endpoint mapping."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.dhan.limits_config import (
    BackoffSpec,
    DhanLimitsConfig,
    RateLimitSpec,
    get_category_for_endpoint,
    get_default_dhan_limits,
    load_dhan_limits,
)


def test_default_dhan_limits() -> None:
    config = get_default_dhan_limits()
    assert config.schema_version == 1
    assert config.default_limit.rate == 10.0
    assert config.default_limit.burst == 10
    assert "option_chain" in config.categories
    assert config.get_rate_limit("option_chain").burst == 1
    assert abs(config.get_rate_limit("option_chain").rate - 0.3333333333333333) < 1e-6
    assert config.get_rate_limit("quotes").rate == 1.0
    assert config.get_rate_limit("quotes").burst == 1
    assert config.get_rate_limit("orders").rate == 10.0
    assert config.get_rate_limit("orders").burst == 10


def test_load_dhan_limits_from_real_yaml() -> None:
    config = load_dhan_limits()
    assert isinstance(config, DhanLimitsConfig)
    assert config.as_of == "2026-09-03"
    assert config.source == "https://dhanhq.co/docs/v2/"
    assert config.get_rate_limit("orders").rate == 10.0
    assert config.get_rate_limit("orders").burst == 10
    assert config.get_rate_limit("quotes").rate == 1.0
    assert config.get_rate_limit("quotes").burst == 1
    assert config.get_rate_limit("historical_daily").rate == 5.0
    assert config.get_rate_limit("unknown_custom_category").rate == 10.0


def test_load_dhan_limits_missing_file_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        non_existent = Path(tmp_dir) / "does_not_exist.yaml"
        config = load_dhan_limits(non_existent)
        assert isinstance(config, DhanLimitsConfig)
        assert config.default_limit.rate == 10.0


def test_load_dhan_limits_malformed_yaml_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        bad_yaml = Path(tmp_dir) / "bad.yaml"
        bad_yaml.write_text("invalid: yaml: [content", encoding="utf-8")
        config = load_dhan_limits(bad_yaml)
        assert isinstance(config, DhanLimitsConfig)
        assert config.default_limit.burst == 10


def test_get_category_for_endpoint() -> None:
    assert get_category_for_endpoint("GET", "optionchain") == "option_chain"
    assert get_category_for_endpoint("GET", "/optionchain/expirylist") == "option_chain"
    assert get_category_for_endpoint("POST", "charts/historical") == "historical_daily"
    assert get_category_for_endpoint("POST", "/charts/intraday") == "historical_intraday"
    assert get_category_for_endpoint("POST", "charts/rollingoption") == "historical_intraday"
    assert get_category_for_endpoint("POST", "marketfeed/quote") == "quotes"
    assert get_category_for_endpoint("POST", "orders") == "orders"
    assert get_category_for_endpoint("PUT", "/orders/12345") == "orders"
    assert get_category_for_endpoint("DELETE", "/positions") == "orders"
    assert get_category_for_endpoint("POST", "killswitch") == "orders"
    assert get_category_for_endpoint("GET", "fundlimit") == "account_funds_holdings"
    assert get_category_for_endpoint("GET", "/holdings") == "account_funds_holdings"
    assert get_category_for_endpoint("GET", "positions") == "account_funds_holdings"
    assert get_category_for_endpoint("GET", "/v2/profile") == "account_funds_holdings"
    assert get_category_for_endpoint("GET", "v2/RenewToken") == "account_funds_holdings"
    assert get_category_for_endpoint("GET", "ip/getIP") == "account_funds_holdings"
    assert get_category_for_endpoint("POST", "margincalculator/multi") == "account_funds_holdings"
    assert get_category_for_endpoint("GET", "unknown/endpoint") == "default"



def test_rate_limit_spec_validation() -> None:
    spec = RateLimitSpec(rate=5.0, burst=10, description="Test")
    assert spec.rate == 5.0
    assert spec.burst == 10


def test_backoff_spec_validation() -> None:
    backoff = BackoffSpec(base_delay_seconds=0.1, max_delay_seconds=1.0, jitter_ratio=0.2)
    assert backoff.base_delay_seconds == 0.1
    assert backoff.max_delay_seconds == 1.0
    assert backoff.jitter_ratio == 0.2
