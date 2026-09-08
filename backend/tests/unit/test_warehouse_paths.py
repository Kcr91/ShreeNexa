"""Unit tests for data-root resolution, the env override, and write admission."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.warehouse import paths
from app.warehouse.paths import (
    DATA_ROOT_ENV_VAR,
    DEFAULT_DATA_ROOT,
    DataRootCapacityError,
    check_write_admission,
    get_disk_usage,
    resolve_data_root,
)
from app.warehouse.publisher import WarehousePublisher
from app.warehouse.reader import WarehouseReader


class TestResolveDataRoot:
    def test_defaults_to_repo_data_directory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(DATA_ROOT_ENV_VAR, raising=False)
        assert resolve_data_root() == DEFAULT_DATA_ROOT.resolve()

    def test_env_override_wins_over_default(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(DATA_ROOT_ENV_VAR, str(tmp_path))
        assert resolve_data_root() == tmp_path.resolve()

    def test_explicit_argument_wins_over_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(DATA_ROOT_ENV_VAR, str(tmp_path / "from_env"))
        explicit = tmp_path / "explicit"
        assert resolve_data_root(explicit) == explicit.resolve()

    def test_blank_env_value_is_ignored(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(DATA_ROOT_ENV_VAR, "   ")
        assert resolve_data_root() == DEFAULT_DATA_ROOT.resolve()

    def test_result_is_always_absolute(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(DATA_ROOT_ENV_VAR, str(tmp_path))
        assert resolve_data_root().is_absolute()


class TestOverrideReachesConsumers:
    """The override is worthless unless the modules that write actually honour it."""

    def test_publisher_honours_env_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(DATA_ROOT_ENV_VAR, str(tmp_path))
        assert WarehousePublisher().data_root == tmp_path.resolve()

    def test_reader_honours_env_override(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(DATA_ROOT_ENV_VAR, str(tmp_path))
        assert WarehouseReader().data_root == tmp_path.resolve()

    def test_explicit_argument_still_wins_for_publisher(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv(DATA_ROOT_ENV_VAR, str(tmp_path / "env"))
        explicit = tmp_path / "explicit"
        assert WarehousePublisher(data_root=explicit).data_root == explicit.resolve()


class TestDiskUsage:
    def test_reports_positive_capacity_for_existing_root(self, tmp_path: Path) -> None:
        usage = get_disk_usage(tmp_path)
        assert usage.total_bytes > 0
        assert usage.free_bytes >= 0
        assert usage.data_root == tmp_path.resolve()

    def test_works_before_the_data_root_exists(self, tmp_path: Path) -> None:
        """Probing walks up to an existing parent, so a first run does not crash."""
        missing = tmp_path / "not" / "created" / "yet"
        usage = get_disk_usage(missing)
        assert usage.total_bytes > 0
        assert usage.data_root == missing.resolve()

    def test_percent_used_is_a_sane_fraction(self, tmp_path: Path) -> None:
        assert 0.0 <= get_disk_usage(tmp_path).percent_used <= 100.0


class TestWriteAdmission:
    def test_passes_when_space_is_plentiful(self, tmp_path: Path) -> None:
        usage = check_write_admission(tmp_path, required_bytes=1)
        assert usage.free_bytes >= 1

    def test_refuses_when_below_requirement(self, tmp_path: Path) -> None:
        huge = 1024**6  # 1 EiB; no test volume satisfies this
        with pytest.raises(DataRootCapacityError) as exc_info:
            check_write_admission(tmp_path, required_bytes=huge)

        err = exc_info.value
        assert err.required_bytes == huge
        assert err.data_root == tmp_path.resolve()
        assert "SHREENEXA_DATA_ROOT" in str(err), "error must say how to fix it"

    def test_warns_but_admits_in_the_low_space_band(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        real = get_disk_usage(tmp_path)
        # Put the warn threshold above actual free space, the hard floor below it.
        monkeypatch.setattr(paths, "WARN_FREE_BYTES", real.free_bytes + 1)

        with caplog.at_level("WARNING", logger="app.warehouse.paths"):
            check_write_admission(tmp_path, required_bytes=1)

        assert any("low on space" in r.message for r in caplog.records)
