"""
test_liveness_live_scan.py - Live Continuous Face Scanner (Like iPhone Face ID)

Continuous scanning until 100% achieved
- Real-time feedback
- No restarts needed
- Live progress tracking
- Show what's wrong in real-time

Run: python test_liveness_live_scan.py
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
from core.face_quality_checker import FaceQualityChecker
from core.challenge_detector import ChallengeGenerator, ChallengeValidator

API_URL = "http://localhost:5001"


class LiveFaceScanner:
    """Live continuous face scanner - like iPhone Face ID"""

    def __init__(self):
        self.session_id = f"KYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        self.face_detector = FaceDetector()
        self.blink_detector = BlinkDetector()
        self.movement_detector = MovementDetector()
        self.spoof_detector = SpoofDetector()
        self.quality_checker = FaceQualityChecker()
        self.challenge_validator = ChallengeValidator()

        # Tracking
        self.frames_buffer = deque(maxlen=30)  # Keep last 30 frames for analysis
        self.face_detected_count = 0
        self.blink_count = 0
        self.movement_detected = False
        self.quality_pass_count = 0
        self.challenge = ChallengeGenerator.generate()
        self.progress = {'face': 0, 'blink': 0, 'movement': 0, 'spoof': 0, 'challenge': 0}
        self.issues = []
        self.best_score = 0
        self.frame_count = 0
        self.start_time = time.time()

    def draw_scanner_overlay(self, frame, progress_percent):
        """Draw iPhone-like scanner overlay"""
        h, w = frame.shape[:2]

        # Animated scanner circle
        center_x, center_y = w // 2, h // 2
        radius = min(w, h) // 3

        # Outer circle (static)
        cv2.circle(frame, (center_x, center_y), radius, (0, 255, 0), 2)

        # Animated scanning line
        elapsed = time.time() - self.start_time
        scan_progress = (elapsed % 2.0) / 2.0  # 0-1 repeating
        scan_y = center_y - radius + int((2 * radius) * scan_progress)
        cv2.line(frame, (center_x - radius, scan_y), (center_x + radius, scan_y), (0, 255, 0), 2)

        # Corner brackets
        bracket_len = 30
        corners = [
            (center_x - radius, center_y - radius),
            (center_x + radius, center_y - radius),
            (center_x - radius, center_y + radius),
            (center_x + radius, center_y + radius),
        ]

        for corner in corners:
            if corner == corners[0]:  # Top-left
                cv2.line(frame, corner, (corner[0] + bracket_len, corner[1]), (0, 255, 0), 3)
                cv2.line(frame, corner, (corner[0], corner[1] + bracket_len), (0, 255, 0), 3)
            elif corner == corners[1]:  # Top-right
                cv2.line(frame, corner, (corner[0] - bracket_len, corner[1]), (0, 255, 0), 3)
                cv2.line(frame, corner, (corner[0], corner[1] + bracket_len), (0, 255, 0), 3)
            elif corner == corners[2]:  # Bottom-left
                cv2.line(frame, corner, (corner[0] + bracket_len, corner[1]), (0, 255, 0), 3)
                cv2.line(frame, corner, (corner[0], corner[1] - bracket_len), (0, 255, 0), 3)
            elif corner == corners[3]:  # Bottom-right
                cv2.line(frame, corner, (corner[0] - bracket_len, corner[1]), (0, 255, 0), 3)
                cv2.line(frame, corner, (corner[0], corner[1] - bracket_len), (0, 255, 0), 3)

        return frame

    def draw_progress_bars(self, frame):
        """Draw real-time progress bars"""
        h, w = frame.shape[:2]

        # Background panel
        overlay = frame.copy()
        cv2.rectangle(overlay, (20, h - 200), (w - 20, h - 20), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        checks = [
            ('Face Quality', self.progress['face']),
            ('Blink', self.progress['blink']),
            ('Movement', self.progress['movement']),
            ('Anti-Spoof', self.progress['spoof']),
            ('Challenge', self.progress['challenge']),
        ]

        y = h - 180
        for name, progress in checks:
            # Check mark or X
            status_icon = "✓" if progress >= 20 else "○"
            color = (0, 255, 0) if progress >= 20 else (0, 150, 255)

            cv2.putText(frame, f"{status_icon} {name}:", (30, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)

            # Progress bar
            bar_x = 220
            bar_width = 200
            bar_h = 20
            bar_filled = int((progress / 20) * bar_width)

            cv2.rectangle(frame, (bar_x, y - 15), (bar_x + bar_width, y + 5), (100, 100, 100), 1)
            cv2.rectangle(frame, (bar_x, y - 15), (bar_x + bar_filled, y + 5), color, -1)

            cv2.putText(frame, f"{int(progress)}/20", (bar_x + bar_width + 20, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

            y += 35

        # Total score
        total = sum(self.progress.values())
        cv2.putText(frame, f"Total: {total}/100", (30, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        return frame

    def draw_instructions(self, frame):
        """Draw instructions based on what's wrong"""
        h, w = frame.shape[:2]

        overlay = frame.copy()
        cv2.rectangle(overlay, (20, 20), (w - 20, 120), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        cv2.putText(frame, "LIVENESS FACE SCAN", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

        # Show challenge
        cv2.putText(frame, f"Challenge: {self.challenge.description}", (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 1)

        # Show current issue
        if self.issues and len(self.issues) > 0:
            issue = self.issues[0]  # Show most recent issue
            cv2.putText(frame, f"Note: {issue}", (30, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

        return frame

    def analyze_frame(self, frame):
        """Analyze single frame for all checks"""
        # Face detection
        face_summary = self.face_detector.analyse([frame])

        if not face_summary.face_detected:
            self.issues = ["Face not detected - move closer or adjust position"]
            return

        self.face_detected_count += 1

        # Quality check
        h, w = frame.shape[:2]
        quality_result = self.quality_checker.check_frame_quality(
            frame,
            face_summary.per_frame[0].landmarks,
            w,
            h
        )

        if quality_result.passes_quality:
            self.quality_pass_count += 1
            self.progress['face'] = 20
            self.issues = []
        else:
            self.progress['face'] = 0
            self.issues = quality_result.failures[:2]  # Show top 2 issues

        # Blink detection
        blink_summary = self.blink_detector.analyse(face_summary)
        if blink_summary.blink_detected:
            self.blink_count = blink_summary.blink_count
            self.progress['blink'] = min(20, self.blink_count * 10)
        else:
            self.progress['blink'] = 0

        if self.progress['blink'] == 0 and not self.issues:
            self.issues = ["Waiting for blink - blink naturally"]

        # Movement detection
        movement_summary = self.movement_detector.analyse(face_summary, w, h)
        if movement_summary.head_movement_detected:
            self.movement_detected = True
            self.progress['movement'] = 20
        else:
            self.progress['movement'] = 0

        if self.progress['movement'] == 0 and not self.issues:
            self.issues = ["Move your head - turn left/right or look up/down"]

        # Anti-spoof
        spoof_summary = self.spoof_detector.analyse([frame], face_summary)
        if not spoof_summary.spoof_detected:
            self.progress['spoof'] = 20
        else:
            self.progress['spoof'] = 0

        # Challenge
        challenge_result = self.challenge_validator.validate_challenge(
            self.challenge.challenge_type,
            blink_count=self.blink_count,
            max_yaw=movement_summary.max_yaw_deg,
            max_pitch=movement_summary.max_pitch_deg,
        )

        if challenge_result.completed:
            self.progress['challenge'] = 20
        else:
            self.progress['challenge'] = 0

        # Store frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
        self.frames_buffer.append(frame_base64)

        self.frame_count += 1

    def run(self):
        """Run live scanner"""
        print(f"\n{'='*60}")
        print("LIVE FACE SCAN - iPhone Style".center(60))
        print(f"{'='*60}\n")
        print(f"Session ID: {self.session_id}")
        print(f"Challenge: {self.challenge.description}")
        print(f"Instruction: {self.challenge.instruction}\n")
        print("Opening live scanner...")
        print("Keep scanning until all bars reach 100%\n")

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
            display_frame = self.draw_scanner_overlay(display_frame, sum(self.progress.values()) / 100)
            display_frame = self.draw_progress_bars(display_frame)
            display_frame = self.draw_instructions(display_frame)

            # Show frame
            cv2.imshow("Face ID Liveness Scan - Press Q to quit", display_frame)

            # Check if 100% achieved
            total_progress = sum(self.progress.values())
            if total_progress >= 100:
                print("\n✓ 100% Achieved! Processing final verification...")
                break

            # Exit on Q
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("\nScanning cancelled")
                cap.release()
                cv2.destroyAllWindows()
                return

        cap.release()
        cv2.destroyAllWindows()

        # Send all frames to API
        self.send_for_final_verification()

    def send_for_final_verification(self):
        """Send all captured frames for final verification"""
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
                self.display_final_result(result)
            else:
                print(f"❌ API Error: {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {str(e)}")

    def display_final_result(self, result):
        """Display final result"""
        score = result.get('score', 0)
        status = result.get('status', 'FAIL')

        print(f"\nScore: {score:.1f} / 100")
        print(f"Status: {status}")
        print(f"Reason: {result.get('reason', 'N/A')}\n")

        if status == 'PASS' and score >= 70:
            print("="*60)
            print("✓ ✓ ✓ LIVENESS VERIFICATION PASSED ✓ ✓ ✓".center(60))
            print("="*60)
            print("\n🎉 CONGRATULATIONS!")
            print("✓ Face quality verified")
            print("✓ Live person confirmed")
            print("✓ Anti-spoof passed")
            print("\n🏦 Account approved for opening!")
        else:
            print("="*60)
            print("✗ ✗ ✗ VERIFICATION FAILED ✗ ✗ ✗".center(60))
            print("="*60)

        # Save result
        filename = f"liveness_result_{self.session_id}.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Result saved to: {filename}")


if __name__ == "__main__":
    try:
        scanner = LiveFaceScanner()
        scanner.run()
    except KeyboardInterrupt:
        print("\n\nScanning cancelled by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
