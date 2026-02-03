"""
Lineage Graph Traversal Utilities.

Traverse lineage graphs to find upstream and downstream dependencies.
"""

import logging
from typing import List, Set, Tuple
from sqlalchemy.orm import Session

from backend.models.lineage import LineageNode, LineageEdge

logger = logging.getLogger(__name__)


def get_upstream_nodes(
    db: Session,
    node_id: int,
    max_depth: int = 10,
    visited: Set[int] = None,
) -> Tuple[List[LineageNode], List[LineageEdge]]:
    """
    Recursively get all upstream (source) nodes.

    Args:
        db: Database session
        node_id: Starting node ID
        max_depth: Maximum traversal depth (prevent infinite loops)
        visited: Set of already visited node IDs

    Returns:
        (nodes: List[LineageNode], edges: List[LineageEdge])
    """
    if visited is None:
        visited = set()

    if node_id in visited or max_depth <= 0:
        return [], []

    visited.add(node_id)

    nodes = []
    edges = []

    # Get all edges where this node is the target (incoming edges)
    upstream_edges = db.query(LineageEdge).filter(
        LineageEdge.target_node_id == node_id
    ).all()

    for edge in upstream_edges:
        edges.append(edge)

        # Get the source node
        source_node = db.query(LineageNode).filter(
            LineageNode.id == edge.source_node_id
        ).first()

        if source_node and source_node.id not in visited:
            nodes.append(source_node)

            # Recursively get upstream of this source node
            upstream_nodes, upstream_edges = get_upstream_nodes(
                db=db,
                node_id=source_node.id,
                max_depth=max_depth - 1,
                visited=visited,
            )

            nodes.extend(upstream_nodes)
            edges.extend(upstream_edges)

    return nodes, edges


def get_downstream_nodes(
    db: Session,
    node_id: int,
    max_depth: int = 10,
    visited: Set[int] = None,
) -> Tuple[List[LineageNode], List[LineageEdge]]:
    """
    Recursively get all downstream (target) nodes.

    Args:
        db: Database session
        node_id: Starting node ID
        max_depth: Maximum traversal depth (prevent infinite loops)
        visited: Set of already visited node IDs

    Returns:
        (nodes: List[LineageNode], edges: List[LineageEdge])
    """
    if visited is None:
        visited = set()

    if node_id in visited or max_depth <= 0:
        return [], []

    visited.add(node_id)

    nodes = []
    edges = []

    # Get all edges where this node is the source (outgoing edges)
    downstream_edges = db.query(LineageEdge).filter(
        LineageEdge.source_node_id == node_id
    ).all()

    for edge in downstream_edges:
        edges.append(edge)

        # Get the target node
        target_node = db.query(LineageNode).filter(
            LineageNode.id == edge.target_node_id
        ).first()

        if target_node and target_node.id not in visited:
            nodes.append(target_node)

            # Recursively get downstream of this target node
            downstream_nodes, downstream_edges = get_downstream_nodes(
                db=db,
                node_id=target_node.id,
                max_depth=max_depth - 1,
                visited=visited,
            )

            nodes.extend(downstream_nodes)
            edges.extend(downstream_edges)

    return nodes, edges


def get_full_lineage_graph(
    db: Session,
    node_id: int,
    max_depth: int = 10,
) -> Tuple[List[LineageNode], List[LineageEdge]]:
    """
    Get the complete lineage graph (both upstream and downstream).

    Args:
        db: Database session
        node_id: Starting node ID
        max_depth: Maximum traversal depth

    Returns:
        (nodes: List[LineageNode], edges: List[LineageEdge])
    """
    # Get the root node
    root_node = db.query(LineageNode).filter(LineageNode.id == node_id).first()

    if not root_node:
        return [], []

    all_nodes = [root_node]
    all_edges = []

    # Get upstream lineage
    upstream_nodes, upstream_edges = get_upstream_nodes(
        db=db,
        node_id=node_id,
        max_depth=max_depth,
    )

    all_nodes.extend(upstream_nodes)
    all_edges.extend(upstream_edges)

    # Get downstream lineage
    downstream_nodes, downstream_edges = get_downstream_nodes(
        db=db,
        node_id=node_id,
        max_depth=max_depth,
    )

    all_nodes.extend(downstream_nodes)
    all_edges.extend(downstream_edges)

    # Deduplicate nodes and edges
    unique_nodes = list({node.id: node for node in all_nodes}.values())
    unique_edges = list({edge.id: edge for edge in all_edges}.values())

    logger.info(
        f"Lineage graph for node {node_id}: "
        f"{len(unique_nodes)} nodes, {len(unique_edges)} edges"
    )

    return unique_nodes, unique_edges


def find_lineage_path(
    db: Session,
    source_node_id: int,
    target_node_id: int,
    max_depth: int = 10,
) -> List[LineageEdge]:
    """
    Find the shortest path between two nodes in the lineage graph.

    Args:
        db: Database session
        source_node_id: Source node ID
        target_node_id: Target node ID
        max_depth: Maximum path length

    Returns:
        List of edges representing the path (empty if no path found)
    """
    # BFS to find shortest path
    from collections import deque

    queue = deque([(source_node_id, [])])
    visited = set()

    while queue:
        current_id, path = queue.popleft()

        if current_id == target_node_id:
            return path

        if current_id in visited or len(path) >= max_depth:
            continue

        visited.add(current_id)

        # Get all outgoing edges
        edges = db.query(LineageEdge).filter(
            LineageEdge.source_node_id == current_id
        ).all()

        for edge in edges:
            if edge.target_node_id not in visited:
                queue.append((edge.target_node_id, path + [edge]))

    return []  # No path found
