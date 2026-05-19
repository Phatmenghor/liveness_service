# Liveness Detection - Next.js Frontend Quick Start

## 🚀 Setup Instructions

### Step 1: Create Next.js Project

```bash
# Create new Next.js project
npx create-next-app@latest liveness-web \
  --typescript \
  --tailwind \
  --no-eslint \
  --no-git

cd liveness-web
```

### Step 2: Install Files

Copy these files into your project:

```bash
# Copy components
cp app_LivenessCamera.tsx src/components/LivenessCamera.tsx
cp app_ProgressBar.tsx src/components/ProgressBar.tsx
cp app_page.tsx src/app/page.tsx
```

### Step 3: Environment Setup

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:5000
```

### Step 4: Update Next.js Config

Edit `next.config.js`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  compiler: {
    removeConsole: false,
  },
};

module.exports = nextConfig;
```

### Step 5: Start Development Server

```bash
npm run dev
```

Visit: `http://localhost:3000`

---

## 🎥 Running the Full System

### Terminal 1: Python Liveness Service

```bash
cd liveness_service
source venv/bin/activate
python app.py
```

Server: `http://localhost:5000`

### Terminal 2: Next.js Frontend

```bash
cd liveness-web
npm run dev
```

Frontend: `http://localhost:3000`

---

## 📱 Features

### Real-Time Display

✅ **Live Camera Feed**
- Shows your face with landmarks
- FPS counter
- Face detection status

✅ **Challenge Instructions**
- Visual arrow indicators (← → ↑ ↓)
- Challenge text
- Real-time feedback

✅ **Progress Bar (0-100%)**
- Face Quality: 20%
- Blink Detection: 20%
- Head Movement: 20%
- Anti-Spoof: 20%
- Challenge: 20%

### User Flow

1. **Open App** → Camera prompts for permission
2. **Face Detection** → Landmarks appear on screen
3. **Random Challenge** → System generates challenge (blink/turn/smile)
4. **Complete Challenge** → User performs action
5. **Progress Updates** → Real-time % increase
6. **Result Screen** → PASS (100%) or FAIL with breakdown

---

## 🔧 API Integration

The app sends frames to the Python service every 3 seconds:

```javascript
POST http://localhost:5000/liveness/check
{
  "sessionId": "session-123-abc",
  "frames": ["data:image/jpeg;base64,...", "..."]
}
```

Response:

```json
{
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

---

## 📊 Testing Scenarios

| Scenario | Expected |
|----------|----------|
| Full face + natural blink + head movement | ✅ **100% PASS** |
| Partial face (covered) | ❌ Fails quality check |
| No blink performed | ❌ Fails blink check |
| Challenge not completed | ❌ Challenge fails |
| Blurry image | ❌ Fails quality check |
| Too dark/bright lighting | ❌ Fails quality check |

---

## 🎯 To Get 100%

1. **Face**: Full face visible, centered, good lighting ✓
2. **Blink**: Blink naturally 1-2 times ✓
3. **Movement**: Turn head or look up/down ✓
4. **Anti-Spoof**: Be a real live person ✓
5. **Challenge**: Follow the random instruction ✓

---

## 🚀 Production Deployment

### Deploy on Vercel

```bash
# Push to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/your-username/liveness-web.git
git push -u origin main

# Deploy on Vercel
vercel
```

### Update Environment

Set `NEXT_PUBLIC_API_URL` to your production Python service URL:

```
https://liveness-api.yourdomain.com
```

### Python Service on AWS/GCP

```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

---

## 📝 Customization

### Change Challenge List

Edit `core/challenge_detector.py`:

```python
CHALLENGES = [
    ChallengeType.BLINK_ONCE,
    ChallengeType.BLINK_TWICE,
    # Add more...
]
```

### Adjust Scoring

Edit `config.py`:

```python
SCORE_FACE_DETECTED = 20
SCORE_BLINK_DETECTED = 20
SCORE_HEAD_MOVEMENT = 20
SCORE_ANTI_SPOOF_PASSED = 20
SCORE_CHALLENGE_PASSED = 20
```

### Change Colors/Themes

Edit `app_page.tsx`, `app_LivenessCamera.tsx`, and `app_ProgressBar.tsx`:

```tsx
className="bg-gradient-to-br from-slate-900 to-slate-800"
```

---

## 🐛 Troubleshooting

**Camera not working?**
- Check browser permissions
- Use HTTPS in production
- Test on `localhost` first

**API Connection Error?**
- Ensure Python service is running on port 5000
- Check `.env.local` has correct URL
- Test with: `curl http://localhost:5000/health`

**Frames not processing?**
- Check browser console for errors
- Verify frame capture is working
- Look at Python service logs

---

## 📚 Additional Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [MediaPipe FaceMesh](https://google.github.io/mediapipe/solutions/face_mesh.html)
- [getUserMedia API](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia)
- [Tailwind CSS](https://tailwindcss.com)

---

**Ready to go live? 🚀**

```bash
npm run build
npm start
```

Your bank-grade liveness detection is ready!
