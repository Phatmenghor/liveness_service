'use client';

import { useRef, useEffect, useState } from 'react';

interface FaceDetection {
  detected: boolean;
  centered: boolean;
  lighting: string; // 'good', 'dark', 'bright'
}

interface LivenessCameraProps {
  onFramesCapture: (frames: string[]) => void;
  isProcessing: boolean;
  challenge?: {
    type: string;
    description: string;
    instruction: string;
  };
}

export default function LivenessCamera({
  onFramesCapture,
  isProcessing,
  challenge,
}: LivenessCameraProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [faceDetection, setFaceDetection] = useState<FaceDetection>({
    detected: false,
    centered: false,
    lighting: 'checking',
  });
  const [frameCount, setFrameCount] = useState(0);
  const [fps, setFps] = useState(0);
  const framesCapturedRef = useRef<string[]>([]);
  const lastTimeRef = useRef(Date.now());

  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } },
          audio: false,
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
      } catch (err) {
        console.error('Camera access denied:', err);
        alert('Please enable camera access to continue');
      }
    };

    startCamera();

    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
        tracks.forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    const captureFrames = setInterval(() => {
      if (videoRef.current && canvasRef.current && !isProcessing) {
        const ctx = canvasRef.current.getContext('2d');
        if (ctx) {
          canvasRef.current.width = videoRef.current.videoWidth;
          canvasRef.current.height = videoRef.current.videoHeight;
          ctx.drawImage(videoRef.current, 0, 0);

          const frameBase64 = canvasRef.current.toDataURL('image/jpeg', 0.8);
          framesCapturedRef.current.push(frameBase64);

          // Calculate FPS
          const now = Date.now();
          const elapsed = now - lastTimeRef.current;
          if (elapsed >= 1000) {
            setFps(frameCount);
            setFrameCount(0);
            lastTimeRef.current = now;
          } else {
            setFrameCount((prev) => prev + 1);
          }

          // Analyze frame (simplified - in real app would use ML model)
          analyzeFrame();

          // Send frames when we have enough
          if (framesCapturedRef.current.length >= 30) {
            onFramesCapture(framesCapturedRef.current);
            framesCapturedRef.current = [];
          }
        }
      }
    }, 100); // Capture every 100ms (10 FPS)

    return () => clearInterval(captureFrames);
  }, [isProcessing, onFramesCapture, frameCount]);

  const analyzeFrame = () => {
    if (canvasRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      if (ctx) {
        const imageData = ctx.getImageData(0, 0, canvasRef.current.width, canvasRef.current.height);
        const brightness = calculateBrightness(imageData.data);

        setFaceDetection({
          detected: true,
          centered: true,
          lighting: brightness < 80 ? 'dark' : brightness > 200 ? 'bright' : 'good',
        });
      }
    }
  };

  const calculateBrightness = (data: Uint8ClampedArray) => {
    let sum = 0;
    for (let i = 0; i < data.length; i += 4) {
      sum += (data[i] + data[i + 1] + data[i + 2]) / 3;
    }
    return sum / (data.length / 4);
  };

  return (
    <div className="w-full h-screen bg-black flex flex-col items-center justify-center relative">
      {/* Video Stream */}
      <div className="relative w-full h-4/5 bg-black">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          className="w-full h-full object-cover"
          style={{ transform: 'scaleX(-1)' }}
        />
        <canvas ref={canvasRef} className="hidden" />

        {/* Status Bar */}
        <div className="absolute top-0 left-0 right-0 bg-gradient-to-b from-black/70 to-transparent p-4">
          <div className="flex justify-between items-center">
            <div className="text-white font-bold">
              {faceDetection.detected ? '✓ FACE DETECTED' : '⚠ NO FACE'}
            </div>
            <div className="text-yellow-400">FPS: {fps}</div>
          </div>
        </div>

        {/* Challenge Overlay */}
        {challenge && (
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <div className="text-4xl mb-4">
              {challenge.type === 'turn_left' && '←'}
              {challenge.type === 'turn_right' && '→'}
              {challenge.type === 'look_up' && '↑'}
              {challenge.type === 'look_down' && '↓'}
              {challenge.type === 'blink_once' && '👁'}
              {challenge.type === 'blink_twice' && '👁👁'}
              {challenge.type === 'smile' && '😊'}
            </div>
            <div className="text-white text-center text-lg font-bold bg-black/60 px-6 py-3 rounded-lg">
              {challenge.description}
            </div>
          </div>
        )}

        {/* Lighting Indicator */}
        <div className="absolute bottom-4 left-4 text-sm font-bold">
          <div
            className={`px-3 py-1 rounded ${
              faceDetection.lighting === 'good'
                ? 'bg-green-500'
                : faceDetection.lighting === 'dark'
                  ? 'bg-red-500'
                  : 'bg-yellow-500'
            } text-white`}
          >
            Lighting: {faceDetection.lighting}
          </div>
        </div>

        {/* Processing Indicator */}
        {isProcessing && (
          <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
            <div className="text-white text-center">
              <div className="animate-spin text-4xl mb-2">⏳</div>
              <div className="font-bold">Processing...</div>
            </div>
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="w-full h-1/5 bg-slate-900 p-4 flex flex-col justify-center">
        <div className="text-white text-center">
          <h2 className="text-lg font-bold mb-2">
            {challenge?.instruction || 'Initializing camera...'}
          </h2>
          <div className="text-xs text-gray-400">
            Make sure face is centered • Good lighting • Follow the challenge
          </div>
        </div>
      </div>
    </div>
  );
}
