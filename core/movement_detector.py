"""
core/movement_detector.py - Head Pose Movement Detection

Estimates yaw (left/right), pitch (up/down), and roll (tilt) from
MediaPipe FaceMesh landmarks using a minimal 6-point PnP solve.

3-D reference model points use a canonical head geometry (in mm).
"""

from dataclasses import dataclass

import cv2
import numpy as np

import config
from core.face_detector import FaceDetectionSummary
from utils.logger import app_logger


# ──────────────────────────────────────────────
# 3-D model points (generic head, millimetres)
# Nose tip, chin, left eye corner, right eye corner,
# left mouth corner, right mouth corner
# ──────────────────────────────────────────────
_MODEL_3D = np.array([
    [0.0,    0.0,    0.0  ],  # Nose tip         – landmark 1
    [0.0,   -330.0, -65.0 ],  # Chin             – landmark 152
    [-225.0, 170.0, -135.0],  # Left eye corner  – landmark 263
    [225.0,  170.0, -135.0],  # Right eye corner – landmark 33
    [-150.0,-150.0, -125.0],  # Left mouth       – landmark 287
    [150.0, -150.0, -125.0],  # Right mouth      – landmark 57
], dtype=np.float64)

# Corresponding MediaPipe landmark indices
_LM_INDICES = [1, 152, 263, 33, 287, 57]


# ──────────────────────────────────────────────
# Result type
# ──────────────────────────────────────────────
@dataclass
class MovementDetectionResult:
    head_movement_detected: bool = False
    max_yaw_deg: float = 0.0
    max_pitch_deg: float = 0.0
    max_roll_deg: float = 0.0
    movement_type: str = "none"   # "horizontal" | "vertical" | "roll" | "combined"


# ──────────────────────────────────────────────
# Detector
# ──────────────────────────────────────────────
class MovementDetector:
    """
    Estimate head pose per frame and detect significant movement.

    Uses a fixed camera matrix derived from frame dimensions.
    This avoids the need for camera calibration — suitable for KYC video.
    """

    def analyse(
        self,
        face_summary: FaceDetectionSummary,
        frame_width: int = 640,
        frame_height: int = 480,
    ) -> MovementDetectionResult:
        """
        Compute head pose for every detected-face frame and check thresholds.
        """
        camera_matrix = self._build_camera_matrix(frame_width, frame_height)
        dist_coeffs   = np.zeros((4, 1), dtype=np.float64)  # assume no lens distortion

        yaws:   list[float] = []
        pitches: list[float] = []
        rolls:  list[float] = []

        for frame_result in face_summary.per_frame:
            if not frame_result.detected or frame_result.landmarks is None:
                continue

            pose = self._estimate_pose(
                frame_result.landmarks,
                frame_width,
                frame_height,
                camera_matrix,
                dist_coeffs,
            )
            if pose is None:
                continue
            yaw, pitch, roll = pose
            yaws.append(yaw)
            pitches.append(pitch)
            rolls.append(roll)

        if not yaws:
            app_logger.debug("MovementDetector: no valid pose estimates")
            return MovementDetectionResult()

        # Maximum deviation from the reference (first) frame
        ref_yaw   = yaws[0]
        ref_pitch = pitches[0]
        ref_roll  = rolls[0]

        max_yaw   = max(abs(y - ref_yaw)   for y in yaws)
        max_pitch = max(abs(p - ref_pitch) for p in pitches)
        max_roll  = max(abs(r - ref_roll)  for r in rolls)

        h_move = max_yaw   > config.YAW_THRESHOLD
        v_move = max_pitch > config.PITCH_THRESHOLD
        r_move = max_roll  > config.ROLL_THRESHOLD

        movement_type = self._classify_movement(h_move, v_move, r_move)
        head_movement_detected = h_move or v_move or r_move

        app_logger.debug(
            f"MovementDetector: yaw={max_yaw:.1f}° pitch={max_pitch:.1f}° "
            f"roll={max_roll:.1f}° type={movement_type}"
        )

        return MovementDetectionResult(
            head_movement_detected=head_movement_detected,
            max_yaw_deg=round(max_yaw, 2),
            max_pitch_deg=round(max_pitch, 2),
            max_roll_deg=round(max_roll, 2),
            movement_type=movement_type,
        )

    # ── Private helpers ───────────────────────
    @staticmethod
    def _build_camera_matrix(w: int, h: int) -> np.ndarray:
        focal = w  # rough approximation: focal ≈ image width
        cx, cy = w / 2.0, h / 2.0
        return np.array([
            [focal, 0,     cx],
            [0,     focal, cy],
            [0,     0,     1 ],
        ], dtype=np.float64)

    @staticmethod
    def _estimate_pose(
        landmarks,
        w: int,
        h: int,
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
    ) -> tuple[float, float, float] | None:
        """
        Run solvePnP and return (yaw, pitch, roll) in degrees.
        Returns None if solvePnP fails.
        """
        img_pts = np.array([
            [landmarks.landmark[i].x * w, landmarks.landmark[i].y * h]
            for i in _LM_INDICES
        ], dtype=np.float64)

        success, rvec, _ = cv2.solvePnP(
            _MODEL_3D,
            img_pts,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return None

        rmat, _ = cv2.Rodrigues(rvec)
        # Decompose rotation matrix to Euler angles (yaw, pitch, roll)
        sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
        if sy > 1e-6:
            pitch = np.degrees(np.arctan2(-rmat[2, 0], sy))
            yaw   = np.degrees(np.arctan2( rmat[1, 0], rmat[0, 0]))
            roll  = np.degrees(np.arctan2( rmat[2, 1], rmat[2, 2]))
        else:
            pitch = np.degrees(np.arctan2(-rmat[2, 0], sy))
            yaw   = 0.0
            roll  = np.degrees(np.arctan2(-rmat[1, 2], rmat[1, 1]))

        return yaw, pitch, roll

    @staticmethod
    def _classify_movement(h: bool, v: bool, r: bool) -> str:
        if h and v:
            return "combined"
        if h:
            return "horizontal"
        if v:
            return "vertical"
        if r:
            return "roll"
        return "none"
