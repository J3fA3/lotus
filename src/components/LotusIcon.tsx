import React from 'react';

interface LotusIconProps {
  className?: string;
  size?: number;
}

/**
 * Minimalist Lotus flower icon - Zen aesthetic with clean lines
 * Represents tranquility, enlightenment, and natural beauty
 */
export const LotusIcon: React.FC<LotusIconProps> = ({
  className = "",
  size = 24
}) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Center circle - lotus seed pod */}
      <circle
        cx="12"
        cy="12"
        r="2"
        fill="currentColor"
        opacity="0.9"
      />

      {/* Inner petals */}
      <path
        d="M12 10C10.5 10 9.5 8.5 9.5 6.5C9.5 5.5 10 4.5 10.5 4.5C11 4.5 11.5 5.5 11.5 7C11.5 8 11.8 9 12 10Z"
        fill="currentColor"
        opacity="0.7"
      />
      <path
        d="M12 10C13.5 10 14.5 8.5 14.5 6.5C14.5 5.5 14 4.5 13.5 4.5C13 4.5 12.5 5.5 12.5 7C12.5 8 12.2 9 12 10Z"
        fill="currentColor"
        opacity="0.7"
      />

      {/* Middle petals - left and right */}
      <path
        d="M10 12C10 10.5 8.5 9.5 6.5 9.5C5.5 9.5 4.5 10 4.5 10.5C4.5 11 5.5 11.5 7 11.5C8 11.5 9 11.8 10 12Z"
        fill="currentColor"
        opacity="0.6"
      />
      <path
        d="M14 12C14 10.5 15.5 9.5 17.5 9.5C18.5 9.5 19.5 10 19.5 10.5C19.5 11 18.5 11.5 17 11.5C16 11.5 15 11.8 14 12Z"
        fill="currentColor"
        opacity="0.6"
      />

      {/* Outer petals */}
      <path
        d="M12 14C10.5 14 9.5 15.5 9.5 17.5C9.5 18.5 10 19.5 10.5 19.5C11 19.5 11.5 18.5 11.5 17C11.5 16 11.8 15 12 14Z"
        fill="currentColor"
        opacity="0.5"
      />
      <path
        d="M12 14C13.5 14 14.5 15.5 14.5 17.5C14.5 18.5 14 19.5 13.5 19.5C13 19.5 12.5 18.5 12.5 17C12.5 16 12.2 15 12 14Z"
        fill="currentColor"
        opacity="0.5"
      />

      {/* Bottom-left and bottom-right petals */}
      <path
        d="M10.5 13.5C9.5 12.5 7.5 13 6 14C5 14.5 4.5 15.5 4.8 16C5.1 16.5 6.5 16.5 7.8 15.8C8.8 15.3 9.8 14.5 10.5 13.5Z"
        fill="currentColor"
        opacity="0.45"
      />
      <path
        d="M13.5 13.5C14.5 12.5 16.5 13 18 14C19 14.5 19.5 15.5 19.2 16C18.9 16.5 17.5 16.5 16.2 15.8C15.2 15.3 14.2 14.5 13.5 13.5Z"
        fill="currentColor"
        opacity="0.45"
      />
    </svg>
  );
};
