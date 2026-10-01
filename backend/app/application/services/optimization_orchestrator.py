import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager

from app.infrastructure.algorithms.or_tools_baseline import run_ortools_job
from app.infrastructure.algorithms.qpso_solver import run_qpso_job

logger = logging.getLogger(__name__)


class OptimizationOrchestrator:
    """PRD Section 7's fairness seam: owns the shared seed and time budget,
    hands both to both solver adapters identically, runs them concurrently
    off the event loop."""

    def __init__(self, executor: ProcessPoolExecutor | None = None):
        self.executor = executor or ProcessPoolExecutor(max_workers=2)
        self.job_results: dict[str, dict] = {}
        self.convergence_cache: dict[str, list] = {}
        # Manager() spawns a real OS subprocess -- deferred until actually
        # needed, not created here. main.py builds an OptimizationOrchestrator
        # at import time; if this ran eagerly, merely importing app.main
        # (including every ProcessPoolExecutor child re-importing the entry
        # script under Windows' spawn method) would itself spawn a subprocess,
        # tripping Python's recursive-bootstrap guard. Found live via Task 5's
        # verification script, not a test.
        self._manager = None

    async def run_comparison(
        self, job_id: str, payload: dict, seed: int, time_budget_s: float, baseline_payload: dict | None = None
    ) -> None:
        if self._manager is None:
            self._manager = Manager()
        loop = asyncio.get_running_loop()
        progress_list = self._manager.list()
        self.convergence_cache[job_id] = progress_list
        self.job_results[job_id] = {"status": "running"}

        try:
            ortools_future = loop.run_in_executor(self.executor, run_ortools_job, payload, seed, time_budget_s)
            qpso_future = loop.run_in_executor(
                self.executor, run_qpso_job, payload, seed, time_budget_s, progress_list
            )
            ortools_result, qpso_result = await asyncio.gather(ortools_future, qpso_future)
            self.job_results[job_id] = {
                "status": "done", "ortools": ortools_result, "qpso": qpso_result,
                "baseline": "pending" if baseline_payload is not None else None,
            }
        except Exception:
            logger.exception("Solver job %s failed", job_id)
            self.job_results[job_id] = {"status": "error", "detail": "Solver failed. Check server logs for details."}
            return

        if baseline_payload is None:
            return
        # Same seed and budget on the accident-free matrices, run only after the
        # main pair finished so it never competes with them for CPU (QPSO's
        # budget is wall-clock). The job is already "done"; a baseline failure
        # must not turn it into an error.
        result = self.job_results[job_id]
        try:
            baseline_ortools, baseline_qpso = await asyncio.gather(
                loop.run_in_executor(self.executor, run_ortools_job, baseline_payload, seed, time_budget_s),
                loop.run_in_executor(self.executor, run_qpso_job, baseline_payload, seed, time_budget_s, None),
            )
            result["baseline"] = {"ortools": baseline_ortools, "qpso": baseline_qpso}
        except Exception:
            logger.exception("Baseline solve for job %s failed", job_id)
            result["baseline"] = "failed"
