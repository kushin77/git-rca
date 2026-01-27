"""
Event Linking Service

Automatically discovers events from git/CI/monitoring systems and links them
to investigations based on temporal proximity and semantic matching.

This service bridges the event discovery layer (git/CI connectors) with
investigation management, enabling automatic event context during RCA.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import re

from src.models.investigation import InvestigationEvent
from src.store.investigation_store import InvestigationStore
from src.connectors import git_connector, ci_connector


class EventLinker:
    """Service for automatically linking events to investigations."""
    
    def __init__(self, investigation_store: InvestigationStore):
        """Initialize event linker with investigation store.
        
        Args:
            investigation_store: Investigation store instance
        """
        self.store = investigation_store
        
    def auto_link_events(
        self,
        investigation_id: str,
        time_window_minutes: int = 60,
        semantic_matching: bool = True,
    ) -> List[InvestigationEvent]:
        """Automatically discover and link events to an investigation.
        
        This method:
        1. Retrieves the investigation's time window
        2. Discovers events from git/CI/monitoring systems
        3. Filters events by temporal proximity
        4. Optionally filters by semantic matching (keywords in title/description)
        5. Links matching events to the investigation
        
        Args:
            investigation_id: Investigation ID
            time_window_minutes: Minutes before/after investigation to search
            semantic_matching: Enable keyword-based event filtering
            
        Returns:
            List of newly linked InvestigationEvent instances
        """
        investigation = self.store.get_investigation(investigation_id)
        if not investigation:
            return []
        
        # Parse investigation created_at timestamp
        try:
            inv_time = datetime.fromisoformat(investigation.created_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return []
        
        # Define time window
        time_start = inv_time - timedelta(minutes=time_window_minutes)
        time_end = inv_time + timedelta(minutes=time_window_minutes)
        
        # Collect events from all sources
        all_events = []
        
        # Git events
        git_events = git_connector.load_events(limit=100)
        for event in git_events:
            if self._is_in_time_window(event, time_start, time_end):
                all_events.append(('git', event))
        
        # CI events
        ci_events = ci_connector.load_events(limit=100)
        for event in ci_events:
            if self._is_in_time_window(event, time_start, time_end):
                all_events.append(('ci', event))
        
        # Filter by semantic matching if enabled
        if semantic_matching and investigation.title:
            all_events = [
                (source, event) for source, event in all_events
                if self._semantic_match(investigation.title, event)
            ]
        
        # Link events to investigation
        linked_events = []
        for source, event in all_events:
            try:
                linked_event = self.store.add_event(
                    investigation_id=investigation_id,
                    event_id=event.get('id', f'{source}-{event.get("timestamp", "")}'),
                    event_type=event.get('type', 'unknown'),
                    source=source.upper(),
                    message=event.get('message', ''),
                    timestamp=event.get('timestamp', datetime.utcnow().isoformat()),
                )
                linked_events.append(linked_event)
            except Exception:
                # Skip events that can't be linked
                continue
        
        return linked_events

    def search_events(
        self,
        query: str,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """Search for events across all sources.
        
        Args:
            query: Search query (searches message, repo, branch fields)
            source: Filter by source ('git', 'ci', or None for all)
            event_type: Filter by event type
            limit: Maximum events to return
            
        Returns:
            List of matching event dictionaries
        """
        results = []
        
        # Search git events
        if source is None or source == 'git':
            git_events = git_connector.load_events(limit=limit)
            for event in git_events:
                if self._matches_query(event, query):
                    if event_type and event.get('type') != event_type:
                        continue
                    results.append({
                        'source': 'git',
                        'type': event.get('type'),
                        'message': event.get('message'),
                        'timestamp': event.get('timestamp'),
                        'repo': event.get('repo'),
                        'author': event.get('author'),
                    })
        
        # Search CI events
        if source is None or source == 'ci':
            ci_events = ci_connector.load_events(limit=limit)
            for event in ci_events:
                if self._matches_query(event, query):
                    if event_type and event.get('type') != event_type:
                        continue
                    results.append({
                        'source': 'ci',
                        'type': event.get('type'),
                        'message': event.get('message'),
                        'timestamp': event.get('timestamp'),
                        'job': event.get('job'),
                        'status': event.get('status'),
                    })
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return results[:limit]

    def suggest_events(
        self,
        investigation_id: str,
        limit: int = 10,
    ) -> List[Dict]:
        """Suggest events that might be relevant to an investigation.
        
        This suggests events that:
        1. Are within a reasonable time window
        2. Match the investigation's title/description keywords
        3. Haven't been linked yet
        
        Args:
            investigation_id: Investigation ID
            limit: Maximum suggestions to return
            
        Returns:
            List of suggested event dictionaries
        """
        investigation = self.store.get_investigation(investigation_id)
        if not investigation:
            return []
        
        # Get already linked events
        linked = self.store.get_investigation_events(investigation_id)
        linked_ids = {evt.event_id for evt in linked}
        
        # Parse investigation time
        try:
            inv_time = datetime.fromisoformat(investigation.created_at.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return []
        
        # Search window: 30 minutes before, 30 minutes after
        time_start = inv_time - timedelta(minutes=30)
        time_end = inv_time + timedelta(minutes=30)
        
        suggestions = []
        
        # Check git events
        git_events = git_connector.load_events(limit=100)
        for event in git_events:
            event_id = event.get('id', f"git-{event.get('timestamp')}")
            if event_id in linked_ids:
                continue
            
            if self._is_in_time_window(event, time_start, time_end):
                if self._semantic_match(investigation.title, event):
                    suggestions.append({
                        'source': 'git',
                        'event_id': event_id,
                        'type': event.get('type'),
                        'message': event.get('message'),
                        'timestamp': event.get('timestamp'),
                        'relevance': 'high',
                    })
        
        # Check CI events
        ci_events = ci_connector.load_events(limit=100)
        for event in ci_events:
            event_id = event.get('id', f"ci-{event.get('timestamp')}")
            if event_id in linked_ids:
                continue
            
            if self._is_in_time_window(event, time_start, time_end):
                if self._semantic_match(investigation.title, event):
                    suggestions.append({
                        'source': 'ci',
                        'event_id': event_id,
                        'type': event.get('type'),
                        'message': event.get('message'),
                        'timestamp': event.get('timestamp'),
                        'relevance': 'high',
                    })
        
        # Sort by timestamp (newest first)
        suggestions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return suggestions[:limit]

    # Helper methods
    
    @staticmethod
    def _is_in_time_window(
        event: Dict,
        time_start: datetime,
        time_end: datetime,
    ) -> bool:
        """Check if event is within time window.
        
        Args:
            event: Event dictionary
            time_start: Window start time
            time_end: Window end time
            
        Returns:
            True if event is in window
        """
        timestamp_str = event.get('timestamp') or event.get('created_at')
        if not timestamp_str:
            return False
        
        try:
            # Parse event time, removing Z and handling timezone info
            ts_clean = timestamp_str.replace('Z', '+00:00')
            event_time = datetime.fromisoformat(ts_clean)
            
            # Make time_start and time_end timezone-aware if needed
            if event_time.tzinfo is not None and time_start.tzinfo is None:
                from datetime import timezone
                time_start = time_start.replace(tzinfo=timezone.utc)
                time_end = time_end.replace(tzinfo=timezone.utc)
            
            return time_start <= event_time <= time_end
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _semantic_match(
        investigation_title: str,
        event: Dict,
    ) -> bool:
        """Check if event semantically matches investigation.
        
        Uses simple keyword matching on event message/title fields.
        
        Args:
            investigation_title: Investigation title
            event: Event dictionary
            
        Returns:
            True if event matches investigation keywords
        """
        if not investigation_title:
            return True  # No title means match all events
        
        # Extract keywords from title (words > 3 chars)
        keywords = [
            word.lower() for word in investigation_title.split()
            if len(word) > 3
        ]
        
        # Search in event fields
        event_text = ' '.join([
            str(v).lower() for v in event.values()
            if isinstance(v, (str, int, float))
        ])
        
        # Match if any keyword appears in event
        for keyword in keywords:
            if keyword in event_text:
                return True
        
        return False

    @staticmethod
    def _matches_query(event: Dict, query: str) -> bool:
        """Check if event matches search query.
        
        Args:
            event: Event dictionary
            query: Search query string
            
        Returns:
            True if event matches query
        """
        query_lower = query.lower()
        
        # Search in key fields
        search_fields = ['message', 'repo', 'branch', 'author', 'job', 'status']
        
        for field in search_fields:
            value = event.get(field)
            if value and query_lower in str(value).lower():
                return True
        
        return False
