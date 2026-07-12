import { useLoaderData } from 'react-router-dom';
import type { AssetSummary } from '../types';
import AssetCard from './AssetCard';

export default function AssetList() {
  const assets = useLoaderData() as AssetSummary[];

  if (!assets || assets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <div className="w-12 h-12 rounded-xl bg-surface border border-border flex items-center justify-center">
          <span className="text-2xl text-text-muted">∅</span>
        </div>
        <p className="text-text-muted text-sm">No predictions yet</p>
        <p className="text-text-muted/60 text-xs">
          Run the predictor to generate predictions — they'll appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {assets.map((asset) => (
        <AssetCard key={asset.prediction_id ?? asset.asset_id} asset={asset} />
      ))}
    </div>
  );
}