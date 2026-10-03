"""FastAPI Router for Feature 3: Strategy Builder & Standalone Python Code Exporter."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine

from app.contracts import heartbeat as hb
from app.strategy.code_generator import export_strategy_python_script
from app.strategy.models import (
    PythonExportResponse,
    StrategyConfigCreate,
    StrategyConfigRecord,
    StrategyConfigUpdate,
    StrategyVersionRecord,
    strategy_configs_table,
    strategy_versions_table,
)
from app.strategy.parser import parse_and_validate_strategy

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy-builder"])


def get_db_engine() -> Engine:
    """Dependency providing a connected SQLAlchemy Engine."""
    return hb.make_engine()


DbEngineDep = Annotated[Engine, Depends(get_db_engine)]


@router.post("/validate", summary="Validate Strategy Configuration")
def validate_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate 4-part modular strategy structure before persisting."""
    return parse_and_validate_strategy(payload)


@router.post(
    "/configs", response_model=StrategyConfigRecord, status_code=201, summary="Create Strategy"
)
def create_strategy_config(
    payload: StrategyConfigCreate,
    db: DbEngineDep,
) -> StrategyConfigRecord:
    """Create a new strategy configuration and record version 1."""
    # Semantic validation
    val_result = parse_and_validate_strategy(payload.config_json)
    if not val_result["valid"]:
        raise HTTPException(
            status_code=422,
            detail={"message": "Strategy validation failed", "errors": val_result["errors"]},
        )

    now = datetime.now(UTC)
    with db.begin() as conn:
        res = conn.execute(
            insert(strategy_configs_table).values(
                name=payload.name,
                description=payload.description,
                strategy_type=payload.strategy_type,
                current_version=1,
                is_active=payload.is_active,
                config_json=payload.config_json,
                created_at=now,
                updated_at=now,
            )
        )
        strategy_id = res.inserted_primary_key[0]  # type: ignore[index]

        # Insert Version 1 record
        conn.execute(
            insert(strategy_versions_table).values(
                strategy_id=strategy_id,
                version=1,
                change_summary="Initial strategy creation",
                config_json=payload.config_json,
                created_at=now,
            )
        )

        row = (
            conn.execute(
                select(strategy_configs_table).where(strategy_configs_table.c.id == strategy_id)
            )
            .mappings()
            .first()
        )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to retrieve created strategy")
    return StrategyConfigRecord.model_validate(dict(row))


@router.get("/configs", response_model=list[StrategyConfigRecord], summary="List Strategies")
def list_strategy_configs(
    db: DbEngineDep,
    strategy_type: str | None = Query(None, description="Filter by strategy type"),
    is_active: bool | None = Query(None, description="Filter active status"),
) -> list[StrategyConfigRecord]:
    """List all saved strategy configurations."""
    query = select(strategy_configs_table).order_by(strategy_configs_table.c.id.desc())
    if strategy_type:
        query = query.where(strategy_configs_table.c.strategy_type == strategy_type.upper())
    if is_active is not None:
        query = query.where(strategy_configs_table.c.is_active == is_active)

    with db.connect() as conn:
        rows = conn.execute(query).mappings().all()

    return [StrategyConfigRecord.model_validate(dict(r)) for r in rows]


@router.get("/configs/{id}", response_model=StrategyConfigRecord, summary="Get Strategy Detail")
def get_strategy_config(id: int, db: DbEngineDep) -> StrategyConfigRecord:
    """Retrieve full strategy detail by ID."""
    with db.connect() as conn:
        row = (
            conn.execute(select(strategy_configs_table).where(strategy_configs_table.c.id == id))
            .mappings()
            .first()
        )

    if not row:
        raise HTTPException(status_code=404, detail=f"Strategy with id {id} not found")
    return StrategyConfigRecord.model_validate(dict(row))


