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
        self.challenges = [
            {'name': 'Face Centered', 'icon': '◉', 'check': 'center', 'target': None},
            {'name': 'Turn LEFT', 'icon': '←', 'check': 'left', 'target_yaw': -15},
            {'name': 'Turn RIGHT', 'icon': '→', 'check': 'right', 'target_yaw': 15},
            {'name': 'Look DOWN', 'icon': '↓', 'check': 'down', 'target_pitch': 12},
            {'name': 'Look UP', 'icon': '↑', 'check': 'up', 'target_pitch': -12},
        ]

        self.current_challenge_idx = 0
        self.completed_challenges = 0
        self.frames_buffer = deque(maxlen=120)
        self.frame_count = 0
        self.start_time = time.time()
        self.challenge_start_time = time.time()

    def get_current_challenge(self):
        """Get current challenge"""
        if self.current_challenge_idx < len(self.challenges):
            return self.challenges[self.current_challenge_idx]
        return None

    def draw_challenge_prompt(self, frame):
        """Draw clear challenge instruction at top"""
        h, w = frame.shape[:2]

        challenge = self.get_current_challenge()
        if not challenge:
            return frame

        # Top instruction banner
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 140), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)

        # Step counter
        step_text = f"STEP {self.completed_challenges + 1} of 5"
        cv2.putText(frame, step_text, (30, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 2)

        # Current challenge name (large and clear)
        cv2.putText(frame, challenge['name'], (30, 90),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 0), 3)

        return frame

    def draw_progress_circle(self, frame):
        """Draw progress circle (top right)"""
        h, w = frame.shape[:2]

        # Calculate progress (0-360 degrees)
        total_progress = (self.completed_challenges / len(self.challenges)) * 100
        angle = (total_progress / 100) * 360

        # Position top right
        center = (w - 100, 70)
        radius = 50

        # Background circle (dark gray)
        cv2.circle(frame, center, radius, (60, 60, 60), 3)

        # Progress arc (green)
        if angle > 0:
            cv2.ellipse(frame, center, (radius, radius), 0, 0, int(angle), (0, 255, 0), 8)

        # Percentage text (center)
        pct = int(total_progress)
        cv2.putText(frame, f"{pct}%", (center[0] - 25, center[1] + 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        return frame

    def draw_completion_list(self, frame):
        """Draw progress checklist at bottom"""
        h, w = frame.shape[:2]

        # Background panel (bottom half)
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, h - 280), (w - 20, h - 20), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Title
        cv2.putText(frame, "PROGRESS", (30, h - 250),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)

        y = h - 200
        for i, challenge in enumerate(self.challenges):
            # Step number
            step_num = f"{i + 1}."

            if i < self.completed_challenges:
                # Completed (green checkmark)
                status_icon = "✓"
                color = (0, 255, 0)
                name_text = challenge['name']
            elif i == self.completed_challenges:
                # Current (arrow)
                status_icon = "→"
                color = (0, 255, 255)
                name_text = challenge['name'] + "  (DO THIS NOW)"
            else:
                # Waiting (circle)
                status_icon = "○"
                color = (120, 120, 120)
                name_text = challenge['name']

            # Draw step indicator
            cv2.putText(frame, f"{status_icon} {step_num} {name_text}", (40, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
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

        yaw = movement_summary.max_yaw_deg
        pitch = movement_summary.max_pitch_deg

        if challenge['check'] == 'left':
            return yaw < -15  # Turn left > 15°
        elif challenge['check'] == 'right':
            return yaw > 15   # Turn right > 15°
        elif challenge['check'] == 'down':
            return pitch > 12  # Look down > 12°
        elif challenge['check'] == 'up':
            return pitch < -12  # Look up > 12°

        return False

    def analyze_frame(self, frame):
        """Analyze frame"""
        h, w = frame.shape[:2]

        # Face detection
        face_summary = self.face_detector.analyse([frame])

        if not face_summary.face_detected:
            return False

        # Movement detection
        movement_summary = self.movement_detector.analyse(face_summary, w, h)

        # Check if current challenge completed
        if self.check_challenge_complete(face_summary, movement_summary, h, w):
            print(f"\n✓ Challenge completed: {self.challenges[self.current_challenge_idx]['name']}")
            self.completed_challenges += 1
            self.current_challenge_idx += 1
            self.challenge_start_time = time.time()

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
            display_frame = self.draw_progress_circle(display_frame)
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
