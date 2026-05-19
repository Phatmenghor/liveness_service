"""
app.py - Application Entry Point
Liveness Detection Microservice — CPBank KYC

Like @SpringBootApplication: bootstraps Flask, registers blueprints,
configures global error handlers, and starts the server.

Dev:   python app.py
Prod:  gunicorn -w 2 -b 0.0.0.0:5000 app:app
"""

import time
from flask import Flask, jsonify, request

import config
from controllers.liveness_controller import liveness_bp
from utils.logger import app_logger


# ──────────────────────────────────────────────
# App factory
# ──────────────────────────────────────────────
def create_app() -> Flask:
    """Create and fully configure the Flask application."""
    app = Flask(__name__)
    app.config["DEBUG"] = config.DEBUG_MODE
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB upload cap

    # ── Register Blueprints ────────────────────
    app.register_blueprint(liveness_bp)

    # ── Request timing middleware ──────────────
    @app.before_request
    def _start_timer():
        request._start_time = time.perf_counter()  # type: ignore[attr-defined]

    @app.after_request
    def _log_request(response):
        elapsed = time.perf_counter() - getattr(request, "_start_time", time.perf_counter())
        app_logger.info(
            f"method={request.method} path={request.path} "
            f"status={response.status_code} time={elapsed:.3f}s"
        )
        return response

    # ── Global Error Handlers ──────────────────
    @app.errorhandler(400)
    def bad_request(exc):
        return jsonify({"status": "FAIL", "errorCode": "BAD_REQUEST", "reason": str(exc)}), 400

    @app.errorhandler(404)
    def not_found(_exc):
        return jsonify({"status": "FAIL", "errorCode": "NOT_FOUND", "reason": "Endpoint not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_exc):
        return jsonify({"status": "FAIL", "errorCode": "METHOD_NOT_ALLOWED", "reason": "HTTP method not allowed."}), 405

    @app.errorhandler(413)
    def payload_too_large(_exc):
        return jsonify({"status": "FAIL", "errorCode": "PAYLOAD_TOO_LARGE", "reason": "Upload exceeds 100 MB limit."}), 413

    @app.errorhandler(500)
    def internal_error(exc):
        app_logger.exception("Unhandled 500 error")
        return jsonify({"status": "FAIL", "errorCode": "INTERNAL_ERROR", "reason": "Internal server error."}), 500

    app_logger.info(
        f"Flask app created | debug={config.DEBUG_MODE} | "
        f"host={config.APP_HOST} port={config.APP_PORT}"
    )
    return app


# ──────────────────────────────────────────────
# Application singleton (used by Gunicorn)
# ──────────────────────────────────────────────
app = create_app()


# ──────────────────────────────────────────────
# Dev server entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    app_logger.info(
        f"Starting development server on {config.APP_HOST}:{config.APP_PORT} ..."
    )
    app.run(
        host=config.APP_HOST,
        port=config.APP_PORT,
        debug=config.DEBUG_MODE,
        use_reloader=False,     # disable reloader to avoid double MediaPipe init
    )
