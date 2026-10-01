import networkx as nx
import numpy as np
import osmnx as ox

from app.domain.entities.node import Node


def _snap_to_graph_nodes(graph: nx.MultiDiGraph, nodes: list[Node]) -> list:
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
    graph_node_ids = _snap_to_graph_nodes(graph, nodes)
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


def build_route_geometries(
    graph: nx.MultiDiGraph, nodes: list[Node], sequences: list[list[str]]
) -> list[list[list[float]]]:
    """Road-following [lat, lon] polyline for each route's node-id sequence.
    Each leg is the fastest (travel_time-weighted) path, i.e. the road the
    reported time came from. Pass the accident-modified graph and a blocked
    road's x5 time makes the line visibly detour around it. (The distance
    matrix uses the shortest-by-length path, which can be a different road.)
    Each leg starts and ends at the stop's own coordinates so the line meets
    the map dots rather than the nearest graph junction."""
    index = {n.id: i for i, n in enumerate(nodes)}
    graph_ids = _snap_to_graph_nodes(graph, nodes)
    legs: dict[tuple[int, int], list[list[float]]] = {}

    def leg(a: int, b: int) -> list[list[float]]:
        if (a, b) not in legs:
            junctions = nx.shortest_path(graph, graph_ids[a], graph_ids[b], weight="travel_time")
            points = [[nodes[a].coordinates.lat, nodes[a].coordinates.lon]]
            points += [[round(graph.nodes[j]["y"], 6), round(graph.nodes[j]["x"], 6)] for j in junctions]
            points.append([nodes[b].coordinates.lat, nodes[b].coordinates.lon])
            legs[(a, b)] = points
        return legs[(a, b)]

    geometries = []
    for sequence in sequences:
        polyline: list[list[float]] = []
        for a, b in zip(sequence, sequence[1:]):
            polyline += leg(index[a], index[b])
        geometries.append(polyline)
    return geometries
