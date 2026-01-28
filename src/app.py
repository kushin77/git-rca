from flask import Flask, jsonify, request, render_template
from typing import List, Dict
import os

from src.connectors import git_connector, ci_connector
from src.store import sql_store
from src.store.investigation_store import InvestigationStore
from src.services.event_linker import EventLinker
from src.services.email_notifier import EmailNotifier, NotificationPreferences
from src.middleware import require_auth, init_auth, init_revocation
from src.utils.logging import setup_logging, log_request_response, LogContext
from src.api.investigation_api import register_investigation_api


def create_app(db_path: str = 'investigations.db'):
    """Create and configure the Flask app.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        Configured Flask app instance
    """
    # Get the path to the src directory
    src_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, 
                template_folder=os.path.join(src_dir, 'templates'),
                static_folder=os.path.join(src_dir, 'static'),
                static_url_path='/static')

    # Initialize structured JSON logging
    setup_logging(app)

    # Initialize authentication
    # Initialize authentication and revocation
    init_auth(app)
    init_revocation(app)

    # Initialize investigation store
    investigation_store = InvestigationStore(db_path=db_path)

    # Initialize event linker
    event_linker = EventLinker(investigation_store)

    # Initialize email notifier (with same database for preferences persistence)
    email_notifier = EmailNotifier(
        smtp_host='localhost',
        smtp_port=587,
        from_email='noreply@git-rca.local',
        from_name='Git RCA Workspace',
        db_path=db_path,  # Share database with investigation store
    )
    
    # Store in app context for access in routes
    app.investigation_store = investigation_store
    app.event_linker = event_linker
    app.email_notifier = email_notifier

    # Register investigation API
    from src.store.event_store import EventStore
    event_store = EventStore(db_path=db_path)
    register_investigation_api(app, investigation_store, event_store)

    # Register canvas UI API
    from src.models.canvas import CanvasStore
    canvas_store = CanvasStore()
    from src.api.canvas_ui_api import register_canvas_ui_api
    register_canvas_ui_api(app, canvas_store, investigation_store)

    # Register analytics API
    from src.api.analytics_api import register_analytics_api
    register_analytics_api(app, event_store, investigation_store)

    
    
    # Register error handlers with logging
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Log all exceptions and return JSON error response."""
        context = LogContext(app.logger)
        context.error(
            f'Unhandled exception: {type(e).__name__}',
            error_type=type(e).__name__,
            error_message=str(e),
            path=request.path,
            method=request.method,
        )
        return jsonify({'error': 'Internal server error'}), 500
    
    @app.errorhandler(404)
    def handle_404(e):
        """Log 404 errors."""
        context = LogContext(app.logger)
        context.warning(
            f'Not found: {request.path}',
            path=request.path,
            method=request.method,
        )
        return jsonify({'error': 'Not found'}), 404
    
    # ========================================================================
    # ISSUE #14: Token Revocation & Admin Token Management Endpoints
    # ========================================================================
    
    @app.get('/api/admin/tokens')
    @require_auth(allowed_roles={'admin'})
    @log_request_response
    def get_tokens():
        """
        List revoked tokens (admin only).
        
        Query parameters:
        - user_id: Filter by user (optional)
        - limit: Number of records (default 50, max 500)
        - offset: Starting offset (default 0)
        
        Returns:
            List of revoked tokens with metadata
        """
        try:
            from src.middleware import get_revocation_manager
            user_id = request.args.get('user_id')
            limit = min(int(request.args.get('limit', 50)), 500)
            offset = int(request.args.get('offset', 0))
            
            revocation_manager = get_revocation_manager()
            records, total = revocation_manager.get_all_revocations(
                limit=limit,
                offset=offset,
                user_id=user_id
            )
            
            # Log admin action
            context = LogContext(app.logger)
            context.info(
                'Admin token list query',
                admin_id=request.user_id,
                filter_user=user_id,
                limit=limit,
                offset=offset,
                result_count=len(records),
                total_count=total,
            )
            
            return jsonify({
                'tokens': records,
                'pagination': {
                    'limit': limit,
                    'offset': offset,
                    'total': total,
                    'returned': len(records),
                }
            }), 200
            
        except Exception as e:
            context = LogContext(app.logger)
            context.error(
                'Failed to list tokens',
                admin_id=request.user_id,
                error=str(e),
            )
            return jsonify({'error': 'Failed to list tokens', 'details': str(e)}), 500
    
    @app.post('/api/admin/users/<user_id>/revoke-all')
    @require_auth(allowed_roles={'admin'})
    @log_request_response
    def revoke_user_sessions(user_id):
        """
        Revoke all sessions for a user (admin only).
        
        Use case: User compromised, password changed, etc.
        
        Path parameter:
        - user_id: User whose sessions to revoke
        
        Request body:
        - reason: Reason for revocation (optional)
        - keep_current: Current token to keep active (optional)
        
        Returns:
            Number of tokens revoked
        """
        try:
            from src.middleware import get_revocation_manager
            data = request.get_json() or {}
            reason = data.get('reason', 'admin_action')
            keep_current = data.get('keep_current')  # Optional token to exclude
            
            revocation_manager = get_revocation_manager()
            revoked_count = revocation_manager.revoke_user_sessions(
                user_id=user_id,
                reason=reason,
                admin_id=request.user_id,
                keep_current=keep_current
            )
            
            # Log admin action
            context = LogContext(app.logger)
            context.warning(
                'Admin bulk session revocation',
                admin_id=request.user_id,
                target_user_id=user_id,
                reason=reason,
                revoked_count=revoked_count,
            )
            
            return jsonify({
                'message': f'Revoked {revoked_count} session(s)',
                'user_id': user_id,
                'revoked_count': revoked_count,
            }), 200
            
        except Exception as e:
            context = LogContext(app.logger)
            context.error(
                'Failed to revoke user sessions',
                admin_id=request.user_id,
                target_user_id=user_id,
                error=str(e),
            )
            return jsonify({'error': 'Failed to revoke sessions', 'details': str(e)}), 500
    
    @app.get('/api/admin/revocation/stats')
    @require_auth(allowed_roles={'admin'})
    @log_request_response
    def get_revocation_stats():
        """
        Get revocation system statistics (admin only).
        
        Returns:
            System statistics and metrics
        """
        try:
            from src.middleware import get_revocation_manager
            revocation_manager = get_revocation_manager()
            stats = revocation_manager.get_stats()
            
            context = LogContext(app.logger)
            context.debug(
                'Admin revocation stats query',
                admin_id=request.user_id,
            )
            
            return jsonify({
                'stats': stats,
                'endpoints': {
                    'logout': '/api/auth/logout',
                    'list_tokens': '/api/admin/tokens',
                    'revoke_token': '/api/admin/tokens/<token_hash>/revoke',
                    'revoke_user': '/api/admin/users/<user_id>/revoke-all',
                }
            }), 200
            
        except Exception as e:
            context = LogContext(app.logger)
            context.error(
                'Failed to get revocation stats',
                admin_id=request.user_id,
                error=str(e),
            )
            return jsonify({'error': 'Failed to get stats', 'details': str(e)}), 500
    
    # Initialize observability (best-effort). Failures won't stop the app.
    try:
        from .observability.init_observability import init_observability
        init_observability(app)
    except Exception:
        try:
            app.logger.debug("Observability initialization skipped or failed")
        except Exception:
            pass

    # If a module-level app (with routes) exists, copy its URL rules into
    # this newly created app so that tests using `create_app()` get the
    # same routes defined at module import time.
    try:
        import sys
        mod = sys.modules[__name__]
        global_app = getattr(mod, 'app', None)
        if global_app is not None and global_app is not app:
            for rule in list(global_app.url_map.iter_rules()):
                if rule.endpoint == 'static':
                    continue
                view_fn = global_app.view_functions.get(rule.endpoint)
                methods = [m for m in rule.methods if m not in ('HEAD', 'OPTIONS')]
                try:
                    app.add_url_rule(rule.rule, endpoint=rule.endpoint, view_func=view_fn, methods=methods)
                except Exception:
                    # ignore failures to re-register; app may already have rule
                    pass
    except Exception:
        pass

    return app


# Create default app instance
app = create_app()

# Expose module-level handles for tests that import `src.app` directly
try:
    investigation_store = app.investigation_store
    event_linker = app.event_linker
    email_notifier = app.email_notifier
except Exception:
    investigation_store = None
    event_linker = None
    email_notifier = None


@app.get('/')
@log_request_response
def index():
    """Health check endpoint."""
    return jsonify({"message": "Git RCA Workspace - MVP skeleton"})


def _collect_events(source: str | None, limit: int) -> List[Dict]:
    # Prefer SQL-backed store if available; fallback to file connectors
    try:
        events = sql_store.query_events(source=source, limit=limit)
        # convert sql rows payload shape to event dicts, preserving inserted_at
        res = []
        for e in events:
            payload = e.get('payload', {})
            if e.get('inserted_at'):
                payload = dict(payload)
                payload['_inserted_at'] = e.get('inserted_at')
            res.append(payload)
        return res[:limit]
    except Exception:
        res: List[Dict] = []
        if source is None or source == 'git':
            res.extend(git_connector.load_events(limit=limit))
        if source is None or source == 'ci':
            res.extend(ci_connector.load_events(limit=limit))
        return res[:limit]


@app.get('/api/events')
def api_events():
    """Return recent events from connectors.

    Query params:
      - source: 'git' | 'ci' (omit to return both)
      - limit: int (default 50)
    """
    source = request.args.get('source')
    try:
        limit = int(request.args.get('limit', '50'))
    except ValueError:
        limit = 50
    events = _collect_events(source, limit)

    # Apply simple filters: type, repo, since
    ev_type = request.args.get('type')
    repo = request.args.get('repo')
    since = request.args.get('since')

    def _filter(e: Dict) -> bool:
        if ev_type and e.get('type') != ev_type:
            return False
        if repo and e.get('repo') != repo:
            return False
        if since:
            # prefer source-provided timestamp if present, otherwise use internal inserted_at
            t = e.get('timestamp') or e.get('_inserted_at')
            if not t:
                return False
            try:
                # string compare is acceptable for ISO8601
                if t < since:
                    return False
            except Exception:
                return False
        return True

    filtered = [e for e in events if _filter(e)]
    return jsonify({"count": len(filtered), "events": filtered})


# Investigation Canvas Routes

@app.get('/investigations')
def investigations_list():
    """List all investigations."""
    # Fetch from database
    investigations = app.investigation_store.list_investigations(limit=100)
    
    # Convert to dict format for template
    investigations_data = [inv.to_dict() for inv in investigations]
    
    # If no investigations exist, show mock data
    if not investigations_data:
        investigations_data = [
            {
                'id': 'inv-001',
                'title': 'Payment Processing Timeout',
                'status': 'closed',
                'severity': 'high',
                'created_at': '2026-01-27 10:30 UTC',
                'impact': '5% of transactions'
            },
            {
                'id': 'inv-002',
                'title': 'Database Connection Pool Exhaustion',
                'status': 'open',
                'severity': 'critical',
                'created_at': '2026-01-27 08:15 UTC',
                'impact': 'Service degradation'
            },
        ]
    
    return render_template('investigations_list.html', investigations=investigations_data)


@app.get('/investigations/<investigation_id>')
def investigation_canvas(investigation_id: str):
    """Render investigation canvas for a specific investigation."""
    # Fetch from database
    investigation = app.investigation_store.get_investigation(investigation_id)
    
    if not investigation:
        # Return 404 if investigation doesn't exist
        return jsonify({'error': 'Investigation not found'}), 404
    
    # Get related events and annotations
    events = app.investigation_store.get_investigation_events(investigation_id)
    annotations = app.investigation_store.get_annotations(investigation_id)
    
    # Build investigation data for template
    investigation_data = investigation.to_dict()
    investigation_data['events'] = [evt.to_dict() for evt in events]
    investigation_data['annotations'] = [ann.to_dict() for ann in annotations]
    investigation_data['team'] = []  # Will be implemented in future stories
    
    return render_template('investigation.html', investigation=investigation_data)


@app.post('/api/investigations')
@require_auth(allowed_roles={'admin', 'engineer'})
@log_request_response
def create_investigation():
    """Create a new investigation (requires auth)."""
    data = request.json or {}
    
    try:
        investigation = app.investigation_store.create_investigation(
            title=data.get('title', 'Untitled Investigation'),
            status=data.get('status', 'open'),
            severity=data.get('severity', 'medium'),
            description=data.get('description', ''),
            impact=data.get('impact', ''),
        )
        return jsonify(investigation.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.get('/api/investigations/<investigation_id>')
@log_request_response
def get_investigation(investigation_id: str):
    """Fetch investigation details (public read)."""
    investigation = app.investigation_store.get_investigation(investigation_id)
    
    if not investigation:
        return jsonify({'error': 'Investigation not found'}), 404
    
    return jsonify(investigation.to_dict())


@app.patch('/api/investigations/<investigation_id>')
@require_auth(allowed_roles={'admin', 'engineer'})
@log_request_response
def update_investigation(investigation_id: str):
    """Update investigation details (requires auth)."""
    data = request.json or {}
    
    try:
        investigation = app.investigation_store.update_investigation(investigation_id, **data)
        if not investigation:
            return jsonify({'error': 'Investigation not found'}), 404
        
        return jsonify(investigation.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.post('/api/investigations/<investigation_id>/annotations')
@require_auth(allowed_roles={'admin', 'engineer'})
@log_request_response
def add_annotation(investigation_id: str):
    """Add annotation to investigation (requires auth)."""
    data = request.json or {}
    
    try:
        annotation = app.investigation_store.add_annotation(
            investigation_id=investigation_id,
            author=data.get('author', request.user_id),  # Use provided author or authenticated user
            text=data.get('text', ''),
            parent_annotation_id=data.get('parent_annotation_id'),
        )
        return jsonify(annotation.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.get('/api/investigations/<investigation_id>/annotations')
def list_annotations(investigation_id: str):
    """List annotations for investigation (public read)."""
    try:
        annotations = app.investigation_store.get_annotations(investigation_id)
        return jsonify({
            'investigation_id': investigation_id,
            'annotations': [ann.to_dict() for ann in annotations],
            'count': len(annotations)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Event Linking Routes

@app.post('/api/investigations/<investigation_id>/events/auto-link')
@require_auth(allowed_roles={'admin', 'engineer'})
@log_request_response
def auto_link_events(investigation_id: str):
    """Automatically discover and link events to investigation (requires auth).
    
    Query params:
      - time_window_minutes: int (default 60)
      - semantic_matching: bool (default true)
    """
    try:
        time_window = request.args.get('time_window_minutes', '60')
        semantic = request.args.get('semantic_matching', 'true').lower() == 'true'
        
        try:
            time_window = int(time_window)
        except ValueError:
            time_window = 60
        
        linked_events = app.event_linker.auto_link_events(
            investigation_id,
            time_window_minutes=time_window,
            semantic_matching=semantic,
        )
        
        return jsonify({
            'investigation_id': investigation_id,
            'linked_count': len(linked_events),
            'events': [evt.to_dict() for evt in linked_events],
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.get('/api/investigations/<investigation_id>/events')
def get_investigation_events(investigation_id: str):
    """Get all linked events for investigation (public read).
    
    Query params:
      - source: 'git' | 'ci' (omit for all)
      - event_type: str
      - limit: int (default 50)
    """
    try:
        source_filter = request.args.get('source')
        type_filter = request.args.get('event_type')
        limit = int(request.args.get('limit', '50'))
        
        events = app.investigation_store.get_investigation_events(investigation_id)
        
        # Filter by source
        if source_filter:
            events = [e for e in events if e.source.lower() == source_filter.lower()]
        
        # Filter by type
        if type_filter:
            events = [e for e in events if e.event_type == type_filter]
        
        return jsonify({
            'investigation_id': investigation_id,
            'events': [evt.to_dict() for evt in events[:limit]],
            'count': len(events),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.post('/api/investigations/<investigation_id>/events/link')
@require_auth(allowed_roles={'admin', 'engineer'})
@log_request_response
def link_event(investigation_id: str):
    """Manually link an event to investigation (requires auth)."""
    data = request.json or {}
    
    try:
        event = app.investigation_store.add_event(
            investigation_id=investigation_id,
            event_id=data.get('event_id', ''),
            event_type=data.get('event_type', 'unknown'),
            source=data.get('source', 'manual'),
            message=data.get('message', ''),
            timestamp=data.get('timestamp'),
        )
        return jsonify(event.to_dict()), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.get('/api/events/search')
def search_events():
    """Search for events across all sources.
    
    Query params:
      - query: str (required)
      - source: 'git' | 'ci' (omit for all)
      - event_type: str
      - limit: int (default 50)
    """
    try:
        query = request.args.get('query', '')
        if not query:
            return jsonify({'error': 'Query parameter required'}), 400
        
        source = request.args.get('source')
        event_type = request.args.get('event_type')
        limit = int(request.args.get('limit', '50'))
        
        results = app.event_linker.search_events(
            query=query,
            source=source,
            event_type=event_type,
            limit=limit,
        )
        
        return jsonify({
            'query': query,
            'results': results,
            'count': len(results),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.get('/api/investigations/<investigation_id>/events/suggestions')
def suggest_events(investigation_id: str):
    """Get suggested events for investigation.
    
    Query params:
      - limit: int (default 10)
    """
    try:
        limit = int(request.args.get('limit', '10'))
        
        suggestions = app.event_linker.suggest_events(
            investigation_id=investigation_id,
            limit=limit,
        )
        
        return jsonify({
            'investigation_id': investigation_id,
            'suggestions': suggestions,
            'count': len(suggestions),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# Email Notification Routes

@app.post('/api/user/preferences')
@require_auth(allowed_roles={'admin', 'engineer', 'analyst'})
@log_request_response
def set_email_preferences():
    """Set email notification preferences for authenticated user.
    
    Request body:
    {
        "user_email": "user@example.com",
        "notify_on_reply": true,
        "notify_on_event": true,
        "notify_on_milestone": true,
        "digest_frequency": "daily"
    }
    """
    try:
        data = request.json or {}
        
        user_email = data.get('user_email')
        if not user_email:
            return jsonify({'error': 'user_email is required'}), 400
        
        notify_on_reply = data.get('notify_on_reply', True)
        notify_on_event = data.get('notify_on_event', True)
        notify_on_milestone = data.get('notify_on_milestone', True)
        digest_frequency = data.get('digest_frequency', 'daily')
        
        # Validate digest_frequency
        valid_frequencies = ['instant', 'daily', 'weekly', 'never']
        if digest_frequency not in valid_frequencies:
            return jsonify({'error': f'digest_frequency must be one of {valid_frequencies}'}), 400
        
        # Create or update preferences
        prefs = NotificationPreferences(
            user_email=user_email,
            notify_on_reply=notify_on_reply,
            notify_on_event=notify_on_event,
            notify_on_milestone=notify_on_milestone,
            digest_frequency=digest_frequency,
        )
        
        app.email_notifier.set_preferences(prefs)
        
        return jsonify({
            'user_email': user_email,
            'preferences': prefs.to_dict(),
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.get('/api/user/preferences/<user_email>')
def get_email_preferences(user_email: str):
    """Get email notification preferences for a user."""
    try:
        prefs = app.email_notifier.get_preferences(user_email)
        
        if not prefs:
            return jsonify({'error': 'Preferences not found'}), 404
        
        return jsonify(prefs.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.post('/api/user/preferences/<user_email>')
@require_auth(allowed_roles={'admin', 'engineer', 'analyst'})
@log_request_response
def update_email_preferences(user_email: str):
    """Update email notification preferences (requires auth).
    
    Request body (partial update):
    {
        "notify_on_reply": false,
        "digest_frequency": "weekly"
    }
    """
    try:
        data = request.json or {}
        
        # Get existing preferences or create new ones
        prefs = app.email_notifier.get_preferences(user_email)
        if not prefs:
            prefs = NotificationPreferences(user_email)
        
        # Update fields if provided
        if 'notify_on_reply' in data:
            prefs.notify_on_reply = data['notify_on_reply']
        if 'notify_on_event' in data:
            prefs.notify_on_event = data['notify_on_event']
        if 'notify_on_milestone' in data:
            prefs.notify_on_milestone = data['notify_on_milestone']
        if 'digest_frequency' in data:
            valid_frequencies = ['instant', 'daily', 'weekly', 'never']
            if data['digest_frequency'] not in valid_frequencies:
                return jsonify({'error': f'digest_frequency must be one of {valid_frequencies}'}), 400
            prefs.digest_frequency = data['digest_frequency']
        
        # Save updated preferences
        app.email_notifier.set_preferences(prefs)
        
        return jsonify(prefs.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.post('/api/unsubscribe/<token>')
@require_auth()  # Allow any authenticated user to manage their own unsubscribe
@log_request_response
def unsubscribe(token: str):
    """Unsubscribe from all email notifications using token.
    
    Args:
        token: Unsubscribe token from email
    """
    try:
        result = app.email_notifier.unsubscribe(token)
        
        if result:
            return jsonify({
                'message': 'Successfully unsubscribed from all notifications',
                'token': token,
            }), 200
        else:
            return jsonify({'error': 'Invalid or expired token'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.post('/api/notifications/test')
@require_auth(allowed_roles={'admin', 'engineer'})
@log_request_response
def send_test_notification():
    """Send a test email notification (requires auth).
    
    Request body:
    {
        "recipient_email": "user@example.com",
        "recipient_name": "User Name",
        "investigation_title": "Test Investigation",
        "investigation_id": "inv-test",
        "notification_type": "reply"
    }
    """
    try:
        data = request.json or {}
        
        recipient_email = data.get('recipient_email')
        recipient_name = data.get('recipient_name', 'User')
        investigation_title = data.get('investigation_title', 'Test Investigation')
        investigation_id = data.get('investigation_id', 'test-inv')
        notification_type = data.get('notification_type', 'reply')
        
        if not recipient_email:
            return jsonify({'error': 'recipient_email is required'}), 400
        
        investigation_url = f'http://localhost:5000/investigations/{investigation_id}'
        
        if notification_type == 'reply':
            result = app.email_notifier.notify_on_reply(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                annotation_author='Test Author',
                reply_text='This is a test notification from the Git RCA system.',
                investigation_title=investigation_title,
                investigation_id=investigation_id,
                investigation_url=investigation_url,
            )
        elif notification_type == 'event':
            result = app.email_notifier.notify_on_event(
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                event_count=3,
                investigation_title=investigation_title,
                investigation_id=investigation_id,
                investigation_url=investigation_url,
            )
        else:
            return jsonify({'error': f'Unknown notification_type: {notification_type}'}), 400
        
        return jsonify({
            'message': 'Test notification sent' if result else 'Test notification blocked by preferences',
            'result': result,
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


# ============================================================================
# ISSUE #14: Token Revocation & Admin Token Management Endpoints
# ============================================================================

# NOTE: Admin endpoints are now registered in create_app() function above
# to ensure they're available on all app instances (including test apps)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8081)))
