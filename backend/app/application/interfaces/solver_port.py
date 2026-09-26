from typing import Protocol


class SolverPort(Protocol):
    def __call__(self, payload: dict, seed: int, time_budget_s: float) -> dict:
        """Returns {"routes": list[Route], "meta": dict}."""
        ...
