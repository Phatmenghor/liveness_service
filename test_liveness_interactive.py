"""
test_liveness_interactive.py - Interactive Live Liveness Testing with Real-Time Camera

Shows:
- Live camera with face detection overlay
- Eye detection circles (red/green)
- Challenge instructions
- Real-time progress bar
- Step-by-step feedback

Run: python test_liveness_interactive.py
"""

import cv2
import numpy as np
import time
import uuid
from datetime import datetime
import json
import requests
from core.face_detector import FaceDetector
from core.blink_detector import BlinkDetector
from core.movement_detector import MovementDetector
from core.spoof_detector import SpoofDetector
from core.face_quality_checker import FaceQualityChecker
from core.challenge_detector import ChallengeGenerator, ChallengeValidator

API_URL = "http://localhost:5001"


class InteractiveLivenessTest:
    """Interactive liveness test with live camera and challenge display"""

    def __init__(self):
        self.session_id = f"KYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        self.face_detector = FaceDetector()
        self.blink_detector = BlinkDetector()
        self.movement_detector = MovementDetector()
        self.spoof_detector = SpoofDetector()
        self.quality_checker = FaceQualityChecker()
        self.challenge_validator = ChallengeValidator()

        self.frames = []
        self.challenge = ChallengeGenerator.generate()
        self.start_time = None

    def draw_face_landmarks(self, frame, landmarks):
        """Draw face landmarks on frame"""
        if not landmarks:
            return frame

        h, w = frame.shape[:2]
        lm_array = np.array([[lm.x * w, lm.y * h] for lm in landmarks.landmark])

        # Draw face mesh (light blue)
        face_points = lm_array[[10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]]
        for point in face_points:
            cv2.circle(frame, tuple(point.astype(int)), 1, (200, 150, 0), -1)

        # Draw left eye (red if closed, green if open)
        left_eye_indices = [33, 160, 158, 133, 153, 144]
        left_eye = lm_array[left_eye_indices]
        cv2.polylines(frame, [left_eye.astype(int)], True, (0, 0, 255), 1)
        cv2.circle(frame, tuple(left_eye.mean(axis=0).astype(int)), 5, (0, 0, 255), 2)

        # Draw right eye (red if closed, green if open)
        right_eye_indices = [362, 385, 387, 373, 380, 374]
        right_eye = lm_array[right_eye_indices]
        cv2.polylines(frame, [right_eye.astype(int)], True, (0, 255, 0), 1)
        cv2.circle(frame, tuple(right_eye.mean(axis=0).astype(int)), 5, (0, 255, 0), 2)

        # Draw mouth
        mouth_indices = [13, 14, 15, 16, 78, 191, 80, 81, 82, 13]
        mouth = lm_array[mouth_indices]
        cv2.polylines(frame, [mouth.astype(int)], False, (255, 255, 255), 2)

        # Draw face outline
        face_outline = lm_array[[10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]]
        cv2.polylines(frame, [face_outline.astype(int)], True, (255, 255, 255), 2)

        return frame

    def draw_challenge_overlay(self, frame, elapsed_seconds):
        """Draw challenge instruction on frame"""
        h, w = frame.shape[:2]

        # Semi-transparent overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Challenge icon and text
        challenge_icons = {
            'blink_once': '👁',
            'blink_twice': '👁👁',
            'smile': '😊',
            'turn_left': '←',
            'turn_right': '→',
            'look_up': '↑',
            'look_down': '↓',
        }

        icon = challenge_icons.get(self.challenge.challenge_type.value, '?')

        # Time remaining
        time_remaining = max(0, 10 - elapsed_seconds)

        # Draw text
        cv2.putText(frame, f"Challenge: {self.challenge.description}", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 2)
        cv2.putText(frame, f"Time: {time_remaining:.1f}s", (w - 200, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        # Progress bar at bottom
        progress = elapsed_seconds / 10.0
        bar_width = int(w * progress)
        cv2.rectangle(frame, (0, h - 10), (bar_width, h), (0, 255, 0), -1)
        cv2.rectangle(frame, (0, h - 10), (w, h), (100, 100, 100), 2)

        return frame

    def draw_stats(self, frame, face_detected, blink_count, fps):
        """Draw stats on frame"""
        h, w = frame.shape[:2]

        stats_text = [
            f"Session: {self.session_id[:16]}...",
            f"Face: {'YES' if face_detected else 'NO'}",
            f"Blinks: {blink_count}",
            f"FPS: {fps:.1f}",
        ]

        y = 30
        for text in stats_text:
            cv2.putText(frame, text, (w - 300, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
            y += 25

        return frame

    def run(self):
        """Run interactive test"""
        print(f"\n{'='*60}")
        print(f"INTERACTIVE LIVENESS TEST".center(60))
        print(f"{'='*60}\n")
        print(f"Session ID: {self.session_id}")
        print(f"\nOpening camera...")
        print(f"Challenge: {self.challenge.description}")
        print(f"Instruction: {self.challenge.instruction}\n")

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera!")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.start_time = time.time()
        frame_count = 0
        last_time = time.time()
        fps = 0

        print("✓ Camera opened. Press Q to stop early, or wait 10 seconds...\n")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            elapsed = time.time() - self.start_time
            frame_count += 1

            # Calculate FPS
            current_time = time.time()
            if current_time - last_time >= 1.0:
                fps = frame_count / (current_time - self.start_time)
                last_time = current_time

            # Detect face
            face_summary = self.face_detector.analyse([frame])
            face_detected = face_summary.face_detected
            blink_summary = self.blink_detector.analyse(face_summary)

            # Draw landmarks if face detected
            if face_detected and face_summary.per_frame[0].detected:
                frame = self.draw_face_landmarks(frame, face_summary.per_frame[0].landmarks)

            # Draw challenge overlay
            frame = self.draw_challenge_overlay(frame, elapsed)

            # Draw stats
            frame = self.draw_stats(frame, face_detected, blink_summary.blink_count, fps)

            # Show frame
            cv2.imshow("Liveness Test - Press Q to Stop", frame)

            # Store frame for later processing
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            import base64
            frame_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
            self.frames.append(frame_base64)

            # Stop after 10 seconds or if Q is pressed
            if elapsed >= 10 or cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        print(f"\n✓ Captured {frame_count} frames in {elapsed:.1f} seconds")
        print(f"\nProcessing with AI service...")

        # Send to API
        self.process_with_api()

    def process_with_api(self):
        """Send frames to API and get results"""
        try:
            response = requests.post(
                f"{API_URL}/liveness/check",
                json={
                    "sessionId": self.session_id,
                    "frames": self.frames
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                self.display_results(result)
            else:
                print(f"❌ API Error: {response.status_code}")
                print(response.text)

        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to API! Is the server running?")
            print(f"Try: PORT=5001 python app.py")
        except Exception as e:
            print(f"❌ Error: {str(e)}")

    def display_results(self, result):
        """Display results with progress bars"""
        print(f"\n{'='*60}")
        print(f"VERIFICATION RESULTS".center(60))
        print(f"{'='*60}\n")

        status = result.get('status')
        score = result.get('score', 0)

        # Main result
        if status == 'PASS':
            print(f"✓ LIVENESS VERIFIED - PASS")
        else:
            print(f"✗ LIVENESS FAILED")

        print(f"\nScore: {score:.1f} / 100")
        print(f"Reason: {result.get('reason', 'N/A')}")

        # Progress breakdown
        print(f"\n{'='*60}")
        print(f"PROGRESS BREAKDOWN".center(60))
        print(f"{'='*60}\n")

        result_data = result.get('result', {})
        challenge = result.get('challenge', {})

        checks = [
            ('Face Quality', result_data.get('faceDetected', False), 20),
            ('Blink Detection', result_data.get('blinkDetected', False), 20),
            ('Head Movement', result_data.get('headMovementDetected', False), 20),
            ('Anti-Spoof', not result_data.get('spoofDetected', True), 20),
            ('Challenge', challenge.get('completed', False) if challenge else False, 20),
        ]

        total = 0
        for name, passed, points in checks:
            if passed:
                filled = 20
                total += points
                status_icon = "✓"
            else:
                filled = 0
                status_icon = "✗"

            bar = "█" * (filled // 1) + "░" * ((100 - filled) // 5)
            print(f"{status_icon} {name:<20} [{bar}] {filled:3d}%")

        print(f"\nTotal: {total}/100")

        # Account decision
        print(f"\n{'='*60}")
        print(f"ACCOUNT OPENING DECISION".center(60))
        print(f"{'='*60}\n")

        if total >= 70:
            print(f"✓ ✓ ✓ ACCOUNT APPROVED ✓ ✓ ✓")
            print(f"Your liveness verification has been approved!")
            print(f"Proceeding to document verification...\n")
        else:
            print(f"✗ ✗ ✗ ACCOUNT REJECTED ✗ ✗ ✗")
            print(f"Please try again with:")
            print(f"  • Full face visible and centered")
            print(f"  • Good lighting (not too dark/bright)")
            print(f"  • Natural blink 1-2 times")
            print(f"  • Head movement (turn or look)")
            print(f"  • Follow challenge instruction\n")

        # Save result
        filename = f"liveness_result_{self.session_id}.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Result saved to: {filename}\n")


if __name__ == "__main__":
    try:
        test = InteractiveLivenessTest()
        test.run()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
