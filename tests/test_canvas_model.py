"""
Phase 3c & 3d: Tests for Investigation Canvas Data Model

Comprehensive test coverage for canvas, nodes, edges, and relationships.
"""

import pytest
import json
from datetime import datetime
from src.models.canvas import (
    Canvas, CanvasNode, CanvasEdge, CanvasStore,
    NodeType, EdgeType
)


@pytest.fixture
def sample_node():
    """Create a sample node"""
    return CanvasNode(
        id="node-1",
        type=NodeType.EVENT,
        title="Database Connection Error",
        description="Connection timeout to primary database",
        data={
            "timestamp": "2024-01-28T10:00:00Z",
            "service": "api-server",
            "duration_ms": 5000,
        },
        position=(100.0, 200.0),
    )


@pytest.fixture
def sample_canvas():
    """Create a sample canvas with nodes and edges"""
    canvas = Canvas(
        id="canvas-1",
        investigation_id="inv-1",
        title="Database Outage Investigation",
        description="Root cause analysis for database outage on 2024-01-28",
    )

    # Add nodes
    node1 = CanvasNode(
        id="node-1",
        type=NodeType.EVENT,
        title="High CPU on DB Primary",
        description="Database CPU spiked to 99%",
        data={"cpu_percent": 99, "timestamp": "2024-01-28T10:00:00Z"},
        position=(100.0, 100.0),
    )
    node2 = CanvasNode(
        id="node-2",
        type=NodeType.EVENT,
        title="Connection Pool Exhaustion",
        description="All connections exhausted",
        position=(300.0, 100.0),
    )
    node3 = CanvasNode(
        id="node-3",
        type=NodeType.RESOLUTION,
        title="Scale Database Connections",
        description="Increased max connections from 100 to 200",
        position=(200.0, 300.0),
    )

    canvas.add_node(node1)
    canvas.add_node(node2)
    canvas.add_node(node3)

    # Add edges
    edge1 = CanvasEdge(
        id="edge-1",
        source_id="node-1",
        target_id="node-2",
        type=EdgeType.CAUSE_EFFECT,
        label="caused",
        strength=0.95,
    )
    edge2 = CanvasEdge(
        id="edge-2",
        source_id="node-2",
        target_id="node-3",
        type=EdgeType.DEPENDS_ON,
        label="requires",
    )

    canvas.add_edge(edge1)
    canvas.add_edge(edge2)

    return canvas


class TestCanvasNode:
    """Test suite for CanvasNode"""

    def test_node_creation(self, sample_node):
        """Test creating a canvas node"""
        assert sample_node.id == "node-1"
        assert sample_node.type == NodeType.EVENT
        assert sample_node.title == "Database Connection Error"
        assert sample_node.position == (100.0, 200.0)

    def test_node_to_dict(self, sample_node):
        """Test converting node to dictionary"""
        node_dict = sample_node.to_dict()

        assert node_dict['id'] == "node-1"
        assert node_dict['type'] == "EVENT"
        assert node_dict['title'] == "Database Connection Error"
        assert node_dict['position']['x'] == 100.0
        assert node_dict['position']['y'] == 200.0
        assert 'created_at' in node_dict
        assert 'updated_at' in node_dict

    def test_node_to_json(self, sample_node):
        """Test converting node to JSON"""
        node_json = sample_node.to_json()
        parsed = json.loads(node_json)

        assert parsed['id'] == "node-1"
        assert parsed['type'] == "EVENT"

    def test_node_from_dict(self, sample_node):
        """Test creating node from dictionary"""
        node_dict = sample_node.to_dict()
        restored_node = CanvasNode.from_dict(node_dict)

        assert restored_node.id == sample_node.id
        assert restored_node.type == sample_node.type
        assert restored_node.title == sample_node.title
        assert restored_node.position == sample_node.position

    def test_node_default_position(self):
        """Test node default position is (0, 0)"""
        node = CanvasNode(
            id="test",
            type=NodeType.METRIC,
            title="Test Node"
        )
        assert node.position == (0.0, 0.0)

    def test_node_default_size(self):
        """Test node default size"""
        node = CanvasNode(
            id="test",
            type=NodeType.METRIC,
            title="Test Node"
        )
        assert node.size == (200.0, 100.0)

    def test_node_metadata_storage(self):
        """Test storing custom metadata on node"""
        node = CanvasNode(
            id="test",
            type=NodeType.EVENT,
            title="Test Node",
            metadata={"severity": "CRITICAL", "owner": "platform-team"}
        )
        assert node.metadata["severity"] == "CRITICAL"
        assert node.metadata["owner"] == "platform-team"

    def test_node_data_storage(self):
        """Test storing data on node"""
        node = CanvasNode(
            id="test",
            type=NodeType.EVENT,
            title="Test Node",
            data={"timestamp": "2024-01-28", "count": 42}
        )
        assert node.data["timestamp"] == "2024-01-28"
        assert node.data["count"] == 42

    def test_node_types_enumeration(self):
        """Test all node types are available"""
        for node_type in NodeType:
            node = CanvasNode(
                id=f"test-{node_type.value}",
                type=node_type,
                title=f"Test {node_type.value}"
            )
            assert node.type == node_type


