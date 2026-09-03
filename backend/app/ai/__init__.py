"""Product runtime AI provider package."""

from app.ai.accounting import AIUsageAccounting, usage_ledger
from app.ai.disabled import DisabledProvider
from app.ai.explainer import explain_strategy_ir
from app.ai.factory import get_ai_provider
from app.ai.generator import (
    GenerationResult,
    check_adversarial_safety,
    generate_strategy_ir_from_prompt,
)
from app.ai.mock import MockProvider
from app.ai.protocol import (
    AIProvider,
    AIResult,
    AIRuntimeDisabledError,
    AIRuntimeError,
    AISchemaValidationError,
    AISecretLeakageError,
    AITimeoutError,
    ProviderStatus,
)
from app.ai.redaction import contains_secret, redact_secrets
from app.ai.repair import repair_strategy_ir

__all__ = [
    "AIProvider",
    "AIResult",
    "AIRuntimeDisabledError",
    "AIRuntimeError",
    "AISchemaValidationError",
    "AISecretLeakageError",
    "AITimeoutError",
    "AIUsageAccounting",
    "DisabledProvider",
    "GenerationResult",
    "MockProvider",
    "ProviderStatus",
    "check_adversarial_safety",
    "contains_secret",
    "explain_strategy_ir",
    "generate_strategy_ir_from_prompt",
    "get_ai_provider",
    "redact_secrets",
    "repair_strategy_ir",
    "usage_ledger",
]
