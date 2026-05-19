"""
test_liveness_full.py - Complete Bank Liveness Verification Test

Simulates a real user going through:
1. Account opening request
2. Liveness verification
3. Challenge-based checks
4. Progress tracking (0-100%)
5. Final PASS/FAIL result with scoring

Run: python test_liveness_full.py
"""

import cv2
import numpy as np
import time
import uuid
from datetime import datetime
import json

# For API calls
import requests

API_URL = "http://localhost:5000"

class Colors:
    """Terminal colors"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{text.center(60)}")
    print(f"{'='*60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_progress_bar(percentage, label=""):
    """Print visual progress bar"""
    filled = int(percentage / 5)
    bar = "█" * filled + "░" * (20 - filled)
    print(f"{Colors.OKBLUE}{label:20} [{bar}] {percentage:3d}% {Colors.ENDC}")


def capture_frames_from_camera(duration_seconds=10, fps=10):
    """
    Capture frames from camera for liveness check

    Args:
        duration_seconds: How long to capture
        fps: Frames per second

    Returns:
        List of base64 encoded frames
    """
    print_info(f"Opening camera for {duration_seconds} seconds...")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print_error("Cannot open camera!")
        return []

    # Set resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    frames_base64 = []
    frame_count = 0
    start_time = time.time()

    print(f"\n{Colors.WARNING}CAMERA INSTRUCTIONS:{Colors.ENDC}")
    print("1. Look directly at camera")
    print("2. Keep full face visible")
    print("3. Good lighting required")
    print("4. Follow challenge instructions")
    print(f"\nCapturing... {Colors.BOLD}", end="", flush=True)

    while time.time() - start_time < duration_seconds:
        ret, frame = cap.read()
        if not ret:
            break

        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_base64 = f"data:image/jpeg;base64,{buffer.tobytes().hex()}"

        # Actually use proper base64 encoding
        import base64
        frame_base64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode()}"
        frames_base64.append(frame_base64)

        frame_count += 1
        if frame_count % 5 == 0:
            print("●", end="", flush=True)

        # Control FPS
        time.sleep(1.0 / fps)

    print(f" {Colors.ENDC}")
    cap.release()

    print_success(f"Captured {frame_count} frames")
    return frames_base64


def send_liveness_check(session_id, frames):
    """
    Send frames to liveness service API

    Args:
        session_id: Unique session identifier
        frames: List of base64 encoded frames

    Returns:
        Response JSON or None if failed
    """
    print_info("Sending frames to liveness service...")

    try:
        response = requests.post(
            f"{API_URL}/liveness/check",
            json={
                "sessionId": session_id,
                "frames": frames
            },
            timeout=30
        )

        if response.status_code == 200:
            print_success(f"API Response: {response.status_code} OK")
            return response.json()
        else:
            print_error(f"API Error: {response.status_code}")
            print(response.text)
            return None

    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API! Is the server running?")
        print_info(f"Try: cd liveness_service && python app.py")
        return None
    except Exception as e:
        print_error(f"API Error: {str(e)}")
        return None


def display_result(result):
    """Display liveness check result"""
    if not result:
        return

    status = result.get('status', 'UNKNOWN')
    score = result.get('score', 0)
    reason = result.get('reason', 'No reason provided')

    # Main status
    if status == 'PASS':
        print_header(f"{Colors.OKGREEN}{Colors.BOLD}✓ LIVENESS VERIFIED - PASS{Colors.ENDC}")
    else:
        print_header(f"{Colors.FAIL}{Colors.BOLD}✗ LIVENESS FAILED{Colors.ENDC}")

    # Score
    print(f"\n{Colors.BOLD}Score: {Colors.OKBLUE}{score:.1f}{Colors.ENDC} / 100")

    if score >= 70:
        print(f"{Colors.OKGREEN}Status: PASS ✓{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}Status: FAIL ✗ (Need 70+){Colors.ENDC}")

    # Reason
    print(f"\nReason: {reason}\n")

    # Breakdown
    result_data = result.get('result', {})
    print(f"{Colors.BOLD}Breakdown:{Colors.ENDC}")

    checks = [
        ('Face Detected', result_data.get('faceDetected'), 20),
        ('Blink Detected', result_data.get('blinkDetected'), 20),
        ('Head Movement', result_data.get('headMovementDetected'), 20),
        ('Anti-Spoof', not result_data.get('spoofDetected'), 20),
    ]

    for check_name, passed, points in checks:
        if passed:
            print_success(f"{check_name} → +{points} pts")
        else:
            print_error(f"{check_name} → +0 pts")

    # Challenge
    challenge = result.get('challenge')
    if challenge:
        print(f"\n{Colors.BOLD}Challenge:{Colors.ENDC}")
        print(f"  Type: {challenge.get('type', 'unknown')}")
        print(f"  Description: {challenge.get('description', 'N/A')}")

        if challenge.get('completed'):
            print_success(f"Completed → +20 pts")
        else:
            print_error(f"Not completed → +0 pts")
            if challenge.get('reason'):
                print(f"  Reason: {challenge.get('reason')}")

    # Processing time
    processing_time = result.get('processingTimeSeconds', 0)
    print(f"\n{Colors.BOLD}Processing Time:{Colors.ENDC} {processing_time:.2f} seconds")


def display_progress_breakdown(result):
    """Display visual progress breakdown"""
    print(f"\n{Colors.BOLD}{'='*60}")
    print(f"PROGRESS BREAKDOWN (0-100%)".center(60))
    print(f"{'='*60}{Colors.ENDC}\n")

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
    for check_name, passed, points in checks:
        if passed:
            total += points
            print_progress_bar(points, f"{Colors.OKGREEN}✓ {check_name:<15}{Colors.ENDC}")
        else:
            print_progress_bar(0, f"{Colors.FAIL}✗ {check_name:<15}{Colors.ENDC}")

    print(f"\n{Colors.BOLD}Total Progress:{Colors.ENDC}")
    print_progress_bar(total, "OVERALL")

    print(f"\n{Colors.BOLD}Final Score: {total}/100{Colors.ENDC}")
    if total >= 70:
        print_success(f"PASS (need 70+)")
    else:
        print_error(f"FAIL (need 70+)")


def test_health_check():
    """Test if API is running"""
    print_header("HEALTH CHECK")

    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("API is running!")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to API!")
        print_info("Make sure to run: python app.py")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False


def main():
    """Main test flow"""

    print(f"\n{Colors.HEADER}{Colors.BOLD}")
    print("╔" + "="*58 + "╗")
    print("║" + "BANK ACCOUNT OPENING - LIVENESS VERIFICATION TEST".center(58) + "║")
    print("╚" + "="*58 + "╝")
    print(f"{Colors.ENDC}\n")

    # Generate session ID
    session_id = f"KYC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
    print_info(f"Session ID: {session_id}\n")

    # Step 1: Health Check
    print_header("STEP 1: Verifying API Connection")
    if not test_health_check():
        print_error("Cannot proceed without API connection!")
        return

    # Step 2: Capture Frames
    print_header("STEP 2: Face Liveness Capture")
    print_info("You will be recorded for 10 seconds")
    print_info("Requirements:")
    print("  • Full face visible")
    print("  • Good lighting")
    print("  • Face centered in frame")
    print("  • Natural blink 1-2 times")
    print("  • Turn head left/right")
    print("  • Follow challenge instructions")

    input(f"\n{Colors.WARNING}Press ENTER to start camera...{Colors.ENDC}")

    frames = capture_frames_from_camera(duration_seconds=10, fps=10)

    if not frames:
        print_error("Failed to capture frames!")
        return

    # Step 3: Send to API
    print_header("STEP 3: Liveness Processing")
    result = send_liveness_check(session_id, frames)

    if not result:
        print_error("Failed to process liveness check!")
        return

    # Step 4: Display Results
    print_header("STEP 4: Verification Results")
    display_result(result)

    # Step 5: Show Progress
    print_header("STEP 5: Progress Summary")
    display_progress_breakdown(result)

    # Step 6: Account Status
    print_header("STEP 6: Account Opening Status")

    status = result.get('status')
    score = result.get('score', 0)

    if status == 'PASS' and score >= 70:
        print_success("✓ LIVENESS VERIFICATION PASSED")
        print_success("✓ Face quality check passed")
        print_success("✓ Anti-spoof validation passed")
        print_success("✓ Challenge completed")
        print_success("\nYour account has been approved for opening!")
        print_info("Proceeding to KYC document verification...")
    else:
        print_error("✗ LIVENESS VERIFICATION FAILED")
        print_error(f"Score: {score:.1f}/100 (need 70+)")
        print_error("\nPlease try again:")
        print("  • Ensure full face is visible")
        print("  • Good lighting (not too dark/bright)")
        print("  • Face centered in frame")
        print("  • Complete all required actions")

    # Step 7: Save Results
    print_header("STEP 7: Saving Verification Record")

    record = {
        'timestamp': datetime.now().isoformat(),
        'sessionId': session_id,
        'status': result.get('status'),
        'score': result.get('score'),
        'result': result.get('result'),
        'challenge': result.get('challenge'),
        'reason': result.get('reason'),
        'processingTime': result.get('processingTimeSeconds'),
    }

    # Save to file
    filename = f"liveness_result_{session_id}.json"
    with open(filename, 'w') as f:
        json.dump(record, f, indent=2)

    print_success(f"Result saved to: {filename}")

    # Final summary
    print_header("VERIFICATION COMPLETE")
    print(f"\n{Colors.BOLD}Summary:{Colors.ENDC}")
    print(f"  Session ID: {session_id}")
    print(f"  Status: {Colors.OKGREEN if status == 'PASS' else Colors.FAIL}{status}{Colors.ENDC}")
    print(f"  Score: {score:.1f}/100")
    print(f"  Time: {result.get('processingTimeSeconds', 0):.2f}s")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Test cancelled by user{Colors.ENDC}")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
