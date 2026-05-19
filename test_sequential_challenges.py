"""
test_sequential_challenges.py - Sequential Challenges Only (4 x 25%)

Complete 4 challenges in sequence:
1. Turn LEFT (25%)
2. Turn RIGHT (25%)
3. Look DOWN (25%)
4. Look UP (25%)

Each challenge = 25%. Complete all 4 = 100% SUCCESS!

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

        # Challenges in sequence
        self.challenges = [
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
        """Draw big challenge prompt"""
        h, w = frame.shape[:2]

        # Large background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)

        challenge = self.get_current_challenge()
        if not challenge:
            return frame

        # Challenge icon (HUGE)
        icon = challenge['icon']
        cv2.putText(frame, icon, (w // 2 - 80, h // 2 - 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 5.0, (0, 255, 255), 8)

        # Challenge text
        cv2.putText(frame, challenge['name'], (w // 2 - 150, h // 2 + 80),
                   cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 255, 0), 3)

        # Progress
        progress_text = f"Step {self.completed_challenges + 1} of 4"
        cv2.putText(frame, progress_text, (w // 2 - 120, h // 2 + 150),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 0), 2)

        return frame

    def draw_progress_circle(self, frame):
        """Draw large progress circle"""
        h, w = frame.shape[:2]

        # Calculate progress (0-360 degrees)
        total_progress = (self.completed_challenges / len(self.challenges)) * 100
        angle = (total_progress / 100) * 360

        center = (w // 2, h // 2)
        radius = 150

        # Background circle (gray)
        cv2.circle(frame, center, radius, (60, 60, 60), 10)

        # Progress arc (green)
        if angle > 0:
            # Draw filled arc
            cv2.ellipse(frame, center, (radius, radius), 0, 0, int(angle), (0, 255, 0), 15)

        # Center circle
        cv2.circle(frame, center, 80, (0, 0, 0), -1)

        # Percentage text
        pct = int((self.completed_challenges / len(self.challenges)) * 100)
        cv2.putText(frame, f"{pct}%", (center[0] - 40, center[1] + 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 0), 3)

        return frame

    def draw_completion_list(self, frame):
        """Draw list of completed challenges"""
        h, w = frame.shape[:2]

        # Background panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, h - 250), (w - 20, h - 20), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        y = h - 220
        for i, challenge in enumerate(self.challenges):
            if i < self.completed_challenges:
                # Completed
                status = f"✓ {challenge['name']}"
                color = (0, 255, 0)
            elif i == self.completed_challenges:
                # Current
                status = f"→ {challenge['name']}"
                color = (0, 255, 255)
            else:
                # Waiting
                status = f"○ {challenge['name']}"
                color = (100, 100, 100)

            cv2.putText(frame, status, (40, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            y += 50

        return frame

    def check_challenge_complete(self, movement_summary):
        """Check if current challenge is completed"""
        challenge = self.get_current_challenge()
        if not challenge:
            return False

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
        if self.check_challenge_complete(movement_summary):
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
        print("Complete 4 challenges in sequence:")
        print("  1. Turn HEAD LEFT (25%)")
        print("  2. Turn HEAD RIGHT (25%)")
        print("  3. Look DOWN (25%)")
        print("  4. Look UP (25%)\n")
        print("Each challenge = 25%. Complete all 4 = 100% SUCCESS!\n")

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
