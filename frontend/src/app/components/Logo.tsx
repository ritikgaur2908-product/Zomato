import React from "react";

interface LogoProps {
  className?: string;
  size?: number | string;
}

export default function Logo({ className = "", size = 32 }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 200"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect width="200" height="200" rx="40" fill="#E23744" />
      <path
        d="M60 140C60 140 70 80 100 80C130 80 140 140 140 140"
        stroke="white"
        strokeWidth="12"
        strokeLinecap="round"
      />
      <circle cx="100" cy="65" r="15" fill="white" />
      <path
        d="M85 110L115 110"
        stroke="white"
        strokeWidth="8"
        strokeLinecap="round"
      />
    </svg>
  );
}
