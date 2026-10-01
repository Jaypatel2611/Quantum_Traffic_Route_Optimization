from app.domain.entities.route import Route


def _sequence_time_s(sequence: list[str], index: dict[str, int], time_matrix) -> float:
    return float(sum(time_matrix[index[a]][index[b]] for a, b in zip(sequence, sequence[1:])))


def compute_route_changes(
    baseline_routes: list[Route], actual_routes: list[Route], node_ids: list[str], time_matrix
) -> dict:
    """Did the accidents change the solver's stop order?

    `baseline_routes` were solved on the accident-free matrices, `actual_routes`
    on the accident ones. The no-accident routes are also priced on the
    accident time matrix, so `saved_time_s` says what choosing differently was
    worth. Both solvers are time-limited, so a changed order can occasionally
    come from search noise rather than the accidents; the saved time is the
    honest measure of whether the new order actually helps."""
    index = {node_id: i for i, node_id in enumerate(node_ids)}
    baseline = [r.node_sequence for r in baseline_routes]
    actual = [r.node_sequence for r in actual_routes]
    baseline_under_accidents_s = sum(_sequence_time_s(seq, index, time_matrix) for seq in baseline)
    actual_time_s = float(sum(r.total_time_s for r in actual_routes))
    return {
        "changed": sorted(map(tuple, baseline)) != sorted(map(tuple, actual)),
        "baseline_sequences": baseline,
        "baseline_time_under_accidents_s": baseline_under_accidents_s,
        "actual_time_s": actual_time_s,
        "saved_time_s": baseline_under_accidents_s - actual_time_s,
    }
