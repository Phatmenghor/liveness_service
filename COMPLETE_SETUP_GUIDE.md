# 🏦 Complete Bank-Grade Liveness Detection System

## What You Have Built

A **production-ready KYC liveness verification system** with:

### Backend (Python Flask)
✅ Multi-face detection rejection  
✅ Bank-grade face quality checks  
✅ Challenge-based liveness detection  
✅ Comprehensive scoring (0-100 points)  
✅ API endpoints for video/frame processing  

### Frontend (Next.js React)
✅ Real-time webcam capture  
✅ Visual challenge indicators  
✅ Live progress bar (0-100%)  
✅ Mobile-responsive design  
✅ PASS/FAIL result screen  

---

## 📋 System Architecture

```
┌─────────────────────────────────────────────────────┐
│         Next.js Frontend (Port 3000)                │
│  ┌─────────────────────────────────────────────┐   │
│  │ • Real-time camera capture                  │   │
│  │ • Challenge display (turn/blink/smile)      │   │
│  │ • Progress bar (0-100%)                     │   │
│  │ • Result screen                             │   │
│  └─────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────┘
                   │ API: POST /liveness/check
                   ↓
┌─────────────────────────────────────────────────────┐
│        Python Flask Backend (Port 5000)             │
│  ┌─────────────────────────────────────────────┐   │
│  │ Stage 1: Face Detection (MediaPipe)         │   │
│  │ Stage 1.5: Face Quality Check (Bank-grade)  │   │
│  │ Stage 2: Blink Detection                    │   │
│  │ Stage 3: Head Movement Detection            │   │
│  │ Stage 4: Anti-Spoof Detection               │   │
│  │ Stage 5: Challenge Validation               │   │
│  └─────────────────────────────────────────────┘   │
│              Scoring: 100 points total              │
│  • Face Quality: 20 pts                             │
│  • Blink: 20 pts                                    │
│  • Movement: 20 pts                                 │
│  • Anti-Spoof: 20 pts                              │
│  • Challenge: 20 pts                                │
│  PASS = Score ≥ 70                                  │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 Complete Setup (5 Steps)

### Step 1: Python Backend Setup

```bash
cd liveness_service

# Ensure Python 3.10-3.12
python3.12 --version

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the service
python app.py
```

**Expected Output:**
```
 * Running on http://127.0.0.1:5000
[INFO] LivenessService initialised — all AI modules loaded.
```

### Step 2: Test Python Service

```bash
# Health check
curl http://localhost:5000/health

# Response
{"status": "running", "service": "liveness-ai"}
```

### Step 3: Create Next.js Project

```bash
# Create new project
npx create-next-app@latest liveness-web \
  --typescript \
  --tailwind \
  --no-eslint

cd liveness-web
```

### Step 4: Add Frontend Files

```bash
# Copy component files (from this repo)
cp ../liveness_service/app_LivenessCamera.tsx src/components/LivenessCamera.tsx
cp ../liveness_service/app_ProgressBar.tsx src/components/ProgressBar.tsx
cp ../liveness_service/app_page.tsx src/app/page.tsx
```

### Step 5: Configure & Run

Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

Run:
```bash
npm run dev
```

Visit: `http://localhost:3000`

---

## ✅ Testing Checklist

### Backend Tests

- [ ] **Health Check**
  ```bash
  curl http://localhost:5000/health
  # Response: {"status": "running", "service": "liveness-ai"}
  ```

- [ ] **Local Camera Test**
  ```bash
  python local_test.py
  # Shows real-time face detection with landmarks
  # Press Q to stop and see summary
  ```

- [ ] **API Video Upload**
  ```bash
  curl -X POST http://localhost:5000/liveness/check \
    -F "sessionId=TEST-001" \
    -F "video=@/path/to/test_video.mp4"
  # Response: {"status": "PASS", "score": 85.0, ...}
  ```

### Frontend Tests

- [ ] **Open Web App**
  - Visit `http://localhost:3000`
  - Should prompt for camera permission
  - Camera should start

