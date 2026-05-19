"""
core/challenge_detector.py - Challenge-Based Liveness Detection

Challenge types:
  - BLINK_ONCE: Blink 1 time
  - BLINK_TWICE: Blink 2 times
  - SMILE: Show smile/mouth open
  - TURN_LEFT: Head yaw left > 15°
  - TURN_RIGHT: Head yaw right > 15°
  - LOOK_UP: Head pitch up > 12°
  - LOOK_DOWN: Head pitch down > 12°
"""

from dataclasses import dataclass
from enum import Enum
import random
import numpy as np

import config
from utils.logger import app_logger


class ChallengeType(Enum):
    """Supported challenge types."""
    BLINK_ONCE = "blink_once"
    BLINK_TWICE = "blink_twice"
    SMILE = "smile"
    TURN_LEFT = "turn_left"
    TURN_RIGHT = "turn_right"
    LOOK_UP = "look_up"
    LOOK_DOWN = "look_down"


@dataclass
class ChallengeRequest:
    """Challenge instruction for user."""
    challenge_type: ChallengeType
    description: str
    instruction: str

    def to_dict(self) -> dict:
        return {
            "type": self.challenge_type.value,
            "description": self.description,
            "instruction": self.instruction,
        }


@dataclass
class ChallengeResult:
    """Challenge completion result."""
    challenge_type: ChallengeType
    completed: bool = False
    reason: str = ""
    confidence: float = 0.0  # 0.0-1.0


class ChallengeGenerator:
    """Generate random liveness challenges."""

    CHALLENGES = [
        ChallengeType.BLINK_ONCE,
        ChallengeType.BLINK_TWICE,
        ChallengeType.SMILE,
        ChallengeType.TURN_LEFT,
        ChallengeType.TURN_RIGHT,
        ChallengeType.LOOK_UP,
        ChallengeType.LOOK_DOWN,
    ]

    @staticmethod
    def generate() -> ChallengeRequest:
        """Generate a random challenge."""
        challenge_type = random.choice(ChallengeGenerator.CHALLENGES)
        return ChallengeGenerator._get_challenge_details(challenge_type)

    @staticmethod
    def generate_multiple(count: int = 2) -> list[ChallengeRequest]:
        """Generate multiple random challenges."""
        challenges = []
        for _ in range(count):
            challenge = ChallengeGenerator.generate()
            challenges.append(challenge)
        return challenges

    @staticmethod
    def _get_challenge_details(challenge_type: ChallengeType) -> ChallengeRequest:
        """Get description and instruction for challenge type."""
        details = {
            ChallengeType.BLINK_ONCE: {
                "description": "Blink once",
                "instruction": "Please blink your eyes once naturally",
            },
            ChallengeType.BLINK_TWICE: {
                "description": "Blink twice",
                "instruction": "Please blink your eyes twice naturally",
            },
            ChallengeType.SMILE: {
                "description": "Smile",
                "instruction": "Please smile naturally (show your teeth)",
            },
            ChallengeType.TURN_LEFT: {
                "description": "Turn head left",
                "instruction": "Please turn your head to the left slowly",
            },
            ChallengeType.TURN_RIGHT: {
                "description": "Turn head right",
                "instruction": "Please turn your head to the right slowly",
            },
            ChallengeType.LOOK_UP: {
                "description": "Look up",
                "instruction": "Please look upward slowly",
            },
            ChallengeType.LOOK_DOWN: {
                "description": "Look down",
                "instruction": "Please look downward slowly",
            },
        }

        detail = details[challenge_type]
        return ChallengeRequest(
            challenge_type=challenge_type,
            description=detail["description"],
            instruction=detail["instruction"],
        )


