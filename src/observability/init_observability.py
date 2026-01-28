try:
    # Optional OpenTelemetry + Prometheus integration
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
except Exception:
    trace = None

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from prometheus_client import CollectorRegistry, multiprocess, Counter
except Exception:
    generate_latest = None


def init_observability(app):
    """Best-effort observability initializer.

    - Configures a ConsoleSpanExporter if OpenTelemetry is available.
    - Instruments Flask app for basic tracing.
    - Exposes a `/metrics` endpoint if `prometheus_client` is installed.
    The function never raises; failures are logged to app.logger.
    """
    try:
        if trace is not None:
            provider = TracerProvider()
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
            trace.set_tracer_provider(provider)
            try:
                FlaskInstrumentor().instrument_app(app)
                app.logger.info("Observability: Flask instrumentation enabled")
            except Exception:
                app.logger.debug("Observability: Flask instrumentation not available or failed")
        else:
            app.logger.debug("Observability: OpenTelemetry not installed")

        if generate_latest is not None:
            @app.route("/metrics")
            def metrics():
                try:
                    output = generate_latest()
                    return output, 200, {"Content-Type": CONTENT_TYPE_LATEST}
                except Exception:
                    app.logger.exception("Failed to generate Prometheus metrics")
                    return "", 500
            app.logger.info("Observability: /metrics endpoint registered")
        else:
            app.logger.debug("Observability: prometheus_client not installed")
    except Exception:
        try:
            app.logger.exception("Observability initialization failed")
        except Exception:
            # Last-resort swallow to avoid startup failure
            pass
