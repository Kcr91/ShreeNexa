import React from "react";

interface Props {
  height?: string | number;
  width?: string | number;
  borderRadius?: string;
  count?: number;
}

export const LoadingSkeleton: React.FC<Props> = ({
  height = "20px",
  width = "100%",
  borderRadius = "var(--radius-sm)",
  count = 1,
}) => {
  const items = Array.from({ length: count }, (_, i) => i);

  return (
    <div role="status" aria-label="Loading content..." style={{ display: "flex", flexDirection: "column", gap: "var(--spacing-2)" }}>
      {items.map((key) => (
        <div
          key={key}
          style={{
            height,
            width,
            borderRadius,
            backgroundColor: "var(--bg-surface)",
            opacity: 0.6,
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
      ))}
      <span style={{ display: "none" }}>Loading...</span>
      <style>{`
        @keyframes pulse {
          0% { opacity: 0.3; }
          50% { opacity: 0.7; }
          100% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
};
