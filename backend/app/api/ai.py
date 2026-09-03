"""REST API endpoints for AI strategy generation, repair, and explanation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.ai.explainer import explain_strategy_ir
from app.ai.generator import generate_strategy_ir_from_prompt
from app.ai.repair import repair_strategy_ir
from app.backtest.models import (
    AIGenerationMetadata,
    BacktestConfig,
    BacktestResult,
)
from app.backtest.runner import StockStrategyBacktestRunner
from app.backtest.store import backtest_store
from app.strategy.ir import StrategyIR

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class GenerateStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str = Field(min_length=3, description="Natural language description of strategy")
    strict: bool = Field(default=False, description="Strict validation mode")


class GenerateStrategyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_ir: dict[str, Any]
    explanation: str
    warnings: list[str]
    draft_status: str = "draft"


class RepairStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    raw_ir: dict[str, Any]


class RepairStrategyResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    repaired_ir: dict[str, Any]
    repairs_applied: list[str]
    is_valid: bool


class ExplainStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strategy_ir: dict[str, Any]


@router.post("/generate-strategy", response_model=GenerateStrategyResponse)
def generate_strategy(request: GenerateStrategyRequest) -> GenerateStrategyResponse:
    """Compile natural-language description into schema-constrained StrategyIR draft."""
    try:
        res = generate_strategy_ir_from_prompt(request.prompt)
        return GenerateStrategyResponse(
            strategy_ir=res.strategy_dict,
            explanation=res.explanation,
            warnings=res.warnings,
            draft_status=res.draft_status,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Generation failed: {exc}") from exc


@router.post("/repair-strategy", response_model=RepairStrategyResponse)
def repair_strategy(request: RepairStrategyRequest) -> RepairStrategyResponse:
    """Repair common syntax or structural defects in a StrategyIR dictionary."""
    repaired, repairs = repair_strategy_ir(request.raw_ir)
    is_valid = True
    try:
        StrategyIR.from_dict(repaired)
    except Exception:
        is_valid = False

    return RepairStrategyResponse(
        repaired_ir=repaired,
        repairs_applied=repairs,
        is_valid=is_valid,
    )


@router.post("/explain-strategy", response_model=dict[str, str])
def explain_strategy(request: ExplainStrategyRequest) -> dict[str, str]:
    """Generate structured human-readable natural language summary of StrategyIR."""
    try:
        explanation = explain_strategy_ir(request.strategy_ir)
        return {"explanation": explanation}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Explanation failed: {exc}") from exc


def compute_ir_hash(ir_dict: dict[str, Any]) -> str:
    """Compute deterministic SHA-256 hash of normalized StrategyIR dictionary."""
    canonical_json = json.dumps(ir_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class BacktestDraftRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strategy_ir: dict[str, Any]
    prompt: str
    provider_name: str = "default-ai"
    model_version: str = "1.0.0"
    start_date: datetime | None = None
    end_date: datetime | None = None
    initial_cash: float = Field(default=1_000_000.0, gt=0.0)


class BacktestDraftResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backtest_id: str
    result: BacktestResult
    ai_metadata: AIGenerationMetadata


@router.post("/backtest-draft", response_model=BacktestDraftResponse, status_code=201)
def backtest_draft(request: BacktestDraftRequest) -> BacktestDraftResponse:
    """Execute a one-click backtest of an approved AI-generated StrategyIR draft."""
    try:
        strategy = StrategyIR.from_dict(request.strategy_ir)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid StrategyIR schema: {exc}") from exc

    now = datetime.now(tz=UTC)
    start_date = request.start_date or (now - timedelta(days=30))
    end_date = request.end_date or now

    ir_hash = compute_ir_hash(request.strategy_ir)
    ai_meta = AIGenerationMetadata(
        prompt=request.prompt,
        provider_name=request.provider_name,
        model_version=request.model_version,
        ir_version=strategy.ir_version,
        ir_hash=ir_hash,
        generated_at=now,
        approved_at=now,
        draft_status="APPROVED_DRAFT",
    )

    config = BacktestConfig(
        strategy=strategy,
        start_date=start_date,
        end_date=end_date,
        initial_cash=request.initial_cash,
        ai_metadata=ai_meta,
    )

    runner = StockStrategyBacktestRunner()
    result = runner.run(config)
    backtest_store.save_result(result)

    return BacktestDraftResponse(
        backtest_id=result.backtest_id,
        result=result,
        ai_metadata=ai_meta,
    )