class TestCanvasEdge:
    """Test suite for CanvasEdge"""

    def test_edge_creation(self):
        """Test creating a canvas edge"""
        edge = CanvasEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            type=EdgeType.CAUSE_EFFECT,
            label="caused",
            strength=0.95,
        )
        assert edge.id == "edge-1"
        assert edge.source_id == "node-1"
        assert edge.target_id == "node-2"
        assert edge.type == EdgeType.CAUSE_EFFECT
        assert edge.strength == 0.95

    def test_edge_to_dict(self):
        """Test converting edge to dictionary"""
        edge = CanvasEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            type=EdgeType.CORRELATION,
        )
        edge_dict = edge.to_dict()

        assert edge_dict['id'] == "edge-1"
        assert edge_dict['source'] == "node-1"
        assert edge_dict['target'] == "node-2"
        assert edge_dict['type'] == "CORRELATION"
        assert edge_dict['strength'] == 1.0

    def test_edge_to_json(self):
        """Test converting edge to JSON"""
        edge = CanvasEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            type=EdgeType.SEQUENCE,
        )
        edge_json = edge.to_json()
        parsed = json.loads(edge_json)

        assert parsed['id'] == "edge-1"
        assert parsed['type'] == "SEQUENCE"

    def test_edge_from_dict(self):
        """Test creating edge from dictionary"""
        edge = CanvasEdge(
            id="edge-1",
            source_id="node-1",
            target_id="node-2",
            type=EdgeType.DEPENDS_ON,
            strength=0.8,
        )
        edge_dict = edge.to_dict()
        restored_edge = CanvasEdge.from_dict(edge_dict)

        assert restored_edge.id == edge.id
        assert restored_edge.source_id == edge.source_id
        assert restored_edge.target_id == edge.target_id
        assert restored_edge.strength == edge.strength

    def test_edge_types_enumeration(self):
        """Test all edge types are available"""
        for edge_type in EdgeType:
            edge = CanvasEdge(
                id=f"test-{edge_type.value}",
                source_id="source",
                target_id="target",
                type=edge_type,
            )
            assert edge.type == edge_type


