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

    SCHEMA = "schema"  # Fast, deterministic
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

    # Minimum acceptable success rate for batch operations
    MIN_SUCCESS_RATE = 0.5

    # Maximum allowed pruning percentage
    MAX_PRUNING_RATE = 0.25

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
        errors = []
        warnings = []

        # Tier 1: Schema checks
        schema_checks = self._run_schema_checks(output, expected)
        schema_errors = [c.message for c in schema_checks if not c.passed and c.message]
        errors.extend(schema_errors)

        # Check success rate if this is an aggregated output
        if "success_count" in output and "sub_task_count" in output:
            total = output["sub_task_count"]
            success = output["success_count"]
            if total > 0:
                rate = success / total
                if rate < self.MIN_SUCCESS_RATE:
                    errors.append(
                        f"Success rate {rate:.1%} below threshold {self.MIN_SUCCESS_RATE:.0%}"
                    )
                elif rate < 1.0:
                    warnings.append(f"Some sub-tasks failed ({total - success}/{total})")

        # Check for empty outputs
        if "outputs" in output and not output["outputs"]:
            if output.get("sub_task_count", 0) > 0:
                warnings.append("No outputs produced despite having sub-tasks")

        # Tier 2: Semantic checks (simplified without LLM)
        semantic_warnings = self._run_semantic_checks(output, expected)
        warnings.extend(semantic_warnings)

        # Determine status
        if errors:
            status = ValidationStatus.FAIL
        elif warnings:
            status = ValidationStatus.WARN
        else:
            status = ValidationStatus.PASS

        # Use schema tier if we found issues there, otherwise semantic
        tier = ValidationTier.SCHEMA if errors else ValidationTier.SEMANTIC

        return ValidationResult(
            status=status,
            tier=tier,
            errors=errors,
            warnings=warnings,
            details={
                "schema_checks": len(schema_checks),
                "schema_passed": sum(1 for c in schema_checks if c.passed),
            },
        )

    def validate_polip(self, polip) -> ValidationResult:
        """
        Validate polip before calcification.

        Args:
            polip: Polip instance to validate

        Returns:
            Validation result
        """
        errors = []
        warnings = []

        # Check required attributes
        if not hasattr(polip, "summary") or not polip.summary:
            errors.append("Polip missing required summary")

        if not hasattr(polip, "type"):
            errors.append("Polip missing type")

        # Check summary quality
        if hasattr(polip, "summary") and polip.summary:
            summary = polip.summary
            if len(summary) < 10:
                warnings.append("Summary is very short (<10 chars)")
            if len(summary) > 500:
                warnings.append("Summary is very long (>500 chars)")
            if summary.lower() == summary[:20].lower():  # All lowercase check
                warnings.append("Summary may lack proper formatting")

        # Check for content if thread or decision
        if hasattr(polip, "type"):
            polip_type = polip.type.value if hasattr(polip.type, "value") else str(polip.type)
            if polip_type in ("thread", "decision"):
                if not hasattr(polip, "context") or not polip.context:
                    if not hasattr(polip, "decisions") or not polip.decisions:
                        warnings.append(f"{polip_type} polip has no content or decisions")

        # Determine status
        if errors:
            status = ValidationStatus.FAIL
        elif warnings:
            status = ValidationStatus.WARN
        else:
            status = ValidationStatus.PASS

        return ValidationResult(
            status=status,
            tier=ValidationTier.SCHEMA,
            errors=errors,
            warnings=warnings,
        )

    def validate_pruning(self, candidates: list) -> ValidationResult:
        """
        Validate pruning decisions before execution.

        Args:
            candidates: List of polips marked for pruning

        Returns:
            Validation result
        """
        errors = []
        warnings = []

        if not candidates:
            return ValidationResult(
                status=ValidationStatus.PASS,
                tier=ValidationTier.SCHEMA,
                errors=[],
                warnings=[],
            )

        # Check pruning rate
        if self.glob:
            index = self.glob.get_index()
            total = len(index.get("blobs", {}))
            if total > 0:
                pruning_rate = len(candidates) / total
                if pruning_rate > self.MAX_PRUNING_RATE:
                    errors.append(
                        f"Pruning rate {pruning_rate:.1%} exceeds max {self.MAX_PRUNING_RATE:.0%}"
                    )
                elif pruning_rate > self.MAX_PRUNING_RATE / 2:
                    warnings.append(
                        f"High pruning rate: {pruning_rate:.1%} ({len(candidates)}/{total})"
                    )

        # Check for protected polips
        protected_types = ["constraint"]
        protected_scopes = ["always"]

        for candidate in candidates:
            polip_type = None
            scope = None

            if hasattr(candidate, "type"):
                polip_type = (
                    candidate.type.value
                    if hasattr(candidate.type, "value")
                    else str(candidate.type)
                )
            if hasattr(candidate, "scope"):
                scope = (
                    candidate.scope.value
                    if hasattr(candidate.scope, "value")
                    else str(candidate.scope)
                )

            if polip_type in protected_types:
                errors.append(f"Cannot prune protected type: {polip_type}")
            if scope in protected_scopes:
                errors.append(f"Cannot prune protected scope: {scope}")

        # Determine status
        if errors:
            status = ValidationStatus.FAIL
        elif warnings:
            status = ValidationStatus.WARN
        else:
            status = ValidationStatus.PASS

        return ValidationResult(
            status=status,
            tier=ValidationTier.SCHEMA,
            errors=errors,
            warnings=warnings,
            details={
                "candidate_count": len(candidates),
            },
        )

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

        # Check min/max values
        if "value_ranges" in expected:
            for field, range_spec in expected["value_ranges"].items():
                if field in output:
                    value = output[field]
                    if isinstance(value, (int, float)):
                        min_val = range_spec.get("min")
                        max_val = range_spec.get("max")

                        if min_val is not None and value < min_val:
                            checks.append(
                                SchemaCheck(
                                    name=f"min_check:{field}",
                                    passed=False,
                                    message=f"{field} ({value}) below minimum ({min_val})",
                                )
                            )
                        elif max_val is not None and value > max_val:
                            checks.append(
                                SchemaCheck(
                                    name=f"max_check:{field}",
                                    passed=False,
                                    message=f"{field} ({value}) above maximum ({max_val})",
                                )
                            )
                        else:
                            checks.append(
                                SchemaCheck(name=f"range_check:{field}", passed=True)
                            )

        return checks

    def _run_semantic_checks(
        self, output: dict[str, Any], expected: dict[str, Any]
    ) -> list[str]:
        """
        Run Tier 2 semantic checks (simplified without LLM).

        Args:
            output: Output to check
            expected: Expected criteria

        Returns:
            List of warning messages
        """
        warnings = []

        # Check for suspiciously short outputs
        if "outputs" in output:
            for key, value in output["outputs"].items():
                if isinstance(value, str) and len(value) < 10:
                    warnings.append(f"Output '{key}' is suspiciously short")

        # Check for error patterns in output
        if isinstance(output, dict):
            for key, value in output.items():
                if isinstance(value, str):
                    lower_val = value.lower()
                    if "error" in lower_val or "failed" in lower_val:
                        warnings.append(f"Potential error in '{key}'")

        return warnings

    def validate_completeness(
        self, output: dict[str, Any], expected_keys: list[str]
    ) -> ValidationResult:
        """
        Validate output completeness.

        Args:
            output: Output to validate
            expected_keys: Keys that should be present

        Returns:
            Validation result
        """
        missing = [k for k in expected_keys if k not in output]
        present = [k for k in expected_keys if k in output]

        if missing:
            return ValidationResult(
                status=ValidationStatus.FAIL,
                tier=ValidationTier.SCHEMA,
                errors=[f"Missing expected keys: {', '.join(missing)}"],
                warnings=[],
                details={
                    "expected": len(expected_keys),
                    "present": len(present),
                    "missing": missing,
                },
            )

        return ValidationResult(
            status=ValidationStatus.PASS,
            tier=ValidationTier.SCHEMA,
            errors=[],
            warnings=[],
            details={
                "expected": len(expected_keys),
                "present": len(present),
            },
        )
