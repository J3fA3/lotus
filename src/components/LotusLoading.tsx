import React from 'react';

interface LotusLoadingProps {
  className?: string;
  size?: number;
  variant?: 'default' | 'large' | 'small';
}

/**
 * Lotus Loading Animation - Beautiful feng shui Zen lotus flower
 * Floating and spinning on water with gentle ripples
 * 
 * @param size - Explicit size override (pixels)
 * @param variant - Size variant: 'large' (64px) for main page, 'small' (24px) for chat, 'default' (32px)
 */
export const LotusLoading: React.FC<LotusLoadingProps> = ({
  className = "",
  size,
  variant = 'default'
}) => {
  // Determine size: explicit size prop > variant > default
  const finalSize = size ?? (variant === 'large' ? 64 : variant === 'small' ? 24 : 32);
  
  return (
    <div className={`inline-flex items-center justify-center ${className}`} style={{ background: 'transparent' }}>
      <svg
        width={finalSize}
        height={finalSize}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="lotus-loading"
        style={{ overflow: 'visible', background: 'transparent' }}
      >
        <defs>
          {/* Outer petal gradient - lotus green */}
          <linearGradient id={`lotus-petal-outer-${finalSize}`} x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 1 }} />
          </linearGradient>

          {/* Inner petal gradient - lighter green */}
          <linearGradient id={`lotus-petal-inner-${finalSize}`} x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0.9 }} />
          </linearGradient>

          {/* Subtle center glow - replaces the green dot */}
          <radialGradient id={`lotus-center-glow-${finalSize}`}>
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 0.4 }} />
            <stop offset="50%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0.2 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0 }} />
          </radialGradient>

          {/* Water ripple gradient */}
          <radialGradient id={`water-ripple-${finalSize}`}>
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 0 }} />
            <stop offset="50%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0.08 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0 }} />
          </radialGradient>
        </defs>

        {/* Water ripples - subtle circles expanding outward */}
        <circle
          cx="60"
          cy="60"
          r="45"
          fill={`url(#water-ripple-${finalSize})`}
          className="water-ripple ripple-1"
        />
        <circle
          cx="60"
          cy="60"
          r="45"
          fill={`url(#water-ripple-${finalSize})`}
          className="water-ripple ripple-2"
        />
        <circle
          cx="60"
          cy="60"
          r="45"
          fill={`url(#water-ripple-${finalSize})`}
          className="water-ripple ripple-3"
        />

        {/* Floating lotus flower group - combines rotation and bobbing */}
        <g className="lotus-flower">
          {/* Outer petals - 8 large, bold petals */}
          {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => (
            <g key={`outer-${i}`} transform={`rotate(${angle} 60 60)`}>
              <path
                d="M 60,60 Q 55,50 54,38 Q 56,34 60,32 Q 64,34 66,38 Q 65,50 60,60 Z"
                fill={`url(#lotus-petal-outer-${finalSize})`}
                stroke="hsl(var(--lotus-green-dark))"
                strokeWidth="0.8"
                className={`outer-petal petal-${i}`}
                opacity="0.95"
              />
            </g>
          ))}

          {/* Inner petals - 5 smaller petals */}
          {[0, 72, 144, 216, 288].map((angle, i) => (
            <g key={`inner-${i}`} transform={`rotate(${angle} 60 60)`}>
              <path
                d="M 60,60 Q 57,54 56,46 Q 58,44 60,42 Q 62,44 64,46 Q 63,54 60,60 Z"
                fill={`url(#lotus-petal-inner-${finalSize})`}
                stroke="hsl(var(--lotus-green-medium))"
                strokeWidth="0.5"
                className={`inner-petal petal-${i}`}
                opacity="1"
              />
            </g>
          ))}

          {/* Subtle center glow - soft and ethereal, no harsh dot */}
          <circle
            cx="60"
            cy="60"
            r="8"
            fill={`url(#lotus-center-glow-${finalSize})`}
            className="lotus-center-glow"
          />
        </g>
      </svg>

      <style>{`
        .lotus-loading {
          background: transparent !important;
        }

        /* Main lotus flower - floating and rotating on water */
        .lotus-flower {
          animation: lotusFloatRotate 6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
          transform-origin: 60px 60px;
        }

        /* Water ripples - expanding outward */
        .water-ripple {
          transform-origin: 60px 60px;
        }
        .ripple-1 {
          animation: waterRipple 3s ease-out infinite;
        }
        .ripple-2 {
          animation: waterRipple 3s ease-out infinite;
          animation-delay: 1s;
        }
        .ripple-3 {
          animation: waterRipple 3s ease-out infinite;
          animation-delay: 2s;
        }

        /* Outer petals - gentle breathing pulse */
        .outer-petal {
          animation: petalBreath 4s ease-in-out infinite;
          transform-origin: 60px 60px;
        }

        .outer-petal.petal-0 { animation-delay: 0s; }
        .outer-petal.petal-1 { animation-delay: 0.15s; }
        .outer-petal.petal-2 { animation-delay: 0.3s; }
        .outer-petal.petal-3 { animation-delay: 0.45s; }
        .outer-petal.petal-4 { animation-delay: 0.6s; }
        .outer-petal.petal-5 { animation-delay: 0.75s; }
        .outer-petal.petal-6 { animation-delay: 0.9s; }
        .outer-petal.petal-7 { animation-delay: 1.05s; }

        /* Inner petals - subtle wave motion */
        .inner-petal {
          animation: innerPetalWave 4s ease-in-out infinite;
          transform-origin: 60px 60px;
        }

        .inner-petal.petal-0 { animation-delay: 0.2s; }
        .inner-petal.petal-1 { animation-delay: 0.5s; }
        .inner-petal.petal-2 { animation-delay: 0.8s; }
        .inner-petal.petal-3 { animation-delay: 1.1s; }
        .inner-petal.petal-4 { animation-delay: 1.4s; }

        /* Center glow - soft pulsing */
        .lotus-center-glow {
          animation: centerGlow 3s ease-in-out infinite;
        }

        /* Keyframe Animations */

        /* Combined floating and rotation - like a leaf on water */
        @keyframes lotusFloatRotate {
          0% {
            transform: rotate(0deg) translateY(0px);
          }
          25% {
            transform: rotate(90deg) translateY(-2px);
          }
          50% {
            transform: rotate(180deg) translateY(0px);
          }
          75% {
            transform: rotate(270deg) translateY(-2px);
          }
          100% {
            transform: rotate(360deg) translateY(0px);
          }
        }

        /* Water ripple expansion */
        @keyframes waterRipple {
          0% {
            opacity: 0;
            transform: scale(0.8);
          }
          30% {
            opacity: 0.12;
          }
          100% {
            opacity: 0;
            transform: scale(1.3);
          }
        }

        /* Petal breathing - gentle opacity and scale */
        @keyframes petalBreath {
          0%, 100% {
            opacity: 0.9;
            transform: scale(1);
          }
          50% {
            opacity: 1;
            transform: scale(1.02);
          }
        }

        /* Inner petal wave - subtle movement */
        @keyframes innerPetalWave {
          0%, 100% {
            opacity: 0.95;
            transform: scale(1) rotate(0deg);
          }
          50% {
            opacity: 1;
            transform: scale(1.03) rotate(1deg);
          }
        }

        /* Center glow pulse - very subtle */
        @keyframes centerGlow {
          0%, 100% {
            opacity: 0.3;
            transform: scale(1);
          }
          50% {
            opacity: 0.5;
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