class TestCanvas:
    """Test suite for Canvas"""

    def test_canvas_creation(self):
        """Test creating a canvas"""
        canvas = Canvas(
            id="canvas-1",
            investigation_id="inv-1",
            title="Test Canvas",
        )
        assert canvas.id == "canvas-1"
        assert canvas.investigation_id == "inv-1"
        assert len(canvas.nodes) == 0
        assert len(canvas.edges) == 0

    def test_add_node_to_canvas(self, sample_canvas, sample_node):
        """Test adding a node to canvas"""
        initial_count = len(sample_canvas.nodes)
        new_node = CanvasNode(
            id="new-node",
            type=NodeType.INSIGHT,
            title="New Insight"
        )
        sample_canvas.add_node(new_node)

        assert len(sample_canvas.nodes) == initial_count + 1
        assert sample_canvas.get_node("new-node") is not None

    def test_add_edge_to_canvas(self, sample_canvas):
        """Test adding an edge to canvas"""
        initial_count = len(sample_canvas.edges)
        edge = CanvasEdge(
            id="new-edge",
            source_id="node-1",
            target_id="node-2",
            type=EdgeType.TRIGGERS,
        )
        sample_canvas.add_edge(edge)

        assert len(sample_canvas.edges) == initial_count + 1

    def test_add_edge_with_missing_source_node(self, sample_canvas):
        """Test adding edge with missing source node raises error"""
        edge = CanvasEdge(
            id="bad-edge",
            source_id="nonexistent-node",
            target_id="node-1",
            type=EdgeType.CAUSE_EFFECT,
        )
        with pytest.raises(ValueError):
            sample_canvas.add_edge(edge)

    def test_add_edge_with_missing_target_node(self, sample_canvas):
        """Test adding edge with missing target node raises error"""
        edge = CanvasEdge(
            id="bad-edge",
            source_id="node-1",
            target_id="nonexistent-node",
            type=EdgeType.CAUSE_EFFECT,
        )
        with pytest.raises(ValueError):
            sample_canvas.add_edge(edge)

    def test_remove_node_from_canvas(self, sample_canvas):
        """Test removing a node from canvas"""
        sample_canvas.remove_node("node-1")

        assert sample_canvas.get_node("node-1") is None
        # Edges should also be removed
        assert all(e.source_id != "node-1" and e.target_id != "node-1"
                   for e in sample_canvas.edges.values())

    def test_remove_nonexistent_node(self, sample_canvas):
        """Test removing nonexistent node raises error"""
        with pytest.raises(ValueError):
            sample_canvas.remove_node("nonexistent")

    def test_remove_edge_from_canvas(self, sample_canvas):
        """Test removing an edge from canvas"""
        initial_count = len(sample_canvas.edges)
        sample_canvas.remove_edge("edge-1")

        assert len(sample_canvas.edges) == initial_count - 1
        assert sample_canvas.get_edge("edge-1") is None

    def test_remove_nonexistent_edge(self, sample_canvas):
        """Test removing nonexistent edge raises error"""
        with pytest.raises(ValueError):
            sample_canvas.remove_edge("nonexistent")

    def test_get_connected_nodes(self, sample_canvas):
        """Test getting connected nodes"""
        connected = sample_canvas.get_connected_nodes("node-1")

        assert len(connected) == 1
        assert connected[0].id == "node-2"

    def test_get_nodes_by_type(self, sample_canvas):
        """Test getting nodes by type"""
        events = sample_canvas.get_nodes_by_type(NodeType.EVENT)
        resolutions = sample_canvas.get_nodes_by_type(NodeType.RESOLUTION)

        assert len(events) == 2
        assert len(resolutions) == 1

    def test_get_edges_by_type(self, sample_canvas):
        """Test getting edges by type"""
        cause_effects = sample_canvas.get_edges_by_type(EdgeType.CAUSE_EFFECT)

        assert len(cause_effects) == 1
        assert cause_effects[0].id == "edge-1"

    def test_get_causality_chain(self, sample_canvas):
        """Test getting causality chain from node"""
        chain = sample_canvas.get_causality_chain("node-1")

        # Should include node-1 and node-2 (connected by CAUSE_EFFECT)
        assert len(chain) > 0
        assert chain[0].id == "node-1"

    def test_canvas_to_dict(self, sample_canvas):
        """Test converting canvas to dictionary"""
        canvas_dict = sample_canvas.to_dict()

        assert canvas_dict['id'] == "canvas-1"
        assert canvas_dict['investigation_id'] == "inv-1"
        assert len(canvas_dict['nodes']) == 3
        assert len(canvas_dict['edges']) == 2

    def test_canvas_to_json(self, sample_canvas):
        """Test converting canvas to JSON"""
        canvas_json = sample_canvas.to_json()
        parsed = json.loads(canvas_json)

        assert parsed['id'] == "canvas-1"
        assert len(parsed['nodes']) == 3

    def test_canvas_from_dict(self, sample_canvas):
        """Test creating canvas from dictionary"""
        canvas_dict = sample_canvas.to_dict()
        restored_canvas = Canvas.from_dict(canvas_dict)

        assert restored_canvas.id == sample_canvas.id
        assert len(restored_canvas.nodes) == len(sample_canvas.nodes)
        assert len(restored_canvas.edges) == len(sample_canvas.edges)

    def test_canvas_node_removal_cascades_edges(self, sample_canvas):
        """Test that removing a node also removes connected edges"""
        assert len(sample_canvas.edges) == 2

        sample_canvas.remove_node("node-1")

        # Both edges connected to node-1 should be removed
        assert len(sample_canvas.edges) == 1
        remaining_edges = list(sample_canvas.edges.values())
        assert remaining_edges[0].source_id != "node-1"
        assert remaining_edges[0].target_id != "node-1"


