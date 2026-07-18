import { useEffect, useMemo, useRef, useState } from 'react';

interface RiskGaugeProps {
  probability: number;
  confidence: number;
  size?: number;
}

export default function RiskGauge({ probability, confidence, size = 160 }: RiskGaugeProps) {
  const prefRef = useRef(true);
  const [animAngle, setAnimAngle] = useState(prefRef.current ? -90 : -90 + probability * 180);

  useEffect(() => {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    prefRef.current = mql.matches;
    if (!mql.matches) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setAnimAngle(-90 + probability * 180);
        });
      });
    } else {
      setAnimAngle(-90 + probability * 180);
    }
  }, [probability]);

  const angle = animAngle;
  const needleColor = useMemo(() => {
    if (probability >= 0.6) return '#E8564A';
    if (probability >= 0.3) return '#E8A33D';
    return '#3FC7B0';
  }, [probability]);

  const cx = size / 2;
  const cy = size / 2;
  const r = size * 0.38;
  const strokeW = size * 0.06;

  const arcPath = (startAngle: number, endAngle: number, offset: number) => {
    const startRad = ((startAngle - 90) * Math.PI) / 180;
    const endRad = ((endAngle - 90) * Math.PI) / 180;
    const x1 = cx + (r + offset) * Math.cos(startRad);
    const y1 = cy + (r + offset) * Math.sin(startRad);
    const x2 = cx + (r + offset) * Math.cos(endRad);
    const y2 = cy + (r + offset) * Math.sin(endRad);
    const large = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r + offset} ${r + offset} 0 ${large} 1 ${x2} ${y2}`;
  };

  const needleRad = ((angle - 90) * Math.PI) / 180;
  const needleLen = r * 0.85;
  const tipX = cx + needleLen * Math.cos(needleRad);
  const tipY = cy + needleLen * Math.sin(needleRad);

  const confidenceLabel = confidence >= 0.8
    ? 'high confidence'
    : confidence >= 0.5
      ? 'moderate confidence'
      : 'low confidence';

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="shrink-0"
      role="img"
      aria-label={`Risk gauge: ${Math.round(probability * 100)}% disruption likelihood`}
    >
      {/* Background arc */}
      <path
        d={arcPath(-90, 90, 0)}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={strokeW}
        strokeLinecap="round"
      />

      {/* Coloured arc segments */}
      <path
        d={arcPath(-90, -18, 0)}
        fill="none"
        stroke="#3FC7B0"
        strokeWidth={strokeW}
        strokeLinecap="round"
        opacity={probability <= 0.3 ? 0.85 : 0.25}
      />
      <path
        d={arcPath(-18, 54, 0)}
        fill="none"
        stroke="#E8A33D"
        strokeWidth={strokeW}
        strokeLinecap="round"
        opacity={probability > 0.3 && probability <= 0.6 ? 0.85 : 0.25}
      />
      <path
        d={arcPath(54, 90, 0)}
        fill="none"
        stroke="#E8564A"
        strokeWidth={strokeW}
        strokeLinecap="round"
        opacity={probability > 0.6 ? 0.85 : 0.25}
      />

      {/* Tick labels */}
      <text x={cx - r - 6} y={cy + 4} textAnchor="end" dominantBaseline="middle" className="fill-text-muted text-[10px] font-mono">
        0%
      </text>
      <text x={cx + r + 6} y={cy + 4} textAnchor="start" dominantBaseline="middle" className="fill-text-muted text-[10px] font-mono">
        100%
      </text>

      {/* Needle */}
      <line
        x1={cx}
        y1={cy}
        x2={tipX}
        y2={tipY}
        stroke={needleColor}
        strokeWidth={2}
        strokeLinecap="round"
        style={{ transition: 'all 0.7s cubic-bezier(0.34, 1.56, 0.64, 1)' }}
      />

      {/* Centre dot */}
      <circle cx={cx} cy={cy} r={3.5} fill={needleColor} />

      {/* Centre value */}
      <text x={cx} y={cy + r * 0.5} textAnchor="middle" className="fill-text-primary font-heading font-bold" style={{ fontSize: size * 0.13 }}>
        {Math.round(probability * 100)}%
      </text>
      <text x={cx} y={cy + r * 0.5 + 16} textAnchor="middle" className="fill-text-muted text-[10px]">
        {confidenceLabel}
      </text>
    </svg>
  );
}