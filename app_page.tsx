'use client';

import { useState, useCallback } from 'react';
import LivenessCamera from './components/LivenessCamera';
import ProgressBar from './components/ProgressBar';

interface LivenessResult {
  status: 'PASS' | 'FAIL';
  score: number;
  result: {
    faceDetected: boolean;
    blinkDetected: boolean;
    headMovementDetected: boolean;
    spoofDetected: boolean;
  };
  challenge?: {
    type: string;
    description: string;
    instruction: string;
    completed: boolean;
  };
  reason: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

export default function LivenessPage() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<LivenessResult | null>(null);
  const [currentChallenge, setCurrentChallenge] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(() => `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);

  const handleFramesCapture = useCallback(
    async (frames: string[]) => {
      if (isProcessing) return;

      setIsProcessing(true);
      setError(null);

      try {
        const response = await fetch(`${API_URL}/liveness/check`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sessionId,
            frames,
          }),
        });

        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }

        const data: LivenessResult = await response.json();
        setResult(data);

        // Update challenge for next iteration
        if (data.challenge) {
          setCurrentChallenge({
            type: data.challenge.type,
            description: data.challenge.description,
            instruction: data.challenge.instruction,
          });
        }

        console.log('Liveness Result:', data);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error';
        setError(`Failed to process liveness check: ${errorMsg}`);
        console.error('Liveness Error:', err);
      } finally {
        setIsProcessing(false);
      }
    },
    [isProcessing, sessionId]
  );

  // If we have a result, show it
  if (result) {
    return (
      <div className="w-full min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex flex-col items-center justify-center p-4">
        <div className="w-full max-w-2xl">
          {/* Result Card */}
          <div
            className={`rounded-lg shadow-2xl p-8 mb-6 ${
              result.status === 'PASS'
                ? 'bg-green-500/10 border-2 border-green-500'
                : 'bg-red-500/10 border-2 border-red-500'
            }`}
          >
            {/* Status */}
            <div className="text-center mb-6">
              <div className="text-6xl mb-4">
                {result.status === 'PASS' ? '✓' : '✗'}
              </div>
              <h1
                className={`text-4xl font-bold ${
                  result.status === 'PASS' ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {result.status}
              </h1>
              <p className="text-gray-300 mt-2">{result.reason}</p>
            </div>

            {/* Score */}
            <div className="text-center mb-6">
              <div className="text-5xl font-bold text-blue-400">{result.score.toFixed(1)}</div>
              <div className="text-gray-400">/100 points</div>
            </div>

            {/* Progress Bar */}
            <ProgressBar
              score={result.score}
              faceDetected={result.result.faceDetected}
              blinkDetected={result.result.blinkDetected}
              headMovement={result.result.headMovementDetected}
              spoofDetected={result.result.spoofDetected}
              challengeCompleted={result.challenge?.completed || false}
            />

            {/* Breakdown */}
            <div className="mt-6 p-4 bg-slate-700/50 rounded-lg">
              <h3 className="text-white font-bold mb-3">Breakdown:</h3>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className={result.result.faceDetected ? 'text-green-400' : 'text-red-400'}>
                  {result.result.faceDetected ? '✓' : '✗'} Face Quality
                </div>
                <div className={result.result.blinkDetected ? 'text-green-400' : 'text-red-400'}>
                  {result.result.blinkDetected ? '✓' : '✗'} Blink Detected
                </div>
                <div className={result.result.headMovementDetected ? 'text-green-400' : 'text-red-400'}>
                  {result.result.headMovementDetected ? '✓' : '✗'} Head Movement
                </div>
                <div className={!result.result.spoofDetected ? 'text-green-400' : 'text-red-400'}>
                  {!result.result.spoofDetected ? '✓' : '✗'} Anti-Spoof
                </div>
                {result.challenge && (
                  <div className={result.challenge.completed ? 'text-green-400' : 'text-red-400'}>
                    {result.challenge.completed ? '✓' : '✗'} {result.challenge.description}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="mt-6 flex gap-3 justify-center">
              <button
                onClick={() => {
                  setResult(null);
                  setCurrentChallenge(null);
                  window.location.reload();
                }}
                className="px-6 py-3 bg-blue-500 hover:bg-blue-600 text-white font-bold rounded-lg"
              >
                Try Again
              </button>
              {result.status === 'PASS' && (
                <button
                  onClick={() => alert('Proceeding to account opening...')}
                  className="px-6 py-3 bg-green-500 hover:bg-green-600 text-white font-bold rounded-lg"
                >
                  Continue
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Show camera with challenge
  return (
    <div className="w-full h-screen bg-black flex flex-col">
      <LivenessCamera
        onFramesCapture={handleFramesCapture}
        isProcessing={isProcessing}
        challenge={currentChallenge}
      />

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-4 left-4 right-4 bg-red-500 text-white p-4 rounded-lg shadow-lg">
          {error}
        </div>
      )}

      {/* Session Info */}
      <div className="absolute top-4 right-4 text-xs text-gray-400">
        Session: {sessionId.substring(0, 12)}...
      </div>
    </div>
  );
}
