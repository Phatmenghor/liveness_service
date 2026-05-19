"""
test_final_scan.py - Final Simplified Scanner - 4 Core Checks

Only 4 Checks (25 points each):
1. Face Centered - Full face visible, centered
2. Blink - Natural eye blink
3. Movement - Turn left/right OR look up/down (COMBINED)
4. Anti-Spoof - Real person

Run: python test_final_scan.py
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


class FinalFaceScanner:
    """Final simplified scanner - 4 core checks only"""

    def __init__(self):
        self.session_id = f"KYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        self.face_detector = FaceDetector()
        self.blink_detector = BlinkDetector()
        self.movement_detector = MovementDetector()
        self.spoof_detector = SpoofDetector()

        # Progress tracking
        self.frames_buffer = deque(maxlen=60)
        self.max_yaw = 0
        self.max_pitch = 0
        self.progress = {
            'face': 0,        # Face centered (25pts)
            'blink': 0,       # Blink (25pts)
            'movement': 0,    # Movement/Challenge (25pts) - COMBINED
            'spoof': 0        # Anti-Spoof (25pts)
        }
        self.frame_count = 0
        self.start_time = time.time()

    def draw_scanner(self, frame):
        """Draw scanner overlay"""
        h, w = frame.shape[:2]
        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 3

        # Circle
        cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 3)

        # Rectangle
        cv2.rectangle(frame,
                     (center_x - radius, center_y - radius),
                     (center_x + radius, center_y + radius),
                     (0, 255, 0), 2)

        return frame

    def draw_4_progress_bars(self, frame):
        """Draw 4 progress bars (25 points each)"""
        h, w = frame.shape[:2]

        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay, (15, h - 180), (w - 15, h - 10), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        checks = [
            ('1. Face Centered', self.progress['face']),
            ('2. Blink', self.progress['blink']),
            ('3. Turn/Look', self.progress['movement']),
            ('4. Anti-Spoof', self.progress['spoof']),
        ]

        y = h - 160
        for name, progress in checks:
            # Icon
            status_icon = "✓" if progress >= 25 else "○"
            color = (0, 255, 0) if progress >= 25 else (0, 165, 255)

            cv2.putText(frame, f"{status_icon} {name}", (25, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 1)

            # Progress bar
            bar_x = 250
            bar_width = 180
            bar_filled = int((progress / 25) * bar_width)

            cv2.rectangle(frame, (bar_x, y - 12), (bar_x + bar_width, y + 6), (50, 50, 50), 1)
            if bar_filled > 0:
                cv2.rectangle(frame, (bar_x, y - 12), (bar_x + bar_filled, y + 6), color, -1)

            cv2.putText(frame, f"{int(progress)}/25", (bar_x + bar_width + 15, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            y += 35

        # Total
        total = sum(self.progress.values())
        total_color = (0, 255, 0) if total >= 100 else (0, 165, 255)
        cv2.putText(frame, f"TOTAL: {total}/100", (25, y + 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.1, total_color, 2)

        return frame

    def draw_instructions(self, frame):
        """Draw instructions"""
        h, w = frame.shape[:2]

        overlay = frame.copy()
        cv2.rectangle(overlay, (15, 15), (w - 15, 95), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        cv2.putText(frame, "LIVENESS SCAN - 4 CHECKS", (30, 45),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        cv2.putText(frame, "Face Centered | Blink | Turn/Look Left-Right-Up-Down",
                    (30, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)

        return frame

    def check_face_centered(self, face_summary, h, w):
        """Check if face visible and centered"""
        if not face_summary.face_detected:
            return False

        try:
            landmarks = face_summary.per_frame[0].landmarks
            lm_array = np.array([[lm.x, lm.y] for lm in landmarks.landmark])

            # Face size check
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

    def analyze_frame(self, frame):
        """Analyze frame for 4 checks"""
        h, w = frame.shape[:2]

        # 1. Face Centered
        face_summary = self.face_detector.analyse([frame])
        if self.check_face_centered(face_summary, h, w):
            self.progress['face'] = 25
        else:
            self.progress['face'] = 0
            return

        # 2. Blink Detection
        blink_summary = self.blink_detector.analyse(face_summary)
        if blink_summary.blink_detected and blink_summary.blink_count >= 1:
            self.progress['blink'] = 25
        else:
            self.progress['blink'] = 0

        # 3. Movement (Turn/Look) - COMBINED
        # Either turn left/right (15°) OR look up/down (12°)
        movement_summary = self.movement_detector.analyse(face_summary, w, h)
        self.max_yaw = max(abs(movement_summary.max_yaw_deg), self.max_yaw)
        self.max_pitch = max(abs(movement_summary.max_pitch_deg), self.max_pitch)

        if abs(self.max_yaw) >= 15 or abs(self.max_pitch) >= 12:
            self.progress['movement'] = 25
        else:
            self.progress['movement'] = 0

        # 4. Anti-Spoof (automatic)
        spoof_summary = self.spoof_detector.analyse([frame], face_summary)
        if not spoof_summary.spoof_detected:
            self.progress['spoof'] = 25
        else:
            self.progress['spoof'] = 0

        # Store frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
        self.frames_buffer.append(frame_base64)

        self.frame_count += 1

    def run(self):
        """Run scanner"""
        print(f"\n{'='*60}")
        print("FINAL LIVENESS SCAN - 4 Checks (25pts each)".center(60))
        print(f"{'='*60}\n")
        print(f"Session ID: {self.session_id}\n")
        print("4 Core Checks:")
        print("  1. Face Centered (25pts) - Keep full face visible")
        print("  2. Blink (25pts) - Blink naturally")
        print("  3. Turn/Look (25pts) - Turn head OR look up/down")
        print("  4. Anti-Spoof (25pts) - Real person\n")
        print("Keep scanning until all 4 bars are GREEN (100/100)\n")

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

            # Analyze
            self.analyze_frame(frame)

            # Draw overlays
            display_frame = frame.copy()
            display_frame = self.draw_scanner(display_frame)
            display_frame = self.draw_4_progress_bars(display_frame)
            display_frame = self.draw_instructions(display_frame)

            # Show
            cv2.imshow("Liveness Scan - Press Q to quit", display_frame)

            # Check completion
            total = sum(self.progress.values())
            if total >= 100:
                print("\n✓ 100% COMPLETE! Verifying...")
                break

            # Exit on Q
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nScanning cancelled")
                cap.release()
                cv2.destroyAllWindows()
                return

        cap.release()
        cv2.destroyAllWindows()

        # Verify
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
        """Show result"""
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
        scanner = FinalFaceScanner()
        scanner.run()
    except KeyboardInterrupt:
        print("\n\nCancelled")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