- [ ] **Face Detection**
  - Face should show landmarks
  - Status should say "FACE DETECTED"
  - FPS counter should show 10+ fps

- [ ] **Challenge Instructions**
  - Should see random challenge (blink/turn/smile)
  - Visual indicator should appear (← → ↑ ↓)

- [ ] **Progress Updates**
  - As you complete checks, % should increase
  - Each check should turn green when completed

- [ ] **Get 100% PASS**
  - Full face visible ✓
  - Blink naturally ✓
  - Move head left/right ✓
  - Complete challenge ✓
  - Should show "PASS" with 100 points

---

## 🎯 To Get 100% PASS

**Requirements (All 5 Must Be Completed):**

| Check | Action | Points |
|-------|--------|--------|
| Face Quality | Face fully visible, centered, good lighting | 20 |
| Blink | Blink 1-2 times naturally | 20 |
| Movement | Turn head left/right OR look up/down | 20 |
| Anti-Spoof | Be a real live person (not photo/video) | 20 |
| Challenge | Follow random instruction | 20 |
| **TOTAL** | All 5 checks completed | **100** |

**Challenge Types (Random):**
- 👁 Blink once
- 👁👁 Blink twice
- 😊 Smile (mouth open)
- ← Turn left (15° yaw)
- → Turn right (15° yaw)
- ↑ Look up (12° pitch)
- ↓ Look down (12° pitch)

---

## 📊 Scoring Breakdown

```
Total Score = 100 points
Passing Score = 70 points

Example 1: Perfect Run
├─ Face Quality ✓ → +20 pts
├─ Blink ✓ → +20 pts
├─ Movement ✓ → +20 pts
├─ Anti-Spoof ✓ → +20 pts
└─ Challenge ✓ → +20 pts
  = 100 points → PASS ✅

Example 2: Missing Challenge
├─ Face Quality ✓ → +20 pts
├─ Blink ✓ → +20 pts
├─ Movement ✓ → +20 pts
├─ Anti-Spoof ✓ → +20 pts
└─ Challenge ✗ → +0 pts
  = 80 points → PASS ✅

Example 3: Missing Movement
├─ Face Quality ✓ → +20 pts
├─ Blink ✓ → +20 pts
├─ Movement ✗ → +0 pts
├─ Anti-Spoof ✓ → +20 pts
└─ Challenge ✓ → +20 pts
  = 80 points → PASS ✅

Example 4: Missing 2 Checks
├─ Face Quality ✓ → +20 pts
├─ Blink ✗ → +0 pts
├─ Movement ✓ → +20 pts
├─ Anti-Spoof ✓ → +20 pts
└─ Challenge ✓ → +20 pts
  = 80 points → PASS ✅

Example 5: Only Face + Blink
├─ Face Quality ✓ → +20 pts
├─ Blink ✓ → +20 pts
├─ Movement ✗ → +0 pts
├─ Anti-Spoof ✗ → +0 pts
└─ Challenge ✗ → +0 pts
  = 40 points → FAIL ❌
```

---

## 🔍 Quality Checks (Bank-Grade)

**Face Size:**
- ✓ Must be 20-70% of frame
- ❌ Fails if too small (< 20%)
- ❌ Fails if too large (> 70%)

**Face Centering:**
- ✓ Must be within ±20% of center
- ❌ Fails if off-center

**Lighting Quality:**
- ✓ Brightness 60-220 (0-255 scale)
- ❌ Fails if too dark (< 60)
- ❌ Fails if too bright (> 220)

**Blur Detection:**
- ✓ Laplacian variance > 100
- ❌ Fails if blurry

**Eye Visibility:**
- ✓ Both eyes visible and clear
- ❌ Fails if eyes covered or not visible

**Occlusion Detection:**
- ✓ No mask, glasses, or hand covering
- ❌ Fails if face partially obstructed

---

## 📱 API Response Example

**Request:**
```bash
curl -X POST http://localhost:5000/liveness/check \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "KYC-SESSION-001",
    "frames": ["data:image/jpeg;base64,...", "..."]
  }'
```

