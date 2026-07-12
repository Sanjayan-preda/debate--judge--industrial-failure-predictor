import type { AssetSummary, AssetDetail, CalibrationData } from './types';

const BASE = '/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchAssets(): Promise<AssetSummary[]> {
  return get<AssetSummary[]>('/assets').catch(() => []);
}

export async function fetchAssetDetail(assetId: string): Promise<AssetDetail | null> {
  return get<AssetDetail>(`/assets/${encodeURIComponent(assetId)}`).catch(() => null);
}

export async function fetchCalibration(): Promise<CalibrationData | null> {
  return get<CalibrationData>('/calibration').catch(() => null);
}