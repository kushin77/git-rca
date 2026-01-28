"""
Logs Connector - Parse structured logs and extract events

Features:
- JSON log parsing
- Error/warning classification
- Context extraction (stack traces, request IDs, user IDs)
- Severity inference based on log level
"""

import json
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from src.models.event import Event, EventSource, EventSeverity
from src.connectors.base_connector import BaseConnector, RetryPolicy, CircuitBreakerConfig


class LogsConnector(BaseConnector):
    """Collect and parse structured logs into events."""
    
    # Common log patterns
    ERROR_PATTERNS = [
        r'error',
        r'exception',
        r'failed',
        r'critical',
        r'fatal',
    ]
    
    WARNING_PATTERNS = [
        r'warning',
        r'warn',
        r'deprecated',
        r'slow query',
    ]
    
    def __init__(self,
                 log_source: str = "stdin",  # Can be file path, URL, or "stdin"
                 retry_policy: RetryPolicy = None,
                 circuit_breaker_config: CircuitBreakerConfig = None):
        """
        Initialize logs connector.
        
        Args:
            log_source: Source of logs (file path, log aggregation URL, etc.)
            retry_policy: Retry configuration
            circuit_breaker_config: Circuit breaker configuration
        """
        super().__init__(
            source=EventSource.LOGS,
            retry_policy=retry_policy,
            circuit_breaker_config=circuit_breaker_config,
        )
        self.log_source = log_source
    
    def _collect_with_timeout(self) -> List[Event]:
        """
        Collect logs from source and parse into events.
        
        Supports:
        - JSON logs with standard fields (level, message, timestamp, etc.)
        - Structured logs with context (stack trace, request ID, user ID)
        
        Returns:
            List of Event objects
        """
        logs = self._fetch_logs()
        events = []
        
        for log_entry in logs:
            try:
                event = self._parse_log_to_event(log_entry)
                if event:
                    events.append(event)
            except Exception as e:
                self.logger.warning(f"Failed to parse log entry: {e}")
                continue
        
        self.logger.info(f"Parsed {len(events)} events from {len(logs)} log entries")
        return events
    
    def _fetch_logs(self) -> List[Dict[str, Any]]:
        """
        Fetch logs from source.
        
        Currently supports:
        - File-based logs (JSON lines)
        - In-memory log list for testing
        
        Returns:
            List of log entries (as dicts)
        """
        if isinstance(self.log_source, list):
            # For testing: accept pre-parsed logs
            return self.log_source
        
        try:
            if self.log_source == "stdin":
                # In production, this would read from stdin or log aggregation service
                return []
            elif self.log_source.startswith("http"):
                # TODO: Implement HTTP fetch from log aggregation service
                return []
            else:
                # File-based logs
                return self._fetch_from_file()
        except Exception as e:
            self.logger.error(f"Failed to fetch logs: {e}")
            raise
    
    def _fetch_from_file(self) -> List[Dict[str, Any]]:
        """Fetch JSON lines logs from file."""
        logs = []
        try:
            with open(self.log_source, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        logs.append(json.loads(line))
        except FileNotFoundError:
            self.logger.warning(f"Log file not found: {self.log_source}")
        
        return logs
    
    def _parse_log_to_event(self, log_entry: Dict[str, Any]) -> Optional[Event]:
        """
        Parse log entry to Event.
        
        Args:
            log_entry: Log entry (as dict)
            
        Returns:
            Event object or None if not relevant
        """
        # Extract standard fields
        level = log_entry.get('level', 'info').lower()
        message = log_entry.get('message', log_entry.get('msg', ''))
        timestamp = log_entry.get('timestamp', datetime.utcnow().isoformat())
        
        # Skip non-error/warning logs by default
        if level not in ['error', 'warn', 'warning', 'critical', 'fatal']:
            return None
        
        # Determine severity
        severity = self._classify_severity(level, message)
        
        # Extract context
        context = self._extract_context(log_entry)
        
        # Create event
        event = Event(
            timestamp=timestamp,
            source=EventSource.LOGS,
            event_type='log_entry',
            severity=severity,
            data={
                'level': level,
                'message': message,
                **context,
            },
            source_id=f"{self.log_source}:{log_entry.get('timestamp', '')}",
            tags=self._extract_tags(log_entry),
            metadata={
                'log_source': self.log_source,
            },
        )
        
        return event
    
    def _classify_severity(self, level: str, message: str) -> EventSeverity:
        """
        Classify log entry severity.
        
        Args:
            level: Log level (debug, info, warn, error, critical)
            message: Log message
            
        Returns:
            EventSeverity enum value
        """
        if level in ['critical', 'fatal']:
            return EventSeverity.CRITICAL
        elif level == 'error':
            return EventSeverity.HIGH
        elif level in ['warn', 'warning']:
            # Check message for critical indicators
            message_lower = message.lower()
            if any(pattern in message_lower for pattern in ['deadlock', 'timeout', 'out of memory']):
                return EventSeverity.HIGH
            return EventSeverity.MEDIUM
        else:
            return EventSeverity.LOW
    
    def _extract_context(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract context from log entry."""
        context = {}
        
        # Stack trace
        if 'stacktrace' in log_entry or 'stack_trace' in log_entry:
            context['stack_trace'] = log_entry.get('stacktrace') or log_entry.get('stack_trace')
        
        # Request context
        request_fields = ['request_id', 'trace_id', 'correlation_id', 'request_path', 'method']
        for field in request_fields:
            if field in log_entry:
                context[field] = log_entry[field]
        
        # User context
        if 'user_id' in log_entry:
            context['user_id'] = log_entry['user_id']
        
        # Service/component
        if 'service' in log_entry or 'component' in log_entry:
            context['service'] = log_entry.get('service') or log_entry.get('component')
        
        return context
    
    def _extract_tags(self, log_entry: Dict[str, Any]) -> List[str]:
        """Extract tags from log entry."""
        tags = []
        
        # Tag by level
        level = log_entry.get('level', 'info').lower()
        if level in ['error', 'critical', 'fatal']:
            tags.append('error')
        if level == 'warning':
            tags.append('warning')
        
        # Tag by service
        if 'service' in log_entry:
            tags.append(f"service:{log_entry['service']}")
        
        # Tag by error type from message
        message = log_entry.get('message', '').lower()
        if 'timeout' in message:
            tags.append('timeout')
        if 'connection' in message or 'connection refused' in message:
            tags.append('connection_error')
        if 'authentication' in message or 'permission' in message:
            tags.append('auth_error')
        if 'database' in message or 'sql' in message:
            tags.append('database')
        
        return list(set(tags))  # Remove duplicates
