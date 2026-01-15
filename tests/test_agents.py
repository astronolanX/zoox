"""
Tests for reef agent infrastructure.

Phase 4 will implement:
- test_orchestrator_flow
- test_strategist_decomposition
- test_validator_tier1
- test_validator_tier2
- test_agent_integration
"""

import pytest

from reef.agents import ReefOrchestrator, ReefStrategist, ReefValidator
from reef.agents.orchestrator import SubTask, TaskResult, WorkerResult
from reef.agents.strategist import TaskAnalysis, ExecutionPlan, Complexity, Sensitivity
from reef.agents.validator import ValidationResult, ValidationStatus, ValidationTier


class TestReefOrchestrator:
    """Tests for reef orchestrator."""

    def test_import(self):
        """Verify module imports correctly."""
        assert ReefOrchestrator is not None

    def test_instantiation(self):
        """Verify can create orchestrator instance."""
        orch = ReefOrchestrator()
        assert orch is not None

    def test_subtask_dataclass(self):
        """Verify SubTask dataclass works."""
        task = SubTask(
            id="test-1",
            description="Test task",
            task_type="search",
            sensitivity="external-ok",
        )
        assert task.id == "test-1"

    def test_task_result_dataclass(self):
        """Verify TaskResult dataclass works."""
        result = TaskResult(
            success=True,
            output={"data": "test"},
        )
        assert result.success is True


class TestReefStrategist:
    """Tests for reef strategist."""

    def test_import(self):
        """Verify module imports correctly."""
        assert ReefStrategist is not None

    def test_instantiation(self):
        """Verify can create strategist instance."""
        strat = ReefStrategist()
        assert strat is not None

    def test_complexity_enum(self):
        """Verify Complexity enum works."""
        assert Complexity.LOW.value == "low"
        assert Complexity.HIGH.value == "high"

    def test_sensitivity_enum(self):
        """Verify Sensitivity enum works."""
        assert Sensitivity.PII.value == "pii"
        assert Sensitivity.EXTERNAL_OK.value == "external-ok"

    def test_classify_sensitivity_default(self):
        """Verify default sensitivity classification."""
        strat = ReefStrategist()
        sensitivity = strat.classify_sensitivity("search for files")
        assert sensitivity == Sensitivity.EXTERNAL_OK


class TestReefValidator:
    """Tests for reef validator."""

    def test_import(self):
        """Verify module imports correctly."""
        assert ReefValidator is not None

    def test_instantiation(self):
        """Verify can create validator instance."""
        val = ReefValidator()
        assert val is not None

    def test_validation_status_enum(self):
        """Verify ValidationStatus enum works."""
        assert ValidationStatus.PASS.value == "pass"
        assert ValidationStatus.FAIL.value == "fail"

    def test_schema_checks_required_fields(self):
        """Verify schema checks for required fields."""
        val = ReefValidator()
        checks = val._run_schema_checks(
            output={"name": "test"},
            expected={"required_fields": ["name", "value"]},
        )
        # One pass (name), one fail (value)
        assert len(checks) == 2
        assert checks[0].passed is True
        assert checks[1].passed is False


# Phase 4 TODO tests

class TestAgentIntegration:
    """Integration tests for agent infrastructure."""

    @pytest.mark.skip(reason="Requires Phase 4 implementation")
    def test_orchestrator_flow(self):
        """Full test of orchestrator task flow."""
        pass

    @pytest.mark.skip(reason="Requires Phase 4 implementation")
    def test_strategist_decomposition(self):
        """Full test of task decomposition."""
        pass

    @pytest.mark.skip(reason="Requires Phase 4 implementation")
    def test_validator_tier1(self):
        """Full test of Tier 1 validation."""
        pass

    @pytest.mark.skip(reason="Requires Phase 4 implementation")
    def test_validator_tier2(self):
        """Full test of Tier 2 semantic validation."""
        pass

    @pytest.mark.skip(reason="Requires Phase 4 implementation")
    def test_agent_integration(self):
        """Full integration test of all agents."""
        pass
