"""
Structured JSON Logging for Investigation RCA Platform

Provides centralized, JSON-formatted logging for:
- All HTTP requests/responses with latency
- Authenticated user context (user_id, role)
- Errors with full stack traces
- Database operations timing
- System events (startup, shutdown, migrations)

All logs are emitted to stderr in JSON format for easy parsing by monitoring/logging systems.
"""

import json
import logging
import time
from datetime import datetime, UTC
from typing import Any, Dict, Optional
from functools import wraps
from flask import request, g, Flask
from logging.handlers import RotatingFileHandler
import sys
import traceback
import os


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.now(UTC).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add request context if available (from Flask g object)
        # Safe access: try/except to handle non-Flask contexts
        try:
            if hasattr(g, 'request_id'):
                log_data['request_id'] = g.request_id
            if hasattr(g, 'user_id'):
                log_data['user_id'] = g.user_id
            if hasattr(g, 'user_role'):
                log_data['user_role'] = g.user_role
        except RuntimeError:
            # g object not available outside Flask application context
            pass
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exc(),
            }
        
        # Add custom fields from LogContext
        if hasattr(record, 'log_context'):
            log_data.update(record.log_context)
        
        return json.dumps(log_data)


class LogContext:
    """Helper to add structured context to logs."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def info(self, message: str, **context) -> None:
        """Log info with context."""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.INFO,
            '(unknown file)',
            0,
            message,
            (),
            None,
        )
        record.log_context = context
        self.logger.handle(record)
    
    def error(self, message: str, **context) -> None:
        """Log error with context."""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.ERROR,
            '(unknown file)',
            0,
            message,
            (),
            None,
        )
        record.log_context = context
        self.logger.handle(record)
    
    def warning(self, message: str, **context) -> None:
        """Log warning with context."""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.WARNING,
            '(unknown file)',
            0,
            message,
            (),
            None,
        )
        record.log_context = context
        self.logger.handle(record)
    
    def debug(self, message: str, **context) -> None:
        """Log debug with context."""
        record = self.logger.makeRecord(
            self.logger.name,
            logging.DEBUG,
            '(unknown file)',
            0,
            message,
            (),
            None,
        )
        record.log_context = context
        self.logger.handle(record)


def setup_logging(app: Flask, log_level: str = 'INFO') -> None:
    """Set up structured JSON logging for Flask app.
    
    Args:
        app: Flask application instance
        log_level: Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    """
    # Set Flask's logger
    app.logger.setLevel(getattr(logging, log_level))
    
    # Remove default handlers
    app.logger.handlers = []
    
    # Create JSON formatter
    formatter = JSONFormatter()
    
    # Create stderr handler (for all logs)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(getattr(logging, log_level))
    stderr_handler.setFormatter(formatter)
    app.logger.addHandler(stderr_handler)
    
    # Optionally create rotating file handler (for persistent logs)
    log_dir = os.environ.get('LOG_DIR', 'logs')
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    if log_dir:
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=10485760,  # 10MB
            backupCount=10,
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
    
    # Log startup
    context = LogContext(app.logger)
    context.info('Application started', level=log_level, log_dir=log_dir or 'stderr only')


def log_request_response(f):
    """Decorator to log HTTP request and response with latency.
    
    Logs:
    - Request: method, path, user context
    - Response: status code, latency (ms)
    - Errors: full exception traceback
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Generate request ID
        request_id = request.headers.get('X-Request-ID', f'{int(time.time() * 1000)}')
        g.request_id = request_id
        
        # Attach user context if available (from auth middleware)
        if hasattr(request, 'user_id'):
            g.user_id = request.user_id
        if hasattr(request, 'user_role'):
            g.user_role = request.user_role
        
        # Start timer
        start_time = time.time()
        
        try:
            # Call the route handler
            response = f(*args, **kwargs)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract status code from response
            if isinstance(response, tuple):
                status_code = response[1] if len(response) > 1 else 200
            else:
                status_code = 200
            
            # Log request/response
            from flask import current_app
            context = LogContext(current_app.logger)
            context.info(
                f'{request.method} {request.path}',
                method=request.method,
                path=request.path,
                status_code=status_code,
                latency_ms=round(latency_ms, 2),
                remote_addr=request.remote_addr,
                user_agent=request.user_agent.string,
            )
            
            return response
        
        except Exception as e:
            # Log error with traceback
            latency_ms = (time.time() - start_time) * 1000
            from flask import current_app
            context = LogContext(current_app.logger)
            context.error(
                f'{request.method} {request.path} - {type(e).__name__}',
                method=request.method,
                path=request.path,
                error_type=type(e).__name__,
                error_message=str(e),
                latency_ms=round(latency_ms, 2),
                exception=traceback.format_exc(),
            )
            
            # Re-raise exception for Flask to handle
            raise
    
    return decorated_function


def log_db_operation(operation: str, table: str, duration_ms: float, **context) -> None:
    """Log database operation with timing.
    
    Args:
        operation: 'SELECT', 'INSERT', 'UPDATE', 'DELETE'
        table: Table name
        duration_ms: Duration in milliseconds
        **context: Additional context to log
    """
    from flask import current_app
    context_obj = LogContext(current_app.logger)
    context_obj.info(
        f'Database {operation}',
        operation=operation,
        table=table,
        duration_ms=round(duration_ms, 2),
        **context
    )


def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)
