"""
Phase 3c & 3d: Investigation Canvas Data Model

Canvas represents a visual workspace for investigation analysis with nodes, edges, and layouts.

Node Types:
- EVENT: An event in the investigation
- INVESTIGATION: An investigation
- RESOLUTION: A resolution path
- TOOL: An analysis tool
- METRIC: A metric or data point

Connection Types:
- CAUSE_EFFECT: A → B means A caused B
- CORRELATION: A and B are correlated
- SEQUENCE: A happened before B
- DEPENDS_ON: A depends on B being resolved
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json


class NodeType(Enum):
    """Types of nodes in the canvas"""

    EVENT = "EVENT"
    INVESTIGATION = "INVESTIGATION"
    RESOLUTION = "RESOLUTION"
    TOOL = "TOOL"
    METRIC = "METRIC"
    INSIGHT = "INSIGHT"


class EdgeType(Enum):
    """Types of connections between nodes"""

    CAUSE_EFFECT = "CAUSE_EFFECT"
    CORRELATION = "CORRELATION"
    SEQUENCE = "SEQUENCE"
    DEPENDS_ON = "DEPENDS_ON"
    RELATES_TO = "RELATES_TO"
    TRIGGERS = "TRIGGERS"


class CanvasNode:
    """Represents a node in the investigation canvas"""

    def __init__(
        self,
        id: str,
        type: NodeType,
        title: str,
        description: str = "",
        data: Optional[Dict] = None,
        position: Optional[Tuple[float, float]] = None,
        size: Optional[Tuple[float, float]] = None,
        metadata: Optional[Dict] = None,
    ):
        self.id = id
        self.type = type
        self.title = title
        self.description = description
        self.data = data or {}
        self.position = position or (0.0, 0.0)  # x, y coordinates
        self.size = size or (200.0, 100.0)  # width, height
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        """Convert node to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "data": self.data,
            "position": {"x": self.position[0], "y": self.position[1]},
            "size": {"width": self.size[0], "height": self.size[1]},
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_json(self) -> str:
        """Convert node to JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "CanvasNode":
        """Create node from dictionary"""
        position = data.get("position", {})
        size = data.get("size", {})
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            title=data["title"],
            description=data.get("description", ""),
            data=data.get("data", {}),
            position=(position.get("x", 0), position.get("y", 0)),
            size=(size.get("width", 200), size.get("height", 100)),
            metadata=data.get("metadata", {}),
        )


class CanvasEdge:
    """Represents a connection between nodes in the canvas"""

    def __init__(
        self,
        id: str,
        source_id: str,
        target_id: str,
        type: EdgeType,
        label: str = "",
        strength: float = 1.0,  # 0.0 to 1.0
        metadata: Optional[Dict] = None,
    ):
        self.id = id
        self.source_id = source_id
        self.target_id = target_id
        self.type = type
        self.label = label
        self.strength = strength  # Confidence or relationship strength
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        """Convert edge to dictionary"""
        return {
            "id": self.id,
            "source": self.source_id,
            "target": self.target_id,
            "type": self.type.value,
            "label": self.label,
            "strength": self.strength,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        """Convert edge to JSON"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "CanvasEdge":
        """Create edge from dictionary"""
        return cls(
            id=data["id"],
            source_id=data["source"],
            target_id=data["target"],
            type=EdgeType(data["type"]),
            label=data.get("label", ""),
            strength=data.get("strength", 1.0),
            metadata=data.get("metadata", {}),
        )


