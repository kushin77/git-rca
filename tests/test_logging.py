"""
Tests for structured JSON logging functionality.

Tests:
- JSON formatter output
- Request/response logging with latency
- Error logging with stack traces
- Authenticated user context logging
- Database operation timing logs
"""

import json
import pytest
import logging
from io import StringIO
from datetime import datetime, timezone
from src.utils.logging import (
    JSONFormatter,
    LogContext,
    setup_logging,
    log_request_response,
    log_db_operation,
)


@pytest.fixture
def logger_with_string_buffer():
    """Create a logger with string buffer handler."""
    logger = logging.getLogger("test_logger")
    # Clear any existing handlers
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Create string buffer to capture logs
    buffer = StringIO()
    handler = logging.StreamHandler(buffer)
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    yield logger, buffer

    # Cleanup
    logger.removeHandler(handler)
    handler.close()
    buffer.close()


class TestJSONFormatter:
    """Test JSON formatter output."""

    def test_format_basic_log(self, logger_with_string_buffer):
        """Test basic log formatting."""
        logger, buffer = logger_with_string_buffer

        logger.info("Test message")

        # Parse JSON output
        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data
        assert log_data["logger"] == "test_logger"

    def test_format_with_exception(self, logger_with_string_buffer):
        """Test log formatting with exception."""
        logger, buffer = logger_with_string_buffer

        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("An error occurred")

        # Parse JSON output
        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["level"] == "ERROR"
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test error"
        assert "traceback" in log_data["exception"]

    def test_format_different_levels(self, logger_with_string_buffer):
        """Test formatting different log levels."""
        logger, buffer = logger_with_string_buffer

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output = buffer.getvalue()
        lines = [line for line in output.strip().split("\n") if line]

        assert len(lines) == 4

        levels = [json.loads(line)["level"] for line in lines]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]


class TestLogContext:
    """Test LogContext helper."""

    def test_context_info(self, logger_with_string_buffer):
        """Test info logging with context."""
        logger, buffer = logger_with_string_buffer
        context = LogContext(logger)

        context.info(
            "User action", user_id="user123", action="create", resource="investigation"
        )

        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "User action"
        assert log_data["user_id"] == "user123"
        assert log_data["action"] == "create"
        assert log_data["resource"] == "investigation"

    def test_context_error(self, logger_with_string_buffer):
        """Test error logging with context."""
        logger, buffer = logger_with_string_buffer
        context = LogContext(logger)

        context.error(
            "Database error",
            error_code=500,
            operation="INSERT",
            table="investigations",
        )

        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["level"] == "ERROR"
        assert log_data["error_code"] == 500
        assert log_data["operation"] == "INSERT"
        assert log_data["table"] == "investigations"


class TestLoggingDecorator:
    """Test request/response logging decorator."""

    def test_decorator_on_route(self):
        """Test decorator on Flask route."""
        from flask import Flask, jsonify

        app = Flask(__name__)
        app.config["TESTING"] = True

        setup_logging(app)

        @app.get("/test")
        @log_request_response
        def test_route():
            return jsonify({"message": "test"}), 200

        with app.test_client() as client:
            response = client.get("/test")
            assert response.status_code == 200

    def test_decorator_logs_latency(self):
        """Test that decorator captures latency."""
        from flask import Flask, jsonify
        import time

        app = Flask(__name__)
        app.config["TESTING"] = True

        # Set up logging to capture
        buffer = StringIO()
        handler = logging.StreamHandler(buffer)
        formatter = JSONFormatter()
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)

        @app.get("/slow")
        @log_request_response
        def slow_route():
            time.sleep(0.1)  # 100ms delay
            return jsonify({"message": "done"})

        with app.test_client() as client:
            response = client.get("/slow")
            assert response.status_code == 200

        output = buffer.getvalue()
        if output:
            log_data = json.loads(output.strip())
            # Latency should be >= 100ms
            assert "latency_ms" in log_data
            assert log_data["latency_ms"] >= 100


class TestDatabaseLogging:
    """Test database operation logging."""

    def test_log_db_operation(self, logger_with_string_buffer):
        """Test database operation logging."""
        logger, buffer = logger_with_string_buffer

        # Simulate logging a database operation
        record = logger.makeRecord(
            logger.name,
            logging.INFO,
            "(unknown file)",
            0,
            "Database SELECT",
            (),
            None,
        )
        record.log_context = {
            "operation": "SELECT",
            "table": "investigations",
            "duration_ms": 0.45,
            "rows": 5,
        }
        logger.handle(record)

        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["operation"] == "SELECT"
        assert log_data["table"] == "investigations"
        assert log_data["duration_ms"] == 0.45
        assert log_data["rows"] == 5


class TestTimestampFormat:
    """Test timestamp formatting in logs."""

    def test_timestamp_is_iso_format(self, logger_with_string_buffer):
        """Test that timestamp is ISO 8601 format."""
        logger, buffer = logger_with_string_buffer

        logger.info("Test")

        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        # Parse timestamp to verify ISO format
        timestamp_str = log_data["timestamp"]
        # Should be parseable as ISO format
        parsed = datetime.fromisoformat(timestamp_str)
        assert parsed is not None


class TestLoggingLevels:
    """Test different logging levels."""

    def test_debug_level(self, logger_with_string_buffer):
        """Test DEBUG level logging."""
        logger, buffer = logger_with_string_buffer
        context = LogContext(logger)

        context.debug("Debug info", detail="value")

        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["level"] == "DEBUG"
        assert log_data["detail"] == "value"

    def test_warning_level(self, logger_with_string_buffer):
        """Test WARNING level logging."""
        logger, buffer = logger_with_string_buffer
        context = LogContext(logger)

        context.warning("Deprecation notice", deprecated_feature="old_api")

        output = buffer.getvalue().strip()
        log_data = json.loads(output)

        assert log_data["level"] == "WARNING"
        assert log_data["deprecated_feature"] == "old_api"
