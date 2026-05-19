# Liveness Detection Microservice — CPBank KYC

> **Production-ready Python AI microservice** for bank-grade face liveness verification.  
> Stack: **Flask · MediaPipe FaceMesh · OpenCV · NumPy · Gunicorn**

---

## Project Structure

```
liveness_service/
│
├── local_test.py               ← LOCAL CAMERA TEST (run first!)
├── app.py                      ← Flask entry point (prod API)
├── config.py                   ← All thresholds & settings
├── requirements.txt
├── .gitignore
│
├── controllers/
│   └── liveness_controller.py  ← HTTP routing only, no AI logic
│
├── services/
│   └── liveness_service.py     ← AI orchestration + scoring
│
├── core/
│   ├── face_detector.py        ← MediaPipe FaceMesh detection
│   ├── blink_detector.py       ← EAR-based blink counting
│   ├── movement_detector.py    ← solvePnP head-pose estimation
│   └── spoof_detector.py       ← Pixel variance anti-spoof
│
├── utils/
│   ├── logger.py               ← Rotating audit logger
│   ├── video_utils.py          ← Frame extraction (video/base64)
│   └── response_builder.py     ← Standardised JSON responses
│
└── logs/
    └── app.log                 ← Auto-created at runtime
```

---

## Scoring Model

| Check             | Points |
|-------------------|--------|
| Face detected     | +30    |
| Blink detected    | +25    |
| Head movement     | +25    |
| Anti-spoof passed | +20    |
| **Total**         | **100** |

**PASS** → score ≥ 70  
**FAIL** → score < 70

---

## Step-by-Step Setup & Run Guide

### Step 1 — Create the project folder (if starting fresh)

```powershell
# Windows PowerShell
mkdir liveness_service
cd liveness_service
```

### Step 2 — Create & activate a virtual environment

```powershell
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

> Make sure you are using **Python 3.10, 3.11, or 3.12** (64-bit).  
> MediaPipe does **not** support 3.13+ yet.

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

> **Why `opencv-python` and not `opencv-python-headless`?**  
> `local_test.py` uses `cv2.imshow()` to display the live camera window.  
> The headless build strips that GUI module out. For production servers  
> with no display, you can swap back to `opencv-python-headless`.

### Step 4 — Run LOCAL CAMERA TEST (development / QA)

```powershell
python local_test.py
```

**Options:**

```
--camera IDX     Webcam index (default: 0)
--width  PX      Capture width  (default: 640)
--height PX      Capture height (default: 480)
--skip   N       Run MediaPipe every N frames (default: 1)
--no-window      Suppress GUI window (log only)
```

**Examples:**

```powershell
python local_test.py                      # default webcam
python local_test.py --camera 1           # second webcam
python local_test.py --skip 2             # faster — every 2nd frame
python local_test.py --no-window          # headless / CI mode
python local_test.py --width 1280 --height 720
```

Press **Q** in the camera window to stop and see the final summary.

### Step 5 — Run the API server (development)

```powershell
python app.py
```

Server starts at `http://localhost:5000`.

### Step 6 — Run with debug mode (verbose logs + debug payload)

```powershell
# Windows PowerShell
$env:DEBUG_MODE="true"; python app.py

# macOS / Linux
DEBUG_MODE=true python app.py
```

### Step 7 — Production server (Gunicorn — Linux/macOS)

```bash
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

> Recommended: **2 workers** (MediaPipe is memory-heavy; scale with caution).  
> On Windows, run the Flask dev server or use Waitress: `pip install waitress`
> ```powershell
> python -c "from waitress import serve; from app import app; serve(app, host='0.0.0.0', port=5000)"
> ```

---

## API Reference

### `GET /health`

```bash
curl http://localhost:5000/health
```

**Response `200 OK`:**
```json
{
  "status": "running",
  "service": "liveness-ai"
}
```

---

### `POST /liveness/check` — Video file upload

```bash
curl -X POST http://localhost:5000/liveness/check \
  -F "sessionId=KYC-SESSION-001" \
  -F "video=@/path/to/face_video.mp4"
```

**PowerShell (Invoke-RestMethod):**

```powershell
$form = @{
    sessionId = "KYC-SESSION-001"
    video     = Get-Item "C:\path\to\face_video.mp4"
}
Invoke-RestMethod -Uri "http://localhost:5000/liveness/check" `
                  -Method Post -Form $form
```

**Accepted formats:** `.mp4` `.avi` `.mov` `.webm` `.mkv`  
**Max duration:** 15 seconds

---

### `POST /liveness/check` — Base64 frames (JSON)

Ideal for Next.js frontend capturing webcam frames via `canvas.toDataURL()`.

```bash
curl -X POST http://localhost:5000/liveness/check \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "KYC-SESSION-002",
    "frames": [
      "data:image/jpeg;base64,/9j/4AAQSkZJRgAB...",
      "data:image/jpeg;base64,/9j/4AAQSkZJRgAB...",
      "data:image/jpeg;base64,/9j/4AAQSkZJRgAB..."
    ]
  }'
```