@router.put("/configs/{id}", response_model=StrategyConfigRecord, summary="Update Strategy")
def update_strategy_config(
    id: int,
    payload: StrategyConfigUpdate,
    db: DbEngineDep,
) -> StrategyConfigRecord:
    """Update strategy configuration, auto-increment version, and snapshot change history."""
    with db.begin() as conn:
        existing = (
            conn.execute(select(strategy_configs_table).where(strategy_configs_table.c.id == id))
            .mappings()
            .first()
        )

        if not existing:
            raise HTTPException(status_code=404, detail=f"Strategy with id {id} not found")

        current_ver = existing["current_version"]
        new_ver = current_ver + 1
        now = datetime.now(UTC)

        update_values: dict[str, Any] = {
            "updated_at": now,
            "current_version": new_ver,
        }

        if payload.name is not None:
            update_values["name"] = payload.name
        if payload.description is not None:
            update_values["description"] = payload.description
        if payload.strategy_type is not None:
            update_values["strategy_type"] = payload.strategy_type
        if payload.is_active is not None:
            update_values["is_active"] = payload.is_active

        final_config = (
            payload.config_json if payload.config_json is not None else existing["config_json"]
        )
        if payload.config_json is not None:
            val_res = parse_and_validate_strategy(payload.config_json)
            if not val_res["valid"]:
                raise HTTPException(
                    status_code=422,
                    detail={"message": "Strategy validation failed", "errors": val_res["errors"]},
                )
            update_values["config_json"] = payload.config_json

        conn.execute(
            update(strategy_configs_table)
            .where(strategy_configs_table.c.id == id)
            .values(**update_values)
        )

        # Snapshot new version
        conn.execute(
            insert(strategy_versions_table).values(
                strategy_id=id,
                version=new_ver,
                change_summary=payload.change_summary or f"Updated to version {new_ver}",
                config_json=final_config,
                created_at=now,
            )
        )

        row = (
            conn.execute(select(strategy_configs_table).where(strategy_configs_table.c.id == id))
            .mappings()
            .first()
        )

    if not row:
        raise HTTPException(status_code=500, detail="Failed to retrieve updated strategy")
    return StrategyConfigRecord.model_validate(dict(row))


@router.delete("/configs/{id}", status_code=204, summary="Delete Strategy")
def delete_strategy_config(id: int, db: DbEngineDep) -> None:
    """Delete strategy configuration and its versions."""
    with db.begin() as conn:
        res = conn.execute(delete(strategy_configs_table).where(strategy_configs_table.c.id == id))
        if res.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Strategy with id {id} not found")


@router.get(
    "/configs/{id}/versions",
    response_model=list[StrategyVersionRecord],
    summary="Get Version History",
)
def get_strategy_versions(id: int, db: DbEngineDep) -> list[StrategyVersionRecord]:
    """Retrieve version history for a given strategy."""
    with db.connect() as conn:
        # Check strategy existence
        exists = conn.execute(
            select(strategy_configs_table.c.id).where(strategy_configs_table.c.id == id)
        ).first()
        if not exists:
            raise HTTPException(status_code=404, detail=f"Strategy with id {id} not found")

        rows = (
            conn.execute(
                select(strategy_versions_table)
                .where(strategy_versions_table.c.strategy_id == id)
                .order_by(strategy_versions_table.c.version.desc())
            )
            .mappings()
            .all()
        )

    return [StrategyVersionRecord.model_validate(dict(r)) for r in rows]


@router.post(
    "/configs/{id}/export-python",
    response_model=PythonExportResponse,
    summary="Export Standalone Python Algo Script",
)
def export_python_script(id: int, db: DbEngineDep) -> PythonExportResponse:
    """Generate and export a standalone, runnable Python file using the dhanhq SDK."""
    with db.connect() as conn:
        row = (
            conn.execute(select(strategy_configs_table).where(strategy_configs_table.c.id == id))
            .mappings()
            .first()
        )

    if not row:
        raise HTTPException(status_code=404, detail=f"Strategy with id {id} not found")

    config_dict = dict(row["config_json"])
    config_dict["name"] = row["name"]
    config_dict["version"] = row["current_version"]
    config_dict["strategy_type"] = row["strategy_type"]

    code = export_strategy_python_script(config_dict)
    clean_name = re.sub(r"[^a-zA-Z0-9_]+", "_", row["name"].lower()).strip("_")
    filename = f"{clean_name}_v{row['current_version']}_algo.py"

    return PythonExportResponse(
        strategy_id=id,
        strategy_name=row["name"],
        version=row["current_version"],
        filename=filename,
        code_content=code,
    )


@router.post(
    "/configs/import",
    response_model=StrategyConfigRecord,
    status_code=201,
    summary="Import Strategy JSON",
)
def import_strategy_config(
    payload: dict[str, Any],
    db: DbEngineDep,
) -> StrategyConfigRecord:
    """Import a strategy definition from a JSON payload."""
    val_result = parse_and_validate_strategy(payload)
    if not val_result["valid"]:
        raise HTTPException(
            status_code=422,
            detail={"message": "Imported strategy is invalid", "errors": val_result["errors"]},
        )

    name = payload.get("name", "Imported Strategy")
    stype = payload.get("strategy_type", "STOCK")
    desc = payload.get("description", "Imported strategy definition")

    create_payload = StrategyConfigCreate(
        name=name,
        description=desc,
        strategy_type=stype,
        config_json=payload,
        is_active=True,
    )
    return create_strategy_config(create_payload, db=db)