class Canvas:
    """Investigation Canvas - visual workspace for analysis"""

    def __init__(
        self,
        id: str,
        investigation_id: str,
        title: str,
        description: str = "",
        layout_type: str = "force-directed",  # force-directed, hierarchical, grid
    ):
        self.id = id
        self.investigation_id = investigation_id
        self.title = title
        self.description = description
        self.layout_type = layout_type
        self.nodes: Dict[str, CanvasNode] = {}
        self.edges: Dict[str, CanvasEdge] = {}
        self.created_at = datetime.utcnow().isoformat()
        self.updated_at = datetime.utcnow().isoformat()

    def add_node(self, node: CanvasNode) -> None:
        """Add a node to the canvas"""
        self.nodes[node.id] = node
        self.updated_at = datetime.utcnow().isoformat()

    def add_edge(self, edge: CanvasEdge) -> None:
        """Add an edge to the canvas"""
        # Validate that both nodes exist
        if edge.source_id not in self.nodes:
            raise ValueError(f"Source node {edge.source_id} not found")
        if edge.target_id not in self.nodes:
            raise ValueError(f"Target node {edge.target_id} not found")

        self.edges[edge.id] = edge
        self.updated_at = datetime.utcnow().isoformat()

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the canvas"""
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} not found")

        # Remove all edges connected to this node
        edges_to_remove = [
            e_id
            for e_id, e in self.edges.items()
            if e.source_id == node_id or e.target_id == node_id
        ]
        for e_id in edges_to_remove:
            del self.edges[e_id]

        del self.nodes[node_id]
        self.updated_at = datetime.utcnow().isoformat()

    def remove_edge(self, edge_id: str) -> None:
        """Remove an edge from the canvas"""
        if edge_id not in self.edges:
            raise ValueError(f"Edge {edge_id} not found")

        del self.edges[edge_id]
        self.updated_at = datetime.utcnow().isoformat()

    def get_node(self, node_id: str) -> Optional[CanvasNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[CanvasEdge]:
        """Get an edge by ID"""
        return self.edges.get(edge_id)

    def get_connected_nodes(self, node_id: str) -> List[CanvasNode]:
        """Get all nodes connected to a given node"""
        connected_ids = set()

        # Find edges where this node is source or target
        for edge in self.edges.values():
            if edge.source_id == node_id:
                connected_ids.add(edge.target_id)
            elif edge.target_id == node_id:
                connected_ids.add(edge.source_id)

        return [self.nodes[n_id] for n_id in connected_ids if n_id in self.nodes]

    def get_nodes_by_type(self, node_type: NodeType) -> List[CanvasNode]:
        """Get all nodes of a specific type"""
        return [n for n in self.nodes.values() if n.type == node_type]

    def get_edges_by_type(self, edge_type: EdgeType) -> List[CanvasEdge]:
        """Get all edges of a specific type"""
        return [e for e in self.edges.values() if e.type == edge_type]

    def get_causality_chain(self, node_id: str) -> List[CanvasNode]:
        """Get the chain of cause-effect relationships"""
        chain = []
        visited = set()

        def traverse(current_id: str):
            if current_id in visited:
                return
            visited.add(current_id)

            if current_id in self.nodes:
                chain.append(self.nodes[current_id])

            # Find cause-effect edges
            for edge in self.edges.values():
                if edge.type == EdgeType.CAUSE_EFFECT:
                    if edge.source_id == current_id:
                        traverse(edge.target_id)

        traverse(node_id)
        return chain

    def to_dict(self) -> Dict:
        """Convert canvas to dictionary"""
        return {
            "id": self.id,
            "investigation_id": self.investigation_id,
            "title": self.title,
            "description": self.description,
            "layout_type": self.layout_type,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges.values()],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_json(self) -> str:
        """Convert canvas to JSON"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> "Canvas":
        """Create canvas from dictionary"""
        canvas = cls(
            id=data["id"],
            investigation_id=data["investigation_id"],
            title=data["title"],
            description=data.get("description", ""),
            layout_type=data.get("layout_type", "force-directed"),
        )

        # Add nodes
        for node_data in data.get("nodes", []):
            canvas.add_node(CanvasNode.from_dict(node_data))

        # Add edges
        for edge_data in data.get("edges", []):
            canvas.add_edge(CanvasEdge.from_dict(edge_data))

        return canvas


class CanvasStore:
    """Store for managing canvases"""

    def __init__(self):
        self.canvases: Dict[str, Canvas] = {}

    def add(self, canvas: Canvas) -> None:
        """Add a canvas to the store"""
        self.canvases[canvas.id] = canvas

    def get(self, canvas_id: str) -> Optional[Canvas]:
        """Get a canvas by ID"""
        return self.canvases.get(canvas_id)

    def get_by_investigation(self, investigation_id: str) -> List[Canvas]:
        """Get all canvases for an investigation"""
        return [
            c for c in self.canvases.values() if c.investigation_id == investigation_id
        ]

    def delete(self, canvas_id: str) -> None:
        """Delete a canvas"""
        if canvas_id in self.canvases:
            del self.canvases[canvas_id]

    def update(self, canvas: Canvas) -> None:
        """Update a canvas"""
        self.canvases[canvas.id] = canvas

    def get_all(self) -> List[Canvas]:
        """Get all canvases"""
        return list(self.canvases.values())

    def count(self) -> int:
        """Get total canvas count"""
        return len(self.canvases)
