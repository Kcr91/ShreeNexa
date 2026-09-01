"""API endpoints for indicator discovery, metadata catalog, and formula validation."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.indicators.formula import FormulaCompiler, FormulaError
from app.indicators.registry import IndicatorFamily, registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/indicators", tags=["indicators"])
alias_router = APIRouter(prefix="/api/indicators", tags=["indicators"])


class IndicatorMetadataResponse(BaseModel):
    """Metadata schema for a registered technical indicator."""

    name: str = Field(description="Unique identifier name of the indicator")
    family: str = Field(description="Indicator category family")
    description: str = Field(description="Description of indicator computation and purpose")
    output_keys: list[str] = Field(description="Names of output series keys")
    default_params: dict[str, Any] = Field(description="Default parameters for calculation")


class ValidateFormulaRequest(BaseModel):
    """Payload for formula validation."""

    formula: str = Field(min_length=1, description="Formula expression to validate")


class ValidateFormulaResponse(BaseModel):
    """Result of AST syntax, security sandboxing, and lookahead validation."""

    valid: bool = Field(description="Whether the formula is syntactically and semantically valid")
    identifiers: list[str] = Field(
        default_factory=list, description="Referenced variables/indicators in expression"
    )
    error: str | None = Field(default=None, description="Diagnostic error message if invalid")


_compiler = FormulaCompiler()


def _list_indicators() -> list[IndicatorMetadataResponse]:
    indicators = registry.list_indicators()
    return [
        IndicatorMetadataResponse(
            name=ind.name,
            family=ind.family.value.lower()
            if isinstance(ind.family, IndicatorFamily)
            else str(ind.family).lower(),
            description=ind.description,
            output_keys=ind.output_keys,
            default_params=ind.default_params,
        )
        for ind in sorted(indicators, key=lambda x: x.name)
    ]


def _get_indicator(name: str) -> IndicatorMetadataResponse:
    try:
        ind = registry.get(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Indicator '{name}' not found") from None

    return IndicatorMetadataResponse(
        name=ind.name,
        family=ind.family.value.lower()
        if isinstance(ind.family, IndicatorFamily)
        else str(ind.family).lower(),
        description=ind.description,
        output_keys=ind.output_keys,
        default_params=ind.default_params,
    )


def _validate_formula(req: ValidateFormulaRequest) -> ValidateFormulaResponse:
    try:
        compiled = _compiler.compile(req.formula)
        return ValidateFormulaResponse(
            valid=True,
            identifiers=sorted(compiled.identifiers),
            error=None,
        )
    except FormulaError as exc:
        return ValidateFormulaResponse(
            valid=False,
            identifiers=[],
            error=str(exc),
        )
    except Exception as exc:
        return ValidateFormulaResponse(
            valid=False,
            identifiers=[],
            error=f"Syntax error: {exc}",
        )


@router.get("", response_model=list[IndicatorMetadataResponse])
@alias_router.get("", response_model=list[IndicatorMetadataResponse], include_in_schema=False)
def list_indicators() -> list[IndicatorMetadataResponse]:
    """List all registered technical indicators with metadata."""
    return _list_indicators()


@router.get("/{name}", response_model=IndicatorMetadataResponse)
@alias_router.get("/{name}", response_model=IndicatorMetadataResponse, include_in_schema=False)
def get_indicator(name: str) -> IndicatorMetadataResponse:
    """Retrieve metadata for a specific technical indicator by name."""
    return _get_indicator(name)


@router.post("/validate-formula", response_model=ValidateFormulaResponse)
@alias_router.post(
    "/validate-formula", response_model=ValidateFormulaResponse, include_in_schema=False
)
def validate_formula(req: ValidateFormulaRequest) -> ValidateFormulaResponse:
    """Validate a formula expression against AST syntax, security, and lookahead rules."""
    return _validate_formula(req)
