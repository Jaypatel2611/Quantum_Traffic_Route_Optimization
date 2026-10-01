import networkx as nx
import numpy as np
import osmnx as ox

from app.domain.entities.node import Node


def snap_to_graph_nodes(graph: nx.MultiDiGraph, nodes: list[Node]) -> list:
    xs = [n.coordinates.lon for n in nodes]
    ys = [n.coordinates.lat for n in nodes]
    snapped_edges = ox.distance.nearest_edges(graph, xs, ys)

    # Anchor each point at whichever of its snapped edge's two endpoints is
    # actually nearer — always picking the destination node collapses two
    # points that both border the same edge (e.g. one at each end) onto a
    # single graph node, silently zeroing the distance between them.
    # Squared-degree distance (not haversine) is enough to compare "nearer
    # vs farther" at city-block scale, where it's monotonic with real distance.
    graph_node_ids = []
    for (u, v, _key), x, y in zip(snapped_edges, xs, ys):
        u_dist = (graph.nodes[u]["x"] - x) ** 2 + (graph.nodes[u]["y"] - y) ** 2
        v_dist = (graph.nodes[v]["x"] - x) ** 2 + (graph.nodes[v]["y"] - y) ** 2
        graph_node_ids.append(u if u_dist <= v_dist else v)
    return graph_node_ids


class FastestPaths:
    """Fastest (travel_time-weighted) paths over a graph, one Dijkstra tree per
    source, cached. The distance matrix, the drawn route and the accident
    analysis all read from this one definition of "the road driven" so the
    reported km, the reported minutes and the line on the map describe the same
    path. Ties between equally fast paths resolve to the same one everywhere."""

    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph
        self._trees: dict = {}
        self._edge: dict[tuple, tuple[float, float]] | None = None

    def _fastest_edges(self) -> dict[tuple, tuple[float, float]]:
        """(u, v) -> (travel_time, length) of the fastest parallel edge, the one a driver takes."""
        if self._edge is None:
            best: dict[tuple, tuple[float, float]] = {}
            for u, v, data in self.graph.edges(data=True):
                if (u, v) not in best or data["travel_time"] < best[(u, v)][0]:
                    best[(u, v)] = (data["travel_time"], data["length"])
            self._edge = best
        return self._edge

    def _tree(self, source):
        if source not in self._trees:
            pred, times = nx.dijkstra_predecessor_and_distance(self.graph, source, weight="travel_time")
            parent = {v: p[0] for v, p in pred.items() if p}
            self._trees[source] = (parent, times)
        return self._trees[source]

    def path(self, source, target) -> list:
        parent, _ = self._tree(source)
        nodes = [target]
        while nodes[-1] != source:
            nodes.append(parent[nodes[-1]])
        return nodes[::-1]

    def time(self, source, target) -> float:
        return self._tree(source)[1][target]

    def lengths_from(self, source) -> dict:
        """Length (m) of the fastest path from source to every reachable node."""
        parent, times = self._tree(source)
        edges = self._fastest_edges()
        lengths = {source: 0.0}
        for v in sorted(times, key=times.__getitem__):
            if v != source:
                lengths[v] = lengths[parent[v]] + edges[(parent[v], v)][1]
        return lengths


def build_distance_time_matrix(graph: nx.MultiDiGraph, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]:
    """Snaps each Node to its nearest routable edge, then computes the asymmetric
    N×N time (seconds) and distance (meters) matrices (PRD Section 10). Both
    describe one road: the fastest path, with distance being that path's length
    (so an accident that slows a road, and makes the fastest path detour, also
    lengthens the distance)."""
    graph_node_ids = snap_to_graph_nodes(graph, nodes)
    paths = FastestPaths(graph)
    n = len(nodes)
    dist = np.zeros((n, n))
    time = np.zeros((n, n))
    for i, source in enumerate(graph_node_ids):
        lengths = paths.lengths_from(source)
        for j, target in enumerate(graph_node_ids):
            if i == j:
                continue
            dist[i, j] = lengths[target]
            time[i, j] = paths.time(source, target)
    return dist, time


