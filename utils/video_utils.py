"""
utils/video_utils.py - Frame Extraction Utilities

Supports:
  - Video file (.mp4, .mov, .avi, .webm)
  - Base64-encoded JPEG/PNG frame list
"""

import base64
import io
from typing import Optional

import cv2
import numpy as np

import config
from utils.logger import app_logger


# ──────────────────────────────────────────────
# Supported video MIME / extensions
# ──────────────────────────────────────────────
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".webm", ".mkv"}


def extract_frames_from_video(video_path: str) -> list[np.ndarray]:
    """
    Extract frames from a video file, applying frame-skip for efficiency.

    Returns a list of BGR numpy arrays (up to MAX_FRAMES).
    Raises ValueError on invalid / unreadable video.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    if duration > config.MAX_VIDEO_DURATION_SEC:
        app_logger.warning(
            f"Video duration {duration:.1f}s exceeds max "
            f"{config.MAX_VIDEO_DURATION_SEC}s — truncating."
        )

    max_source_frames = int(config.MAX_VIDEO_DURATION_SEC * fps)
    frames: list[np.ndarray] = []
    idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx > max_source_frames:
            break
        if idx % config.FRAME_SKIP == 0:
            frames.append(frame)
        if len(frames) >= config.MAX_FRAMES:
            break
        idx += 1

    cap.release()

    if len(frames) < config.MIN_FRAMES_REQUIRED:
        raise ValueError(
            f"Too few frames extracted ({len(frames)}). "
            f"Minimum required: {config.MIN_FRAMES_REQUIRED}."
        )

    app_logger.debug(f"Extracted {len(frames)} frames from video (duration={duration:.1f}s)")
    return frames


def extract_frames_from_base64(b64_list: list[str]) -> list[np.ndarray]:
    """
    Decode a list of base64 image strings into BGR numpy arrays.

    Each item may optionally have a 'data:image/...;base64,' prefix.
    Raises ValueError if the list is empty or all frames are corrupt.
    """
    if not b64_list:
        raise ValueError("Base64 frame list is empty.")

    # Apply frame-skip to avoid processing every single frame
    sampled: list[str] = b64_list[:: config.FRAME_SKIP][: config.MAX_FRAMES]

    frames: list[np.ndarray] = []
    for i, b64 in enumerate(sampled):
        frame = _decode_b64_frame(b64, index=i)
        if frame is not None:
            frames.append(frame)

    if len(frames) < config.MIN_FRAMES_REQUIRED:
        raise ValueError(
            f"Too few valid frames decoded ({len(frames)}). "
            f"Minimum required: {config.MIN_FRAMES_REQUIRED}."
        )

    app_logger.debug(f"Decoded {len(frames)} frames from base64 list")
    return frames


def _decode_b64_frame(b64_str: str, index: int = 0) -> Optional[np.ndarray]:
    """Decode a single base64 image string. Returns None on failure."""
    try:
        # Strip data-URI prefix if present
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]

        raw = base64.b64decode(b64_str)
        arr = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if frame is None:
            app_logger.warning(f"Frame[{index}]: cv2.imdecode returned None — skipping.")
            return None

        return frame
    except Exception as exc:
        app_logger.warning(f"Frame[{index}]: decode error — {exc}")
        return None


def validate_extension(filename: str) -> bool:
    """Return True if the filename has an allowed video extension."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in ALLOWED_VIDEO_EXTENSIONS
