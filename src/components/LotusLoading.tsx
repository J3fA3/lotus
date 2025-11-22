import React from 'react';

interface LotusLoadingProps {
  className?: string;
  size?: number;
}

/**
 * Lotus Loading Animation - Dynamic blooming lotus with spinning petals
 * Features realistic lotus flower with 3D rotation and floating petals
 */
export const LotusLoading: React.FC<LotusLoadingProps> = ({
  className = "",
  size = 32
}) => {
  return (
    <div className={`inline-flex items-center justify-center ${className}`} style={{ position: 'relative' }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 120 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="lotus-flower-animation"
      >
        <defs>
          {/* Pink gradient for lotus petals */}
          <linearGradient id="petal-pink" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#FFB6D9', stopOpacity: 1 }} />
            <stop offset="50%" style={{ stopColor: '#FF80C0', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#E84393', stopOpacity: 1 }} />
          </linearGradient>

          {/* White-pink gradient for inner petals */}
          <linearGradient id="petal-white-pink" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#FFFFFF', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#FFD0E8', stopOpacity: 1 }} />
          </linearGradient>

          {/* Yellow gradient for center */}
          <radialGradient id="center-yellow">
            <stop offset="0%" style={{ stopColor: '#FFF9C4', stopOpacity: 1 }} />
            <stop offset="50%" style={{ stopColor: '#FFD54F', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#FFA000', stopOpacity: 1 }} />
          </radialGradient>

          {/* Green gradient for lotus leaf */}
          <radialGradient id="leaf-green">
            <stop offset="0%" style={{ stopColor: 'hsl(var(--lotus-green-light))', stopOpacity: 0.4 }} />
            <stop offset="100%" style={{ stopColor: 'hsl(var(--lotus-green-dark))', stopOpacity: 0.6 }} />
          </radialGradient>

          {/* Glow filter */}
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Background lotus leaves (lily pads) */}
        <g className="lotus-leaves">
          <ellipse cx="30" cy="75" rx="18" ry="15" fill="url(#leaf-green)" className="leaf leaf-1" opacity="0.5" />
          <ellipse cx="90" cy="80" rx="15" ry="12" fill="url(#leaf-green)" className="leaf leaf-2" opacity="0.4" />
          <ellipse cx="60" cy="85" rx="20" ry="16" fill="url(#leaf-green)" className="leaf leaf-3" opacity="0.6" />
        </g>

        {/* Main lotus flower container with 3D rotation */}
        <g className="lotus-main" transform="translate(60, 50)">
          {/* Outer layer - 8 large pink petals */}
          <g className="outer-petals">
            {[0, 45, 90, 135, 180, 225, 270, 315].map((angle, i) => {
              const rad = (angle * Math.PI) / 180;
              const x = Math.cos(rad) * 2;
              const y = Math.sin(rad) * 2;
              return (
                <g key={`outer-${i}`} transform={`rotate(${angle})`}>
                  <path
                    d="M 0,-5 Q -4,-15 -6,-25 Q -3,-28 0,-30 Q 3,-28 6,-25 Q 4,-15 0,-5 Z"
                    fill="url(#petal-pink)"
                    stroke="#E84393"
                    strokeWidth="0.5"
                    className={`petal-outer petal-${i}`}
                    filter="url(#glow)"
                  />
                </g>
              );
            })}
          </g>

          {/* Middle layer - 8 white-pink petals */}
          <g className="middle-petals">
            {[22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5].map((angle, i) => (
              <g key={`middle-${i}`} transform={`rotate(${angle})`}>
                <path
                  d="M 0,-3 Q -3,-10 -4,-18 Q -2,-20 0,-21 Q 2,-20 4,-18 Q 3,-10 0,-3 Z"
                  fill="url(#petal-white-pink)"
                  stroke="#FFB6D9"
                  strokeWidth="0.3"
                  className={`petal-middle petal-${i}`}
                />
              </g>
            ))}
          </g>

          {/* Inner layer - 6 white petals */}
          <g className="inner-petals">
            {[0, 60, 120, 180, 240, 300].map((angle, i) => (
              <g key={`inner-${i}`} transform={`rotate(${angle})`}>
                <path
                  d="M 0,-2 Q -2,-6 -3,-12 Q -1,-13 0,-14 Q 1,-13 3,-12 Q 2,-6 0,-2 Z"
                  fill="url(#petal-white-pink)"
                  stroke="#FFD0E8"
                  strokeWidth="0.2"
                  className={`petal-inner petal-${i}`}
                />
              </g>
            ))}
          </g>

          {/* Center - yellow stigma */}
          <circle cx="0" cy="0" r="5" fill="url(#center-yellow)" className="lotus-center" filter="url(#glow)" />

          {/* Stamen dots */}
          <g className="stamens">
            {[0, 60, 120, 180, 240, 300].map((angle, i) => {
              const rad = (angle * Math.PI) / 180;
              const x = 3 * Math.cos(rad);
              const y = 3 * Math.sin(rad);
              return (
                <circle
                  key={`stamen-${i}`}
                  cx={x}
                  cy={y}
                  r="0.8"
                  fill="#FFA000"
                  className={`stamen stamen-${i}`}
                />
              );
            })}
          </g>
        </g>

        {/* Floating petals around the flower */}
        <g className="floating-petals">
          <path
            d="M 15,30 Q 12,25 10,20 Q 12,18 15,17 Q 18,18 20,20 Q 18,25 15,30 Z"
            fill="url(#petal-pink)"
            opacity="0.7"
            className="floating-petal petal-float-1"
          />
          <path
            d="M 95,45 Q 92,40 90,35 Q 92,33 95,32 Q 98,33 100,35 Q 98,40 95,45 Z"
            fill="url(#petal-white-pink)"
            opacity="0.6"
            className="floating-petal petal-float-2"
          />
          <path
            d="M 105,70 Q 102,65 100,60 Q 102,58 105,57 Q 108,58 110,60 Q 108,65 105,70 Z"
            fill="url(#petal-pink)"
            opacity="0.5"
            className="floating-petal petal-float-3"
          />
          <path
            d="M 20,85 Q 17,80 15,75 Q 17,73 20,72 Q 23,73 25,75 Q 23,80 20,85 Z"
            fill="url(#petal-white-pink)"
            opacity="0.6"
            className="floating-petal petal-float-4"
          />
        </g>

        {/* Sparkle particles */}
        <g className="sparkles">
          <circle cx="25" cy="45" r="1.5" fill="#FFD54F" className="sparkle sparkle-1" opacity="0" />
          <circle cx="95" cy="55" r="1" fill="#FFFFFF" className="sparkle sparkle-2" opacity="0" />
          <circle cx="50" cy="25" r="1.2" fill="#FFB6D9" className="sparkle sparkle-3" opacity="0" />
          <circle cx="85" cy="30" r="1" fill="#FFD54F" className="sparkle sparkle-4" opacity="0" />
          <circle cx="35" cy="70" r="1.3" fill="#FFFFFF" className="sparkle sparkle-5" opacity="0" />
        </g>
      </svg>

      <style>{`
        .lotus-flower-animation {
          filter: drop-shadow(0 4px 8px rgba(232, 67, 147, 0.2));
        }

        /* Lotus leaves gentle sway */
        .leaf {
          animation: leafSway 4s ease-in-out infinite;
          transform-origin: center;
        }

        .leaf-1 { animation-delay: 0s; }
        .leaf-2 { animation-delay: 0.5s; }
        .leaf-3 { animation-delay: 1s; }

        /* Main lotus flower - 3D rotation effect */
        .lotus-main {
          animation: lotus3DRotate 4s ease-in-out infinite;
          transform-origin: center;
          transform-box: fill-box;
        }

        /* Outer petals - opening and spinning */
        .petal-outer {
          animation: petalOpenSpin 4s ease-in-out infinite;
          transform-origin: bottom center;
          transform-box: fill-box;
        }

        .petal-outer.petal-0 { animation-delay: 0s; }
        .petal-outer.petal-1 { animation-delay: 0.1s; }
        .petal-outer.petal-2 { animation-delay: 0.2s; }
        .petal-outer.petal-3 { animation-delay: 0.3s; }
        .petal-outer.petal-4 { animation-delay: 0.4s; }
        .petal-outer.petal-5 { animation-delay: 0.5s; }
        .petal-outer.petal-6 { animation-delay: 0.6s; }
        .petal-outer.petal-7 { animation-delay: 0.7s; }

        /* Middle petals */
        .petal-middle {
          animation: petalOpenSpin 4s ease-in-out infinite;
          transform-origin: bottom center;
          transform-box: fill-box;
        }

        .petal-middle.petal-0 { animation-delay: 0.2s; }
        .petal-middle.petal-1 { animation-delay: 0.3s; }
        .petal-middle.petal-2 { animation-delay: 0.4s; }
        .petal-middle.petal-3 { animation-delay: 0.5s; }
        .petal-middle.petal-4 { animation-delay: 0.6s; }
        .petal-middle.petal-5 { animation-delay: 0.7s; }
        .petal-middle.petal-6 { animation-delay: 0.8s; }
        .petal-middle.petal-7 { animation-delay: 0.9s; }

        /* Inner petals */
        .petal-inner {
          animation: petalOpenSpin 4s ease-in-out infinite;
          transform-origin: bottom center;
          transform-box: fill-box;
        }

        .petal-inner.petal-0 { animation-delay: 0.4s; }
        .petal-inner.petal-1 { animation-delay: 0.5s; }
        .petal-inner.petal-2 { animation-delay: 0.6s; }
        .petal-inner.petal-3 { animation-delay: 0.7s; }
        .petal-inner.petal-4 { animation-delay: 0.8s; }
        .petal-inner.petal-5 { animation-delay: 0.9s; }

        /* Center glow pulse */
        .lotus-center {
          animation: centerGlow 2s ease-in-out infinite;
          transform-origin: center;
        }

        /* Stamens */
        .stamen {
          animation: stamenDance 4s ease-in-out infinite;
          transform-origin: center;
        }

        .stamen-0 { animation-delay: 0s; }
        .stamen-1 { animation-delay: 0.15s; }
        .stamen-2 { animation-delay: 0.3s; }
        .stamen-3 { animation-delay: 0.45s; }
        .stamen-4 { animation-delay: 0.6s; }
        .stamen-5 { animation-delay: 0.75s; }

        /* Floating petals */
        .petal-float-1 {
          animation: petalFall1 5s ease-in-out infinite;
        }

        .petal-float-2 {
          animation: petalFall2 6s ease-in-out infinite;
        }

        .petal-float-3 {
          animation: petalFall3 5.5s ease-in-out infinite;
        }

        .petal-float-4 {
          animation: petalFall4 6.5s ease-in-out infinite;
        }

        /* Sparkles */
        .sparkle {
          animation: sparkleShine 3s ease-in-out infinite;
        }

        .sparkle-1 { animation-delay: 0s; }
        .sparkle-2 { animation-delay: 0.6s; }
        .sparkle-3 { animation-delay: 1.2s; }
        .sparkle-4 { animation-delay: 1.8s; }
        .sparkle-5 { animation-delay: 2.4s; }

        /* Keyframe Animations */

        @keyframes leafSway {
          0%, 100% {
            transform: rotate(0deg) scale(1);
            opacity: 0.5;
          }
          50% {
            transform: rotate(2deg) scale(1.05);
            opacity: 0.7;
          }
        }

        @keyframes lotus3DRotate {
          0%, 100% {
            transform: rotateY(0deg) rotateX(0deg);
          }
          25% {
            transform: rotateY(10deg) rotateX(5deg);
          }
          50% {
            transform: rotateY(0deg) rotateX(10deg);
          }
          75% {
            transform: rotateY(-10deg) rotateX(5deg);
          }
        }

        @keyframes petalOpenSpin {
          0% {
            transform: scaleY(0.6) translateY(2px);
            opacity: 0.7;
          }
          50% {
            transform: scaleY(1) translateY(0px);
            opacity: 1;
          }
          100% {
            transform: scaleY(0.6) translateY(2px);
            opacity: 0.7;
          }
        }

        @keyframes centerGlow {
          0%, 100% {
            transform: scale(1);
            opacity: 1;
          }
          50% {
            transform: scale(1.15);
            opacity: 0.9;
          }
        }

        @keyframes stamenDance {
          0%, 100% {
            transform: scale(0.9) translateY(0px);
            opacity: 0.8;
          }
          50% {
            transform: scale(1.1) translateY(-1px);
            opacity: 1;
          }
        }

        @keyframes petalFall1 {
          0% {
            transform: translate(0, -20px) rotate(0deg);
            opacity: 0;
          }
          20% {
            opacity: 0.8;
          }
          80% {
            opacity: 0.8;
          }
          100% {
            transform: translate(-10px, 40px) rotate(180deg);
            opacity: 0;
          }
        }

        @keyframes petalFall2 {
          0% {
            transform: translate(0, -15px) rotate(0deg);
            opacity: 0;
          }
          20% {
            opacity: 0.7;
          }
          80% {
            opacity: 0.7;
          }
          100% {
            transform: translate(15px, 50px) rotate(-160deg);
            opacity: 0;
          }
        }

        @keyframes petalFall3 {
          0% {
            transform: translate(0, -10px) rotate(0deg);
            opacity: 0;
          }
          20% {
            opacity: 0.6;
          }
          80% {
            opacity: 0.6;
          }
          100% {
            transform: translate(20px, 35px) rotate(140deg);
            opacity: 0;
          }
        }

        @keyframes petalFall4 {
          0% {
            transform: translate(0, -25px) rotate(0deg);
            opacity: 0;
          }
          20% {
            opacity: 0.7;
          }
          80% {
            opacity: 0.7;
          }
          100% {
            transform: translate(-15px, 45px) rotate(-170deg);
            opacity: 0;
          }
        }

        @keyframes sparkleShine {
          0%, 100% {
            opacity: 0;
            transform: scale(0.5);
          }
          50% {
            opacity: 1;
            transform: scale(1.5);
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
