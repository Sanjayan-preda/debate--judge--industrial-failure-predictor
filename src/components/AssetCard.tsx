import { Link } from 'react-router-dom';
import { ChevronRight, Cpu } from 'lucide-react';
import type { AssetSummary } from '../types';
import StatusDot from './StatusDot';
import RiskGauge from './RiskGauge';

interface AssetCardProps {
  asset: AssetSummary;
}

export default function AssetCard({ asset }: AssetCardProps) {
  const prob = asset.failure_probability;
  const probPct = Math.round(prob * 100);

  return (
    <Link
      to={`/asset/${encodeURIComponent(asset.asset_id)}`}
      className="group block bg-surface border border-border rounded-xl p-4 hover:bg-surface-hover transition-all duration-200 active:scale-[0.98] focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-2"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <Cpu className="w-4 h-4 text-text-muted shrink-0" aria-hidden="true" />
          <span className="font-mono text-sm text-text-primary truncate">{asset.asset_id}</span>
        </div>
        <StatusDot risk={asset.risk_level} />
      </div>

      {/* Gauge */}
      <div className="flex justify-center -mx-2">
        <RiskGauge probability={prob} confidence={asset.confidence} size={120} />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
        <span className="text-[11px] text-text-muted font-mono">
          {new Date(asset.timestamp).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </span>
        <span className="flex items-center gap-1 text-[11px] font-medium text-teal group-hover:text-teal-dim transition-colors">
          Details <ChevronRight className="w-3 h-3" aria-hidden="true" />
        </span>
      </div>
    </Link>
  );
}