class ChallengeValidator:
    """Validate if challenge was completed."""

    def validate_blink_once(self, blink_count: int) -> ChallengeResult:
        """Check if user blinked at least once."""
        completed = blink_count >= 1
        confidence = min(blink_count / 1.0, 1.0)
        return ChallengeResult(
            challenge_type=ChallengeType.BLINK_ONCE,
            completed=completed,
            reason=f"Blink count: {blink_count}" if not completed else "",
            confidence=confidence,
        )

    def validate_blink_twice(self, blink_count: int) -> ChallengeResult:
        """Check if user blinked at least twice."""
        completed = blink_count >= 2
        confidence = min(blink_count / 2.0, 1.0)
        return ChallengeResult(
            challenge_type=ChallengeType.BLINK_TWICE,
            completed=completed,
            reason=f"Blink count: {blink_count} (need ≥2)" if not completed else "",
            confidence=confidence,
        )

    def validate_smile(self, mouth_aspect_ratio: float) -> ChallengeResult:
        """Check if user smiled (mouth opened)."""
        SMILE_THRESHOLD = 0.5
        completed = mouth_aspect_ratio > SMILE_THRESHOLD
        confidence = min(mouth_aspect_ratio / SMILE_THRESHOLD, 1.0)
        return ChallengeResult(
            challenge_type=ChallengeType.SMILE,
            completed=completed,
            reason=f"Mouth openness: {mouth_aspect_ratio:.2f}" if not completed else "",
            confidence=confidence,
        )

    def validate_turn_left(self, max_yaw: float) -> ChallengeResult:
        """Check if user turned head left (yaw < -15°)."""
        TURN_THRESHOLD = 15.0
        completed = max_yaw < -TURN_THRESHOLD
        confidence = min(abs(max_yaw) / TURN_THRESHOLD, 1.0) if max_yaw < 0 else 0.0
        return ChallengeResult(
            challenge_type=ChallengeType.TURN_LEFT,
            completed=completed,
            reason=f"Head turn: {max_yaw:.1f}° (need ≤-{TURN_THRESHOLD}°)" if not completed else "",
            confidence=confidence,
        )

    def validate_turn_right(self, max_yaw: float) -> ChallengeResult:
        """Check if user turned head right (yaw > 15°)."""
        TURN_THRESHOLD = 15.0
        completed = max_yaw > TURN_THRESHOLD
        confidence = min(abs(max_yaw) / TURN_THRESHOLD, 1.0) if max_yaw > 0 else 0.0
        return ChallengeResult(
            challenge_type=ChallengeType.TURN_RIGHT,
            completed=completed,
            reason=f"Head turn: {max_yaw:.1f}° (need ≥{TURN_THRESHOLD}°)" if not completed else "",
            confidence=confidence,
        )

    def validate_look_up(self, max_pitch: float) -> ChallengeResult:
        """Check if user looked up (pitch < -12°)."""
        LOOK_THRESHOLD = 12.0
        completed = max_pitch < -LOOK_THRESHOLD
        confidence = min(abs(max_pitch) / LOOK_THRESHOLD, 1.0) if max_pitch < 0 else 0.0
        return ChallengeResult(
            challenge_type=ChallengeType.LOOK_UP,
            completed=completed,
            reason=f"Head pitch: {max_pitch:.1f}° (need ≤-{LOOK_THRESHOLD}°)" if not completed else "",
            confidence=confidence,
        )

    def validate_look_down(self, max_pitch: float) -> ChallengeResult:
        """Check if user looked down (pitch > 12°)."""
        LOOK_THRESHOLD = 12.0
        completed = max_pitch > LOOK_THRESHOLD
        confidence = min(abs(max_pitch) / LOOK_THRESHOLD, 1.0) if max_pitch > 0 else 0.0
        return ChallengeResult(
            challenge_type=ChallengeType.LOOK_DOWN,
            completed=completed,
            reason=f"Head pitch: {max_pitch:.1f}° (need ≥{LOOK_THRESHOLD}°)" if not completed else "",
            confidence=confidence,
        )

    def validate_challenge(
        self,
        challenge_type: ChallengeType,
        blink_count: int = 0,
        mouth_ratio: float = 0.0,
        max_yaw: float = 0.0,
        max_pitch: float = 0.0,
    ) -> ChallengeResult:
        """Route to appropriate validator based on challenge type."""
        if challenge_type == ChallengeType.BLINK_ONCE:
            return self.validate_blink_once(blink_count)
        elif challenge_type == ChallengeType.BLINK_TWICE:
            return self.validate_blink_twice(blink_count)
        elif challenge_type == ChallengeType.SMILE:
            return self.validate_smile(mouth_ratio)
        elif challenge_type == ChallengeType.TURN_LEFT:
            return self.validate_turn_left(max_yaw)
        elif challenge_type == ChallengeType.TURN_RIGHT:
            return self.validate_turn_right(max_yaw)
        elif challenge_type == ChallengeType.LOOK_UP:
            return self.validate_look_up(max_pitch)
        elif challenge_type == ChallengeType.LOOK_DOWN:
            return self.validate_look_down(max_pitch)

        return ChallengeResult(
            challenge_type=challenge_type,
            completed=False,
            reason="Unknown challenge type",
        )
