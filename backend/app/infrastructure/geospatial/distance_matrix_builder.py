import networkx as nx
import numpy as np
import osmnx as ox

from app.domain.entities.node import Node


def build_distance_time_matrix(graph: nx.MultiDiGraph, nodes: list[Node]) -> tuple[np.ndarray, np.ndarray]:
    """Snaps each Node to its nearest routable edge, then computes the asymmetric
    N×N shortest-path distance (meters) and time (seconds) matrices (PRD Section 10)."""
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
