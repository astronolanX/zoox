"""
Tests for reef agent infrastructure.

Phase 4 implementation complete:
- test_orchestrator_flow
- test_strategist_decomposition
- test_validator_tier1
- test_validator_tier2
- test_agent_integration
"""

import pytest
from pathlib import Path

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

    def test_worker_result_dataclass(self):
        """Verify WorkerResult dataclass works."""
        result = WorkerResult(
            sub_task_id="test-1",
            success=True,
            output="test output",
            worker_used="groq",
            latency_ms=100,
        )
        assert result.success is True
        assert result.worker_used == "groq"

    def test_lazy_loading(self):
        """Verify lazy loading of dependencies."""
        orch = ReefOrchestrator()
        assert orch._strategist is None
        assert orch._validator is None
        # Access triggers lazy load
        _ = orch.strategist
        assert orch._strategist is not None

    def test_aggregate_results(self):
        """Test aggregation of worker results."""
        orch = ReefOrchestrator()

        results = [
            WorkerResult("task-1", True, "output1", "groq", 100),
            WorkerResult("task-2", True, "output2", "ollama", 200),
            WorkerResult("task-3", False, None, "groq", 50, error="Failed"),
        ]

        aggregated = orch.aggregate(results)

        assert aggregated["sub_task_count"] == 3
        assert aggregated["success_count"] == 2
        assert aggregated["failure_count"] == 1
        assert aggregated["total_latency_ms"] == 350
        assert "groq" in aggregated["workers_used"]
        assert "ollama" in aggregated["workers_used"]

    def test_decompose_simple(self):
        """Test decomposition of simple task."""
        orch = ReefOrchestrator()
        sub_tasks = orch.decompose("search for files")

        assert len(sub_tasks) >= 1
        assert sub_tasks[0].task_type == "search"


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

    def test_classify_sensitivity_pii(self):
        """Verify PII sensitivity classification."""
        strat = ReefStrategist()
        sensitivity = strat.classify_sensitivity("find user password")
        assert sensitivity == Sensitivity.PII

    def test_classify_sensitivity_legal(self):
        """Verify legal sensitivity classification."""
        strat = ReefStrategist()
        sensitivity = strat.classify_sensitivity("review the contract")
        assert sensitivity == Sensitivity.LEGAL

    def test_analyze_simple_task(self):
        """Test analysis of simple task."""
        strat = ReefStrategist()
        analysis = strat.analyze_task("search for files")

        assert analysis.original_task == "search for files"
        assert analysis.complexity == Complexity.LOW
        assert len(analysis.sub_tasks) >= 1

    def test_analyze_complex_task(self):
        """Test analysis of complex task."""
        strat = ReefStrategist()
        analysis = strat.analyze_task(
            "1. Search for all test files "
            "2. Extract the test names "
            "3. Combine them into a report"
        )

        assert analysis.complexity in (Complexity.MEDIUM, Complexity.HIGH)
        assert len(analysis.sub_tasks) >= 2

    def test_route_to_workers(self):
        """Test worker routing."""
        strat = ReefStrategist()

        sub_tasks = [
            {"id": "1", "task_type": "search", "sensitivity": "external-ok"},
            {"id": "2", "task_type": "summarize", "sensitivity": "external-ok"},
            {"id": "3", "task_type": "validate", "sensitivity": "pii"},
        ]

        routing = strat.route_to_workers(sub_tasks)

        # Search goes to groq
        assert any(t["id"] == "1" for t in routing["groq"])
        # Summarize goes to ollama
        assert any(t["id"] == "2" for t in routing["ollama"])
        # PII goes to claude
        assert any(t["id"] == "3" for t in routing["claude"])

    def test_plan_execution(self):
        """Test execution planning."""
        strat = ReefStrategist()
        analysis = strat.analyze_task("search for files then summarize results")

        plan = strat.plan_execution(analysis)

        assert len(plan.phases) >= 1
        assert isinstance(plan.estimated_workers, dict)
        assert isinstance(plan.requires_validation, bool)


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

    def test_schema_checks_types(self):
        """Verify schema checks for types."""
        val = ReefValidator()
        checks = val._run_schema_checks(
            output={"count": 5, "name": "test"},
            expected={
                "field_types": {"count": "int", "name": "str"},
            },
        )
        assert len(checks) == 2
        assert all(c.passed for c in checks)

    def test_validate_output_pass(self):
        """Test output validation passes."""
        val = ReefValidator()
        result = val.validate_output(
            output={
                "sub_task_count": 3,
                "success_count": 3,
                "outputs": {
                    "a": "This is a longer result with more content",
                    "b": "Another result with sufficient length",
                },
            },
            expected={},
        )
        assert result.status == ValidationStatus.PASS

    def test_validate_output_fail_success_rate(self):
        """Test output validation fails on low success rate."""
        val = ReefValidator()
        result = val.validate_output(
            output={
                "sub_task_count": 10,
                "success_count": 2,  # 20% success rate
                "outputs": {},
            },
            expected={},
        )
        assert result.status == ValidationStatus.FAIL
        assert any("success rate" in e.lower() for e in result.errors)

    def test_validate_polip(self):
        """Test polip validation."""
        from reef.blob import Blob, BlobType, BlobScope

        val = ReefValidator()

        # Valid polip
        polip = Blob(
            type=BlobType.THREAD,
            scope=BlobScope.PROJECT,
            summary="Test thread with good summary",
        )
        result = val.validate_polip(polip)
        assert result.status in (ValidationStatus.PASS, ValidationStatus.WARN)

    def test_validate_pruning_empty(self):
        """Test pruning validation with empty list."""
        val = ReefValidator()
        result = val.validate_pruning([])
        assert result.status == ValidationStatus.PASS

    def test_validate_pruning_protected(self):
        """Test pruning validation with protected polips."""
        from reef.blob import Blob, BlobType, BlobScope

        val = ReefValidator()

        # Protected by type
        polip = Blob(
            type=BlobType.CONSTRAINT,
            scope=BlobScope.ALWAYS,
            summary="Protected constraint",
        )
        result = val.validate_pruning([polip])
        assert result.status == ValidationStatus.FAIL

    def test_validate_completeness(self):
        """Test completeness validation."""
        val = ReefValidator()

        # Complete
        result = val.validate_completeness(
            output={"a": 1, "b": 2, "c": 3},
            expected_keys=["a", "b", "c"],
        )
        assert result.status == ValidationStatus.PASS

        # Missing keys
        result = val.validate_completeness(
            output={"a": 1},
            expected_keys=["a", "b", "c"],
        )
        assert result.status == ValidationStatus.FAIL


