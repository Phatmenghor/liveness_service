"""
test_simple_scan.py - Simplified Face Liveness Scanner

5 Core Checks Only:
1. Face Centered - Full face visible, centered
2. Blink - Natural eye blink
3. Movement - Turn left/right OR look up/down
4. Anti-Spoof - Real person (not photo/video)
5. Challenge - Turn left/right or look up/down

Run: python test_simple_scan.py
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
from core.blink_detector import BlinkDetector
from core.movement_detector import MovementDetector
from core.spoof_detector import SpoofDetector

API_URL = "http://localhost:5001"


class SimpleFaceScanner:
    """Simplified face scanner - 5 core checks only"""

    def __init__(self):
        self.session_id = f"KYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        self.face_detector = FaceDetector()
        self.blink_detector = BlinkDetector()
        self.movement_detector = MovementDetector()
        self.spoof_detector = SpoofDetector()

        # Progress tracking
        self.frames_buffer = deque(maxlen=60)  # Keep last 60 frames
        self.blink_count = 0
        self.movement_detected = False
        self.max_yaw = 0
        self.max_pitch = 0
        self.progress = {
            'face': 0,      # Face centered
            'blink': 0,     # Natural blink
            'movement': 0,  # Head movement
            'spoof': 0,     # Anti-spoof
            'challenge': 0  # Challenge (turn/look)
        }
        self.frame_count = 0
        self.start_time = time.time()

    def draw_simple_scanner(self, frame):
        """Draw simple scanner circle"""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 3

        # Outer circle
        cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 3)

        # Face area indicator
        cv2.rectangle(frame,
                     (center_x - radius, center_y - radius),
                     (center_x + radius, center_y + radius),
                     (0, 255, 0), 2)

        return frame

    def draw_5_progress_bars(self, frame):
        """Draw 5 simple progress bars"""
        h, w = frame.shape[:2]

        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay, (15, h - 210), (w - 15, h - 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        checks = [
            ('1. Face Centered', self.progress['face']),
            ('2. Blink', self.progress['blink']),
            ('3. Movement', self.progress['movement']),
            ('4. Anti-Spoof', self.progress['spoof']),
            ('5. Challenge', self.progress['challenge']),
        ]

        y = h - 190
        for name, progress in checks:
            # Icon
            status_icon = "✓" if progress >= 20 else "○"
            color = (0, 255, 0) if progress >= 20 else (0, 165, 255)

            cv2.putText(frame, f"{status_icon} {name}", (25, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 1)

            # Progress bar
            bar_x = 250
            bar_width = 180
            bar_filled = int((progress / 20) * bar_width)

            cv2.rectangle(frame, (bar_x, y - 12), (bar_x + bar_width, y + 6), (50, 50, 50), 1)
            if bar_filled > 0:
                cv2.rectangle(frame, (bar_x, y - 12), (bar_x + bar_filled, y + 6), color, -1)

            cv2.putText(frame, f"{int(progress)}/20", (bar_x + bar_width + 15, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            y += 35

        # Total
        total = sum(self.progress.values())
        total_color = (0, 255, 0) if total >= 100 else (0, 165, 255)
        cv2.putText(frame, f"TOTAL: {total}/100", (25, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, total_color, 2)

        return frame

    def draw_instructions(self, frame):
        """Draw simple instructions"""
        h, w = frame.shape[:2]

        overlay = frame.copy()
        cv2.rectangle(overlay, (15, 15), (w - 15, 100), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        cv2.putText(frame, "FACE LIVENESS SCAN", (30, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        instructions = [
            "Face Center | Blink | Turn Head Left/Right OR Look Up/Down"
        ]

        cv2.putText(frame, instructions[0], (30, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)

        return frame

    def check_face_centered(self, face_summary, h, w):
        """Check if face is visible and roughly centered"""
        if not face_summary.face_detected:
            return False

        try:
            landmarks = face_summary.per_frame[0].landmarks
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Face size check (simplified - just check visible)
            x_min, x_max = lm_array[:, 0].min(), lm_array[:, 0].max()
            y_min, y_max = lm_array[:, 1].min(), lm_array[:, 1].max()

            face_width = (x_max - x_min)
            face_height = (y_max - y_min)

            # Must be at least 15% of frame (simplified from 20%)
            if face_width < 0.15 or face_height < 0.15:
                return False

            # Must be roughly centered (±30% tolerance, simplified from ±20%)
            center_x = (x_max + x_min) / 2
            center_y = (y_max + y_min) / 2

            if abs(center_x - 0.5) > 0.3 or abs(center_y - 0.5) > 0.3:
                return False

            return True
        except:
            return False

    def analyze_frame(self, frame):
        """Analyze frame for 5 checks"""
        h, w = frame.shape[:2]

        # 1. Face Centered
        face_summary = self.face_detector.analyse([frame])
        if self.check_face_centered(face_summary, h, w):
            self.progress['face'] = 20
        else:
            self.progress['face'] = 0

        if not face_summary.face_detected:
            # Clear other progress if no face
            self.progress['blink'] = 0
            self.progress['movement'] = 0
            self.progress['spoof'] = 0
            self.progress['challenge'] = 0
            return

        # 2. Blink Detection
        blink_summary = self.blink_detector.analyse(face_summary)
        if blink_summary.blink_detected and blink_summary.blink_count >= 1:
            self.blink_count = blink_summary.blink_count
            self.progress['blink'] = 20
        else:
            self.progress['blink'] = 0

        # 3. Movement Detection (left/right/up/down)
        movement_summary = self.movement_detector.analyse(face_summary, w, h)
        self.max_yaw = max(abs(movement_summary.max_yaw_deg), self.max_yaw)
        self.max_pitch = max(abs(movement_summary.max_pitch_deg), self.max_pitch)

        # Either left/right turn (15°) OR up/down look (12°)
        if (abs(self.max_yaw) >= 15 or abs(self.max_pitch) >= 12):
            self.movement_detected = True
            self.progress['movement'] = 20
        else:
            self.progress['movement'] = 0

        # 4. Anti-Spoof (automatic)
        spoof_summary = self.spoof_detector.analyse([frame], face_summary)
        if not spoof_summary.spoof_detected:
            self.progress['spoof'] = 20
        else:
            self.progress['spoof'] = 0

        # 5. Challenge = Same as Movement (turn/look)
        # Only accept turn left/right or look up/down challenges
        if self.progress['movement'] == 20:
            self.progress['challenge'] = 20
        else:
            self.progress['challenge'] = 0

        # Store frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
        self.frames_buffer.append(frame_base64)

        self.frame_count += 1

    def run(self):
        """Run scanner"""
        print(f"\n{'='*60}")
        print("SIMPLIFIED LIVENESS SCAN - 5 Checks Only".center(60))
        print(f"{'='*60}\n")
        print(f"Session ID: {self.session_id}\n")
        print("5 Simple Checks:")
        print("  1. Face Centered - Keep full face visible")
        print("  2. Blink - Blink naturally")
        print("  3. Movement - Turn head left/right OR look up/down")
        print("  4. Anti-Spoof - Real person (automatic)")
        print("  5. Challenge - Turn/Look (same as #3)\n")
        print("Keep scanning until all 5 bars are GREEN (100/100)\n")

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera!")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.start_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Analyze frame
            self.analyze_frame(frame)

            # Draw overlays
            display_frame = frame.copy()
            display_frame = self.draw_simple_scanner(display_frame)
            display_frame = self.draw_5_progress_bars(display_frame)
            display_frame = self.draw_instructions(display_frame)

            # Show frame
            cv2.imshow("Simple Face Scan - Press Q to quit", display_frame)

            # Check if 100% achieved
            total = sum(self.progress.values())
            if total >= 100:
                print("\n✓ 100% Achieved! Verifying...")
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
        self.final_verification()

    def final_verification(self):
        """Send frames for final verification"""
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
            print("✓ ✓ ✓ LIVENESS VERIFIED ✓ ✓ ✓".center(60))
            print("="*60)
            print("\n🎉 Account Approved!")
            print("✓ Face verified")
            print("✓ Live person confirmed")
            print("✓ Ready for account opening\n")
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
        scanner = SimpleFaceScanner()
        scanner.run()
    except KeyboardInterrupt:
        print("\n\nCancelled")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
