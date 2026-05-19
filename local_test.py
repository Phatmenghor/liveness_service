"""
local_test.py — LOCAL CAMERA TEST MODE
CPBank Liveness Detection — Development / QA Tool

PURPOSE
  Opens the system webcam, runs MediaPipe FaceMesh in real time,
  prints structured per-frame logs to the terminal, and displays a
  live annotated camera window.

  Press  Q  to quit and see a final summary.

USAGE
  python local_test.py                # default webcam (index 0)
  python local_test.py --camera 1     # alternate camera index
  python local_test.py --width 1280 --height 720
  python local_test.py --skip 2       # process every 2nd frame
"""

import argparse
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np

# ── Ensure the project root is on sys.path so config / utils load fine ──
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config  # noqa: E402  (project config)


# ══════════════════════════════════════════════
# STANDALONE LOGGER (no Flask dependency)
# ══════════════════════════════════════════════
def _make_local_logger() -> logging.Logger:
    """Create a simple console + file logger for the local test."""
    os.makedirs(config.LOG_DIR, exist_ok=True)

    logger = logging.getLogger("liveness.local_test")
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "[%(levelname)s] %(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    ch.setLevel(logging.DEBUG)
    logger.addHandler(ch)

    # File handler (shared log file)
    fh = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    return logger


log = _make_local_logger()


# ══════════════════════════════════════════════
# CLI ARGUMENTS
# ══════════════════════════════════════════════
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CPBank Liveness — Local Camera Test"
    )
    parser.add_argument(
        "--camera", type=int, default=0,
        metavar="IDX",
        help="Webcam device index (default: 0)",
    )
    parser.add_argument(
        "--width", type=int, default=640,
        help="Capture width in pixels (default: 640)",
    )
    parser.add_argument(
        "--height", type=int, default=480,
        help="Capture height in pixels (default: 480)",
    )
    parser.add_argument(
        "--skip", type=int, default=1,
        metavar="N",
        help="Run MediaPipe every N frames (default: 1 = every frame)",
    )
    parser.add_argument(
        "--no-window", action="store_true",
        help="Suppress the camera window (log only)",
    )
    return parser.parse_args()


# ══════════════════════════════════════════════
# PER-FRAME STATE
# ══════════════════════════════════════════════
@dataclass
class FrameStats:
    total: int = 0
    processed: int = 0          # frames sent to MediaPipe
    face_detected_count: int = 0
    no_face_count: int = 0
    ear_values: list = field(default_factory=list)

    @property
    def detection_rate(self) -> float:
        return self.face_detected_count / max(self.processed, 1)


# ══════════════════════════════════════════════
# EAR HELPERS  (inline, no import from core/)
# ══════════════════════════════════════════════
_LEFT_EYE  = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE = [33,  160, 158, 133, 153, 144]


def _ear(landmarks, indices: list[int]) -> float:
    pts = [
        np.array([landmarks.landmark[i].x, landmarks.landmark[i].y])
        for i in indices
    ]
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3])
    return (A + B) / (2.0 * C) if C > 1e-6 else 1.0


def _avg_ear(landmarks) -> float:
    return (_ear(landmarks, _LEFT_EYE) + _ear(landmarks, _RIGHT_EYE)) / 2.0


# ══════════════════════════════════════════════
# OVERLAY HELPERS
# ══════════════════════════════════════════════
_GREEN  = (0, 230, 80)
_RED    = (0, 60, 220)
_YELLOW = (0, 210, 255)
_WHITE  = (240, 240, 240)
_DARK   = (20, 20, 20)
_FONT   = cv2.FONT_HERSHEY_SIMPLEX


