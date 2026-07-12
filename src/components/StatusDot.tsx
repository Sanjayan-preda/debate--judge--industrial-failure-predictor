import type { AssetSummary } from '../types';

interface StatusDotProps {
  risk: AssetSummary['risk_level'];
  className?: string;
}

const colorMap: Record<AssetSummary['risk_level'], string> = {
  low: 'bg-teal shadow-[0_0_6px_rgba(63,199,176,0.5)]',
  medium: 'bg-amber shadow-[0_0_6px_rgba(232,163,61,0.5)]',
  high: 'bg-red shadow-[0_0_6px_rgba(232,86,74,0.5)]',
  unknown: 'bg-text-muted shadow-none',
};

const labelMap: Record<AssetSummary['risk_level'], string> = {
  low: 'Low risk',
  medium: 'Medium risk',
  high: 'High risk',
  unknown: 'Unknown',
};

export default function StatusDot({ risk, className = '' }: StatusDotProps) {
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${colorMap[risk]} ${className}`}
      role="status"
      aria-label={labelMap[risk]}
    />
  );
}