def build_route_leg_geometries(
    graph: nx.MultiDiGraph, nodes: list[Node], sequences: list[list[str]]
) -> list[list[list[list[float]]]]:
    """Per route, one road-following [lat, lon] polyline per leg (consecutive
    stop pair), in visit order. Each leg is the fastest (travel_time-weighted)
    path -- the same road the distance and time matrices describe. Pass the
    accident-modified graph and a blocked road's x5 time makes the line visibly
    detour around it. Each leg starts and ends at the stop's own coordinates so
    the line meets the map dots rather than the nearest graph junction."""
    index = {n.id: i for i, n in enumerate(nodes)}
    graph_ids = snap_to_graph_nodes(graph, nodes)
    paths = FastestPaths(graph)
    legs: dict[tuple[int, int], list[list[float]]] = {}

    def leg(a: int, b: int) -> list[list[float]]:
        if (a, b) not in legs:
            junctions = paths.path(graph_ids[a], graph_ids[b])
            points = [[nodes[a].coordinates.lat, nodes[a].coordinates.lon]]
            points += [[round(graph.nodes[j]["y"], 6), round(graph.nodes[j]["x"], 6)] for j in junctions]
            points.append([nodes[b].coordinates.lat, nodes[b].coordinates.lon])
            legs[(a, b)] = points
        return legs[(a, b)]

    return [[leg(index[a], index[b]) for a, b in zip(sequence, sequence[1:])] for sequence in sequences]


def build_route_geometries(
    graph: nx.MultiDiGraph, nodes: list[Node], sequences: list[list[str]]
) -> list[list[list[float]]]:
    """build_route_leg_geometries with each route's legs joined into one polyline."""
    return [
        [point for leg in legs for point in leg]
        for legs in build_route_leg_geometries(graph, nodes, sequences)
    ]


def build_accident_impacts(
    graph: nx.MultiDiGraph,
    nodes: list[Node],
    sequences: list[list[str]],
    accident_edges: list[tuple[int, int]],
    multiplier: float,
) -> list[dict]:
    """One entry per accident, judged against the routes' actual stop order.
    `graph` is the accident-free graph. Statuses:
      not_on_route   -- no leg's fastest free path uses the segment: no effect.
      rerouted       -- legs crossed it for free but now drive around it.
      driven_through -- no cheaper way around: legs still use it, slowed.
    added_time_s is that accident's own base road-time cost over the crossed legs
    (the injected random delay is applied to the whole matrix, not per road)."""
    index = {n.id: i for i, n in enumerate(nodes)}
    graph_ids = snap_to_graph_nodes(graph, nodes)

    def delayed(pairs: set[frozenset]) -> nx.MultiDiGraph:
        g = graph.copy()
        for u, v, data in g.edges(data=True):
            if frozenset((u, v)) in pairs:
                data["travel_time"] *= multiplier
        return g

    def uses(path: list, pair: frozenset) -> bool:
        return any(frozenset((u, v)) == pair for u, v in zip(path, path[1:]))

    free = FastestPaths(graph)

    legs = {
        (index[a], index[b])
        for sequence in sequences
        for a, b in zip(sequence, sequence[1:])
    }
    free_paths = {leg: free.path(graph_ids[leg[0]], graph_ids[leg[1]]) for leg in legs}
    with_all = FastestPaths(delayed({frozenset(e) for e in accident_edges}))
    drawn_paths = {leg: with_all.path(graph_ids[leg[0]], graph_ids[leg[1]]) for leg in legs}

    impacts = []
    for from_id, to_id in accident_edges:
        pair = frozenset((from_id, to_id))
        crossed = [leg for leg, path in free_paths.items() if uses(path, pair)]
        status, added = "not_on_route", 0.0
        if crossed:
            alone = FastestPaths(delayed({pair}))
            added = sum(
                alone.time(graph_ids[leg[0]], graph_ids[leg[1]]) - free.time(graph_ids[leg[0]], graph_ids[leg[1]])
                for leg in crossed
            )
            status = "driven_through" if any(uses(drawn_paths[leg], pair) for leg in crossed) else "rerouted"
        impacts.append({
            "from_node_id": from_id, "to_node_id": to_id,
            "status": status, "added_time_s": float(added),
        })
    return impacts

