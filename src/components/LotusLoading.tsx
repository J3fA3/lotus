import React from 'react';

interface LotusLoadingProps {
  className?: string;
  size?: number;
}

/**
 * Lotus Loading Animation - Beautiful blooming lotus flower
 * Elegant petals that gently open and close with a meditative, flowing effect
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
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="lotus-flower-animation"
      >
        <defs>
          {/* Gradient for outer petals - lighter lotus green */}
          <linearGradient id="petal-gradient-outer" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 0.9 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0.85 }} />
          </linearGradient>

          {/* Gradient for inner petals - medium lotus green */}
          <linearGradient id="petal-gradient-inner" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0.95 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-dark))', stopOpacity: 0.9 }} />
          </linearGradient>

          {/* Gradient for center - warm accent */}
          <radialGradient id="center-gradient">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-dark))', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-medium))', stopOpacity: 0.8 }} />
          </radialGradient>
        </defs>

        {/* Water ripple effects */}
        <circle cx="50" cy="50" r="40" className="ripple ripple-1" />
        <circle cx="50" cy="50" r="35" className="ripple ripple-2" />
        <circle cx="50" cy="50" r="30" className="ripple ripple-3" />

        {/* Outer petals layer (8 petals) */}
        <g className="outer-petals">
          {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => (
            <ellipse
              key={`outer-${i}`}
              cx="50"
              cy="50"
              rx="8"
              ry="22"
              fill="url(#petal-gradient-outer)"
              className={`petal outer-petal petal-${i}`}
              style={{
                transformOrigin: '50px 50px',
                transform: `rotate(${angle}deg)`,
              }}
            />
          ))}
        </g>

        {/* Middle petals layer (8 petals, offset) */}
        <g className="middle-petals">
          {[22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5].map((angle, i) => (
            <ellipse
              key={`middle-${i}`}
              cx="50"
              cy="50"
              rx="7"
              ry="18"
              fill="url(#petal-gradient-inner)"
              className={`petal middle-petal petal-${i}`}
              style={{
                transformOrigin: '50px 50px',
                transform: `rotate(${angle}deg)`,
              }}
            />
          ))}
        </g>

        {/* Inner petals layer (6 petals) */}
        <g className="inner-petals">
          {[0, 60, 120, 180, 240, 300].map((angle, i) => (
            <ellipse
              key={`inner-${i}`}
              cx="50"
              cy="50"
              rx="5"
              ry="12"
              fill="url(#petal-gradient-inner)"
              className={`petal inner-petal petal-${i}`}
              style={{
                transformOrigin: '50px 50px',
                transform: `rotate(${angle}deg)`,
              }}
            />
          ))}
        </g>

        {/* Center stigma with stamens */}
        <circle cx="50" cy="50" r="6" fill="url(#center-gradient)" className="lotus-center" />

        {/* Small stamen dots around center */}
        <g className="stamens">
          {[0, 60, 120, 180, 240, 300].map((angle, i) => {
            const rad = (angle * Math.PI) / 180;
            const x = 50 + 8 * Math.cos(rad);
            const y = 50 + 8 * Math.sin(rad);
            return (
              <circle
                key={`stamen-${i}`}
                cx={x}
                cy={y}
                r="1.5"
                fill="hsl(var(--lotus-green-dark))"
                className={`stamen stamen-${i}`}
              />
            );
          })}
        </g>
      </svg>

      <style>{`
        .lotus-flower-animation {
          filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
        }

        /* Gentle floating animation for entire flower */
        .lotus-flower-animation {
          animation: lotusFloat 4s ease-in-out infinite;
        }

        /* Water ripple effects */
        .ripple {
          fill: none;
          stroke: hsl(var(--lotus-green-light));
          stroke-width: 0.5;
          opacity: 0;
          animation: rippleExpand 3s ease-out infinite;
        }

        .ripple-1 {
          animation-delay: 0s;
        }

        .ripple-2 {
          animation-delay: 1s;
        }

        .ripple-3 {
          animation-delay: 2s;
        }

        /* Outer petals - bloom outward */
        .outer-petal {
          animation: petalBloom 3s ease-in-out infinite;
          transform-origin: 50px 50px;
        }

        .outer-petal.petal-0 { animation-delay: 0s; }
        .outer-petal.petal-1 { animation-delay: 0.1s; }
        .outer-petal.petal-2 { animation-delay: 0.2s; }
        .outer-petal.petal-3 { animation-delay: 0.3s; }
        .outer-petal.petal-4 { animation-delay: 0.4s; }
        .outer-petal.petal-5 { animation-delay: 0.5s; }
        .outer-petal.petal-6 { animation-delay: 0.6s; }
        .outer-petal.petal-7 { animation-delay: 0.7s; }

        /* Middle petals - bloom with slight delay */
        .middle-petal {
          animation: petalBloom 3s ease-in-out infinite;
          animation-delay: 0.3s;
          transform-origin: 50px 50px;
        }

        .middle-petal.petal-0 { animation-delay: 0.35s; }
        .middle-petal.petal-1 { animation-delay: 0.45s; }
        .middle-petal.petal-2 { animation-delay: 0.55s; }
        .middle-petal.petal-3 { animation-delay: 0.65s; }
        .middle-petal.petal-4 { animation-delay: 0.75s; }
        .middle-petal.petal-5 { animation-delay: 0.85s; }
        .middle-petal.petal-6 { animation-delay: 0.95s; }
        .middle-petal.petal-7 { animation-delay: 1.05s; }

        /* Inner petals - bloom last */
        .inner-petal {
          animation: petalBloomInner 3s ease-in-out infinite;
          transform-origin: 50px 50px;
        }

        .inner-petal.petal-0 { animation-delay: 0.7s; }
        .inner-petal.petal-1 { animation-delay: 0.8s; }
        .inner-petal.petal-2 { animation-delay: 0.9s; }
        .inner-petal.petal-3 { animation-delay: 1s; }
        .inner-petal.petal-4 { animation-delay: 1.1s; }
        .inner-petal.petal-5 { animation-delay: 1.2s; }

        /* Center pulse */
        .lotus-center {
          animation: centerPulse 3s ease-in-out infinite;
          transform-origin: 50px 50px;
        }

        /* Stamens gentle movement */
        .stamen {
          animation: stamenPulse 3s ease-in-out infinite;
          transform-origin: 50px 50px;
        }

        .stamen-0 { animation-delay: 0s; }
        .stamen-1 { animation-delay: 0.15s; }
        .stamen-2 { animation-delay: 0.3s; }
        .stamen-3 { animation-delay: 0.45s; }
        .stamen-4 { animation-delay: 0.6s; }
        .stamen-5 { animation-delay: 0.75s; }

        /* Keyframe animations */
        @keyframes lotusFloat {
          0%, 100% {
            transform: translateY(0px) rotate(0deg);
          }
          25% {
            transform: translateY(-2px) rotate(1deg);
          }
          50% {
            transform: translateY(0px) rotate(0deg);
          }
          75% {
            transform: translateY(-1px) rotate(-1deg);
          }
        }

        @keyframes rippleExpand {
          0% {
            opacity: 0;
            transform: scale(0.5);
          }
          30% {
            opacity: 0.3;
          }
          100% {
            opacity: 0;
            transform: scale(1.3);
          }
        }

        @keyframes petalBloom {
          0% {
            opacity: 0.5;
            transform: scale(0.7) translateY(3px);
          }
          50% {
            opacity: 1;
            transform: scale(1) translateY(0px);
          }
          100% {
            opacity: 0.5;
            transform: scale(0.7) translateY(3px);
          }
        }

        @keyframes petalBloomInner {
          0% {
            opacity: 0.6;
            transform: scale(0.6);
          }
          50% {
            opacity: 1;
            transform: scale(1.1);
          }
          100% {
            opacity: 0.6;
            transform: scale(0.6);
          }
        }

        @keyframes centerPulse {
          0%, 100% {
            transform: scale(0.9);
            opacity: 0.9;
          }
          50% {
            transform: scale(1.1);
            opacity: 1;
          }
        }

        @keyframes stamenPulse {
          0%, 100% {
            opacity: 0.6;
            transform: scale(0.8);
          }
          50% {
            opacity: 1;
            transform: scale(1.2);
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
