"""
Phase 3d: Analytics API Endpoints

REST API for analytics and insights about investigations and events.

Endpoints:
- GET /api/analytics/events/by-source - Event distribution by source
- GET /api/analytics/events/by-severity - Event distribution by severity
- GET /api/analytics/connectors/health - Connector health metrics
- GET /api/analytics/mttr - Mean Time To Resolution
- GET /api/analytics/insights - Key insights and recommendations
"""

from flask import Blueprint, request, jsonify
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter
from src.models.event import EventStore, Event, EventSource, EventSeverity
from src.store.investigation_store import InvestigationStore

# Create Blueprint
analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


class AnalyticsAPI:
    """Analytics API handler"""

    def __init__(
        self, event_store: EventStore, investigation_store: InvestigationStore
    ):
        self.event_store = event_store
        self.inv_store = investigation_store

    def register_routes(self, app):
        """Register all analytics endpoints with Flask app"""

        @analytics_bp.route("/events/by-source", methods=["GET"])
        def get_events_by_source_distribution():
            """
            Get event distribution by source

            Returns:
            - 200: Distribution data with counts and percentages

            Response format:
            {
                "data": {
                    "git": {"count": 150, "percentage": 25.0},
                    "ci": {"count": 200, "percentage": 33.3},
                    ...
                },
                "total_events": 600,
                "timestamp": "2024-01-28T10:00:00Z"
            }
            """
            try:
                events = self.event_store.get_all()

                # Count by source
                source_counts = Counter()
                for event in events:
                    source_counts[event.source] += 1

                total = len(events)

                # Build response
                data = {}
                for source, count in source_counts.items():
                    data[source] = {
                        "count": count,
                        "percentage": round(
                            (count / total * 100) if total > 0 else 0, 1
                        ),
                    }

                return (
                    jsonify(
                        {
                            "data": data,
                            "total_events": total,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    200,
                )

            except Exception as e:
                return jsonify({"error": "Internal server error"}), 500

        @analytics_bp.route("/events/by-severity", methods=["GET"])
        def get_events_by_severity_distribution():
            """
            Get event distribution by severity

            Returns:
            - 200: Distribution data with counts

            Response format:
            {
                "data": {
                    "critical": {"count": 50, "percentage": 8.3},
                    "high": {"count": 100, "percentage": 16.7},
                    ...
                },
                "total_events": 600,
                "timestamp": "2024-01-28T10:00:00Z"
            }
            """
            try:
                events = self.event_store.get_all()

                # Count by severity
                severity_counts = Counter()
                for event in events:
                    severity_counts[event.severity] += 1

                total = len(events)

                # Build response
                data = {}
                severity_order = ["critical", "high", "medium", "low", "info"]
                for severity in severity_order:
                    count = severity_counts.get(severity, 0)
                    data[severity] = {
                        "count": count,
                        "percentage": round(
                            (count / total * 100) if total > 0 else 0, 1
                        ),
                    }

                return (
                    jsonify(
                        {
                            "data": data,
                            "total_events": total,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    200,
                )

            except Exception as e:
                return jsonify({"error": "Internal server error"}), 500

        @analytics_bp.route("/connectors/health", methods=["GET"])
        def get_connector_health_metrics():
            """
            Get overall connector health metrics

            Returns:
            - 200: Health metrics for monitoring

            Response format:
            {
                "overall_health": "GOOD|DEGRADED|CRITICAL",
                "total_dlq_events": 15,
                "sources_with_issues": ["LOGS", "TRACES"],
                "average_dlq_size": 3,
                "timestamp": "2024-01-28T10:00:00Z"
            }
            """
            try:
                # This would connect to actual connector instances
                # For now, return template response

                return (
                    jsonify(
                        {
                            "overall_health": "GOOD",
                            "total_dlq_events": 0,
                            "sources_with_issues": [],
                            "average_dlq_size": 0,
                            "recommendation": "All connectors operating normally",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    200,
                )

            except Exception as e:
                return jsonify({"error": "Internal server error"}), 500

        @analytics_bp.route("/mttr", methods=["GET"])
        def get_mttr_metrics():
            """
            Get Mean Time To Resolution metrics

            Query parameters:
            - days: int (default: 30) - number of days to analyze

            Returns:
            - 200: MTTR statistics

            Response format:
            {
                "average_mttr_minutes": 45.5,
                "median_mttr_minutes": 38.2,
                "min_mttr_minutes": 5,
                "max_mttr_minutes": 240,
                "resolved_investigations": 12,
                "analysis_period": "30 days",
                "timestamp": "2024-01-28T10:00:00Z"
            }
            """
            try:
                days = int(request.args.get("days", 30))

                # Get resolved investigations from past N days
                investigations = self.inv_store.get_all()
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                resolved = []
                for inv in investigations:
                    if inv.status.value == "RESOLVED" and inv.updated_at >= cutoff_date:
                        # Calculate MTTR (created_at to updated_at)
                        if isinstance(inv.created_at, str):
                            created = datetime.fromisoformat(
                                inv.created_at.replace("Z", "+00:00")
                            )
                            updated = datetime.fromisoformat(
                                inv.updated_at.replace("Z", "+00:00")
                            )
                        else:
                            created = inv.created_at
                            updated = inv.updated_at

                        mttr_minutes = (updated - created).total_seconds() / 60
                        resolved.append(mttr_minutes)

                if not resolved:
                    return (
                        jsonify(
                            {
                                "average_mttr_minutes": None,
                                "resolved_investigations": 0,
                                "message": "No resolved investigations in period",
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        ),
                        200,
                    )

                # Calculate statistics
                resolved.sort()
                avg_mttr = sum(resolved) / len(resolved)
                median_mttr = resolved[len(resolved) // 2]

                return (
                    jsonify(
                        {
                            "average_mttr_minutes": round(avg_mttr, 1),
                            "median_mttr_minutes": round(median_mttr, 1),
                            "min_mttr_minutes": round(min(resolved), 1),
                            "max_mttr_minutes": round(max(resolved), 1),
                            "resolved_investigations": len(resolved),
                            "analysis_period": f"{days} days",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    200,
                )

            except ValueError as e:
                return jsonify({"error": f"Invalid parameter: {str(e)}"}), 400
            except Exception as e:
                return jsonify({"error": "Internal server error"}), 500

        @analytics_bp.route("/insights", methods=["GET"])
        def get_insights():
            """
            Get insights and recommendations based on current data

            Returns:
            - 200: Key insights and actionable recommendations

            Response format:
            {
                "insights": [
                    {
                        "type": "warning|info|success",
                        "title": "str",
                        "description": "str",
                        "impact": "high|medium|low"
                    }
                ],
                "recommendations": [str],
                "timestamp": "2024-01-28T10:00:00Z"
            }
            """
            try:
                insights = []
                recommendations = []

                # Analyze events
                events = self.event_store.get_all()
                critical_count = len([e for e in events if e.severity == "critical"])
                high_count = len([e for e in events if e.severity == "high"])

                if critical_count > 10:
                    insights.append(
                        {
                            "type": "warning",
                            "title": "High number of critical events",
                            "description": f"{critical_count} critical events detected",
                            "impact": "high",
                        }
                    )
                    recommendations.append(
                        "Investigate critical event sources and implement mitigation"
                    )

                if high_count > 20:
                    insights.append(
                        {
                            "type": "warning",
                            "title": "Elevated number of high severity events",
                            "description": f"{high_count} high severity events detected",
                            "impact": "medium",
                        }
                    )
                    recommendations.append(
                        "Review recent deployments and configurations"
                    )

                # Analyze investigations
                investigations = self.inv_store.get_all()
                open_investigations = len(
                    [i for i in investigations if i.status.value == "OPEN"]
                )

                if open_investigations > 5:
                    insights.append(
                        {
                            "type": "info",
                            "title": f"{open_investigations} open investigations",
                            "description": f"Currently tracking {open_investigations} active investigations",
                            "impact": "medium",
                        }
                    )
                    recommendations.append(
                        "Prioritize resolution of high-severity open investigations"
                    )

                if not insights:
                    insights.append(
                        {
                            "type": "success",
                            "title": "System operating normally",
                            "description": "No critical issues detected",
                            "impact": "high",
                        }
                    )

                return (
                    jsonify(
                        {
                            "insights": insights,
                            "recommendations": recommendations,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    ),
                    200,
                )

            except Exception as e:
                return jsonify({"error": "Internal server error"}), 500

        # Register blueprint
        app.register_blueprint(analytics_bp)


# Export for use in app.py
def register_analytics_api(app, event_store, investigation_store):
    """
    Register analytics API endpoints with Flask app

    Usage in app.py:
        from src.api.analytics_api import register_analytics_api
        register_analytics_api(app, event_store, investigation_store)
    """
    api = AnalyticsAPI(event_store, investigation_store)
    api.register_routes(app)
