"""
Phase 3d: Event API Endpoints

REST API for managing events with filtering, searching, and analytics.

Endpoints:
- POST /api/events - Create event
- GET /api/events - List with filtering/pagination
- GET /api/events/:id - Get event detail
- GET /api/events/source/:source - Filter by source
- GET /api/events/severity/:severity - Filter by severity
- GET /api/events/service/:service - Filter by service
- GET /api/events/search - Full text search
- GET /api/events/range - Filter by time range
- PUT /api/events/:id/tags - Update tags
"""

from flask import Blueprint, request, jsonify
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.models.event import Event, EventStore, EventSource, EventSeverity

# Create Blueprint
event_bp = Blueprint('events', __name__, url_prefix='/api/events')


class EventAPI:
    """Event API handler"""

    def __init__(self, event_store: EventStore):
        self.event_store = event_store

    def register_routes(self, app):
        """Register all event endpoints with Flask app"""

        @event_bp.route('', methods=['POST'])
        def create_event():
            """
            Create a new event
            
            Request body:
            {
                "investigation_id": "str",
                "message": "str",
                "source": "GIT|CI|LOGS|METRICS|TRACES|MANUAL",
                "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
                "service": "str (optional)",
                "environment": "str (optional)",
                "correlation_id": "str (optional)",
                "tags": ["str"] (optional),
                "metadata": {json} (optional)
            }
            
            Returns:
            - 201: Created event
            - 400: Validation error
            - 500: Server error
            """
            try:
                data = request.get_json()

                # Validate required fields
                required_fields = ['investigation_id', 'message', 'source', 'severity']
                if not all(f in data for f in required_fields):
                    return jsonify({'error': f'Missing required fields: {required_fields}'}), 400

                # Create event
                event = Event(
                    investigation_id=data['investigation_id'],
                    message=data['message'],
                    source=EventSource[data['source']],
                    severity=EventSeverity[data['severity']],
                    service=data.get('service'),
                    environment=data.get('environment'),
                    correlation_id=data.get('correlation_id'),
                    tags=data.get('tags', []),
                    metadata=data.get('metadata'),
                    timestamp=data.get('timestamp', datetime.utcnow().isoformat()),
                )

                # Save
                saved = self.event_store.create(event)

                return jsonify(saved.to_dict()), 201

            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('', methods=['GET'])
        def list_events():
            """
            List events with filtering and pagination
            
            Query parameters:
            - page: int (default: 1)
            - page_size: int (default: 10, max: 100)
            - source: GIT|CI|LOGS|METRICS|TRACES|MANUAL
            - severity: CRITICAL|HIGH|MEDIUM|LOW|INFO
            - service: str
            - investigation_id: str
            - search: str
            - sort_by: timestamp|severity (default: timestamp)
            - sort_order: asc|desc (default: desc)
            
            Returns:
            - 200: List of events with pagination
            """
            try:
                # Parse pagination
                page = int(request.args.get('page', 1))
                page_size = min(int(request.args.get('page_size', 10)), 100)

                if page < 1 or page_size < 1:
                    return jsonify({'error': 'Invalid pagination parameters'}), 400

                # Parse filters
                source_filter = request.args.get('source')
                severity_filter = request.args.get('severity')
                service_filter = request.args.get('service')
                investigation_filter = request.args.get('investigation_id')
                search_query = request.args.get('search', '')

                # Parse sorting
                sort_by = request.args.get('sort_by', 'timestamp')
                sort_order = request.args.get('sort_order', 'desc')

                # Get all events
                all_events = self.event_store.get_all()

                # Apply filters
                filtered = all_events
                if source_filter:
                    filtered = [e for e in filtered if e.source.value == source_filter]
                if severity_filter:
                    filtered = [e for e in filtered if e.severity.value == severity_filter]
                if service_filter:
                    filtered = [e for e in filtered if e.service == service_filter]
                if investigation_filter:
                    filtered = [e for e in filtered if e.investigation_id == investigation_filter]
                if search_query:
                    query_lower = search_query.lower()
                    filtered = [e for e in filtered if
                               query_lower in e.message.lower() or
                               query_lower in (e.service or '').lower()]

                # Apply sorting
                def get_sort_key(evt):
                    if sort_by == 'severity':
                        severity_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4}
                        return severity_order.get(evt.severity.value, 5)
                    else:  # timestamp
                        return evt.timestamp

                filtered.sort(key=get_sort_key, reverse=(sort_order == 'desc'))

                # Apply pagination
                total_count = len(filtered)
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated = filtered[start_idx:end_idx]

                return jsonify({
                    'events': [e.to_dict() for e in paginated],
                    'total_count': total_count,
                    'page': page,
                    'page_size': page_size,
                }), 200

            except ValueError as e:
                return jsonify({'error': f'Invalid parameter: {str(e)}'}), 400
            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('/<event_id>', methods=['GET'])
        def get_event(event_id: str):
            """
            Get event detail
            
            Parameters:
            - event_id: str
            
            Returns:
            - 200: Event details
            - 404: Not found
            """
            try:
                event = self.event_store.get_by_id(event_id)
                if not event:
                    return jsonify({'error': 'Event not found'}), 404

                return jsonify(event.to_dict()), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('/source/<source>', methods=['GET'])
        def get_events_by_source(source: str):
            """
            Get events filtered by source
            
            Parameters:
            - source: GIT|CI|LOGS|METRICS|TRACES|MANUAL
            
            Query parameters:
            - limit: int (default: 50)
            - offset: int (default: 0)
            
            Returns:
            - 200: List of events
            - 400: Invalid source
            """
            try:
                # Validate source
                try:
                    event_source = EventSource[source]
                except KeyError:
                    return jsonify({'error': f'Invalid source: {source}'}), 400

                limit = min(int(request.args.get('limit', 50)), 200)
                offset = int(request.args.get('offset', 0))

                # Filter events
                all_events = self.event_store.get_all()
                filtered = [e for e in all_events if e.source == event_source]

                # Apply pagination
                paginated = filtered[offset:offset + limit]

                return jsonify({
                    'events': [e.to_dict() for e in paginated],
                    'total_count': len(filtered),
                    'source': source,
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('/severity/<severity>', methods=['GET'])
        def get_events_by_severity(severity: str):
            """
            Get events filtered by severity
            
            Parameters:
            - severity: CRITICAL|HIGH|MEDIUM|LOW|INFO
            
            Query parameters:
            - limit: int (default: 50)
            - offset: int (default: 0)
            
            Returns:
            - 200: List of events
            - 400: Invalid severity
            """
            try:
                # Validate severity
                try:
                    event_severity = EventSeverity[severity]
                except KeyError:
                    return jsonify({'error': f'Invalid severity: {severity}'}), 400

                limit = min(int(request.args.get('limit', 50)), 200)
                offset = int(request.args.get('offset', 0))

                # Filter events
                all_events = self.event_store.get_all()
                filtered = [e for e in all_events if e.severity == event_severity]

                # Apply pagination
                paginated = filtered[offset:offset + limit]

                return jsonify({
                    'events': [e.to_dict() for e in paginated],
                    'total_count': len(filtered),
                    'severity': severity,
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('/service/<service>', methods=['GET'])
        def get_events_by_service(service: str):
            """
            Get events filtered by service
            
            Parameters:
            - service: str
            
            Query parameters:
            - limit: int (default: 50)
            - offset: int (default: 0)
            
            Returns:
            - 200: List of events
            """
            try:
                limit = min(int(request.args.get('limit', 50)), 200)
                offset = int(request.args.get('offset', 0))

                # Filter events
                all_events = self.event_store.get_all()
                filtered = [e for e in all_events if e.service == service]

                # Apply pagination
                paginated = filtered[offset:offset + limit]

                return jsonify({
                    'events': [e.to_dict() for e in paginated],
                    'total_count': len(filtered),
                    'service': service,
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('/search', methods=['GET'])
        def search_events():
            """
            Full text search across events
            
            Query parameters:
            - q: str (required) - search query
            - limit: int (default: 20)
            
            Returns:
            - 200: List of matching events
            """
            try:
                search_query = request.args.get('q', '').strip()
                if not search_query:
                    return jsonify({'error': 'Search query required'}), 400

                limit = min(int(request.args.get('limit', 20)), 100)

                # Search
                all_events = self.event_store.get_all()
                query_lower = search_query.lower()

                matching = [e for e in all_events if
                           query_lower in e.message.lower() or
                           query_lower in (e.service or '').lower()]

                return jsonify({
                    'results': [e.to_dict() for e in matching[:limit]],
                    'total_count': len(matching),
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('/range', methods=['GET'])
        def get_events_by_range():
            """
            Get events within a time range
            
            Query parameters:
            - start_time: ISO 8601 datetime (required)
            - end_time: ISO 8601 datetime (required)
            - limit: int (default: 100)
            
            Returns:
            - 200: List of events
            """
            try:
                start_str = request.args.get('start_time')
                end_str = request.args.get('end_time')

                if not start_str or not end_str:
                    return jsonify({'error': 'start_time and end_time required'}), 400

                # Parse dates
                try:
                    start_time = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                except ValueError:
                    return jsonify({'error': 'Invalid datetime format'}), 400

                limit = min(int(request.args.get('limit', 100)), 500)

                # Filter events
                all_events = self.event_store.get_all()
                filtered = [e for e in all_events if
                           start_time <= datetime.fromisoformat(e.timestamp.replace('Z', '+00:00')) <= end_time]

                return jsonify({
                    'events': [e.to_dict() for e in filtered[:limit]],
                    'total_count': len(filtered),
                    'start_time': start_str,
                    'end_time': end_str,
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @event_bp.route('/<event_id>/tags', methods=['PUT'])
        def update_event_tags(event_id: str):
            """
            Update event tags
            
            Parameters:
            - event_id: str
            
            Request body:
            {
                "tags": ["str"]
            }
            
            Returns:
            - 200: Updated event
            - 404: Not found
            """
            try:
                event = self.event_store.get_by_id(event_id)
                if not event:
                    return jsonify({'error': 'Event not found'}), 404

                data = request.get_json()
                if 'tags' in data:
                    event.tags = data['tags']

                # Note: In a real implementation, we'd update the store
                # For now, we return the updated event

                return jsonify(event.to_dict()), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        # Register blueprint
        app.register_blueprint(event_bp)


# Export for use in app.py
def register_event_api(app, event_store):
    """
    Register event API endpoints with Flask app
    
    Usage in app.py:
        from src.api.event_api import register_event_api
        register_event_api(app, event_store)
    """
    api = EventAPI(event_store)
    api.register_routes(app)
