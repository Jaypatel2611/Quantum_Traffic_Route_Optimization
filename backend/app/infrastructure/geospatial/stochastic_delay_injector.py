import numpy as np

# SVRPBench Section 2.1 parameters (svrp_benchmark_doc.md)
MU_BASE = 0.0
SIGMA_BASE = 0.3
DELTA = 0.1
EPSILON = 0.2
PEAK_HOURS = (8.0, 17.0)
PEAK_SIGMA = 1.5


def _peak_hour_amplification(hour_of_day: float) -> float:
    closest_peak_distance = min(abs(hour_of_day - peak) for peak in PEAK_HOURS)
    gaussian_congestion = np.exp(-(closest_peak_distance**2) / (2 * PEAK_SIGMA**2))
    return DELTA + EPSILON * gaussian_congestion


def inject_stochastic_delay(
    time_matrix: np.ndarray, rng: np.random.Generator, hour_of_day: float = 8.0
) -> np.ndarray:
    """Multiplies each base travel time by a log-normal random multiplier, per
    SVRPBench's formulation (PRD Section 10 point 7). All randomness is drawn
    from the caller's seeded Generator — never numpy's global random state.

    Flagged interpretation: a raw lognormal(mean=0, sigma) draw has median 1.0
    but can fall below it, which would mean arriving faster than the
    deterministic free-flow base time — not what "stochastic delay" means.
    Multipliers are floored at 1.0 so delay only ever adds time, never
    subtracts it.
    """
    amplification = _peak_hour_amplification(hour_of_day)
    sigma = SIGMA_BASE + amplification
    multipliers = rng.lognormal(mean=MU_BASE, sigma=sigma, size=time_matrix.shape)
    multipliers = np.maximum(multipliers, 1.0)
    delayed = time_matrix * multipliers
    np.fill_diagonal(delayed, 0)
    return delayed
