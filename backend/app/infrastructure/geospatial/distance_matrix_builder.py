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


def build_distance_time_matrix(graph: nx.MultiDiGraph, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]:
    """Snaps each Node to its nearest routable edge, then computes the asymmetric
    N×N shortest-path distance (meters) and time (seconds) matrices (PRD Section 10)."""
    graph_node_ids = snap_to_graph_nodes(graph, nodes)
    n = len(nodes)
    dist = np.zeros((n, n))
    time = np.zeros((n, n))
    for i, source in enumerate(graph_node_ids):
        lengths = nx.single_source_dijkstra_path_length(graph, source, weight="length")
        times = nx.single_source_dijkstra_path_length(graph, source, weight="travel_time")
        for j, target in enumerate(graph_node_ids):
            if i == j:
                continue
            dist[i, j] = lengths[target]
            time[i, j] = times[target]
    return dist, time


def build_route_leg_geometries(
    graph: nx.MultiDiGraph, nodes: list[Node], sequences: list[list[str]]
) -> list[list[list[list[float]]]]:
    """Per route, one road-following [lat, lon] polyline per leg (consecutive
    stop pair), in visit order. Road-following [lat, lon] polyline for each route's node-id sequence.
    Each leg is the fastest (travel_time-weighted) path, i.e. the road the
    reported time came from. Pass the accident-modified graph and a blocked
    road's x5 time makes the line visibly detour around it. (The distance
    matrix uses the shortest-by-length path, which can be a different road.)
    Each leg starts and ends at the stop's own coordinates so the line meets
    the map dots rather than the nearest graph junction."""
    index = {n.id: i for i, n in enumerate(nodes)}
    graph_ids = snap_to_graph_nodes(graph, nodes)
    legs: dict[tuple[int, int], list[list[float]]] = {}

    def leg(a: int, b: int) -> list[list[float]]:
        if (a, b) not in legs:
            junctions = nx.shortest_path(graph, graph_ids[a], graph_ids[b], weight="travel_time")
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

    def fastest(g: nx.MultiDiGraph, leg: tuple[int, int]) -> list:
        return nx.shortest_path(g, graph_ids[leg[0]], graph_ids[leg[1]], weight="travel_time")

    legs = {
        (index[a], index[b])
        for sequence in sequences
        for a, b in zip(sequence, sequence[1:])
    }
    free_paths = {leg: fastest(graph, leg) for leg in legs}
    with_all = delayed({frozenset(e) for e in accident_edges})
    drawn_paths = {leg: fastest(with_all, leg) for leg in legs}

    impacts = []
    for from_id, to_id in accident_edges:
        pair = frozenset((from_id, to_id))
        crossed = [leg for leg, path in free_paths.items() if uses(path, pair)]
        status, added = "not_on_route", 0.0
        if crossed:
            alone = delayed({pair})
            added = sum(
                nx.path_weight(alone, fastest(alone, leg), "travel_time")
                - nx.path_weight(graph, free_paths[leg], "travel_time")
                for leg in crossed
            )
            status = "driven_through" if any(uses(drawn_paths[leg], pair) for leg in crossed) else "rerouted"
        impacts.append({
            "from_node_id": from_id, "to_node_id": to_id,
            "status": status, "added_time_s": float(added),
        })
    return impacts