---

### Response Schema

**PASS response:**
```json
{
  "sessionId": "KYC-SESSION-001",
  "status": "PASS",
  "score": 80.0,
  "result": {
    "faceDetected": true,
    "blinkDetected": true,
    "headMovementDetected": true,
    "spoofDetected": false
  },
  "reason": "Liveness verified.",
  "processingTimeSeconds": 1.842
}
```

**FAIL response (low score):**
```json
{
  "sessionId": "KYC-SESSION-003",
  "status": "FAIL",
  "score": 55.0,
  "result": {
    "faceDetected": true,
    "blinkDetected": false,
    "headMovementDetected": true,
    "spoofDetected": false
  },
  "reason": "No blink detected (count=0).",
  "processingTimeSeconds": 2.103
}
```

**Error response:**
```json
{
  "sessionId": "KYC-SESSION-004",
  "status": "FAIL",
  "score": 0,
  "result": {
    "faceDetected": false,
    "blinkDetected": false,
    "headMovementDetected": false,
    "spoofDetected": true
  },
  "errorCode": "MISSING_VIDEO",
  "reason": "No 'video' field found in multipart request."
}
```

| `status` | Meaning |
|----------|---------|
| `PASS`   | score ≥ 70 — user is live |
| `FAIL`   | score < 70 — liveness not confirmed |

---

## Sample Log Output

### Terminal (local_test.py)

```
[INFO]  2026-05-19 14:30:00 | ============================================================
[INFO]  2026-05-19 14:30:00 | CPBank Liveness — LOCAL CAMERA TEST MODE
[INFO]  2026-05-19 14:30:00 | Camera index : 0
[INFO]  2026-05-19 14:30:00 | Resolution   : 640x480
[INFO]  2026-05-19 14:30:00 | Frame skip   : every 1 frame(s)
[INFO]  2026-05-19 14:30:00 | EAR threshold: 0.22
[INFO]  2026-05-19 14:30:00 | Press  Q  to stop
[INFO]  2026-05-19 14:30:00 | ============================================================
[INFO]  2026-05-19 14:30:00 | Camera opened — actual resolution: 640x480
[DEBUG] 2026-05-19 14:30:01 | frame=00001 | face=TRUE  | EAR=0.312 | eye=open   | blinks=0 | rate=100.0% | fps=28.4
[DEBUG] 2026-05-19 14:30:01 | frame=00002 | face=TRUE  | EAR=0.298 | eye=open   | blinks=0 | rate=100.0% | fps=29.1
[DEBUG] 2026-05-19 14:30:02 | frame=00031 | face=TRUE  | EAR=0.189 | eye=CLOSED | blinks=0 | rate=100.0% | fps=28.7
[DEBUG] 2026-05-19 14:30:02 | frame=00033 | face=TRUE  | EAR=0.305 | eye=open   | blinks=1 | rate=100.0% | fps=28.9
[DEBUG] 2026-05-19 14:30:05 | frame=00120 | face=FALSE | rate=91.7% | fps=28.5

[INFO]  2026-05-19 14:30:10 | ============================================================
[INFO]  2026-05-19 14:30:10 | FINAL SUMMARY
[INFO]  2026-05-19 14:30:10 | ============================================================
[INFO]  2026-05-19 14:30:10 | Total frames captured  : 284
[INFO]  2026-05-19 14:30:10 | Frames processed (AI)  : 284
[INFO]  2026-05-19 14:30:10 | Face detected          : 261 frames
[INFO]  2026-05-19 14:30:10 | No face                : 23 frames
[INFO]  2026-05-19 14:30:10 | Detection rate         : 91.9%
[INFO]  2026-05-19 14:30:10 | Blinks detected        : 3
[INFO]  2026-05-19 14:30:10 | Average EAR            : 0.2980  (threshold=0.22)
[INFO]  2026-05-19 14:30:10 | Total execution time   : 10.02s
[INFO]  2026-05-19 14:30:10 | Average FPS            : 28.3
[INFO]  2026-05-19 14:30:10 | ============================================================
[INFO]  2026-05-19 14:30:10 | Quick score (face+blink): 55
[INFO]  2026-05-19 14:30:10 | Quick verdict           : FAIL (partial — no movement/spoof check in local mode)
```

### API Audit Log (logs/app.log)

```
[INFO]  2026-05-19 14:31:01 | session=KYC-001 | input=video  | score=80.0 | result=PASS | time=1.842s
[INFO]  2026-05-19 14:31:45 | session=KYC-002 | input=frames | score=75.0 | result=PASS | time=0.973s
[WARNING] 2026-05-19 14:32:10 | session=KYC-003 | input=video  | score=55.0 | result=FAIL | time=2.103s
[WARNING] 2026-05-19 14:32:55 | session=KYC-004 | input=frames | score=30.0 | result=FAIL | time=0.521s
[INFO]  2026-05-19 14:33:20 | method=POST path=/liveness/check status=200 time=1.845s
[INFO]  2026-05-19 14:33:20 | method=GET  path=/health        status=200 time=0.001s
```