class TestCanvasStore:
    """Test suite for CanvasStore"""

    def test_canvas_store_creation(self):
        """Test creating a canvas store"""
        store = CanvasStore()
        assert store.count() == 0

    def test_add_canvas_to_store(self):
        """Test adding canvas to store"""
        store = CanvasStore()
        canvas = Canvas("c1", "inv-1", "Canvas 1")

        store.add(canvas)
        assert store.count() == 1

    def test_get_canvas_from_store(self):
        """Test getting canvas from store"""
        store = CanvasStore()
        canvas = Canvas("c1", "inv-1", "Canvas 1")
        store.add(canvas)

        retrieved = store.get("c1")
        assert retrieved is not None
        assert retrieved.id == "c1"

    def test_get_nonexistent_canvas(self):
        """Test getting nonexistent canvas returns None"""
        store = CanvasStore()
        assert store.get("nonexistent") is None

    def test_get_canvases_by_investigation(self):
        """Test getting canvases by investigation"""
        store = CanvasStore()

        c1 = Canvas("c1", "inv-1", "Canvas 1")
        c2 = Canvas("c2", "inv-1", "Canvas 2")
        c3 = Canvas("c3", "inv-2", "Canvas 3")

        store.add(c1)
        store.add(c2)
        store.add(c3)

        inv1_canvases = store.get_by_investigation("inv-1")
        assert len(inv1_canvases) == 2

        inv2_canvases = store.get_by_investigation("inv-2")
        assert len(inv2_canvases) == 1

    def test_delete_canvas_from_store(self):
        """Test deleting canvas from store"""
        store = CanvasStore()
        canvas = Canvas("c1", "inv-1", "Canvas 1")
        store.add(canvas)

        assert store.count() == 1
        store.delete("c1")
        assert store.count() == 0

    def test_update_canvas_in_store(self):
        """Test updating canvas in store"""
        store = CanvasStore()
        canvas = Canvas("c1", "inv-1", "Canvas 1")
        store.add(canvas)

        canvas.title = "Updated Canvas"
        store.update(canvas)

        retrieved = store.get("c1")
        assert retrieved.title == "Updated Canvas"

    def test_get_all_canvases(self):
        """Test getting all canvases"""
        store = CanvasStore()

        for i in range(5):
            canvas = Canvas(f"c{i}", f"inv-{i}", f"Canvas {i}")
            store.add(canvas)

        all_canvases = store.get_all()
        assert len(all_canvases) == 5


class TestCanvasIntegration:
    """Integration tests for canvas system"""

    def test_complex_investigation_canvas(self):
        """Test building a complex investigation canvas"""
        canvas = Canvas("c-complex", "inv-1", "Complex Investigation")

        # Add event nodes
        events = [
            CanvasNode("e1", NodeType.EVENT, "API Timeout", position=(100, 100)),
            CanvasNode("e2", NodeType.EVENT, "DB Slow Queries", position=(300, 100)),
            CanvasNode("e3", NodeType.EVENT, "High Memory Usage", position=(500, 100)),
        ]

        for event in events:
            canvas.add_node(event)

        # Add causality
        canvas.add_edge(CanvasEdge(
            "rel1", "e1", "e2", EdgeType.CAUSE_EFFECT, "caused", 0.9
        ))
        canvas.add_edge(CanvasEdge(
            "rel2", "e2", "e3", EdgeType.CAUSE_EFFECT, "caused", 0.85
        ))

        # Add resolution
        resolution = CanvasNode(
            "r1", NodeType.RESOLUTION, "Scale DB", position=(300, 300)
        )
        canvas.add_node(resolution)
        canvas.add_edge(CanvasEdge(
            "rel3", "e3", "r1", EdgeType.DEPENDS_ON
        ))

        # Verify structure
        assert len(canvas.nodes) == 4
        assert len(canvas.edges) == 3

        # Get causality chain
        chain = canvas.get_causality_chain("e1")
        assert len(chain) >= 1

    def test_canvas_serialization_roundtrip(self, sample_canvas):
        """Test full serialization and deserialization"""
        # Serialize
        json_str = sample_canvas.to_json()

        # Deserialize
        dict_data = json.loads(json_str)
        restored = Canvas.from_dict(dict_data)

        # Verify
        assert restored.id == sample_canvas.id
        assert len(restored.nodes) == len(sample_canvas.nodes)
        assert len(restored.edges) == len(sample_canvas.edges)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
