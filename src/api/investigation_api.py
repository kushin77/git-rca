"""
Phase 3d: Investigation API Endpoints

REST API for managing investigations with full CRUD operations, 
filtering, searching, and analytics capabilities.

Endpoints:
- POST /api/investigations - Create investigation
- GET /api/investigations - List with filtering/search/pagination
- GET /api/investigations/:id - Get investigation detail
- PUT /api/investigations/:id - Update investigation
- DELETE /api/investigations/:id - Delete investigation
- GET /api/investigations/:id/events - Get related events
- PUT /api/investigations/:id/status - Update status
- GET /api/investigations/search - Full text search
"""

from flask import Blueprint, request, jsonify
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from src.store.investigation_store import InvestigationStore
from src.models.investigation import Investigation, InvestigationStatus
from src.models.event import Event, EventSeverity
from src.store.event_store import EventStore

# Create Blueprint
investigation_bp = Blueprint('investigations', __name__, url_prefix='/api/investigations')


class InvestigationAPI:
    """Investigation API handler"""

    def __init__(self, investigation_store: InvestigationStore, event_store: EventStore):
        self.inv_store = investigation_store
        self.event_store = event_store

    def register_routes(self, app):
        """Register all investigation endpoints with Flask app"""

        @investigation_bp.route('', methods=['POST'])
        def create_investigation():
            """
            Create a new investigation
            
            Request body:
            {
                "title": "str",
                "description": "str",
                "service": "str",
                "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
                "environment": "str (optional)",
                "assigned_to": "str (optional)",
                "tags": ["str"] (optional)
            }
            
            Returns:
            - 201: Created investigation with ID
            - 400: Validation error
            - 500: Server error
            """
            try:
                data = request.get_json()

                # Validate required fields
                required_fields = ['title', 'description', 'service', 'severity']
                if not all(f in data for f in required_fields):
                    return jsonify({'error': f'Missing required fields: {required_fields}'}), 400

                # Create investigation object
                investigation = Investigation(
                    title=data['title'],
                    description=data['description'],
                    service=data['service'],
                    severity=EventSeverity[data['severity']],
                    status=InvestigationStatus.OPEN,
                    environment=data.get('environment'),
                    assigned_to=data.get('assigned_to'),
                    created_by=request.headers.get('X-User-ID', 'system'),
                    tags=data.get('tags', []),
                )

                # Save to store
                saved = self.inv_store.create(investigation)

                return jsonify(saved.to_dict()), 201

            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('', methods=['GET'])
        def list_investigations():
            """
            List investigations with filtering and pagination
            
            Query parameters:
            - page: int (default: 1)
            - page_size: int (default: 10, max: 100)
            - status: OPEN|IN_PROGRESS|RESOLVED|CLOSED
            - severity: CRITICAL|HIGH|MEDIUM|LOW|INFO
            - service: str (filter by service)
            - search: str (search in title/description)
            - sort_by: created_at|updated_at|severity|status (default: created_at)
            - sort_order: asc|desc (default: desc)
            
            Returns:
            - 200: List of investigations with pagination metadata
            """
            try:
                # Parse pagination
                page = int(request.args.get('page', 1))
                page_size = min(int(request.args.get('page_size', 10)), 100)

                if page < 1 or page_size < 1:
                    return jsonify({'error': 'Invalid pagination parameters'}), 400

                # Parse filters
                status_filter = request.args.get('status')
                severity_filter = request.args.get('severity')
                service_filter = request.args.get('service')
                search_query = request.args.get('search', '')

                # Parse sorting
                sort_by = request.args.get('sort_by', 'created_at')
                sort_order = request.args.get('sort_order', 'desc')

                # Get all investigations
                all_investigations = self.inv_store.get_all()

                # Apply filters
                filtered = all_investigations
                if status_filter:
                    filtered = [i for i in filtered if i.status.value == status_filter]
                if severity_filter:
                    filtered = [i for i in filtered if i.severity.value == severity_filter]
                if service_filter:
                    filtered = [i for i in filtered if i.service == service_filter]
                if search_query:
                    query_lower = search_query.lower()
                    filtered = [i for i in filtered if 
                               query_lower in i.title.lower() or
                               query_lower in i.description.lower() or
                               query_lower in i.id.lower()]

                # Apply sorting
                def get_sort_key(inv):
                    if sort_by == 'severity':
                        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
                        return severity_order.get(inv.severity.value, 5)
                    elif sort_by == 'status':
                        status_order = {'OPEN': 0, 'IN_PROGRESS': 1, 'RESOLVED': 2, 'CLOSED': 3}
                        return status_order.get(inv.status.value, 4)
                    elif sort_by == 'updated_at':
                        return inv.updated_at
                    else:  # created_at
                        return inv.created_at

                filtered.sort(key=get_sort_key, reverse=(sort_order == 'desc'))

                # Apply pagination
                total_count = len(filtered)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated = filtered[start_idx:end_idx]

                return jsonify({
                    'investigations': [i.to_dict() for i in paginated],
                    'total_count': total_count,
                    'page': page,
                    'page_size': page_size,
                }), 200

            except ValueError as e:
                return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('/<investigation_id>', methods=['GET'])
        def get_investigation(investigation_id: str):
            """
            Get investigation detail
            
            Parameters:
            - investigation_id: str
            
            Returns:
            - 200: Investigation details
            - 404: Not found
            """
            try:
                investigation = self.inv_store.get_by_id(investigation_id)
                if not investigation:
                    return jsonify({'error': 'Investigation not found'}), 404

                return jsonify(investigation.to_dict()), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('/<investigation_id>', methods=['PUT'])
        def update_investigation(investigation_id: str):
            """
            Update investigation
            
            Parameters:
            - investigation_id: str
            
            Request body:
            {
                "title": "str (optional)",
                "description": "str (optional)",
                "assigned_to": "str (optional)",
                "root_cause": "str (optional)",
                "resolution_summary": "str (optional)",
                "automation_potential": "int (optional)",
                "tags": ["str"] (optional)
            }
            
            Returns:
            - 200: Updated investigation
            - 404: Not found
            """
            try:
                investigation = self.inv_store.get_by_id(investigation_id)
                if not investigation:
                    return jsonify({'error': 'Investigation not found'}), 404

                data = request.get_json()

                # Update fields
                if 'title' in data:
                    investigation.title = data['title']
                if 'description' in data:
                    investigation.description = data['description']
                if 'assigned_to' in data:
                    investigation.assigned_to = data['assigned_to']
                if 'root_cause' in data:
                    investigation.root_cause = data['root_cause']
                if 'resolution_summary' in data:
                    investigation.resolution_summary = data['resolution_summary']
                if 'automation_potential' in data:
                    investigation.automation_potential = data['automation_potential']
                if 'tags' in data:
                    investigation.tags = data['tags']

                investigation.updated_at = datetime.utcnow()

                # Save
                updated = self.inv_store.update(investigation)

                return jsonify(updated.to_dict()), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('/<investigation_id>', methods=['DELETE'])
        def delete_investigation(investigation_id: str):
            """
            Delete investigation (soft delete)
            
            Parameters:
            - investigation_id: str
            
            Returns:
            - 204: Success (no content)
            - 404: Not found
            """
            try:
                investigation = self.inv_store.get_by_id(investigation_id)
                if not investigation:
                    return jsonify({'error': 'Investigation not found'}), 404

                self.inv_store.delete(investigation_id)
                return '', 204

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('/<investigation_id>/events', methods=['GET'])
        def get_investigation_events(investigation_id: str):
            """
            Get events related to investigation
            
            Parameters:
            - investigation_id: str
            
            Query parameters:
            - limit: int (default: 100)
            - offset: int (default: 0)
            
            Returns:
            - 200: List of events
            """
            try:
                investigation = self.inv_store.get_by_id(investigation_id)
                if not investigation:
                    return jsonify({'error': 'Investigation not found'}), 404

                # Get limit and offset
                limit = int(request.args.get('limit', 100))
                offset = int(request.args.get('offset', 0))

                # Get events from event store
                all_events = self.event_store.get_all()
                related_events = [e for e in all_events if e.investigation_id == investigation_id]

                # Apply limit and offset
                paginated = related_events[offset:offset + limit]

                return jsonify({
                    'events': [e.to_dict() for e in paginated],
                    'total_count': len(related_events),
                    'limit': limit,
                    'offset': offset,
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('/<investigation_id>/events/link', methods=['POST'])
        def link_event_to_investigation(investigation_id):
            """
            Link an event to an investigation
            
            Request body:
            {
                "event_id": "str",
                "event_type": "str", 
                "source": "str",
                "message": "str",
                "timestamp": "ISO string"
            }
            
            Returns:
            - 201: Event linked successfully
            - 400: Validation error
            - 404: Investigation not found
            - 500: Server error
            """
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['event_id', 'event_type', 'source', 'message', 'timestamp']
                if not all(f in data for f in required_fields):
                    return jsonify({'error': f'Missing required fields: {required_fields}'}), 400
                
                # Check if investigation exists
                investigation = self.inv_store.get_investigation(investigation_id)
                if not investigation:
                    return jsonify({'error': 'Investigation not found'}), 404
                
                # Create event
                from src.models.event import Event, EventSource, EventSeverity
                event = Event(
                    id=data['event_id'],
                    timestamp=data['timestamp'],
                    source=data['source'],
                    event_type=data['event_type'],
                    severity=EventSeverity.MEDIUM,
                    data={'message': data['message']},
                )
                
                # Save event
                self.event_store.create_event(event)
                
                # Link to investigation
                self.inv_store.add_event(
                    investigation_id=investigation_id,
                    event_id=event.id,
                    event_type=event.event_type,
                    source=event.source,
                    message=data['message'],
                    timestamp=event.timestamp
                )
                
                return jsonify({
                    'event_id': event.id,
                    'investigation_id': investigation_id,
                    'source': event.source,
                    'message': 'Event linked successfully'
                }), 201
                
            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('/<investigation_id>/status', methods=['PUT'])
        def update_investigation_status(investigation_id: str):
            """
            Update investigation status
            
            Parameters:
            - investigation_id: str
            
            Request body:
            {
                "status": "OPEN|IN_PROGRESS|RESOLVED|CLOSED"
            }
            
            Returns:
            - 200: Updated investigation
            - 400: Invalid status
            - 404: Not found
            """
            try:
                investigation = self.inv_store.get_by_id(investigation_id)
                if not investigation:
                    return jsonify({'error': 'Investigation not found'}), 404

                data = request.get_json()
                if 'status' not in data:
                    return jsonify({'error': 'Status required'}), 400

                try:
                    new_status = InvestigationStatus[data['status']]
                except KeyError:
                    return jsonify({'error': 'Invalid status value'}), 400

                investigation.status = new_status
                investigation.updated_at = datetime.utcnow()

                updated = self.inv_store.update(investigation)

                return jsonify(updated.to_dict()), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @investigation_bp.route('/search', methods=['GET'])
        def search_investigations():
            """
            Full text search across investigations
            
            Query parameters:
            - q: str (required) - search query
            - limit: int (default: 20)
            
            Returns:
            - 200: List of matching investigations
            """
            try:
                search_query = request.args.get('q', '').strip()
                if not search_query:
                    return jsonify({'error': 'Search query required'}), 400

                limit = min(int(request.args.get('limit', 20)), 100)

                # Search
                all_investigations = self.inv_store.get_all()
                query_lower = search_query.lower()

                matching = [i for i in all_investigations if
                           query_lower in i.title.lower() or
                           query_lower in i.description.lower() or
                           query_lower in i.id.lower() or
                           query_lower in i.service.lower()]

                return jsonify({
                    'results': [i.to_dict() for i in matching[:limit]],
                    'total_count': len(matching),
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        # Register blueprint
        app.register_blueprint(investigation_bp)


# Export for use in app.py
def register_investigation_api(app, investigation_store, event_store):
    """
    Register investigation API endpoints with Flask app
    
    Usage in app.py:
        from src.api.investigation_api import register_investigation_api
        register_investigation_api(app, investigation_store, event_store)
    """
    api = InvestigationAPI(investigation_store, event_store)
    api.register_routes(app)