class TestAgentIntegration:
    """Integration tests for agent infrastructure."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project with .claude directory."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        return tmp_path

    def test_orchestrator_flow(self, temp_project):
        """Full test of orchestrator task flow."""
        orch = ReefOrchestrator(project_dir=temp_project)

        # Decompose a task
        sub_tasks = orch.decompose("search for test files")

        assert len(sub_tasks) >= 1
        assert sub_tasks[0].task_type == "search"

        # Aggregate mock results
        mock_results = [
            WorkerResult("task-1", True, "found 5 files", "groq", 100),
        ]
        aggregated = orch.aggregate(mock_results)

        assert aggregated["success_count"] == 1
        assert "groq" in aggregated["workers_used"]

    def test_strategist_decomposition(self, temp_project):
        """Full test of task decomposition."""
        strat = ReefStrategist()

        # Complex multi-step task
        task = "Search for all Python files and extract their imports then summarize the dependencies"
        analysis = strat.analyze_task(task)

        assert analysis.complexity in (Complexity.MEDIUM, Complexity.HIGH)
        assert len(analysis.sub_tasks) >= 1

        # Create execution plan
        plan = strat.plan_execution(analysis)
        assert len(plan.phases) >= 1

    def test_validator_tier1(self, temp_project):
        """Full test of Tier 1 validation."""
        val = ReefValidator()

        # Schema validation
        result = val.validate_output(
            output={"name": "test", "count": 5},
            expected={
                "required_fields": ["name", "count"],
                "field_types": {"name": "str", "count": "int"},
            },
        )

        assert result.status == ValidationStatus.PASS
        assert result.tier == ValidationTier.SEMANTIC  # No errors = semantic tier

    def test_validator_tier2(self, temp_project):
        """Full test of Tier 2 semantic validation."""
        val = ReefValidator()

        # Output with potential issues
        result = val.validate_output(
            output={
                "sub_task_count": 2,
                "success_count": 2,
                "outputs": {"task1": "short"},  # Suspiciously short
            },
            expected={},
        )

        # Should have warnings but pass
        assert result.status == ValidationStatus.WARN
        assert len(result.warnings) > 0

    def test_agent_integration(self, temp_project):
        """Full integration test of all agents."""
        orch = ReefOrchestrator(project_dir=temp_project)

        # Test full pipeline (without actual worker execution)
        task = "Summarize the project structure"

        # Analyze via strategist
        analysis = orch.strategist.analyze_task(task)
        assert analysis is not None

        # Create plan
        plan = orch.strategist.plan_execution(analysis)
        assert plan is not None

        # Mock worker results
        mock_results = [
            WorkerResult("main-task", True, "Project has 10 files", "ollama", 150),
        ]

        # Aggregate
        aggregated = orch.aggregate(mock_results)
        assert aggregated["success_count"] == 1

        # Validate
        validation = orch.validator.validate_output(aggregated, expected={})
        assert validation.status == ValidationStatus.PASS

    def test_pii_sensitivity_routing(self, temp_project):
        """Test that PII tasks are routed correctly."""
        strat = ReefStrategist()

        # Task with PII
        analysis = strat.analyze_task("Find user credentials in the config")
        assert analysis.sensitivity == Sensitivity.PII

        # Should require Claude
        assert "claude" in analysis.model_requirements

    def test_parallel_execution_grouping(self, temp_project):
        """Test parallel execution grouping."""
        strat = ReefStrategist()

        # Task with independent sub-tasks
        analysis = strat.analyze_task("Search for files")

        # Should have at least one parallel group
        assert len(analysis.parallel_groups) >= 1


class TestAgentDefinitions:
    """Test agent definition files."""

    def test_orchestrator_definition_exists(self):
        """Verify orchestrator definition file exists."""
        path = Path(".claude/agents/reef-orchestrator.md")
        assert path.exists()

    def test_strategist_definition_exists(self):
        """Verify strategist definition file exists."""
        path = Path(".claude/agents/reef-strategist.md")
        assert path.exists()

    def test_validator_definition_exists(self):
        """Verify validator definition file exists."""
        path = Path(".claude/agents/reef-validator.md")
        assert path.exists()