---

## Configuration Reference (`config.py`)

All values can be tuned **without code changes**.

| Key | Default | Description |
|-----|---------|-------------|
| `DEBUG_MODE` | `false` | Verbose debug logs + debug JSON payload |
| `PASS_THRESHOLD` | `70` | Min score to pass |
| `FRAME_SKIP` | `3` | Process every Nth frame (API mode) |
| `MAX_VIDEO_DURATION_SEC` | `15` | Hard cap on video length |
| `MIN_FRAMES_REQUIRED` | `5` | Reject if fewer frames extracted |
| `FACE_DETECTION_CONFIDENCE` | `0.6` | MediaPipe min_detection_confidence |
| `EAR_THRESHOLD` | `0.22` | Eye aspect ratio blink trigger |
| `MIN_BLINKS_REQUIRED` | `1` | Blinks needed to score blink points |
| `YAW_THRESHOLD` | `8.0°` | Horizontal head movement trigger |
| `PITCH_THRESHOLD` | `6.0°` | Vertical head movement trigger |
| `MIN_FRAME_VARIANCE` | `50.0` | Anti-spoof pixel motion floor |
| `SPOOF_STABLE_FRAME_RATIO` | `0.85` | Max ratio of static frames allowed |
| `SESSION_TTL_SECONDS` | `300` | In-memory session expiry (5 min) |

---

## Anti-Spoof Logic (MVP)

Four heuristic checks — **all must pass**:

| Check | What it catches |
|-------|----------------|
| Inter-frame pixel variance | Printed photo held in front of camera |
| Landmark positional variance | Rock-solid face with no micro-movement |
| Stable-frame ratio | Video loop / replay attack |
| Minimum motion frames | Insufficient temporal change |

---

## Integration Guide — Spring Boot + Next.js

### Next.js Frontend (TypeScript)

```typescript
// Capture frames from webcam, send to backend proxy
const response = await fetch('/api/liveness/check', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    sessionId: session.id,
    frames: capturedFramesBase64,   // string[] from canvas.toDataURL()
  }),
});
const result = await response.json();
if (result.status === 'PASS') { /* proceed with KYC */ }
```

### Spring Boot Gateway Route

```yaml
# application.yml  (Spring Cloud Gateway)
spring:
  cloud:
    gateway:
      routes:
        - id: liveness-service
          uri: http://liveness-service:5000
          predicates:
            - Path=/liveness/**,/health
          filters:
            - name: RequestRateLimiter
            - name: AddRequestHeader
              args:
                name: X-Internal-Auth
                value: ${INTERNAL_API_KEY}
```

### Spring Boot Controller (REST Client)

```java
@RestController
@RequestMapping("/api/liveness")
public class LivenessProxyController {

    private final RestTemplate restTemplate;
    private final String livenessUrl = "http://liveness-service:5000";

    @PostMapping("/check")
    public ResponseEntity<Map<String, Object>> checkLiveness(
            @RequestParam String sessionId,
            @RequestParam MultipartFile video) throws IOException {

        var body = new LinkedMultiValueMap<String, Object>();
        body.add("sessionId", sessionId);
        body.add("video", new ByteArrayResource(video.getBytes()) {
            @Override public String getFilename() { return video.getOriginalFilename(); }
        });

        var headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        var request = new HttpEntity<>(body, headers);
        return restTemplate.postForEntity(
            livenessUrl + "/liveness/check", request, Map.class
        );
    }
}
```

---

## Error Codes

| `errorCode` | HTTP | Cause |
|-------------|------|-------|
| `MISSING_VIDEO` | 400 | No `video` field in multipart |
| `MISSING_FRAMES` | 400 | `frames` list is empty or missing |
| `INVALID_FORMAT` | 400 | Unsupported video extension |
| `VALIDATION_ERROR` | 400 | Too few frames, corrupt data |
| `UNSUPPORTED_CONTENT_TYPE` | 415 | Not multipart or JSON |
| `PAYLOAD_TOO_LARGE` | 413 | Upload > 100 MB |
| `INTERNAL_ERROR` | 500 | Unhandled server error |

---

## Audit Logging

Every request writes a **pipe-delimited** line to `logs/app.log`:

```
[LEVEL] YYYY-MM-DD HH:MM:SS | session=<id> | input=<type> | score=<n> | result=<PASS/FAIL> | time=<s>s
```

- Logs rotate at **10 MB**, keeping **5 backups**
- All logs also mirror to **stdout** (compatible with Docker/K8s log collectors)
- Log level controlled by `LOG_LEVEL` env var (`DEBUG` / `INFO` / `WARNING`)
