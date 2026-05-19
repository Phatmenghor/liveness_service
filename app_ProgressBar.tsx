'use client';

import { useEffect, useState } from 'react';

interface ProgressItem {
  name: string;
  percent: number;
  completed: boolean;
  icon: string;
  status: 'pending' | 'loading' | 'completed' | 'failed';
}

interface ProgressBarProps {
  score: number;
  faceDetected: boolean;
  blinkDetected: boolean;
  headMovement: boolean;
  spoofDetected: boolean;
  challengeCompleted: boolean;
}

export default function ProgressBar({
  score,
  faceDetected,
  blinkDetected,
  headMovement,
  spoofDetected,
  challengeCompleted,
}: ProgressBarProps) {
  const [items, setItems] = useState<ProgressItem[]>([
    {
      name: 'Face Quality',
      percent: 20,
      completed: faceDetected,
      icon: '👤',
      status: faceDetected ? 'completed' : 'pending',
    },
    {
      name: 'Blink',
      percent: 20,
      completed: blinkDetected,
      icon: '👁',
      status: blinkDetected ? 'completed' : 'pending',
    },
    {
      name: 'Movement',
      percent: 20,
      completed: headMovement,
      icon: '🔄',
      status: headMovement ? 'completed' : 'pending',
    },
    {
      name: 'Anti-Spoof',
      percent: 20,
      completed: !spoofDetected,
      icon: '🛡️',
      status: !spoofDetected ? 'completed' : 'pending',
    },
    {
      name: 'Challenge',
      percent: 20,
      completed: challengeCompleted,
      icon: '✓',
      status: challengeCompleted ? 'completed' : 'pending',
    },
  ]);

  useEffect(() => {
    setItems([
      {
        name: 'Face Quality',
        percent: 20,
        completed: faceDetected,
        icon: '👤',
        status: faceDetected ? 'completed' : 'pending',
      },
      {
        name: 'Blink',
        percent: 20,
        completed: blinkDetected,
        icon: '👁',
        status: blinkDetected ? 'completed' : 'pending',
      },
      {
        name: 'Movement',
        percent: 20,
        completed: headMovement,
        icon: '🔄',
        status: headMovement ? 'completed' : 'pending',
      },
      {
        name: 'Anti-Spoof',
        percent: 20,
        completed: !spoofDetected,
        icon: '🛡️',
        status: !spoofDetected ? 'completed' : 'pending',
      },
      {
        name: 'Challenge',
        percent: 20,
        completed: challengeCompleted,
        icon: '✓',
        status: challengeCompleted ? 'completed' : 'pending',
      },
    ]);
  }, [faceDetected, blinkDetected, headMovement, spoofDetected, challengeCompleted]);

  const completedCount = items.filter((i) => i.completed).length;
  const totalPercent = (completedCount / items.length) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-gradient-to-br from-slate-900 to-slate-800 rounded-lg shadow-xl">
      {/* Main Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <h3 className="text-white font-bold text-lg">Liveness Verification Progress</h3>
          <span className="text-3xl font-bold text-blue-400">{Math.round(totalPercent)}%</span>
        </div>

        <div className="w-full bg-slate-700 rounded-full h-8 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-500 flex items-center justify-end pr-2"
            style={{ width: `${totalPercent}%` }}
          >
            {totalPercent > 10 && (
              <span className="text-white text-sm font-bold">{Math.round(totalPercent)}%</span>
            )}
          </div>
        </div>

        {/* Score */}
        <div className="mt-3 text-center">
          <div className="text-white font-bold">
            Score: <span className={`text-2xl ${score >= 70 ? 'text-green-400' : 'text-red-400'}`}>
              {Math.round(score)}/100
            </span>
          </div>
          {score >= 70 ? (
            <div className="text-green-400 font-bold text-lg mt-1">✓ PASS</div>
          ) : (
            <div className="text-red-400 font-bold text-lg mt-1">✗ FAIL (need 70+)</div>
          )}
        </div>
      </div>

      {/* Individual Items */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        {items.map((item, idx) => (
          <div
            key={idx}
            className={`p-4 rounded-lg text-center transition-all ${
              item.completed
                ? 'bg-green-500/20 border border-green-500'
                : 'bg-slate-700 border border-slate-600'
            }`}
          >
            <div className="text-2xl mb-2">{item.icon}</div>
            <h4 className={`text-sm font-bold ${item.completed ? 'text-green-400' : 'text-gray-300'}`}>
              {item.name}
            </h4>
            <div className="text-xs text-gray-400 mt-1">{item.percent}%</div>
            {item.completed && <div className="text-green-400 text-lg mt-1">✓</div>}
          </div>
        ))}
      </div>

      {/* Requirement List */}
      <div className="mt-6 p-4 bg-slate-700/50 rounded-lg">
        <h4 className="text-white font-bold mb-3">Requirements to achieve 100%:</h4>
        <ul className="text-sm text-gray-300 space-y-2">
          {items.map((item, idx) => (
            <li key={idx} className="flex items-center gap-2">
              <span className={item.completed ? 'text-green-400' : 'text-gray-500'}>
                {item.completed ? '✓' : '○'}
              </span>
              <span>{item.name} - {item.percent}%</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