**Response (PASS):**
```json
{
  "sessionId": "KYC-SESSION-001",
  "status": "PASS",
  "score": 100.0,
  "result": {
    "faceDetected": true,
    "blinkDetected": true,
    "headMovementDetected": true,
    "spoofDetected": false
  },
  "challenge": {
    "type": "turn_left",
    "description": "Turn head left",
    "instruction": "Please turn your head to the left slowly",
    "completed": true,
    "confidence": 0.95
  },
  "reason": "Liveness verified.",
  "processingTimeSeconds": 2.145
}
```

**Response (FAIL):**
```json
{
  "sessionId": "KYC-SESSION-002",
  "status": "FAIL",
  "score": 45.0,
  "result": {
    "faceDetected": true,
    "blinkDetected": false,
    "headMovementDetected": false,
    "spoofDetected": false
  },
  "challenge": {
    "type": "blink_once",
    "description": "Blink once",
    "instruction": "Please blink your eyes once naturally",
    "completed": false,
    "reason": "Blink count: 0"
  },
  "reason": "No blink detected (count=0) | No head movement detected",
  "processingTimeSeconds": 1.842
}
```

---

## 🚀 Production Deployment

### Python Backend (AWS/GCP)

```bash
# Using Gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 30 app:app

# Or on Heroku
heroku create liveness-api
git push heroku main
```

### Frontend (Vercel)

```bash
# Deploy Next.js
vercel

# Set environment variable
vercel env add NEXT_PUBLIC_API_URL https://liveness-api.yourdomain.com
```

### Docker Deployment

**Python Service:**
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

---

## 🔧 Configuration & Tuning

### Quality Check Strictness

Edit `config.py`:
```python
# Strict: 100% of frames must pass (default - bank-grade)
QUALITY_CHECKS_MANDATORY = True
MIN_QUALITY_FRAMES_RATIO = 1.0

# Lenient: 95% of frames must pass
MIN_QUALITY_FRAMES_RATIO = 0.95
```

### Scoring Weights

Edit `config.py`:
```python
SCORE_FACE_DETECTED = 20
SCORE_BLINK_DETECTED = 20
SCORE_HEAD_MOVEMENT = 20
SCORE_ANTI_SPOOF_PASSED = 20
SCORE_CHALLENGE_PASSED = 20
PASS_THRESHOLD = 70  # Need 70+ to pass
```

### Challenge Difficulty

Edit `core/challenge_detector.py`:
```python
# Add/remove challenge types
CHALLENGES = [
    ChallengeType.BLINK_ONCE,
    ChallengeType.BLINK_TWICE,
    ChallengeType.SMILE,
    # ... add more
]
```

---

## 📝 Summary

You have successfully built:

✅ **Production-Ready Backend**
- Flask API with 6 AI detection stages
- Bank-grade quality validation
- Challenge-based liveness detection
- Comprehensive logging and error handling

✅ **Mobile-Friendly Frontend**
- Real-time webcam interface
- Visual progress tracker
- Challenge instructions with indicators
- Responsive design for all devices

✅ **Complete Documentation**
- Setup guides
- API specifications
- Testing procedures
- Deployment instructions

---

## 🎯 Next Steps

1. **Test Locally**
   - Run `python local_test.py` to verify camera
   - Run `python app.py` for API
   - Run `npm run dev` for frontend
   - Open `http://localhost:3000`

2. **Get 100% PASS**
   - Follow all challenge instructions
   - Keep full face visible
   - Good lighting required
   - Complete challenge action

3. **Deploy to Production**
   - Push Python to Heroku/AWS/GCP
   - Deploy Next.js to Vercel
   - Configure CORS for cross-origin requests
   - Set up database for result storage

4. **Integrate with KYC System**
   - Connect to your user onboarding flow
   - Store liveness results in database
   - Add final account approval step
   - Set up audit logging

---

**🏦 You now have a bank-grade liveness detection system!**

Questions? Check the logs:
```bash
# Python service logs
tail -f logs/app.log

# Browser console
F12 → Console tab
```

Good luck! 🚀
