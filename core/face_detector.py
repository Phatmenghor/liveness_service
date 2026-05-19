"""
core/face_detector.py - MediaPipe FaceMesh Face Detection

Wraps mediapipe.solutions.face_mesh to:
  - Detect if a face is present in each frame
  - Return the 478-point landmark mesh for downstream analysers
"""

import contextlib
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

import config
from utils.logger import app_logger


# ──────────────────────────────────────────────
# Data container
# ──────────────────────────────────────────────
@dataclass
class FaceFrameResult:
    """Holds per-frame face detection output."""
    detected: bool = False
    landmarks: Optional[object] = None   # mediapipe NormalizedLandmarkList
    frame_index: int = 0


@dataclass
class FaceDetectionSummary:
    """Aggregated result across all frames."""
    face_detected: bool = False
    detection_rate: float = 0.0          # fraction of frames with a face
    per_frame: list[FaceFrameResult] = field(default_factory=list)


# ──────────────────────────────────────────────
# Detector class
# ──────────────────────────────────────────────
class FaceDetector:
    """
    Stateless wrapper around MediaPipe FaceMesh.

    One instance is shared across requests (thread-safe read).
    MediaPipe FaceMesh is **not** thread-safe for concurrent writes,
    so we create a new FaceMesh context per request via a context manager.
    """

    def __init__(self) -> None:
        self._mp_face_mesh = mp.solutions.face_mesh

    # ── public API ────────────────────────────
    def analyse(self, frames: list[np.ndarray]) -> FaceDetectionSummary:
        """
        Run face detection on every frame.

        Returns FaceDetectionSummary with per-frame results.
        """
        per_frame: list[FaceFrameResult] = []
        detected_count = 0

        with self._mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=config.FACE_REFINE_LANDMARKS,
            min_detection_confidence=config.FACE_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.FACE_TRACKING_CONFIDENCE,
        ) as mesh:
            for idx, frame in enumerate(frames):
                result = self._process_frame(mesh, frame, idx)
                per_frame.append(result)
                if result.detected:
                    detected_count += 1

        total = len(frames) or 1
        detection_rate = detected_count / total
        face_detected = detected_count > 0

        app_logger.debug(
            f"FaceDetector: {detected_count}/{total} frames with face "
            f"(rate={detection_rate:.2f})"
        )

        return FaceDetectionSummary(
            face_detected=face_detected,
            detection_rate=detection_rate,
            per_frame=per_frame,
        )

    # ── private helpers ───────────────────────
    @staticmethod
    def _process_frame(
        mesh,
        frame: np.ndarray,
        idx: int,
    ) -> FaceFrameResult:
        """Run FaceMesh on a single BGR frame."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = mesh.process(rgb)

        if results.multi_face_landmarks:
            return FaceFrameResult(
                detected=True,
                landmarks=results.multi_face_landmarks[0],
                frame_index=idx,
            )
        return FaceFrameResult(detected=False, frame_index=idx)
