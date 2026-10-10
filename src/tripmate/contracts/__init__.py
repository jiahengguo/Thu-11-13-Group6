"""Versioned JSON contracts: the language-neutral source of truth."""
import json
from importlib.resources import files
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

VERSION = "1.0.0"
SCHEMA_NAMES = (
    "Case", "TravelRequest", "SupplierOffer", "PriceBreakdown",
    "ItineraryVersion", "AgentResult", "Approval", "TraceEvent",
)


class ContractError(ValueError):
    """A boundary rejected a payload; callers must not continue with it."""


def schema_bundle() -> dict:
    return json.loads(files(__package__).joinpath("v1/schemas.json").read_text())


def validate(name: str, payload: Any) -> None:
    """Validate structure/formats; business-rule validation belongs to B04."""
    if name not in SCHEMA_NAMES:
        raise ContractError(f"Unknown contract: {name}")
    schema = schema_bundle()
    schema["$ref"] = f"#/$defs/{name}"
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(payload), key=lambda error: str(error.path))
    if errors:
        details = "; ".join(
            f"{'/'.join(map(str, error.path)) or '$'}: {error.message}"
            for error in errors
        )
        raise ContractError(f"{name}: {details}")
