"""FastAPI REST router for the Dynamic Screener Engine (configs CRUD & execution)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine

from app.contracts import heartbeat as hb
from app.screener.dynamic_engine import DynamicScreenerEngine
from app.screener.engine_models import (
    DynamicScreenerRunResponse,
    ScreenerConfigCreate,
    ScreenerConfigRecord,
    ScreenerConfigUpdate,
    screener_configs_table,
    screener_results_table,
)

router = APIRouter(prefix="/api/v1/screener", tags=["Dynamic Screener Engine"])


def get_db_engine() -> Engine:
    """Dependency providing a connected SQLAlchemy Engine."""
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


@router.post("/configs", response_model=ScreenerConfigRecord)
def create_screener_config(
    engine: DbEngineDep,
    payload: ScreenerConfigCreate,
) -> ScreenerConfigRecord:
    """Save a new screener configuration."""
    now = datetime.now(UTC)
    with engine.begin() as conn:
        ins_stmt = (
            pg_insert(screener_configs_table)
            .values(
                name=payload.name,
                description=payload.description,
                universe_filter=payload.universe_filter,
                condition_tree=payload.condition_tree,
                is_strategy_mode=payload.is_strategy_mode,
                created_at=now,
                updated_at=now,
            )
            .returning(screener_configs_table)
        )
        row = conn.execute(ins_stmt).first()
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create screener config")
        return ScreenerConfigRecord.model_validate(dict(row._mapping))


@router.get("/configs", response_model=list[ScreenerConfigRecord])
def list_screener_configs(
    engine: DbEngineDep,
    is_strategy_mode: Annotated[bool | None, Query(description="Filter by strategy mode")] = None,
) -> list[ScreenerConfigRecord]:
    """List all saved screener configurations."""
    stmt = select(screener_configs_table)
    if is_strategy_mode is not None:
        stmt = stmt.where(screener_configs_table.c.is_strategy_mode == is_strategy_mode)
    stmt = stmt.order_by(screener_configs_table.c.updated_at.desc())

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()
        return [ScreenerConfigRecord.model_validate(dict(r._mapping)) for r in rows]


@router.get("/configs/{config_id}", response_model=ScreenerConfigRecord)
def get_screener_config(
    engine: DbEngineDep,
    config_id: int,
) -> ScreenerConfigRecord:
    """Retrieve details and condition tree of a specific screener configuration."""
    stmt = select(screener_configs_table).where(screener_configs_table.c.id == config_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Screener config id {config_id} not found")
        return ScreenerConfigRecord.model_validate(dict(row._mapping))


@router.put("/configs/{config_id}", response_model=ScreenerConfigRecord)
def update_screener_config(
    engine: DbEngineDep,
    config_id: int,
    payload: ScreenerConfigUpdate,
) -> ScreenerConfigRecord:
    """Update an existing screener configuration."""
    values: dict[str, Any] = {"updated_at": datetime.now(UTC)}
    if payload.name is not None:
        values["name"] = payload.name
    if payload.description is not None:
        values["description"] = payload.description
    if payload.universe_filter is not None:
        values["universe_filter"] = payload.universe_filter
    if payload.condition_tree is not None:
        values["condition_tree"] = payload.condition_tree
    if payload.is_strategy_mode is not None:
        values["is_strategy_mode"] = payload.is_strategy_mode

    with engine.begin() as conn:
        stmt = (
            update(screener_configs_table)
            .where(screener_configs_table.c.id == config_id)
            .values(**values)
            .returning(screener_configs_table)
        )
        row = conn.execute(stmt).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Screener config id {config_id} not found")
        return ScreenerConfigRecord.model_validate(dict(row._mapping))


@router.delete("/configs/{config_id}")
def delete_screener_config(
    engine: DbEngineDep,
    config_id: int,
) -> dict[str, str]:
    """Delete a screener configuration."""
    with engine.begin() as conn:
        stmt = delete(screener_configs_table).where(screener_configs_table.c.id == config_id)
        result = conn.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Screener config id {config_id} not found")
    return {"status": "deleted", "message": f"Screener config {config_id} deleted successfully"}


@router.post("/run/{config_id}", response_model=DynamicScreenerRunResponse)
def run_screener_scan(
    engine: DbEngineDep,
    config_id: int,
    universe_override: Annotated[
        str | None, Query(description="Optional universe override")
    ] = None,
) -> DynamicScreenerRunResponse:
    """Execute a saved screener scan across target universe and return live results."""
    stmt = select(screener_configs_table).where(screener_configs_table.c.id == config_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Screener config id {config_id} not found")
        config_name = row.name
        condition_tree = row.condition_tree
        universe = universe_override or row.universe_filter

    screener_engine = DynamicScreenerEngine(engine=engine)
    return screener_engine.run_screener(
        condition_tree=condition_tree,
        universe_code=universe,
        config_id=config_id,
        config_name=config_name,
        save_results=True,
    )


@router.get("/results/{result_id}")
def get_screener_run_result(
    engine: DbEngineDep,
    result_id: int,
) -> dict[str, Any]:
    """Retrieve full result snapshot of a previous screener execution run."""
    stmt = select(screener_results_table).where(screener_results_table.c.id == result_id)
    with engine.connect() as conn:
        row = conn.execute(stmt).first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Screener result id {result_id} not found")
        return dict(row._mapping)


@router.get("/results")
def list_screener_results_history(
    engine: DbEngineDep,
    config_id: Annotated[int | None, Query(description="Filter by config id")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict[str, Any]]:
    """List historical screener execution runs."""
    stmt = select(screener_results_table)
    if config_id is not None:
        stmt = stmt.where(screener_results_table.c.config_id == config_id)
    stmt = stmt.order_by(screener_results_table.c.run_at.desc()).limit(limit)

    with engine.connect() as conn:
        rows = conn.execute(stmt).fetchall()
        return [dict(r._mapping) for r in rows]
