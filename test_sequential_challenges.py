"""
test_sequential_challenges.py - Sequential Challenges Only (5 x 20%)

Complete 5 challenges in sequence:
1. Face Centered (20%)
2. Turn LEFT (20%)
3. Turn RIGHT (20%)
4. Look DOWN (20%)
5. Look UP (20%)

Each challenge = 20%. Complete all 5 = 100% SUCCESS!

Run: python test_sequential_challenges.py
"""

import cv2
import numpy as np
import time
import uuid
from datetime import datetime
import json
import requests
import base64
from collections import deque
from core.face_detector import FaceDetector
from core.movement_detector import MovementDetector
from core.spoof_detector import SpoofDetector

API_URL = "http://localhost:5001"


class SequentialChallengeScanner:
    """Sequential challenges - 4 movements to 100%"""

    def __init__(self):
        self.session_id = f"KYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        self.face_detector = FaceDetector()
        self.movement_detector = MovementDetector()
        self.spoof_detector = SpoofDetector()

        # Challenges in sequence (5 challenges x 20% each)
        # Thresholds lowered for easier detection
        self.challenges = [
            {'name': 'Face Centered', 'icon': '◉', 'check': 'center', 'target': None},
            {'name': 'Turn LEFT', 'icon': '←', 'check': 'left', 'target_yaw': -12},
            {'name': 'Turn RIGHT', 'icon': '→', 'check': 'right', 'target_yaw': 12},
            {'name': 'Look DOWN', 'icon': '↓', 'check': 'down', 'target_pitch': 10},
            {'name': 'Look UP', 'icon': '↑', 'check': 'up', 'target_pitch': -10},
        ]

        self.current_challenge_idx = 0
        self.completed_challenges = 0
        self.frames_buffer = deque(maxlen=120)
        self.frame_count = 0
        self.start_time = time.time()
        self.challenge_start_time = time.time()
        self.last_yaw = 0
        self.last_pitch = 0

        # Track yaw/pitch across frames for cumulative movement
        self.yaw_values = []
        self.pitch_values = []
        self.challenge_yaw_min = float('inf')
        self.challenge_yaw_max = float('-inf')
        self.challenge_pitch_min = float('inf')
        self.challenge_pitch_max = float('-inf')

    def get_current_challenge(self):
        """Get current challenge"""
        if self.current_challenge_idx < len(self.challenges):
            return self.challenges[self.current_challenge_idx]
        return None

    def draw_challenge_prompt(self, frame):
        """Draw challenge instruction at top"""
        h, w = frame.shape[:2]

        challenge = self.get_current_challenge()
        if not challenge:
            return frame

        # Top instruction banner
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w // 2, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)

        # Step counter
        step_text = f"STEP {self.completed_challenges + 1}/5"
        cv2.putText(frame, step_text, (20, 35),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        # Current challenge name (large and clear)
        cv2.putText(frame, challenge['name'], (20, 75),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

        return frame

    def draw_face_guide(self, frame, yaw_deg=0, pitch_deg=0):
        """Draw face guide circle in center with head pose debug"""
        h, w = frame.shape[:2]

        center_x, center_y = w // 2, h // 2
        radius = 140

        # Guide circle (green outline)
        cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 3)

        # Corner guides
        corner_len = 40
        thickness = 3
        color = (0, 255, 0)

        # Top-left
        cv2.line(frame, (center_x - radius - 5, center_y - radius - 5),
                (center_x - radius + corner_len, center_y - radius - 5), color, thickness)
        cv2.line(frame, (center_x - radius - 5, center_y - radius - 5),
                (center_x - radius - 5, center_y - radius + corner_len), color, thickness)

        # Top-right
        cv2.line(frame, (center_x + radius + 5, center_y - radius - 5),
                (center_x + radius - corner_len, center_y - radius - 5), color, thickness)
        cv2.line(frame, (center_x + radius + 5, center_y - radius - 5),
                (center_x + radius + 5, center_y - radius + corner_len), color, thickness)

        # Bottom-left
        cv2.line(frame, (center_x - radius - 5, center_y + radius + 5),
                (center_x - radius + corner_len, center_y + radius + 5), color, thickness)
        cv2.line(frame, (center_x - radius - 5, center_y + radius + 5),
                (center_x - radius - 5, center_y + radius - corner_len), color, thickness)

        # Bottom-right
        cv2.line(frame, (center_x + radius + 5, center_y + radius + 5),
                (center_x + radius - corner_len, center_y + radius + 5), color, thickness)
        cv2.line(frame, (center_x + radius + 5, center_y + radius + 5),
                (center_x + radius + 5, center_y + radius - corner_len), color, thickness)

        # Debug: Show head pose angles
        debug_text = f"YAW: {yaw_deg:.1f}° | PITCH: {pitch_deg:.1f}°"
        cv2.putText(frame, debug_text, (20, h - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

        return frame

    def draw_progress_percentage(self, frame):
        """Draw progress percentage (top right)"""
        h, w = frame.shape[:2]

        # Calculate progress
        total_progress = (self.completed_challenges / len(self.challenges)) * 100
        pct = int(total_progress)

        # Draw on top right
        cv2.putText(frame, f"{pct}%", (w - 120, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

        return frame

    def draw_completion_list(self, frame):
        """Draw progress checklist on RIGHT SIDE (not blocking face)"""
        h, w = frame.shape[:2]

        # Right panel (vertical list)
        overlay = frame.copy()
        cv2.rectangle(overlay, (w - 250, 100), (w, h - 20), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        y = 130
        for i, challenge in enumerate(self.challenges):
            if i < self.completed_challenges:
                # Completed (green checkmark)
                status_icon = "✓"
                color = (0, 255, 0)
            elif i == self.completed_challenges:
                # Current (arrow)
                status_icon = "→"
                color = (0, 255, 255)
            else:
                # Waiting (circle)
                status_icon = "○"
                color = (120, 120, 120)

            # Draw step indicator
            step_text = f"{status_icon} {i + 1}. {challenge['name']}"
            cv2.putText(frame, step_text, (w - 240, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
            y += 45

        return frame

    def check_face_centered(self, face_summary, h, w):
        """Check if face is centered"""
        if not face_summary.face_detected:
            return False

        try:
            landmarks = face_summary.per_frame[0].landmarks
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Face size
            x_min, x_max = lm_array[:, 0].min(), lm_array[:, 0].max()
            y_min, y_max = lm_array[:, 1].min(), lm_array[:, 1].max()

            face_width = (x_max - x_min)
            face_height = (y_max - y_min)

            # Must be at least 15% of frame
            if face_width < 0.15 or face_height < 0.15:
                return False

            # Must be centered (±30% tolerance)
            center_x = (x_max + x_min) / 2
            center_y = (y_max + y_min) / 2

            if abs(center_x - 0.5) > 0.3 or abs(center_y - 0.5) > 0.3:
                return False

            return True
        except:
            return False

    def check_challenge_complete(self, face_summary, movement_summary, h, w):
        """Check if current challenge is completed"""
        challenge = self.get_current_challenge()
        if not challenge:
            return False

        if challenge['check'] == 'center':
            return self.check_face_centered(face_summary, h, w)

        # Use accumulated min/max values across frames
        yaw_range = self.challenge_yaw_max - self.challenge_yaw_min
        pitch_range = self.challenge_pitch_max - self.challenge_pitch_min

        if challenge['check'] == 'left':
            return self.challenge_yaw_min < -12  # Max left turn > 12°
        elif challenge['check'] == 'right':
            return self.challenge_yaw_max > 12   # Max right turn > 12°
        elif challenge['check'] == 'down':
            return self.challenge_pitch_max > 10  # Max down look > 10°
        elif challenge['check'] == 'up':
            return self.challenge_pitch_min < -10  # Max up look > 10°

        return False

    def analyze_frame(self, frame):
        """Analyze frame"""
        h, w = frame.shape[:2]

        # Face detection
        face_summary = self.face_detector.analyse([frame])

        if not face_summary.face_detected:
            return False

        # Get head pose for this frame
        try:
            # Extract 6 key landmarks for pose estimation
            landmarks = face_summary.per_frame[0].landmarks
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Get a simplified pose estimate from landmark positions
            # (nose to chin vertical movement = pitch, ear to ear horizontal = yaw)
            nose_y = landmarks.landmark[1].y
            chin_y = landmarks.landmark[152].y
            left_ear_x = landmarks.landmark[263].x
            right_ear_x = landmarks.landmark[33].x

            # Pitch: vertical face movement (0 to 1 normalized)
            face_height = chin_y - nose_y
            center_y = (chin_y + nose_y) / 2
            pitch = (center_y - 0.5) * 50  # Scale to degrees

            # Yaw: horizontal face movement (0 to 1 normalized)
            face_center_x = (left_ear_x + right_ear_x) / 2
            yaw = (face_center_x - 0.5) * 50  # Scale to degrees

            self.last_yaw = yaw
            self.last_pitch = pitch

            # Track cumulative movement for current challenge
            self.yaw_values.append(yaw)
            self.pitch_values.append(pitch)
            self.challenge_yaw_min = min(self.challenge_yaw_min, yaw)
            self.challenge_yaw_max = max(self.challenge_yaw_max, yaw)
            self.challenge_pitch_min = min(self.challenge_pitch_min, pitch)
            self.challenge_pitch_max = max(self.challenge_pitch_max, pitch)

        except:
            return False

        # Check if current challenge completed
        if self.check_challenge_complete(face_summary, None, h, w):
            print(f"\n✓ Challenge completed: {self.challenges[self.current_challenge_idx]['name']}")
            self.completed_challenges += 1
            self.current_challenge_idx += 1
            self.challenge_start_time = time.time()

            # Reset accumulators for next challenge
            self.yaw_values = []
            self.pitch_values = []
            self.challenge_yaw_min = float('inf')
            self.challenge_yaw_max = float('-inf')
            self.challenge_pitch_min = float('inf')
            self.challenge_pitch_max = float('-inf')

            # Check if all done
            if self.completed_challenges >= len(self.challenges):
                return True  # All challenges complete!

        # Store frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
        self.frames_buffer.append(frame_base64)

        self.frame_count += 1
        return False

    def run(self):
        """Run sequential challenges"""
        print(f"\n{'='*60}")
        print("SEQUENTIAL LIVENESS CHALLENGES".center(60))
        print(f"{'='*60}\n")
        print(f"Session ID: {self.session_id}\n")
        print("Complete 5 challenges in sequence:")
        print("  1. Face Centered (20%)")
        print("  2. Turn HEAD LEFT (20%)")
        print("  3. Turn HEAD RIGHT (20%)")
        print("  4. Look DOWN (20%)")
        print("  5. Look UP (20%)\n")
        print("Each challenge = 20%. Complete all 5 = 100% SUCCESS!\n")

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera!")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.start_time = time.time()
        self.challenge_start_time = time.time()

        all_complete = False

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Analyze frame
            all_complete = self.analyze_frame(frame)

            # Draw overlays
            display_frame = frame.copy()
            display_frame = self.draw_challenge_prompt(display_frame)
            display_frame = self.draw_face_guide(display_frame, self.last_yaw, self.last_pitch)
            display_frame = self.draw_progress_percentage(display_frame)
            display_frame = self.draw_completion_list(display_frame)

            # Show
            cv2.imshow("Sequential Challenges - Press Q to quit", display_frame)

            # Check if all complete
            if all_complete:
                print("\n✓ ALL CHALLENGES COMPLETED! Verifying...")
                break

            # Exit on Q
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nScanning cancelled")
                cap.release()
                cv2.destroyAllWindows()
                return

        cap.release()
        cv2.destroyAllWindows()

        # Final verification
        self.final_verify()

    def final_verify(self):
        """Final verification"""
        print(f"\n{'='*60}")
        print("FINAL VERIFICATION".center(60))
        print(f"{'='*60}\n")

        try:
            response = requests.post(
                f"{API_URL}/liveness/check",
                json={
                    "sessionId": self.session_id,
                    "frames": list(self.frames_buffer)
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                self.show_result(result)
            else:
                print(f"❌ Error: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

    def show_result(self, result):
        """Show final result"""
        score = result.get('score', 0)
        status = result.get('status', 'FAIL')

        print(f"Score: {score:.1f} / 100")
        print(f"Status: {status}\n")

        if status == 'PASS':
            print("="*60)
            print("✓ ✓ ✓ 100% LIVENESS VERIFIED ✓ ✓ ✓".center(60))
            print("="*60)
            print("\n🎉 ALL CHALLENGES COMPLETED!")
            print("✓ Face Centered - Complete")
            print("✓ Turn LEFT - Complete")
            print("✓ Turn RIGHT - Complete")
            print("✓ Look DOWN - Complete")
            print("✓ Look UP - Complete")
            print("\n🏦 Account Approved for Opening!")
            print("Proceeding to document verification...\n")
        else:
            print("="*60)
            print("✗ VERIFICATION FAILED".center(60))
            print("="*60)
            print(f"\nReason: {result.get('reason', 'N/A')}\n")

        # Save
        with open(f"result_{self.session_id}.json", 'w') as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    try:
        scanner = SequentialChallengeScanner()
        scanner.run()
    except KeyboardInterrupt:
        print("\n\nCancelled")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
