"""
controllers/liveness_controller.py - API Layer (Flask Blueprint)

Responsibilities:
  - Parse & validate incoming requests (JSON / multipart)
  - Save uploaded video to a temp file
  - Delegate all AI logic to LivenessService
  - Format and return responses via response_builder

NO business logic lives here.
"""

import os
import tempfile
import uuid
from typing import Any

from flask import Blueprint, request

import config
from services.liveness_service import LivenessService
from utils.logger import app_logger, log_error
from utils.response_builder import (
    build_liveness_response,
    build_error_response,
    build_health_response,
)
from utils.video_utils import (
    extract_frames_from_video,
    extract_frames_from_base64,
    validate_extension,
)


# ──────────────────────────────────────────────
# Blueprint & shared service instance
# ──────────────────────────────────────────────
liveness_bp = Blueprint("liveness", __name__)
_service = LivenessService()


# ──────────────────────────────────────────────
# POST /liveness/check
# ──────────────────────────────────────────────
@liveness_bp.route("/liveness/check", methods=["POST"])
def check_liveness():
    """
    Liveness check endpoint.

    Accepts:
      • multipart/form-data  with field 'video' (file) + 'sessionId'
      • application/json     with fields 'sessionId' and 'frames' (base64 list)

    Returns standard liveness JSON response.
    """
    # ── 1. Extract sessionId ──────────────────
    session_id = _resolve_session_id()
    app_logger.info(f"session={session_id} | Received liveness check request")

    content_type = request.content_type or ""

    # ── 2. Route to correct input handler ─────
    try:
        if "multipart/form-data" in content_type:
            return _handle_video_upload(session_id)
        elif "application/json" in content_type:
            return _handle_json_frames(session_id)
        else:
            return build_error_response(
                session_id,
                "UNSUPPORTED_CONTENT_TYPE",
                f"Content-Type '{content_type}' is not supported. "
                "Use multipart/form-data (video) or application/json (base64 frames).",
                http_status=415,
            )
    except ValueError as exc:
        log_error(session_id, str(exc))
        return build_error_response(session_id, "VALIDATION_ERROR", str(exc), 400)
    except Exception as exc:
        log_error(session_id, f"Unexpected error: {exc}", exc)
        return build_error_response(session_id, "INTERNAL_ERROR", "Internal server error.", 500)


# ──────────────────────────────────────────────
# GET /health
# ──────────────────────────────────────────────
@liveness_bp.route("/health", methods=["GET"])
def health_check():
    """Service health probe — used by load balancers and Kubernetes."""
    return build_health_response()


# ──────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────
def _resolve_session_id() -> str:
    """Extract sessionId from request body/form or generate a new UUID."""
    sid: str | None = None
    if request.is_json:
        sid = (request.get_json(silent=True) or {}).get("sessionId")
    else:
        sid = request.form.get("sessionId")
    return sid or str(uuid.uuid4())


def _handle_video_upload(session_id: str):
    """Process a multipart video file upload."""
    if "video" not in request.files:
        return build_error_response(
            session_id, "MISSING_VIDEO", "No 'video' field found in multipart request.", 400
        )

    video_file = request.files["video"]
    filename   = video_file.filename or "upload.mp4"

    if not validate_extension(filename):
        return build_error_response(
            session_id,
            "INVALID_FORMAT",
            f"Unsupported video format '{filename}'. "
            "Accepted: .mp4, .avi, .mov, .webm, .mkv",
            400,
        )

    # Save to a secure temp file
    suffix = "." + filename.rsplit(".", 1)[-1].lower()
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            video_file.save(tmp)
            tmp_path = tmp.name

        app_logger.debug(f"session={session_id} | Saved video to temp: {tmp_path}")
        frames = extract_frames_from_video(tmp_path)

        return _run_service_and_respond(session_id, frames, input_type="video")

    finally:
        # Always clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


def _handle_json_frames(session_id: str):
    """Process a JSON payload containing base64-encoded frames."""
    body: dict[str, Any] = request.get_json(silent=True) or {}
    frames_b64: list = body.get("frames", [])

    if not isinstance(frames_b64, list) or len(frames_b64) == 0:
        return build_error_response(
            session_id,
            "MISSING_FRAMES",
            "'frames' must be a non-empty list of base64 image strings.",
            400,
        )

    frames = extract_frames_from_base64(frames_b64)
    return _run_service_and_respond(session_id, frames, input_type="frames")


def _run_service_and_respond(session_id: str, frames, input_type: str):
    """Delegate to LivenessService and build the HTTP response."""
    result = _service.check_liveness(
        session_id=session_id,
        frames=frames,
        input_type=input_type,
    )

    result_dict = {
        "faceDetected":         result.face_detected,
        "blinkDetected":        result.blink_detected,
        "headMovementDetected": result.head_movement_detected,
        "spoofDetected":        result.spoof_detected,
    }

    response, http_status = build_liveness_response(
        session_id=result.session_id,
        status=result.status,
        score=result.score,
        result=result_dict,
        reason=result.reason,
        processing_time=result.processing_time,
        challenge=result.challenge,
        http_status=200,
    )

    # Attach debug info in DEBUG_MODE
    if config.DEBUG_MODE and result.debug_info:
        payload = response.get_json()
        payload["debug"] = result.debug_info
        from flask import jsonify
        response = jsonify(payload)

    return response, http_status
