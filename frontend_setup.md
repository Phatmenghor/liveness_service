# Liveness Detection - Next.js Frontend Setup

## Project Structure

```
liveness-web/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main liveness page
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── LivenessCamera.tsx    # Webcam capture + detection
│   │   ├── ChallengeDisplay.tsx  # Challenge instructions
│   │   ├── ProgressBar.tsx       # 100% progress indicator
│   │   └── ResultScreen.tsx      # PASS/FAIL result
│   ├── hooks/
│   │   └── useLiveness.ts        # Liveness API hook
│   └── utils/
│       └── api.ts               # API client
├── public/
├── package.json
└── next.config.js
```

## Features

### 1. **Real-Time Webcam Capture**
- Shows video stream
- Face detection overlay
- FPS counter

### 2. **Challenge Display**
- Current challenge text
- Visual arrow indicators (← → ↑ ↓)
- Confidence score
- Challenge progress

### 3. **Progress Bar (0-100%)**
- Face Detection: 20% ✓
- Blink: 20% ✓
- Movement: 20% ✓
- Anti-Spoof: 20% ✓
- Challenge: 20% ✓

### 4. **Real-Time Feedback**
- ✅ Green checkmarks for passed checks
- ❌ Red X for failed checks
- 🔄 Loading state during processing

### 5. **Mobile Responsive**
- Works on iPhone, Android, tablet
- Full-screen camera mode
- Touch-friendly buttons

## Installation

```bash
# Create Next.js project
npx create-next-app@latest liveness-web --typescript --tailwind

# Install dependencies
cd liveness-web
npm install axios zustand

# Run dev server
npm run dev
```

## Configuration

Create `.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## API Integration

The app sends frames to the Python service:
```
POST http://localhost:5000/liveness/check
Content-Type: application/json

{
  "sessionId": "session-123",
  "frames": ["data:image/jpeg;base64,..."]
}
```

Response:
```json
{
  "status": "PASS",
  "score": 100.0,
  "challenge": {
    "type": "turn_left",
    "completed": true
  }
}
```
