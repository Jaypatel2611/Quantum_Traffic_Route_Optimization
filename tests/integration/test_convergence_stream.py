import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

import pytest
from app.presentation.sse.convergence_stream import convergence_event_stream


class _FakeOrchestrator:
    """Avoids spawning real subprocesses for this task's tests -- Task 2
    already proved the orchestrator's own cross-process mechanics for real;
    this task tests the SSE generator's own logic (replay, termination on
    done/error) against a controllable fake."""
    def __init__(self):
        self.convergence_cache = {}
        self.job_results = {}


@pytest.mark.asyncio
async def test_streams_progress_then_terminates_on_done():
    orch = _FakeOrchestrator()
    orch.convergence_cache["job1"] = [0.5, 0.3, 0.1]
    orch.job_results["job1"] = {"status": "done", "ortools": {}, "qpso": {}}

    events = [event async for event in convergence_event_stream("job1", orch)]
    assert any("event: progress" in e for e in events)
    assert events[-1].startswith("event: complete")


@pytest.mark.asyncio
async def test_terminates_on_error_not_infinite_spin():
    orch = _FakeOrchestrator()
    orch.convergence_cache["job2"] = [0.5]
    orch.job_results["job2"] = {"status": "error", "detail": "boom"}

    events = [event async for event in convergence_event_stream("job2", orch)]
    assert events[-1].startswith("event: error")
    assert "boom" in events[-1]


@pytest.mark.asyncio
async def test_reconnect_replays_full_history_from_index_zero():
    """PRD Section 15: a fresh connection to an already-populated job
    replays the FULL convergence_history, not just what's new -- no data
    point silently lost from the judge's view."""
    orch = _FakeOrchestrator()
    orch.convergence_cache["job3"] = [0.5, 0.3, 0.1]
    orch.job_results["job3"] = {"status": "done", "ortools": {}, "qpso": {}}

    first_connection = [event async for event in convergence_event_stream("job3", orch)]
    second_connection = [event async for event in convergence_event_stream("job3", orch)]
    progress_events = [e for e in second_connection if "event: progress" in e]
    assert len(progress_events) == 3  # all three points replayed, not zero
    assert first_connection == second_connection
