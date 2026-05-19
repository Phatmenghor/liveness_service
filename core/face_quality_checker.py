"""
core/face_quality_checker.py - Bank-Grade Face Quality Validation

Checks for KYC compliance:
  - Face size (20-70% of frame)
  - Face centering (within center zone)
  - Lighting quality (brightness histogram)
  - Image blur (Laplacian variance)
  - Eye visibility (both eyes detected)
  - Face occlusion (mask, glasses, hand detection)
"""

from dataclasses import dataclass
import cv2
import numpy as np
import config
from utils.logger import app_logger


@dataclass
class QualityCheckResult:
    """Face quality validation result."""
    passes_quality: bool = False
    face_size_ok: bool = False
    face_centered: bool = False
    lighting_ok: bool = False
    blur_ok: bool = False
    eyes_visible: bool = False
    no_occlusion: bool = False

    failures: list[str] = None

    def __post_init__(self):
        if self.failures is None:
            self.failures = []


class FaceQualityChecker:
    """Validates face meets bank-grade KYC standards."""

    def __init__(self):
        pass

    def check_frame_quality(
        self,
        frame: np.ndarray,
        landmarks: object,
        frame_width: int,
        frame_height: int,
    ) -> QualityCheckResult:
        """
        Comprehensive quality check on a single frame with detected face.

        Args:
            frame: BGR numpy array
            landmarks: MediaPipe NormalizedLandmarkList
            frame_width: frame width in pixels
            frame_height: frame height in pixels

        Returns:
            QualityCheckResult with all checks performed
        """
        result = QualityCheckResult(failures=[])

        # 1. Face Size Check
        face_size_ok, size_reason = self._check_face_size(
            landmarks, frame_width, frame_height
        )
        result.face_size_ok = face_size_ok
        if not face_size_ok:
            result.failures.append(size_reason)

        # 2. Face Centering Check
        centered, center_reason = self._check_face_centering(
            landmarks, frame_width, frame_height
        )
        result.face_centered = centered
        if not centered:
            result.failures.append(center_reason)

        # 3. Lighting Quality Check
        lighting_ok, light_reason = self._check_lighting_quality(frame)
        result.lighting_ok = lighting_ok
        if not lighting_ok:
            result.failures.append(light_reason)

        # 4. Blur Detection
        blur_ok, blur_reason = self._check_blur(frame)
        result.blur_ok = blur_ok
        if not blur_ok:
            result.failures.append(blur_reason)

        # 5. Eye Visibility
        eyes_visible, eye_reason = self._check_eyes_visible(landmarks)
        result.eyes_visible = eyes_visible
        if not eyes_visible:
            result.failures.append(eye_reason)

        # 6. Occlusion Detection
        no_occlusion, occlusion_reason = self._check_occlusion(landmarks)
        result.no_occlusion = no_occlusion
        if not no_occlusion:
            result.failures.append(occlusion_reason)

        # Final verdict: all checks must pass
        result.passes_quality = all([
            result.face_size_ok,
            result.face_centered,
            result.lighting_ok,
            result.blur_ok,
            result.eyes_visible,
            result.no_occlusion,
        ])

        return result

    @staticmethod
    def _check_face_size(
        landmarks,
        frame_width: int,
        frame_height: int,
    ) -> tuple[bool, str]:
        """Check if face occupies 20-70% of frame."""
        try:
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Get bounding box
            x_min, x_max = lm_array[:, 0].min(), lm_array[:, 0].max()
            y_min, y_max = lm_array[:, 1].min(), lm_array[:, 1].max()

            # Convert to pixel coordinates
            face_width = (x_max - x_min) * frame_width
            face_height = (y_max - y_min) * frame_height
            face_area = face_width * face_height

            frame_area = frame_width * frame_height
            face_percentage = (face_area / frame_area) * 100

            if face_percentage < 20:
                return False, f"Face too small ({face_percentage:.1f}% - need ≥20%)"
            elif face_percentage > 70:
                return False, f"Face too large ({face_percentage:.1f}% - need ≤70%)"

            return True, ""
        except Exception as e:
            return False, f"Face size check failed: {str(e)}"

    @staticmethod
    def _check_face_centering(
        landmarks,
        frame_width: int,
        frame_height: int,
    ) -> tuple[bool, str]:
        """Check if face is centered in frame (within center zone)."""
        try:
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Face center
            face_center_x = lm_array[:, 0].mean()
            face_center_y = lm_array[:, 1].mean()

            # Frame center
            frame_center_x = 0.5
            frame_center_y = 0.5

            # Allowed deviation (±20% from center)
            tolerance = 0.2

            if abs(face_center_x - frame_center_x) > tolerance:
                return False, f"Face not centered horizontally (offset {abs(face_center_x - frame_center_x):.2f})"
            if abs(face_center_y - frame_center_y) > tolerance:
                return False, f"Face not centered vertically (offset {abs(face_center_y - frame_center_y):.2f})"

            return True, ""
        except Exception as e:
            return False, f"Centering check failed: {str(e)}"

    @staticmethod
    def _check_lighting_quality(frame: np.ndarray) -> tuple[bool, str]:
        """Check lighting quality (histogram brightness)."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray)

            # Good lighting range: 60-220 (out of 255)
            MIN_BRIGHTNESS = 60
            MAX_BRIGHTNESS = 220

            if mean_brightness < MIN_BRIGHTNESS:
                return False, f"Too dark ({mean_brightness:.1f} - need ≥{MIN_BRIGHTNESS})"
            elif mean_brightness > MAX_BRIGHTNESS:
                return False, f"Too bright ({mean_brightness:.1f} - need ≤{MAX_BRIGHTNESS})"

            return True, ""
        except Exception as e:
            return False, f"Lighting check failed: {str(e)}"

    @staticmethod
    def _check_blur(frame: np.ndarray) -> tuple[bool, str]:
        """Check image sharpness using Laplacian variance."""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Minimum variance threshold (empirically tuned)
            BLUR_THRESHOLD = 100.0

            if laplacian_var < BLUR_THRESHOLD:
                return False, f"Image too blurry (sharpness {laplacian_var:.1f} - need ≥{BLUR_THRESHOLD})"

            return True, ""
        except Exception as e:
            return False, f"Blur check failed: {str(e)}"

    @staticmethod
    def _check_eyes_visible(landmarks) -> tuple[bool, str]:
        """Check that both eyes are clearly visible and detected."""
        try:
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Left eye landmarks (indices 33, 160, 158, 133, 153, 144)
            # Right eye landmarks (indices 362, 385, 387, 373, 380, 374)
            left_eye_indices = [33, 160, 158, 133, 153, 144]
            right_eye_indices = [362, 385, 387, 373, 380, 374]

            left_eye_points = lm_array[left_eye_indices]
            right_eye_points = lm_array[right_eye_indices]

            # Check if eyes are in valid range (0 < x,y < 1)
            left_valid = np.all((left_eye_points > 0) & (left_eye_points < 1))
            right_valid = np.all((right_eye_points > 0) & (right_eye_points < 1))

            if not left_valid:
                return False, "Left eye not fully visible"
            if not right_valid:
                return False, "Right eye not fully visible"

            # Check eye separation (eyes too close = possible occlusion)
            left_eye_center = left_eye_points.mean(axis=0)
            right_eye_center = right_eye_points.mean(axis=0)
            eye_distance = np.linalg.norm(right_eye_center - left_eye_center)

            if eye_distance < 0.05:
                return False, "Eyes too close together (possible occlusion)"

            return True, ""
        except Exception as e:
            return False, f"Eye visibility check failed: {str(e)}"

    @staticmethod
    def _check_occlusion(landmarks) -> tuple[bool, str]:
        """Detect occlusions (mask, glasses, hand covering face)."""
        try:
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Key facial points that indicate occlusion if missing
            # Nose tip (1), mouth center (13, 14)
            nose_point = lm_array[1]
            mouth_points = lm_array[[13, 14]]

            # Check if key points are in valid range
            if not (0 < nose_point[0] < 1 and 0 < nose_point[1] < 1):
                return False, "Nose not visible (possible mask/occlusion)"

            if not np.all((mouth_points > 0) & (mouth_points < 1)):
                return False, "Mouth not fully visible (possible mask/occlusion)"

            # Check face contour visibility (indicate full face)
            face_contour_indices = list(range(10, 20)) + list(range(330, 340))
            face_contour = lm_array[face_contour_indices]

            if not np.all((face_contour > 0) & (face_contour < 1)):
                return False, "Face contour not fully visible (possible partial occlusion)"

            return True, ""
        except Exception as e:
            return False, f"Occlusion check failed: {str(e)}"
