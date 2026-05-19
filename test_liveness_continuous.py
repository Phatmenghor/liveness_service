"""
test_liveness_continuous.py - Continuous Liveness Verification Until 100% PASS

Keeps running until user achieves 100/100 PASS
- Shows live camera continuously
- One challenge at a time
- Real-time feedback
- Progress tracking
- Loops until complete

Run: python test_liveness_continuous.py
"""

import cv2
import numpy as np
import time
import uuid
from datetime import datetime
import json
import requests
import base64
from core.face_detector import FaceDetector
from core.challenge_detector import ChallengeGenerator

API_URL = "http://localhost:5001"


class ContinuousLivenessTest:
    """Continuous liveness test - loops until 100% achieved"""

    def __init__(self):
        self.session_id = f"KYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        self.face_detector = FaceDetector()
        self.attempt = 0
        self.best_score = 0
        self.best_result = None

    def draw_instructions(self, frame):
        """Draw helpful instructions"""
        h, w = frame.shape[:2]

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 200), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.8, frame, 0.2, 0, frame)

        # Title
        cv2.putText(frame, "LIVENESS VERIFICATION TEST", (20, 40),
                    cv2.FONT_HERSHEY_BOLD, 1.2, (0, 255, 0), 2)

        # Instructions
        instructions = [
            "1. Move CLOSER to camera (face should fill 50% of screen)",
            "2. Center your face in frame",
            "3. Good lighting (well-lit face)",
            "4. Keep full face visible (no hands, masks)",
            "5. Follow challenge instructions",
            "Press SPACE to capture 10 seconds"
        ]

        y = 80
        for instr in instructions:
            cv2.putText(frame, instr, (30, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            y += 25

        return frame

    def draw_live_stats(self, frame, face_detected, frame_count, best_score):
        """Draw live stats on frame"""
        h, w = frame.shape[:2]

        # Top bar
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - 100), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Stats
        cv2.putText(frame, f"Best Score: {best_score:.0f}/100", (20, h - 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0) if best_score >= 70 else (0, 0, 255), 2)
        cv2.putText(frame, f"Face: {'✓ YES' if face_detected else '✗ NO'}", (20, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0) if face_detected else (0, 0, 255), 2)
        cv2.putText(frame, f"Frames: {frame_count}", (w - 250, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        return frame

    def capture_and_process(self):
        """Capture frames and send to API"""
        print("\n" + "="*60)
        print(f"ATTEMPT #{self.attempt + 1}".center(60))
        print("="*60)

        frames = []
        frame_count = 0
        start_time = time.time()

        print("\n📷 Capturing 10 seconds of video...")
        print("   Make sure to:")
        print("   • Move closer (face fills more of screen)")
        print("   • Center your face")
        print("   • Good lighting")
        print("   • Follow the challenge\n")

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera!")
            return None

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            elapsed = time.time() - start_time
            frame_count += 1

            # Detect face
            face_summary = self.face_detector.analyse([frame])
            face_detected = face_summary.face_detected

            # Draw instructions/stats
            display_frame = frame.copy()
            if elapsed < 2:  # Show instructions first 2 seconds
                display_frame = self.draw_instructions(display_frame)
            else:
                display_frame = self.draw_live_stats(display_frame, face_detected, frame_count, self.best_score)

            # Challenge text (after 2 seconds)
            if elapsed >= 2:
                h, w = display_frame.shape[:2]
                overlay = display_frame.copy()
                cv2.rectangle(overlay, (w // 4, h // 3), (3 * w // 4, h // 2), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, display_frame, 0.3, 0, display_frame)

                challenge = ChallengeGenerator.generate()
                cv2.putText(display_frame, challenge.description, (w // 4 + 20, h // 2 - 20),
                            cv2.FONT_HERSHEY_BOLD, 1.5, (0, 255, 255), 2)
                cv2.putText(display_frame, challenge.instruction, (w // 4 + 20, h // 2 + 20),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)

            # Progress bar
            progress = (elapsed - 2) / 8.0 if elapsed >= 2 else 0
            progress = min(progress, 1.0)
            bar_width = int(640 * progress)
            cv2.rectangle(display_frame, (0, 479), (bar_width, 479), (0, 255, 0), 3)

            # Show frame
            cv2.imshow("Liveness Test - Keep Going Until 100% (Press Q to quit)", display_frame)

            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
            frames.append(frame_base64)

            # Stop after 10 seconds or Q pressed
            if elapsed >= 10 or cv2.waitKey(1) & 0xFF == ord('q'):
                if elapsed < 10:
                    print("\n⏹️ Stopped early by user")
                break

        cap.release()
        cv2.destroyAllWindows()

        print(f"✓ Captured {frame_count} frames in {elapsed:.1f} seconds")

        # Send to API
        try:
            print("\n🔄 Processing with AI service...")
            response = requests.post(
                f"{API_URL}/liveness/check",
                json={
                    "sessionId": self.session_id,
                    "frames": frames
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API Error: {response.status_code}")
                return None

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None

    def display_results(self, result):
        """Display results"""
        score = result.get('score', 0)
        status = result.get('status', 'FAIL')

        print("\n" + "="*60)
        print(f"ATTEMPT #{self.attempt + 1} RESULTS".center(60))
        print("="*60 + "\n")

        # Score
        if status == 'PASS':
            print(f"✓ STATUS: PASS")
        else:
            print(f"✗ STATUS: FAIL")

        print(f"Score: {score:.1f} / 100")
        print(f"Reason: {result.get('reason', 'N/A')}\n")

        # Breakdown
        result_data = result.get('result', {})
        challenge = result.get('challenge', {})

        print("Breakdown:")
        print(f"  {'✓' if result_data.get('faceDetected') else '✗'} Face Quality (20 pts)")
        print(f"  {'✓' if result_data.get('blinkDetected') else '✗'} Blink Detection (20 pts)")
        print(f"  {'✓' if result_data.get('headMovementDetected') else '✗'} Head Movement (20 pts)")
        print(f"  {'✓' if not result_data.get('spoofDetected') else '✗'} Anti-Spoof (20 pts)")
        if challenge:
            print(f"  {'✓' if challenge.get('completed') else '✗'} Challenge: {challenge.get('description', 'N/A')} (20 pts)")

        # Track best
        if score > self.best_score:
            self.best_score = score
            self.best_result = result
            print(f"\n🎉 New best score: {self.best_score:.0f}/100")

        return score >= 100

    def run(self):
        """Main loop"""
        print(f"\n{'='*60}")
        print(f"CONTINUOUS LIVENESS TEST - Loop Until 100% PASS".center(60))
        print(f"{'='*60}\n")
        print(f"Session ID: {self.session_id}")
        print(f"\nGoal: Achieve 100/100 to pass liveness verification")
        print(f"Instructions will appear on camera\n")

        input("Press ENTER to start...")

        while True:
            self.attempt += 1

            # Capture and process
            result = self.capture_and_process()

            if not result:
                print("\n❌ Failed to process. Try again?\n")
                continue

            # Display results
            passed_100 = self.display_results(result)

            # Check if 100%
            if passed_100:
                self.print_final_success()
                break
            else:
                print(f"\n⏳ Not 100% yet. Best so far: {self.best_score:.0f}/100")
                print(f"Try again - remember to:")
                print(f"  • Move CLOSER to camera (face bigger)")
                print(f"  • Center face vertically")
                print(f"  • Full face visible (mouth clear)")
                print(f"  • Natural blink and movement\n")

                try_again = input("Try again? (y/n): ").strip().lower()
                if try_again != 'y':
                    break

        # Save final result
        if self.best_result:
            filename = f"liveness_result_FINAL_{self.session_id}.json"
            with open(filename, 'w') as f:
                json.dump(self.best_result, f, indent=2)
            print(f"✓ Result saved to: {filename}")

    def print_final_success(self):
        """Print success message"""
        print("\n" + "="*60)
        print("✓ ✓ ✓ 100% LIVENESS VERIFICATION PASSED ✓ ✓ ✓".center(60))
        print("="*60)
        print("\n🎉 CONGRATULATIONS!")
        print("✓ Face quality check passed")
        print("✓ Blink detection passed")
        print("✓ Head movement passed")
        print("✓ Anti-spoof check passed")
        print("✓ Challenge completed\n")
        print("🏦 Your account has been approved for opening!")
        print("Proceeding to document verification...\n")


if __name__ == "__main__":
    try:
        test = ContinuousLivenessTest()
        test.run()
    except KeyboardInterrupt:
        print("\n\n❌ Test cancelled by user")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
