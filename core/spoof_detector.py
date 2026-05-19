"""
core/spoof_detector.py - Anti-Spoof / Presentation Attack Detection

MVP heuristics (no deep learning required):
  1. Frame-level pixel variance  →  catches printed photos / static images
  2. Face landmark motion variance  →  catches replayed or looped video
  3. Stable-frame ratio  →  if >85 % of frames have no motion → spoof
  4. Minimum motion-frames count

These are additive risk signals; all must pass for anti-spoof to succeed.
"""

from dataclasses import dataclass

import cv2
import numpy as np

import config
from core.face_detector import FaceDetectionSummary
from utils.logger import app_logger


# ──────────────────────────────────────────────
# Result type
# ──────────────────────────────────────────────
@dataclass
class SpoofDetectionResult:
    spoof_detected: bool = True      # default pessimistic
    frame_variance: float = 0.0
    landmark_variance: float = 0.0
    stable_frame_ratio: float = 1.0
    motion_frames: int = 0
    reason: str = ""


# ──────────────────────────────────────────────
# Detector
# ──────────────────────────────────────────────
class SpoofDetector:
    """
    Lightweight presentation-attack detector.

    Operates entirely on frame pixel data and landmark positions —
    no external model required.
    """

    def analyse(
        self,
        frames: list[np.ndarray],
        face_summary: FaceDetectionSummary,
    ) -> SpoofDetectionResult:
        """
        Run all anti-spoof checks and return a consolidated result.

        Returns spoof_detected=False only if ALL checks pass.
        """
        if len(frames) < 2:
            return SpoofDetectionResult(
                spoof_detected=True,
                reason="Insufficient frames for anti-spoof analysis.",
            )

        frame_var        = self._compute_inter_frame_variance(frames)
        landmark_var     = self._compute_landmark_variance(face_summary)
        stable_ratio, motion_frames = self._compute_stable_ratio(frames)

        app_logger.debug(
            f"SpoofDetector: frame_var={frame_var:.2f} lm_var={landmark_var:.4f} "
            f"stable_ratio={stable_ratio:.2f} motion_frames={motion_frames}"
        )

        # ── Check 1: inter-frame pixel variance ──
        if frame_var < config.MIN_FRAME_VARIANCE:
            return SpoofDetectionResult(
                spoof_detected=True,
                frame_variance=frame_var,
                landmark_variance=landmark_var,
                stable_frame_ratio=stable_ratio,
                motion_frames=motion_frames,
                reason=(
                    f"No significant pixel motion detected "
                    f"(variance={frame_var:.1f} < threshold={config.MIN_FRAME_VARIANCE})."
                ),
            )

        # ── Check 2: landmark positional variance ──
        if landmark_var < config.MIN_LANDMARK_VARIANCE:
            return SpoofDetectionResult(
                spoof_detected=True,
                frame_variance=frame_var,
                landmark_variance=landmark_var,
                stable_frame_ratio=stable_ratio,
                motion_frames=motion_frames,
                reason=(
                    f"Face landmarks show no natural movement "
                    f"(var={landmark_var:.5f} < threshold={config.MIN_LANDMARK_VARIANCE})."
                ),
            )

        # ── Check 3: too many stable frames ──
        if stable_ratio > config.SPOOF_STABLE_FRAME_RATIO:
            return SpoofDetectionResult(
                spoof_detected=True,
                frame_variance=frame_var,
                landmark_variance=landmark_var,
                stable_frame_ratio=stable_ratio,
                motion_frames=motion_frames,
                reason=(
                    f"Excessive static frames detected "
                    f"({stable_ratio*100:.0f}% > {config.SPOOF_STABLE_FRAME_RATIO*100:.0f}%)."
                ),
            )

        # ── Check 4: minimum motion frame count ──
        if motion_frames < config.MIN_MOTION_FRAMES:
            return SpoofDetectionResult(
                spoof_detected=True,
                frame_variance=frame_var,
                landmark_variance=landmark_var,
                stable_frame_ratio=stable_ratio,
                motion_frames=motion_frames,
                reason=(
                    f"Too few motion frames ({motion_frames} < {config.MIN_MOTION_FRAMES})."
                ),
            )

        # ── All checks passed ──
        return SpoofDetectionResult(
            spoof_detected=False,
            frame_variance=frame_var,
            landmark_variance=landmark_var,
            stable_frame_ratio=stable_ratio,
            motion_frames=motion_frames,
            reason="Anti-spoof checks passed.",
        )

    # ── Private helpers ────────────────────────────────────────
    @staticmethod
    def _compute_inter_frame_variance(frames: list[np.ndarray]) -> float:
        """
        Mean absolute pixel difference between consecutive grayscale frames.

        High value → natural movement / live video.
        Low value  → static image or replay without scene change.
        """
        diffs: list[float] = []
        for i in range(1, len(frames)):
            prev = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY).astype(np.float32)
            curr = cv2.cvtColor(frames[i],     cv2.COLOR_BGR2GRAY).astype(np.float32)
            diff = np.mean(np.abs(curr - prev))
            diffs.append(diff)
        return float(np.mean(diffs)) if diffs else 0.0

    @staticmethod
    def _compute_landmark_variance(face_summary: FaceDetectionSummary) -> float:
        """
        Compute standard deviation of nose-tip (landmark 1) x-coordinate
        across all detected frames.

        Real faces exhibit micro-movements; photos are rock-solid.
        """
        xs: list[float] = []
        for fr in face_summary.per_frame:
            if fr.detected and fr.landmarks is not None:
                xs.append(fr.landmarks.landmark[1].x)
        if len(xs) < 2:
            return 0.0
        return float(np.std(xs))

    @staticmethod
    def _compute_stable_ratio(
        frames: list[np.ndarray],
    ) -> tuple[float, int]:
        """
        Return (ratio of static frames, number of motion frames).

        A frame is "static" if the pixel diff to the next frame is
        below MIN_FRAME_VARIANCE.
        """
        stable = 0
        motion = 0
        for i in range(1, len(frames)):
            prev = cv2.cvtColor(frames[i - 1], cv2.COLOR_BGR2GRAY).astype(np.float32)
            curr = cv2.cvtColor(frames[i],     cv2.COLOR_BGR2GRAY).astype(np.float32)
            diff = np.mean(np.abs(curr - prev))
            if diff < config.MIN_FRAME_VARIANCE:
                stable += 1
            else:
                motion += 1

        total = stable + motion or 1
        return stable / total, motion