def _draw_hud(
    frame: np.ndarray,
    stats: FrameStats,
    face_detected: bool,
    ear: Optional[float],
    fps: float,
) -> None:
    """Draw a semi-transparent HUD overlay on the frame."""
    h, w = frame.shape[:2]

    # ── Status banner ──────────────────────────
    banner_color = _GREEN if face_detected else _RED
    status_text  = "FACE DETECTED" if face_detected else "NO FACE"
    cv2.rectangle(frame, (0, 0), (w, 44), banner_color, -1)
    cv2.putText(frame, status_text, (12, 30),
                _FONT, 0.85, (255, 255, 255), 2, cv2.LINE_AA)

    # ── FPS top-right ──────────────────────────
    fps_text = f"FPS: {fps:.1f}"
    tw, _ = cv2.getTextSize(fps_text, _FONT, 0.65, 1)[0]
    cv2.putText(frame, fps_text, (w - tw - 14, 30),
                _FONT, 0.65, (255, 255, 255), 1, cv2.LINE_AA)

    # ── Stats panel bottom-left ────────────────
    panel_y = h - 130
    cv2.rectangle(frame, (0, panel_y), (280, h), (0, 0, 0), -1)

    lines = [
        f"Frame : {stats.total}",
        f"Processed : {stats.processed}",
        f"Detected  : {stats.face_detected_count}",
        f"Rate      : {stats.detection_rate:.1%}",
        f"EAR       : {ear:.3f}" if ear is not None else "EAR       : --",
        f"Eye       : {'CLOSED' if (ear is not None and ear < config.EAR_THRESHOLD) else 'open'}",
    ]
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (10, panel_y + 20 + i * 19),
                    _FONT, 0.5, _WHITE, 1, cv2.LINE_AA)

    # ── Quit hint ──────────────────────────────
    cv2.putText(frame, "Press  Q  to quit", (w // 2 - 80, h - 12),
                _FONT, 0.5, _YELLOW, 1, cv2.LINE_AA)


def _draw_landmarks(frame: np.ndarray, face_landmarks, w: int, h: int) -> None:
    """Draw a minimal subset of face mesh contours for visual feedback."""
    mp_drawing = mp.solutions.drawing_utils
    mp_styles  = mp.solutions.drawing_styles
    mp_mesh    = mp.solutions.face_mesh

    mp_drawing.draw_landmarks(
        image=frame,
        landmark_list=face_landmarks,
        connections=mp_mesh.FACEMESH_CONTOURS,
        landmark_drawing_spec=None,
        connection_drawing_spec=mp_styles.get_default_face_mesh_contours_style(),
    )


# ══════════════════════════════════════════════
# BLINK COUNTER  (simple state machine)
# ══════════════════════════════════════════════
class BlinkCounter:
    def __init__(self) -> None:
        self._consec = 0
        self.count   = 0

    def update(self, ear: float) -> None:
        if ear < config.EAR_THRESHOLD:
            self._consec += 1
        else:
            if config.BLINK_CONSEC_MIN <= self._consec <= config.BLINK_CONSEC_MAX:
                self.count += 1
            self._consec = 0


# ══════════════════════════════════════════════
# MAIN LOOP
# ══════════════════════════════════════════════
def run(args: argparse.Namespace) -> None:
    log.info("=" * 60)
    log.info("CPBank Liveness — LOCAL CAMERA TEST MODE")
    log.info(f"Camera index : {args.camera}")
    log.info(f"Resolution   : {args.width}x{args.height}")
    log.info(f"Frame skip   : every {args.skip} frame(s)")
    log.info(f"EAR threshold: {config.EAR_THRESHOLD}")
    log.info("Press  Q  to stop")
    log.info("=" * 60)

    # ── Open webcam ────────────────────────────────────────────────
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        log.error(
            f"Cannot open camera (index={args.camera}). "
            "Check that a webcam is connected and not in use by another app."
        )
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    log.info(f"Camera opened — actual resolution: {actual_w}x{actual_h}")

    # ── MediaPipe FaceMesh ─────────────────────────────────────────
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=1,
        refine_landmarks=config.FACE_REFINE_LANDMARKS,
        min_detection_confidence=config.FACE_DETECTION_CONFIDENCE,
        min_tracking_confidence=config.FACE_TRACKING_CONFIDENCE,
    )

    stats        = FrameStats()
    blink_ctr    = BlinkCounter()
    t_start      = time.perf_counter()
    fps_timer    = time.perf_counter()
    fps_display  = 0.0
    prev_time    = time.perf_counter()

    window_name = "CPBank Liveness — Local Test  [Q to quit]"
    if not args.no_window:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, actual_w, actual_h)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                log.warning("Frame read failed — camera may have disconnected.")
                break

            stats.total += 1

            # ── FPS calculation ────────────────────────────────────
            now = time.perf_counter()
            elapsed_frame = now - prev_time
            prev_time = now
            if elapsed_frame > 0:
                fps_display = 0.9 * fps_display + 0.1 * (1.0 / elapsed_frame)

            # ── Skip frames (for performance) ──────────────────────
            if stats.total % args.skip != 0:
                if not args.no_window:
                    cv2.imshow(window_name, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                continue

            stats.processed += 1

            # ── Run MediaPipe ──────────────────────────────────────
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = face_mesh.process(rgb)
            rgb.flags.writeable = True

            face_detected = bool(results.multi_face_landmarks)
            ear: Optional[float] = None

            if face_detected:
                stats.face_detected_count += 1
                lm = results.multi_face_landmarks[0]
                ear = _avg_ear(lm)
                blink_ctr.update(ear)
                stats.ear_values.append(ear)

                if not args.no_window:
                    _draw_landmarks(frame, lm, actual_w, actual_h)

                log.debug(
                    f"frame={stats.total:05d} | "
                    f"face=TRUE | "
                    f"EAR={ear:.3f} | "
                    f"eye={'CLOSED' if ear < config.EAR_THRESHOLD else 'open '} | "
                    f"blinks={blink_ctr.count} | "
                    f"rate={stats.detection_rate:.1%} | "
                    f"fps={fps_display:.1f}"
                )
            else:
                stats.no_face_count += 1
                log.debug(
                    f"frame={stats.total:05d} | "
                    f"face=FALSE | "
                    f"rate={stats.detection_rate:.1%} | "
                    f"fps={fps_display:.1f}"
                )

            # ── Draw HUD & show ────────────────────────────────────
            if not args.no_window:
                _draw_hud(frame, stats, face_detected, ear, fps_display)
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    log.info("Q pressed — stopping.")
                    break

    except KeyboardInterrupt:
        log.info("Interrupted by user (Ctrl+C).")
    finally:
        face_mesh.close()
        cap.release()
        if not args.no_window:
            cv2.destroyAllWindows()

    # ══════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════
    total_elapsed = time.perf_counter() - t_start
    avg_ear_val   = float(np.mean(stats.ear_values)) if stats.ear_values else 0.0

    log.info("")
    log.info("=" * 60)
    log.info("FINAL SUMMARY")
    log.info("=" * 60)
    log.info(f"Total frames captured  : {stats.total}")
    log.info(f"Frames processed (AI)  : {stats.processed}")
    log.info(f"Face detected          : {stats.face_detected_count} frames")
    log.info(f"No face                : {stats.no_face_count} frames")
    log.info(f"Detection rate         : {stats.detection_rate:.1%}")
    log.info(f"Blinks detected        : {blink_ctr.count}")
    log.info(f"Average EAR            : {avg_ear_val:.4f}  (threshold={config.EAR_THRESHOLD})")
    log.info(f"Total execution time   : {total_elapsed:.2f}s")
    log.info(f"Average FPS            : {stats.total / max(total_elapsed, 0.001):.1f}")
    log.info("=" * 60)

    # ── Quick liveness verdict from local data ──────────────────
    face_ok  = stats.detection_rate >= 0.5
    blink_ok = blink_ctr.count >= config.MIN_BLINKS_REQUIRED
    score = 0
    if face_ok:  score += config.SCORE_FACE_DETECTED
    if blink_ok: score += config.SCORE_BLINK_DETECTED
    verdict = "PASS" if score >= config.PASS_THRESHOLD else "FAIL (partial — no movement/spoof check in local mode)"

    log.info(f"Quick score (face+blink): {score}")
    log.info(f"Quick verdict           : {verdict}")
    log.info("")
    log.info("For a FULL liveness score (with movement + anti-spoof),")
    log.info("submit a video to:  POST http://localhost:5000/liveness/check")
    log.info("=" * 60)


# ══════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════
if __name__ == "__main__":
    args = _parse_args()
    run(args)
