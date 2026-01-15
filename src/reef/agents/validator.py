"""
Reef Validator - Karen-style validation for reef operations.

Two-tier validation:
- Tier 1 (Schema): Fast, deterministic checks
- Tier 2 (Semantic): LLM-based judgment
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationTier(Enum):
    """Validation tier."""

    SCHEMA = "schema"    # Fast, deterministic
    SEMANTIC = "semantic"  # LLM-based judgment


class ValidationStatus(Enum):
    """Validation result status."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class ValidationResult:
    """Result from validation."""

    status: ValidationStatus
    tier: ValidationTier
    errors: list[str]
    warnings: list[str]
    details: dict[str, Any] | None = None


@dataclass
class SchemaCheck:
    """Schema validation check."""

    name: str
    passed: bool
    message: str | None = None


class ReefValidator:
    """Karen-style validation for reef operations."""

    def __init__(self, glob=None):
        """
        Initialize validator.

        Args:
            glob: Glob instance for reef operations
        """
        self.glob = glob

    def validate_output(
        self, output: dict[str, Any], expected: dict[str, Any]
    ) -> ValidationResult:
        """
        Two-tier validation.

        Tier 1 (Schema): Fast, deterministic checks
        - Format correct?
        - Required fields present?
        - Types match?

        Tier 2 (Semantic): LLM-based judgment
        - Does output match intent?
        - Quality acceptable?
        - Completeness verified?

        Args:
            output: Output to validate
            expected: Expected schema/criteria

        Returns:
            Validation result
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def validate_polip(self, polip) -> ValidationResult:
        """
        Validate polip before calcification.

        Args:
            polip: Polip instance to validate

        Returns:
            Validation result
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def validate_pruning(self, candidates: list) -> ValidationResult:
        """
        Validate pruning decisions before execution.

        Args:
            candidates: List of polips marked for pruning

        Returns:
            Validation result
        """
        # Will be implemented in Phase 4
        raise NotImplementedError("Will be implemented in Phase 4")

    def _run_schema_checks(
        self, output: dict[str, Any], expected: dict[str, Any]
    ) -> list[SchemaCheck]:
        """
        Run Tier 1 schema checks.

        Args:
            output: Output to check
            expected: Expected schema

        Returns:
            List of schema check results
        """
        checks = []

        # Check required fields
        if "required_fields" in expected:
            for field in expected["required_fields"]:
                passed = field in output
                checks.append(
                    SchemaCheck(
                        name=f"required_field:{field}",
                        passed=passed,
                        message=None if passed else f"Missing required field: {field}",
                    )
                )

        # Check types
        if "field_types" in expected:
            for field, expected_type in expected["field_types"].items():
                if field in output:
                    actual_type = type(output[field]).__name__
                    passed = actual_type == expected_type
                    checks.append(
                        SchemaCheck(
                            name=f"type_check:{field}",
                            passed=passed,
                            message=None
                            if passed
                            else f"Expected {expected_type}, got {actual_type}",
                        )
                    )

        return checks
