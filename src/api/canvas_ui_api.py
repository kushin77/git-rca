"""
Phase 3c: Canvas UI API Endpoints

REST API for managing investigation canvas visualization.

Endpoints:
- GET /api/canvas/{canvas_id} - Get canvas with nodes and edges
- POST /api/canvas - Create new canvas
- PUT /api/canvas/{canvas_id} - Update canvas
- DELETE /api/canvas/{canvas_id} - Delete canvas
- POST /api/canvas/{canvas_id}/nodes - Add node to canvas
- DELETE /api/canvas/{canvas_id}/nodes/{node_id} - Remove node
- POST /api/canvas/{canvas_id}/edges - Add edge to canvas
- DELETE /api/canvas/{canvas_id}/edges/{edge_id} - Remove edge
- GET /api/canvas/{canvas_id}/analysis - Get analysis/recommendations
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Optional
from datetime import datetime
from src.models.canvas import (
    Canvas, CanvasNode, CanvasEdge, CanvasStore,
    NodeType, EdgeType
)
from src.models.investigation import Investigation
from src.store.investigation_store import InvestigationStore

# Create Blueprint
canvas_bp = Blueprint('canvas', __name__, url_prefix='/api/canvas')

# Global store (would be dependency injected in production)
canvas_store = CanvasStore()
investigation_store = None  # Set via initialize


class CanvasUIAPI:
    """Canvas UI API handler"""

    def __init__(self, canvas_store: CanvasStore, inv_store: InvestigationStore):
        self.canvas_store = canvas_store
        self.inv_store = inv_store

    def register_routes(self, app):
        """Register all canvas endpoints"""

        # If the blueprint has already had routes set up once, avoid
        # redefining the decorators (which raises when called after
        # the blueprint was registered). Instead, just ensure the
        # blueprint is registered on this app and return.
        try:
            if getattr(canvas_bp, '_got_registered_once', False):
                try:
                    app.register_blueprint(canvas_bp)
                except Exception:
                    pass
                return
        except Exception:
            pass

        @canvas_bp.route('/<canvas_id>', methods=['GET'])
        def get_canvas(canvas_id):
            """
            Get canvas by ID
            
            Returns:
            - 200: Canvas data with all nodes and edges
            - 404: Canvas not found
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                return jsonify(canvas.to_dict()), 200

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('', methods=['POST'])
        def create_canvas():
            """
            Create new canvas
            
            Request body:
            {
                "investigation_id": "inv-1",
                "title": "Investigation Canvas",
                "description": "Optional description",
                "layout_type": "force-directed"
            }
            
            Returns:
            - 201: Created canvas with ID
            - 400: Invalid request
            """
            try:
                data = request.get_json()

                # Validate required fields
                if not data or 'investigation_id' not in data:
                    return jsonify({'error': 'Missing investigation_id'}), 400
                if 'title' not in data:
                    return jsonify({'error': 'Missing title'}), 400

                # Verify investigation exists
                inv = self.inv_store.get_investigation(data['investigation_id'])
                if not inv:
                    return jsonify({'error': 'Investigation not found'}), 404

                # Create canvas
                canvas = Canvas(
                    id=f"canvas-{datetime.utcnow().timestamp()}",
                    investigation_id=data['investigation_id'],
                    title=data['title'],
                    description=data.get('description', ''),
                    layout_type=data.get('layout_type', 'force-directed'),
                )

                self.canvas_store.add(canvas)

                return jsonify(canvas.to_dict()), 201

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('/<canvas_id>', methods=['PUT'])
        def update_canvas(canvas_id):
            """
            Update canvas
            
            Request body:
            {
                "title": "Updated title",
                "description": "Updated description"
            }
            
            Returns:
            - 200: Updated canvas
            - 404: Canvas not found
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                data = request.get_json()

                if 'title' in data:
                    canvas.title = data['title']
                if 'description' in data:
                    canvas.description = data['description']

                canvas.updated_at = datetime.utcnow().isoformat()
                self.canvas_store.update(canvas)

                return jsonify(canvas.to_dict()), 200

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('/<canvas_id>', methods=['DELETE'])
        def delete_canvas(canvas_id):
            """
            Delete canvas
            
            Returns:
            - 204: Canvas deleted
            - 404: Canvas not found
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                self.canvas_store.delete(canvas_id)
                return '', 204

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('/<canvas_id>/nodes', methods=['POST'])
        def add_node(canvas_id):
            """
            Add node to canvas
            
            Request body:
            {
                "type": "EVENT|INVESTIGATION|RESOLUTION|TOOL|METRIC|INSIGHT",
                "title": "Node title",
                "description": "Optional description",
                "data": {"key": "value"},
                "position": {"x": 100, "y": 200},
                "size": {"width": 200, "height": 100}
            }
            
            Returns:
            - 201: Node created
            - 400: Invalid request
            - 404: Canvas not found
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                data = request.get_json()

                # Validate required fields
                if 'type' not in data or 'title' not in data:
                    return jsonify({'error': 'Missing required fields'}), 400

                # Create node
                node = CanvasNode(
                    id=f"node-{datetime.utcnow().timestamp()}",
                    type=NodeType(data['type']),
                    title=data['title'],
                    description=data.get('description', ''),
                    data=data.get('data', {}),
                    position=tuple(data.get('position', {}).values()) or (0, 0),
                    size=tuple(data.get('size', {}).values()) or (200, 100),
                )

                canvas.add_node(node)
                self.canvas_store.update(canvas)

                return jsonify(node.to_dict()), 201

            except ValueError as e:
                return jsonify({'error': f'Invalid node type: {str(e)}'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('/<canvas_id>/nodes/<node_id>', methods=['DELETE'])
        def remove_node(canvas_id, node_id):
            """
            Remove node from canvas
            
            Returns:
            - 204: Node removed
            - 404: Canvas or node not found
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                if canvas.get_node(node_id) is None:
                    return jsonify({'error': 'Node not found'}), 404

                canvas.remove_node(node_id)
                self.canvas_store.update(canvas)

                return '', 204

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('/<canvas_id>/edges', methods=['POST'])
        def add_edge(canvas_id):
            """
            Add edge (relationship) between nodes
            
            Request body:
            {
                "source_id": "node-1",
                "target_id": "node-2",
                "type": "CAUSE_EFFECT|CORRELATION|SEQUENCE|DEPENDS_ON|RELATES_TO|TRIGGERS",
                "label": "Optional label",
                "strength": 0.95
            }
            
            Returns:
            - 201: Edge created
            - 400: Invalid request
            - 404: Canvas not found
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                data = request.get_json()

                # Validate
                if 'source_id' not in data or 'target_id' not in data:
                    return jsonify({'error': 'Missing source/target'}), 400
                if 'type' not in data:
                    return jsonify({'error': 'Missing edge type'}), 400

                # Create edge
                edge = CanvasEdge(
                    id=f"edge-{datetime.utcnow().timestamp()}",
                    source_id=data['source_id'],
                    target_id=data['target_id'],
                    type=EdgeType(data['type']),
                    label=data.get('label', ''),
                    strength=data.get('strength', 1.0),
                )

                canvas.add_edge(edge)
                self.canvas_store.update(canvas)

                return jsonify(edge.to_dict()), 201

            except ValueError as e:
                return jsonify({'error': f'Invalid edge type: {str(e)}'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('/<canvas_id>/edges/<edge_id>', methods=['DELETE'])
        def remove_edge(canvas_id, edge_id):
            """
            Remove edge from canvas
            
            Returns:
            - 204: Edge removed
            - 404: Canvas or edge not found
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                if canvas.get_edge(edge_id) is None:
                    return jsonify({'error': 'Edge not found'}), 404

                canvas.remove_edge(edge_id)
                self.canvas_store.update(canvas)

                return '', 204

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @canvas_bp.route('/<canvas_id>/analysis', methods=['GET'])
        def get_canvas_analysis(canvas_id):
            """
            Get analysis and recommendations for canvas
            
            Returns:
            - 200: Analysis data with insights
            - 404: Canvas not found
            
            Response:
            {
                "node_count": 5,
                "edge_count": 4,
                "event_nodes": 3,
                "resolution_nodes": 1,
                "most_connected_node": "node-1",
                "causality_chains": [[...], ...],
                "insights": [...],
                "timestamp": "2024-01-28T10:00:00Z"
            }
            """
            try:
                canvas = self.canvas_store.get(canvas_id)
                if not canvas:
                    return jsonify({'error': 'Canvas not found'}), 404

                # Count nodes by type
                event_count = len(canvas.get_nodes_by_type(NodeType.EVENT))
                resolution_count = len(canvas.get_nodes_by_type(NodeType.RESOLUTION))
                insight_count = len(canvas.get_nodes_by_type(NodeType.INSIGHT))

                # Find most connected node
                most_connected = None
                max_connections = 0
                for node in canvas.nodes.values():
                    connected = canvas.get_connected_nodes(node.id)
                    if len(connected) > max_connections:
                        max_connections = len(connected)
                        most_connected = node.id

                # Generate insights
                insights = []
                if max_connections > 5:
                    insights.append({
                        'type': 'warning',
                        'message': f'High complexity detected: {max_connections} connections',
                    })

                if resolution_count == 0:
                    insights.append({
                        'type': 'info',
                        'message': 'No resolution nodes found - add resolution steps',
                    })

                if event_count > 10:
                    insights.append({
                        'type': 'info',
                        'message': f'Multiple events ({event_count}) - consider grouping',
                    })

                return jsonify({
                    'node_count': len(canvas.nodes),
                    'edge_count': len(canvas.edges),
                    'event_nodes': event_count,
                    'resolution_nodes': resolution_count,
                    'insight_nodes': insight_count,
                    'most_connected_node': most_connected,
                    'connections_to_most_connected': max_connections,
                    'insights': insights,
                    'timestamp': datetime.utcnow().isoformat(),
                }), 200

            except Exception as e:
                return jsonify({'error': str(e)}), 500

        # Register blueprint
        app.register_blueprint(canvas_bp)


def register_canvas_ui_api(app, canvas_store: CanvasStore, inv_store: InvestigationStore):
    """
    Register canvas UI API with Flask app
    
    Usage in app.py:
        from src.api.canvas_ui_api import register_canvas_ui_api
        register_canvas_ui_api(app, canvas_store, investigation_store)
    """
    api = CanvasUIAPI(canvas_store, inv_store)
    api.register_routes(app)
