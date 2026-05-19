"""
services/liveness_service.py - Core AI Orchestration Layer

Orchestrates all AI components and computes the final liveness score.
No Flask or HTTP logic lives here — pure business logic.

Scoring:
  Face detected      +30
  Blink detected     +25
  Head movement      +25
  Anti-spoof passed  +20
  ─────────────────────
  Total possible     100

PASS threshold: >= 70
"""

import time
from dataclasses import dataclass

import numpy as np

import config
from core.face_detector import FaceDetector, FaceDetectionSummary
from core.blink_detector import BlinkDetector, BlinkDetectionResult
from core.movement_detector import MovementDetector, MovementDetectionResult
from core.spoof_detector import SpoofDetector, SpoofDetectionResult
from core.face_quality_checker import FaceQualityChecker, QualityCheckResult
from utils.logger import app_logger, log_request, log_error, log_debug


# ──────────────────────────────────────────────
# Session tracking  (in-memory, process-local)
# ──────────────────────────────────────────────
_session_store: dict[str, dict] = {}


# ──────────────────────────────────────────────
# Result container
# ──────────────────────────────────────────────
@dataclass
class LivenessCheckResult:
    session_id: str
    status: str                 # "PASS" | "FAIL"
    score: float
    face_detected: bool
    blink_detected: bool
    head_movement_detected: bool
    spoof_detected: bool
    reason: str
    processing_time: float
    debug_info: dict | None = None


