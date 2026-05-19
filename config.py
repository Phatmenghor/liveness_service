"""
config.py - Central Configuration & Threshold Tuning
Liveness Detection Microservice - CPBank KYC
"""

import os

# ──────────────────────────────────────────────
# APPLICATION SETTINGS
# ──────────────────────────────────────────────
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 5000))
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# ──────────────────────────────────────────────
# LOGGING SETTINGS
# ──────────────────────────────────────────────
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB per log file
LOG_BACKUP_COUNT = 5                # keep last 5 rotated files

# ──────────────────────────────────────────────
# SCORING WEIGHTS  (must sum to 100)
# ──────────────────────────────────────────────
SCORE_FACE_DETECTED      = 30
SCORE_BLINK_DETECTED     = 25
SCORE_HEAD_MOVEMENT      = 25
SCORE_ANTI_SPOOF_PASSED  = 20

PASS_THRESHOLD = 70  # score >= 70 → PASS

# ──────────────────────────────────────────────
# VIDEO / FRAME PROCESSING
# ──────────────────────────────────────────────
MAX_VIDEO_DURATION_SEC = 15       # hard cap on video length
FRAME_SKIP = 3                    # process every Nth frame for speed
MAX_FRAMES = 150                  # absolute ceiling for frames analysed
MIN_FRAMES_REQUIRED = 5           # reject if fewer frames extracted

# ──────────────────────────────────────────────
# FACE DETECTION THRESHOLDS (MediaPipe)
# ──────────────────────────────────────────────
FACE_DETECTION_CONFIDENCE = 0.6   # min_detection_confidence
FACE_TRACKING_CONFIDENCE  = 0.6   # min_tracking_confidence
FACE_REFINE_LANDMARKS     = True  # use refined 478-landmark model
MAX_FACES_ALLOWED         = 1     # reject if multiple faces detected (spoof protection)

# ──────────────────────────────────────────────
# BLINK DETECTION THRESHOLDS
# ──────────────────────────────────────────────
EAR_THRESHOLD      = 0.22         # Eye Aspect Ratio below → eye closed
BLINK_CONSEC_MIN   = 2            # consecutive frames eye must be closed
BLINK_CONSEC_MAX   = 8            # more than this → not a blink (held shut)
MIN_BLINKS_REQUIRED = 1           # blinks needed to pass

# ──────────────────────────────────────────────
# HEAD MOVEMENT DETECTION THRESHOLDS
# ──────────────────────────────────────────────
YAW_THRESHOLD   = 8.0   # degrees – horizontal movement (left/right)
PITCH_THRESHOLD = 6.0   # degrees – vertical movement (up/down)
ROLL_THRESHOLD  = 5.0   # degrees – tilt movement

# ──────────────────────────────────────────────
# ANTI-SPOOF THRESHOLDS
# ──────────────────────────────────────────────
# Minimum pixel-level variance between consecutive frames
MIN_FRAME_VARIANCE       = 50.0   # below this → no motion (photo/replay)
MIN_LANDMARK_VARIANCE    = 0.003  # face landmark positional variance
SPOOF_STABLE_FRAME_RATIO = 0.85   # if >85 % frames are "stable" → spoof
MIN_MOTION_FRAMES        = 3      # need at least this many motion frames

# ──────────────────────────────────────────────
# SESSION TRACKING
# ──────────────────────────────────────────────
SESSION_TTL_SECONDS = 300         # 5 min session expiry
MAX_ACTIVE_SESSIONS = 500         # cap in-memory session store

# ──────────────────────────────────────────────
# FACE QUALITY CHECKS (Bank-Grade KYC)
# ──────────────────────────────────────────────
# Face Size — must occupy 20-70% of frame
FACE_SIZE_MIN_PERCENT = 20.0
FACE_SIZE_MAX_PERCENT = 70.0

# Face Centering — must be within ±20% of frame center
FACE_CENTER_TOLERANCE = 0.2

# Lighting Quality — brightness must be 60-220 (0-255 scale)
LIGHTING_MIN_BRIGHTNESS = 60
LIGHTING_MAX_BRIGHTNESS = 220

# Blur Detection — Laplacian variance must be > 100
BLUR_THRESHOLD = 100.0

# Quality Check Strictness (Bank-Grade KYC)
QUALITY_CHECKS_MANDATORY = True   # if true, ALL frames must pass quality checks
MIN_QUALITY_FRAMES_RATIO = 1.0    # 100% of frames must pass quality checks

# ──────────────────────────────────────────────
# REQUEST TIMEOUT
# ──────────────────────────────────────────────
REQUEST_TIMEOUT_SEC = 30          # processing hard timeout
