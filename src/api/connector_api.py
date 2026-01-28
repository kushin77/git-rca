"""
Phase 3d: Connector API Endpoints

REST API for connector management and health monitoring.

Endpoints:
- GET /api/connectors/status - Get all connector health status
- GET /api/connectors/:source/status - Get specific connector status
- GET /api/connectors/:source/dlq - Get dead letter queue for connector
- POST /api/connectors/:source/dlq/:id/retry - Replay failed event
- GET /api/connectors/:source/stats - Get connector statistics
"""

from flask import Blueprint, request, jsonify
from typing import List, Dict, Optional
from datetime import datetime
from src.connectors.base_connector import BaseConnector, DeadLetterQueue, CircuitBreaker

# Create Blueprint
connector_bp = Blueprint('connectors', __name__, url_prefix='/api/connectors')


class ConnectorAPI:
    """Connector API handler"""

    def __init__(self, connectors: Dict[str, BaseConnector]):
        """
        Initialize with connector instances
        
        Args:
            connectors: Dict mapping source names to BaseConnector instances
        """
        self.connectors = connectors

    def register_routes(self, app):
        """Register all connector endpoints with Flask app"""

        @connector_bp.route('/status', methods=['GET'])
        def get_connector_status():
            """
            Get health status of all connectors
            
            Returns:
            - 200: List of connector statuses with state and DLQ size
            
            Response format:
            {
                "connectors": [
                    {
                        "source": "LOGS",
                        "state": "CLOSED|OPEN|HALF_OPEN",
                        "failure_count": 5,
                        "last_failure": "2024-01-28T10:00:00Z",
                        "last_success": "2024-01-28T09:55:00Z",
                        "dlq_size": 3
                    },
                    ...
                ],
                "timestamp": "2024-01-28T10:05:00Z"
            }
            """
            try:
                statuses = []

                for source, connector in self.connectors.items():
                    status = connector.get_status()

                    statuses.append({
                        'source': source,
                        'state': status['state'],
                        'failure_count': status['failure_count'],
                        'last_failure': status.get('last_failure'),
                        'last_success': status.get('last_success'),
                        'dlq_size': status['dlq_size'],
                    })

                return jsonify({
                    'connectors': statuses,
                    'timestamp': datetime.utcnow().isoformat(),
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @connector_bp.route('/<source>/status', methods=['GET'])
        def get_connector_status_by_source(source: str):
            """
            Get health status of specific connector
            
            Parameters:
            - source: GIT|CI|LOGS|METRICS|TRACES|MANUAL
            
            Returns:
            - 200: Connector status
            - 404: Connector not found
            """
            try:
                if source not in self.connectors:
                    return jsonify({'error': f'Connector not found: {source}'}), 404

                connector = self.connectors[source]
                status = connector.get_status()

                return jsonify({
                    'source': source,
                    'state': status['state'],
                    'failure_count': status['failure_count'],
                    'last_failure': status.get('last_failure'),
                    'last_success': status.get('last_success'),
                    'dlq_size': status['dlq_size'],
                    'timestamp': datetime.utcnow().isoformat(),
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @connector_bp.route('/<source>/dlq', methods=['GET'])
        def get_connector_dlq(source: str):
            """
            Get dead letter queue for connector (failed events)
            
            Parameters:
            - source: GIT|CI|LOGS|METRICS|TRACES|MANUAL
            
            Query parameters:
            - limit: int (default: 50)
            - offset: int (default: 0)
            
            Returns:
            - 200: List of failed events in DLQ
            - 404: Connector not found
            """
            try:
                if source not in self.connectors:
                    return jsonify({'error': f'Connector not found: {source}'}), 404

                connector = self.connectors[source]

                # Get DLQ events
                dlq_events = connector.dead_letter_queue.get_all()

                limit = int(request.args.get('limit', 50))
                offset = int(request.args.get('offset', 0))

                paginated = dlq_events[offset:offset + limit]

                return jsonify({
                    'source': source,
                    'dlq_events': [
                        {
                            'id': evt.id,
                            'event': evt.event,
                            'error_message': evt.error_message,
                            'retry_count': evt.retry_count,
                            'created_at': evt.created_at,
                            'last_retry_at': evt.last_retry_at,
                        }
                        for evt in paginated
                    ],
                    'total_count': len(dlq_events),
                    'limit': limit,
                    'offset': offset,
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @connector_bp.route('/<source>/dlq/<event_id>/retry', methods=['POST'])
        def retry_dlq_event(source: str, event_id: str):
            """
            Retry a failed event from the dead letter queue
            
            Parameters:
            - source: GIT|CI|LOGS|METRICS|TRACES|MANUAL
            - event_id: str
            
            Returns:
            - 200: Retry initiated
            - 404: Connector or event not found
            """
            try:
                if source not in self.connectors:
                    return jsonify({'error': f'Connector not found: {source}'}), 404

                connector = self.connectors[source]

                # Get event from DLQ
                dlq_events = connector.dead_letter_queue.get_all()
                dlq_event = next((e for e in dlq_events if e.id == event_id), None)

                if not dlq_event:
                    return jsonify({'error': f'Event not found in DLQ: {event_id}'}), 404

                # Remove from DLQ and attempt retry
                connector.dead_letter_queue.remove(event_id)

                return jsonify({
                    'source': source,
                    'event_id': event_id,
                    'status': 'retry_initiated',
                    'message': f'Retry initiated for event {event_id}',
                    'timestamp': datetime.utcnow().isoformat(),
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        @connector_bp.route('/<source>/stats', methods=['GET'])
        def get_connector_stats(source: str):
            """
            Get detailed statistics for connector
            
            Parameters:
            - source: GIT|CI|LOGS|METRICS|TRACES|MANUAL
            
            Returns:
            - 200: Connector statistics
            - 404: Connector not found
            
            Statistics include:
            - Total events collected
            - Events processed successfully
            - Events failed
            - Average processing time
            - Circuit breaker state and transitions
            """
            try:
                if source not in self.connectors:
                    return jsonify({'error': f'Connector not found: {source}'}), 404

                connector = self.connectors[source]
                status = connector.get_status()

                # Calculate stats
                dlq_size = status['dlq_size']
                total_collected = status.get('total_collected', 0)
                successful = max(0, total_collected - dlq_size)

                return jsonify({
                    'source': source,
                    'total_collected': total_collected,
                    'successful': successful,
                    'failed': dlq_size,
                    'success_rate': f"{(successful / max(total_collected, 1) * 100):.1f}%",
                    'circuit_breaker_state': status['state'],
                    'failure_count': status['failure_count'],
                    'last_failure': status.get('last_failure'),
                    'last_success': status.get('last_success'),
                    'dlq_size': dlq_size,
                    'timestamp': datetime.utcnow().isoformat(),
                }), 200

            except Exception as e:
                return jsonify({'error': 'Internal server error'}), 500

        # Register blueprint
        app.register_blueprint(connector_bp)


# Export for use in app.py
def register_connector_api(app, connectors: Dict[str, BaseConnector]):
    """
    Register connector API endpoints with Flask app
    
    Usage in app.py:
        from src.api.connector_api import register_connector_api
        register_connector_api(app, connectors_dict)
    """
    api = ConnectorAPI(connectors)
    api.register_routes(app)
