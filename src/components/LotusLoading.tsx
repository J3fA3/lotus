import React from 'react';

interface LotusLoadingProps {
  className?: string;
  size?: number;
}

/**
 * Lotus Loading Animation - Zen calligraphy brush drawing on papyrus
 * Animated brush strokes that create a meditative, flowing effect
 */
export const LotusLoading: React.FC<LotusLoadingProps> = ({
  className = "",
  size = 32
}) => {
  return (
    <div className={`inline-flex items-center justify-center ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="lotus-loading-animation"
      >
        {/* Brush stroke 1 - flowing curve */}
        <path
          d="M10 20 Q 15 10, 20 20"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          opacity="0.7"
          className="brush-stroke brush-stroke-1"
        />

        {/* Brush stroke 2 - flowing curve */}
        <path
          d="M20 20 Q 25 30, 30 20"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          fill="none"
          opacity="0.7"
          className="brush-stroke brush-stroke-2"
        />

        {/* Brush stroke 3 - center dot */}
        <circle
          cx="20"
          cy="20"
          r="2"
          fill="currentColor"
          opacity="0.8"
          className="brush-dot"
        />

        {/* Small accent dots for papyrus ink effect */}
        <circle
          cx="15"
          cy="16"
          r="1"
          fill="currentColor"
          opacity="0.4"
          className="ink-dot ink-dot-1"
        />
        <circle
          cx="25"
          cy="24"
          r="1"
          fill="currentColor"
          opacity="0.4"
          className="ink-dot ink-dot-2"
        />
      </svg>

      <style>{`
        .lotus-loading-animation {
          color: hsl(var(--lotus-green-medium));
        }

        /* Brush stroke animations - sequential drawing effect */
        .brush-stroke {
          stroke-dasharray: 20;
          stroke-dashoffset: 20;
          animation: drawStroke 1.8s ease-in-out infinite;
        }

        .brush-stroke-1 {
          animation-delay: 0s;
        }

        .brush-stroke-2 {
          animation-delay: 0.3s;
        }

        /* Center dot pulse */
        .brush-dot {
          animation: dotPulse 1.8s ease-in-out infinite;
          transform-origin: center;
        }

        /* Ink dots fade in and out */
        .ink-dot {
          animation: inkFade 1.8s ease-in-out infinite;
        }

        .ink-dot-1 {
          animation-delay: 0.6s;
        }

        .ink-dot-2 {
          animation-delay: 0.9s;
        }

        @keyframes drawStroke {
          0% {
            stroke-dashoffset: 20;
            opacity: 0;
          }
          30% {
            opacity: 0.7;
          }
          60% {
            stroke-dashoffset: 0;
            opacity: 0.7;
          }
          100% {
            stroke-dashoffset: 0;
            opacity: 0;
          }
        }

        @keyframes dotPulse {
          0%, 100% {
            opacity: 0.3;
            transform: scale(0.8);
          }
          50% {
            opacity: 0.9;
            transform: scale(1.2);
          }
        }

        @keyframes inkFade {
          0%, 100% {
            opacity: 0;
            transform: scale(0.5);
          }
          50% {
            opacity: 0.6;
            transform: scale(1);
          }
        }
      `}</style>
    </div>
  );
};

/**
 * Alternative: Simple Zen circle loading (Enso)
 */
export const LotusLoadingEnso: React.FC<LotusLoadingProps> = ({
  className = "",
  size = 32
}) => {
  return (
    <div className={`inline-flex items-center justify-center ${className}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="enso-loading"
      >
        {/* Enso circle - Zen circle of enlightenment */}
        <circle
          cx="20"
          cy="20"
          r="15"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          fill="none"
          opacity="0.7"
          className="enso-circle"
        />
      </svg>

      <style>{`
        .enso-loading {
          color: hsl(var(--lotus-green-medium));
        }

        .enso-circle {
          stroke-dasharray: 94.2; /* 2πr where r=15 */
          stroke-dashoffset: 94.2;
          animation: drawEnso 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
          transform-origin: center;
        }

        @keyframes drawEnso {
          0% {
            stroke-dashoffset: 94.2;
            transform: rotate(0deg);
            opacity: 0.3;
          }
          50% {
            stroke-dashoffset: 0;
            opacity: 0.8;
          }
          100% {
            stroke-dashoffset: -94.2;
            transform: rotate(360deg);
            opacity: 0.3;
          }
        }
      `}</style>
    </div>
  );
};
