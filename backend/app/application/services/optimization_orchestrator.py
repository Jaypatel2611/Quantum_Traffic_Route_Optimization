import asyncio
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager

from app.infrastructure.algorithms.or_tools_baseline import run_ortools_job
from app.infrastructure.algorithms.qpso_solver import run_qpso_job


class OptimizationOrchestrator:
    """PRD Section 7's fairness seam: owns the shared seed and time budget,
    hands both to both solver adapters identically, runs them concurrently
    off the event loop."""

    def __init__(self, executor: ProcessPoolExecutor | None = None):
        self.executor = executor or ProcessPoolExecutor(max_workers=2)
        self.job_results: dict[str, dict] = {}
        self.convergence_cache: dict[str, list] = {}
        self._manager = Manager()

    async def run_comparison(self, job_id: str, payload: dict, seed: int, time_budget_s: float) -> None:
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
            self.job_results[job_id] = {"status": "done", "ortools": ortools_result, "qpso": qpso_result}
        except Exception as exc:
            self.job_results[job_id] = {"status": "error", "detail": str(exc)}
