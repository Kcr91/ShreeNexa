"""REST API endpoints for AI strategy generation, repair, and explanation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.ai.explainer import explain_strategy_ir
from app.ai.generator import generate_strategy_ir_from_prompt
from app.ai.repair import repair_strategy_ir
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
