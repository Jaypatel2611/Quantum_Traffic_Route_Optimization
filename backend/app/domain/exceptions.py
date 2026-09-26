class GraphDisconnectedError(Exception):
    """Raised when a graph has no usable largest strongly-connected component."""


class CapacityExceededError(Exception):
    """Raised by the QPSO dynamic penalty function (Phase 3) — not used until then."""


class TimeWindowViolation(Exception):
    """Raised by the QPSO dynamic penalty function (Phase 3) — not used until then."""
