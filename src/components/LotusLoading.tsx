import React from 'react';

interface LotusLoadingProps {
  className?: string;
  size?: number;
}

/**
 * Lotus Loading Animation - Clean, recognizable lotus flower
 * Simple, bold design optimized for small sizes with smooth rotation
 */
export const LotusLoading: React.FC<LotusLoadingProps> = ({
  className = "",
  size = 32
}) => {
  return (
    <div className={`inline-flex items-center justify-center ${className}`} style={{ background: 'transparent' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="lotus-loading"
        style={{ overflow: 'visible', background: 'transparent' }}
      >
        <defs>
          {/* Outer petal gradient - lotus green */}
          <linearGradient id={`lotus-petal-outer-${size}`} x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 1 }} />
          </linearGradient>

          {/* Inner petal gradient - lighter green */}
          <linearGradient id={`lotus-petal-inner-${size}`} x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0.9 }} />
          </linearGradient>

          {/* Center gradient - warm accent */}
          <radialGradient id={`lotus-center-${size}`}>
            <stop offset="0%" style={{ stopColor: 'hsl(var(--primary))', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-dark))', stopOpacity: 1 }} />
          </radialGradient>
        </defs>

        {/* Rotating lotus flower group - centered */}
        <g className="lotus-flower" transform="translate(60, 60)">

          {/* Outer petals - 8 large, bold petals */}
          {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => (
            <g key={`outer-${i}`} transform={`rotate(${angle})`}>
              <path
                d="M 0,0 Q -5,-10 -6,-22 Q -4,-26 0,-28 Q 4,-26 6,-22 Q 5,-10 0,0 Z"
                fill={`url(#lotus-petal-outer-${size})`}
                stroke="hsl(var(--lotus-green-dark))"
                strokeWidth="0.8"
                className={`outer-petal petal-${i}`}
                opacity="0.95"
              />
            </g>
          ))}

          {/* Inner petals - 5 smaller petals */}
          {[0, 72, 144, 216, 288].map((angle, i) => (
            <g key={`inner-${i}`} transform={`rotate(${angle})`}>
              <path
                d="M 0,0 Q -3,-6 -4,-14 Q -2,-16 0,-18 Q 2,-16 4,-14 Q 3,-6 0,0 Z"
                fill={`url(#lotus-petal-inner-${size})`}
                stroke="hsl(var(--lotus-green-medium))"
                strokeWidth="0.5"
                className={`inner-petal petal-${i}`}
                opacity="1"
              />
            </g>
          ))}

          {/* Center circle */}
          <circle
            cx="0"
            cy="0"
            r="6"
            fill={`url(#lotus-center-${size})`}
            className="lotus-center-dot"
          />

          {/* Inner center details */}
          <circle
            cx="0"
            cy="0"
            r="3"
            fill="hsl(var(--lotus-green-dark))"
            opacity="0.6"
            className="lotus-center-inner"
          />
        </g>
      </svg>

      <style>{`
        .lotus-loading {
          background: transparent !important;
        }

        /* Main lotus flower rotation - spins in place like floating on water */
        .lotus-flower {
          animation: lotusRotate 4s linear infinite;
          transform-origin: center center;
        }

        /* Outer petals - subtle pulse */
        .outer-petal {
          animation: petalPulse 3s ease-in-out infinite;
          transform-origin: 0 0;
        }

        .outer-petal.petal-0 { animation-delay: 0s; }
        .outer-petal.petal-1 { animation-delay: 0.1s; }
        .outer-petal.petal-2 { animation-delay: 0.2s; }
        .outer-petal.petal-3 { animation-delay: 0.3s; }
        .outer-petal.petal-4 { animation-delay: 0.4s; }
        .outer-petal.petal-5 { animation-delay: 0.5s; }
        .outer-petal.petal-6 { animation-delay: 0.6s; }
        .outer-petal.petal-7 { animation-delay: 0.7s; }

        /* Inner petals - counter-rotate slightly */
        .inner-petal {
          animation: innerPetalPulse 3s ease-in-out infinite;
          transform-origin: 0 0;
        }

        .inner-petal.petal-0 { animation-delay: 0.2s; }
        .inner-petal.petal-1 { animation-delay: 0.4s; }
        .inner-petal.petal-2 { animation-delay: 0.6s; }
        .inner-petal.petal-3 { animation-delay: 0.8s; }
        .inner-petal.petal-4 { animation-delay: 1s; }

        /* Center pulse */
        .lotus-center-dot {
          animation: centerPulse 2s ease-in-out infinite;
        }

        .lotus-center-inner {
          animation: centerPulse 2s ease-in-out infinite reverse;
        }

        /* Water ripple */
        .water-ripple {
          animation: ripple 3s ease-out infinite;
        }

        /* Keyframe Animations */

        @keyframes lotusRotate {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }

        @keyframes petalPulse {
          0%, 100% {
            opacity: 0.85;
          }
          50% {
            opacity: 1;
          }
        }

        @keyframes innerPetalPulse {
          0%, 100% {
            opacity: 0.9;
            transform: scale(1);
          }
          50% {
            opacity: 1;
            transform: scale(1.05);
          }
        }

        @keyframes centerPulse {
          0%, 100% {
            transform: scale(1);
            opacity: 0.8;
          }
          50% {
            transform: scale(1.15);
            opacity: 1;
          }
        }

        @keyframes ripple {
          0% {
            opacity: 0;
            transform: scale(0.8);
          }
          50% {
            opacity: 0.15;
          }
          100% {
            opacity: 0;
            transform: scale(1.1);
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