# ──────────────────────────────────────────────
# Service
# ──────────────────────────────────────────────
class LivenessService:
    """
    Orchestrates the full liveness detection pipeline.

    Instantiated once per app lifetime and shared across requests.
    Each method call is independent and stateless w.r.t. AI state.
    """

    def __init__(self) -> None:
        self._face_detector     = FaceDetector()
        self._quality_checker   = FaceQualityChecker()
        self._blink_detector    = BlinkDetector()
        self._movement_detector = MovementDetector()
        self._spoof_detector    = SpoofDetector()
        app_logger.info("LivenessService initialised — all AI modules loaded.")

    # ── Public API ─────────────────────────────
    def check_liveness(
        self,
        session_id: str,
        frames: list[np.ndarray],
        input_type: str = "unknown",
    ) -> LivenessCheckResult:
        """
        Run the complete liveness pipeline on a list of BGR frames.

        Args:
            session_id:  Caller-supplied session identifier.
            frames:      List of BGR numpy arrays (pre-extracted).
            input_type:  "video" | "frames" (for audit log).

        Returns:
            LivenessCheckResult with score, status, and breakdown.
        """
        t_start = time.perf_counter()
        log_debug(session_id, f"Pipeline start — {len(frames)} frames, type={input_type}")

        try:
            result = self._run_pipeline(session_id, frames)
        except Exception as exc:
            elapsed = time.perf_counter() - t_start
            log_error(session_id, str(exc), exc)
            return LivenessCheckResult(
                session_id=session_id,
                status="FAIL",
                score=0.0,
                face_detected=False,
                blink_detected=False,
                head_movement_detected=False,
                spoof_detected=True,
                reason=f"Internal pipeline error: {exc}",
                processing_time=round(elapsed, 3),
            )

        elapsed = time.perf_counter() - t_start
        result.processing_time = round(elapsed, 3)

        # ── Audit log ──
        log_request(
            session_id=session_id,
            input_type=input_type,
            score=result.score,
            result=result.status,
            elapsed=elapsed,
        )

        # ── Session store ──
        self._update_session(session_id, result)

        return result

    # ── Pipeline orchestration ─────────────────
    def _run_pipeline(
        self,
        session_id: str,
        frames: list[np.ndarray],
    ) -> LivenessCheckResult:
        """Execute all AI stages in sequence and compute score."""

        # ── Derive frame dimensions from first frame ──
        h, w = frames[0].shape[:2]

        # ── Stage 1: Face Detection ──
        log_debug(session_id, "Stage 1: FaceDetector")
        face_summary: FaceDetectionSummary = self._face_detector.analyse(frames)

        # Short-circuit: no face at all → skip remaining stages
        if not face_summary.face_detected:
            return self._build_result(
                session_id=session_id,
                face_detected=False,
                blink=BlinkDetectionResult(),
                movement=MovementDetectionResult(),
                spoof=SpoofDetectionResult(
                    spoof_detected=True, reason="No face detected."
                ),
                reason="No face detected in the submitted frames.",
            )

        # Short-circuit: multiple faces detected → spoof attempt
        if face_summary.multi_face_detected:
            log_debug(session_id, f"Multiple faces detected in {face_summary.multi_face_frames} frames — REJECTED")
            return self._build_result(
                session_id=session_id,
                face_detected=False,
                blink=BlinkDetectionResult(),
                movement=MovementDetectionResult(),
                spoof=SpoofDetectionResult(
                    spoof_detected=True, reason="Multiple faces detected (possible spoof)."
                ),
                reason=f"Multiple faces detected in {face_summary.multi_face_frames} frames — only 1 face allowed.",
            )

        # ── Stage 1.5: Face Quality Check (Bank-Grade KYC) ──
        log_debug(session_id, "Stage 1.5: FaceQualityChecker")
        quality_issues = self._check_face_quality(
            session_id, frames, face_summary, w, h
        )
        if quality_issues:
            return self._build_result(
                session_id=session_id,
                face_detected=False,
                blink=BlinkDetectionResult(),
                movement=MovementDetectionResult(),
                spoof=SpoofDetectionResult(
                    spoof_detected=True, reason="Face quality check failed."
                ),
                reason=f"Face quality check failed: {quality_issues}",
            )

        # ── Stage 2: Blink Detection ──
        log_debug(session_id, "Stage 2: BlinkDetector")
        blink: BlinkDetectionResult = self._blink_detector.analyse(face_summary)

        # ── Stage 3: Head Movement ──
        log_debug(session_id, "Stage 3: MovementDetector")
        movement: MovementDetectionResult = self._movement_detector.analyse(
            face_summary, frame_width=w, frame_height=h
        )

        # ── Stage 4: Anti-Spoof ──
        log_debug(session_id, "Stage 4: SpoofDetector")
        spoof: SpoofDetectionResult = self._spoof_detector.analyse(frames, face_summary)

        return self._build_result(
            session_id=session_id,
            face_detected=True,
            blink=blink,
            movement=movement,
            spoof=spoof,
        )

    # ── Face Quality Validation ────────────────
    def _check_face_quality(
        self,
        session_id: str,
        frames: list[np.ndarray],
        face_summary: FaceDetectionSummary,
        frame_width: int,
        frame_height: int,
    ) -> str:
        """
        Check all frames pass quality standards (bank-grade KYC).

        Returns empty string if all pass, or failure reason if any fail.
        """
        quality_failures = []
        quality_pass_count = 0

        for idx, frame_result in enumerate(face_summary.per_frame):
            if not frame_result.detected:
                continue

            quality_result = self._quality_checker.check_frame_quality(
                frames[idx],
                frame_result.landmarks,
                frame_width,
                frame_height,
            )

            if quality_result.passes_quality:
                quality_pass_count += 1
            else:
                # Log first few failures for debugging
                if len(quality_failures) < 3:
                    quality_failures.append(
                        f"Frame {idx}: {' | '.join(quality_result.failures)}"
                    )

        detected_count = sum(1 for r in face_summary.per_frame if r.detected)
        if detected_count == 0:
            return "No frames with detected face"

        quality_ratio = quality_pass_count / detected_count

        if config.QUALITY_CHECKS_MANDATORY and quality_ratio < 1.0:
            failure_msg = " | ".join(quality_failures) if quality_failures else "Quality check failed"
            log_debug(session_id, f"Quality check failed: {failure_msg} ({quality_pass_count}/{detected_count} frames)")
            return failure_msg

        if quality_ratio < config.MIN_QUALITY_FRAMES_RATIO:
            log_debug(
                session_id,
                f"Insufficient quality frames: {quality_ratio:.1%} < {config.MIN_QUALITY_FRAMES_RATIO:.1%}"
            )
            return f"Only {quality_ratio:.1%} frames pass quality checks (need {config.MIN_QUALITY_FRAMES_RATIO:.1%})"

        log_debug(session_id, f"Quality check passed: {quality_pass_count}/{detected_count} frames")
        return ""

    # ── Score computation ─────────────────────
    @staticmethod
    def _build_result(
        session_id: str,
        face_detected: bool,
        blink: BlinkDetectionResult,
        movement: MovementDetectionResult,
        spoof: SpoofDetectionResult,
        reason: str = "",
    ) -> LivenessCheckResult:
        """Compute score from component results and assemble the final object."""

        score = 0.0
        reasons: list[str] = []

        if face_detected:
            score += config.SCORE_FACE_DETECTED
        else:
            reasons.append("No face detected.")

        if blink.blink_detected:
            score += config.SCORE_BLINK_DETECTED
        else:
            reasons.append(f"No blink detected (count={blink.blink_count}).")

        if movement.head_movement_detected:
            score += config.SCORE_HEAD_MOVEMENT
        else:
            reasons.append(f"No head movement detected (type={movement.movement_type}).")

        if not spoof.spoof_detected:
            score += config.SCORE_ANTI_SPOOF_PASSED
        else:
            reasons.append(f"Spoof risk: {spoof.reason}")

        status = "PASS" if score >= config.PASS_THRESHOLD else "FAIL"
        final_reason = reason or (
            "Liveness verified." if status == "PASS"
            else " | ".join(reasons)
        )

        debug_info = None
        if config.DEBUG_MODE:
            debug_info = {
                "blinkCount":       blink.blink_count,
                "avgEar":           blink.avg_ear,
                "maxYawDeg":        movement.max_yaw_deg,
                "maxPitchDeg":      movement.max_pitch_deg,
                "maxRollDeg":       movement.max_roll_deg,
                "movementType":     movement.movement_type,
                "frameVariance":    spoof.frame_variance,
                "landmarkVariance": spoof.landmark_variance,
                "stableFrameRatio": spoof.stable_frame_ratio,
                "motionFrames":     spoof.motion_frames,
            }

        return LivenessCheckResult(
            session_id=session_id,
            status=status,
            score=score,
            face_detected=face_detected,
            blink_detected=blink.blink_detected,
            head_movement_detected=movement.head_movement_detected,
            spoof_detected=spoof.spoof_detected,
            reason=final_reason,
            processing_time=0.0,  # set by caller
            debug_info=debug_info,
        )

    # ── Session helpers ────────────────────────
    @staticmethod
    def _update_session(session_id: str, result: LivenessCheckResult) -> None:
        """Persist the latest result for a session (capped store)."""
        if len(_session_store) >= config.MAX_ACTIVE_SESSIONS:
            # Evict the oldest entry (FIFO)
            oldest = next(iter(_session_store))
            _session_store.pop(oldest, None)

        _session_store[session_id] = {
            "status":           result.status,
            "score":            result.score,
            "processing_time":  result.processing_time,
        }

    @staticmethod
    def get_session(session_id: str) -> dict | None:
        """Retrieve stored session data (returns None if not found)."""
        return _session_store.get(session_id)
