"""
core/blink_detector.py - Eye Blink Detection via Eye Aspect Ratio (EAR)

Algorithm:
  1. Extract 6 landmark points around each eye (MediaPipe indices).
  2. Compute EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||).
  3. EAR < threshold  →  eye closed.
  4. Count consecutive closed frames to identify blinks.

Reference landmarks (FaceMesh 468-point model):
  Left eye:  [362, 385, 387, 263, 373, 380]
  Right eye: [33,  160, 158, 133, 153, 144]
"""

from dataclasses import dataclass

import numpy as np

import config
from core.face_detector import FaceDetectionSummary
from utils.logger import app_logger


# MediaPipe FaceMesh landmark indices for each eye
_LEFT_EYE  = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE = [33,  160, 158, 133, 153, 144]


# ──────────────────────────────────────────────
# Result type
# ──────────────────────────────────────────────
@dataclass
class BlinkDetectionResult:
    blink_detected: bool = False
    blink_count: int = 0
    avg_ear: float = 0.0


# ──────────────────────────────────────────────
# Detector
# ──────────────────────────────────────────────
class BlinkDetector:
    """Stateless blink analyser — operates on pre-extracted face landmarks."""

    def analyse(self, face_summary: FaceDetectionSummary) -> BlinkDetectionResult:
        """
        Detect blinks from landmark sequences.

        Requires at least some detected frames; returns False if none.
        """
        ear_sequence: list[float] = []

        for frame_result in face_summary.per_frame:
            if not frame_result.detected or frame_result.landmarks is None:
                ear_sequence.append(1.0)  # open-eye placeholder
                continue
            ear = self._compute_avg_ear(frame_result.landmarks)
            ear_sequence.append(ear)

        blink_count = self._count_blinks(ear_sequence)
        avg_ear = float(np.mean(ear_sequence)) if ear_sequence else 0.0
        blink_detected = blink_count >= config.MIN_BLINKS_REQUIRED

        app_logger.debug(
            f"BlinkDetector: count={blink_count} avg_ear={avg_ear:.3f} "
            f"detected={blink_detected}"
        )

        return BlinkDetectionResult(
            blink_detected=blink_detected,
            blink_count=blink_count,
            avg_ear=round(avg_ear, 4),
        )

    # ── EAR calculation ───────────────────────
    @staticmethod
    def _compute_avg_ear(landmarks) -> float:
        """Return the average EAR across both eyes for a single frame."""
        left  = BlinkDetector._eye_aspect_ratio(landmarks, _LEFT_EYE)
        right = BlinkDetector._eye_aspect_ratio(landmarks, _RIGHT_EYE)
        return (left + right) / 2.0

    @staticmethod
    def _eye_aspect_ratio(landmarks, indices: list[int]) -> float:
        """
        Compute EAR for one eye given 6 landmark indices.

        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        """
        pts = [
            np.array([landmarks.landmark[i].x, landmarks.landmark[i].y])
            for i in indices
        ]
        # Vertical distances
        A = np.linalg.norm(pts[1] - pts[5])
        B = np.linalg.norm(pts[2] - pts[4])
        # Horizontal distance
        C = np.linalg.norm(pts[0] - pts[3])
        if C < 1e-6:
            return 1.0
        return (A + B) / (2.0 * C)

    # ── Blink counting ────────────────────────
    @staticmethod
    def _count_blinks(ear_seq: list[float]) -> int:
        """
        Count blinks as transitions: open → closed (N frames) → open.

        Consecutive closed frames must be in [BLINK_CONSEC_MIN, BLINK_CONSEC_MAX].
        """
        blinks = 0
        consec = 0

        for ear in ear_seq:
            if ear < config.EAR_THRESHOLD:
                consec += 1
            else:
                if config.BLINK_CONSEC_MIN <= consec <= config.BLINK_CONSEC_MAX:
                    blinks += 1
                consec = 0

        # Handle blink still in progress at end of sequence
        if config.BLINK_CONSEC_MIN <= consec <= config.BLINK_CONSEC_MAX:
            blinks += 1

        return blinks
