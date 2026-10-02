"""Redis-backed Daily API Quota Manager shared between worker and feedd processes."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from app.worker.data_engine.models import ApiQuotaRecord, mkt_api_quota_table
from redis import Redis
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

DAILY_DEFAULT_LIMIT = 100000
DEFAULT_RESERVED_LIVE = 5000


def _quota_key(d: date | None = None) -> str:
    target_date = d or datetime.now(UTC).date()
    return f"mkt:quota:{target_date.isoformat()}"


class QuotaManager:
    """Manages the daily 100,000 requests/day budget across historical sync and live feed."""

    def __init__(
        self,
        redis_client: Redis | None = None,
        db_engine: Engine | None = None,
        daily_limit: int = DAILY_DEFAULT_LIMIT,
        reserved_live: int = DEFAULT_RESERVED_LIVE,
    ) -> None:
        self._redis = redis_client
        self._engine = db_engine
        self._daily_limit = daily_limit
        self._reserved_live = reserved_live

    def get_quota_status(self, d: date | None = None) -> ApiQuotaRecord:
        """Fetch current quota usage and remaining allowance for a specific date."""
        target_date = d or datetime.now(UTC).date()
        key = _quota_key(target_date)

        if self._redis is not None:
            try:
                raw_data: Any = self._redis.hgetall(key)
                if raw_data and isinstance(raw_data, dict):
                    data: dict[Any, Any] = raw_data
                    used_hist = int(data.get(b"used_historical", data.get("used_historical", 0)) or 0)
                    used_live = int(data.get(b"used_live", data.get("used_live", 0)) or 0)
                    limit = int(data.get(b"limit", data.get("limit", self._daily_limit)) or self._daily_limit)
                    reserved = int(
                        data.get(b"reserved_live", data.get("reserved_live", self._reserved_live))
                        or self._reserved_live
                    )
                    available = max(0, limit - used_hist - reserved)
                    return ApiQuotaRecord(
                        date=target_date,
                        daily_limit=limit,
                        used_historical=used_hist,
                        used_live=used_live,
                        reserved_live=reserved,
                        available_historical=available,
                        updated_at=datetime.now(UTC),
                    )
            except Exception as exc:
                logger.warning("Redis quota fetch error: %s", exc)

        # Fallback to DB if Redis unavailable
        if self._engine is not None:
            with self._engine.connect() as conn:
                stmt = select(mkt_api_quota_table).where(mkt_api_quota_table.c.date == target_date)
                row = conn.execute(stmt).first()
                if row is not None:
                    used_hist = int(row.used_historical)
                    used_live = int(row.used_live)
                    limit = int(row.daily_limit)
                    reserved = int(row.reserved_live)
                    available = max(0, limit - used_hist - reserved)
                    return ApiQuotaRecord(
                        date=target_date,
                        daily_limit=limit,
                        used_historical=used_hist,
                        used_live=used_live,
                        reserved_live=reserved,
                        available_historical=available,
                        updated_at=row.updated_at,
                    )

        # Default initial status
        return ApiQuotaRecord(
            date=target_date,
            daily_limit=self._daily_limit,
            used_historical=0,
            used_live=0,
            reserved_live=self._reserved_live,
            available_historical=max(0, self._daily_limit - self._reserved_live),
            updated_at=datetime.now(UTC),
        )

    def can_make_historical_request(self, count: int = 1, d: date | None = None) -> bool:
        """Check if requested number of historical API calls can be made within budget."""
        status = self.get_quota_status(d)
        return status.available_historical >= count

    def consume_historical_quota(self, count: int = 1, d: date | None = None) -> int:
        """Increment historical API usage counter in Redis and persist to DB."""
        target_date = d or datetime.now(UTC).date()
        key = _quota_key(target_date)
        used_hist = count

        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.hincrby(key, "used_historical", count)
                pipe.hsetnx(key, "limit", str(self._daily_limit))
                pipe.hsetnx(key, "reserved_live", str(self._reserved_live))
                pipe.expire(key, 172800)  # 48 hours TTL
                results = pipe.execute()
                used_hist = int(results[0])
            except Exception as exc:
                logger.warning("Redis consume_historical_quota error: %s", exc)

        if self._engine is not None:
            try:
                with self._engine.begin() as conn:
                    ins_stmt = pg_insert(mkt_api_quota_table).values(
                        date=target_date,
                        daily_limit=self._daily_limit,
                        used_historical=count,
                        used_live=0,
                        reserved_live=self._reserved_live,
                        updated_at=datetime.now(UTC),
                    )
                    upsert_stmt = ins_stmt.on_conflict_do_update(
                        index_elements=["date"],
                        set_={
                            "used_historical": mkt_api_quota_table.c.used_historical + count,
                            "updated_at": datetime.now(UTC),
                        },
                    )
                    conn.execute(upsert_stmt)
            except Exception as exc:
                logger.warning("DB persist quota error: %s", exc)

        return used_hist

    def consume_live_quota(self, count: int = 1, d: date | None = None) -> int:
        """Increment live API usage counter in Redis and persist to DB."""
        target_date = d or datetime.now(UTC).date()
        key = _quota_key(target_date)
        used_live = count

        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                pipe.hincrby(key, "used_live", count)
                pipe.hsetnx(key, "limit", str(self._daily_limit))
                pipe.hsetnx(key, "reserved_live", str(self._reserved_live))
                pipe.expire(key, 172800)
                results = pipe.execute()
                used_live = int(results[0])
            except Exception as exc:
                logger.warning("Redis consume_live_quota error: %s", exc)

        if self._engine is not None:
            try:
                with self._engine.begin() as conn:
                    ins_stmt = pg_insert(mkt_api_quota_table).values(
                        date=target_date,
                        daily_limit=self._daily_limit,
                        used_historical=0,
                        used_live=count,
                        reserved_live=self._reserved_live,
                        updated_at=datetime.now(UTC),
                    )
                    upsert_stmt = ins_stmt.on_conflict_do_update(
                        index_elements=["date"],
                        set_={
                            "used_live": mkt_api_quota_table.c.used_live + count,
                            "updated_at": datetime.now(UTC),
                        },
                    )
                    conn.execute(upsert_stmt)
            except Exception as exc:
                logger.warning("DB persist live quota error: %s", exc)

        return used_live
