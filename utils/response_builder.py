"""
utils/response_builder.py - Standardised API Response Formatting

All API responses are constructed here so the shape is always
consistent regardless of controller or service path.
"""

from flask import jsonify, Response
from typing import Any


# ──────────────────────────────────────────────
# Success response
# ──────────────────────────────────────────────
def build_liveness_response(
    session_id: str,
    status: str,
    score: float,
    result: dict[str, bool],
    reason: str,
    processing_time: float,
    http_status: int = 200,
) -> tuple[Response, int]:
    """
    Build the standard liveness check API response.

    Returns a (Flask Response, HTTP status code) tuple.
    """
    body: dict[str, Any] = {
        "sessionId": session_id,
        "status": status,          # "PASS" | "FAIL"
        "score": round(score, 1),
        "result": {
            "faceDetected":          result.get("faceDetected", False),
            "blinkDetected":         result.get("blinkDetected", False),
            "headMovementDetected":  result.get("headMovementDetected", False),
            "spoofDetected":         result.get("spoofDetected", True),
        },
        "reason": reason,
        "processingTimeSeconds": round(processing_time, 3),
    }
    return jsonify(body), http_status


# ──────────────────────────────────────────────
# Error response
# ──────────────────────────────────────────────
def build_error_response(
    session_id: str,
    error_code: str,
    message: str,
    http_status: int = 400,
) -> tuple[Response, int]:
    """
    Build a standardised error response.

    Always sets status=FAIL so the frontend never needs to
    branch on error vs. result payloads.
    """
    body: dict[str, Any] = {
        "sessionId": session_id,
        "status": "FAIL",
        "score": 0,
        "result": {
            "faceDetected":         False,
            "blinkDetected":        False,
            "headMovementDetected": False,
            "spoofDetected":        True,
        },
        "errorCode": error_code,
        "reason": message,
    }
    return jsonify(body), http_status


# ──────────────────────────────────────────────
# Health-check response
# ──────────────────────────────────────────────
def build_health_response() -> tuple[Response, int]:
    """Return a simple service health-check payload."""
    return jsonify({"status": "running", "service": "liveness-ai"}), 200
