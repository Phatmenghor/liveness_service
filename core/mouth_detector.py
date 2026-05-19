"""
core/mouth_detector.py - Smile/Mouth Opening Detection

Detects mouth opening for smile challenges using mouth aspect ratio (MAR).
"""

import numpy as np


class MouthDetector:
    """Detects mouth opening and smile."""

    # Mouth landmarks from MediaPipe (out of 478)
    # Upper lip: 61, 185, 40, 39, 37, 0, 267, 269, 270, 409
    # Lower lip: 146, 91, 181, 84, 17, 314, 405, 321, 375
    MOUTH_TOP = [13, 312]  # Top lip center
    MOUTH_BOTTOM = [14, 87]  # Bottom lip center

    @staticmethod
    def calculate_mouth_aspect_ratio(landmarks) -> float:
        """
        Calculate Mouth Aspect Ratio (MAR).

        Higher MAR = mouth more open (smile/talking).
        Lower MAR = mouth closed.
        """
        try:
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Use specific mouth points
            top_lip_y = lm_array[13, 1]  # Upper lip center
            bottom_lip_y = lm_array[14, 1]  # Lower lip center

            # Mouth corners (left and right)
            mouth_left = lm_array[78]  # Left mouth corner
            mouth_right = lm_array[308]  # Right mouth corner

            # MAR = vertical mouth opening / horizontal mouth width
            vertical_dist = abs(top_lip_y - bottom_lip_y)
            horizontal_dist = abs(mouth_right[0] - mouth_left[0])

            if horizontal_dist == 0:
                return 0.0

            mar = vertical_dist / horizontal_dist

            return float(mar)
        except (IndexError, AttributeError):
            return 0.0

    @staticmethod
    def is_smiling(landmarks, threshold: float = 0.5) -> bool:
        """Check if person is smiling (mouth open)."""
        mar = MouthDetector.calculate_mouth_aspect_ratio(landmarks)
        return mar > threshold
