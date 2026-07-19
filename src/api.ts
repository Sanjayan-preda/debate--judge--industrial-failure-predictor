import type { AssetSummary, AssetDetail, CalibrationData } from './types';

/**
 * Frontend API layer — fetches from pre-built static JSON files
 * during build (via api/export_data.py), not from a live backend.
 *
 * In dev mode (npm run dev), the Vite proxy forwards /api/* to the
 * Python API server on port 8001.  In production, these files are
 * served as static assets from the build output.
 */

const DATA_BASE = '/data';

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to load ${url}: ${res.status}`);
  }
  return res.json();
}

export async function fetchAssets(): Promise<AssetSummary[]> {
  return getJson<AssetSummary[]>(`${DATA_BASE}/assets.json`).catch(() => []);
}

export async function fetchAssetDetail(assetId: string): Promise<AssetDetail | null> {
  // Sanitise asset ID for the filename (same logic as export script)
  const safeName = assetId.replace('/', '_').replace(/ /g, '_');
  return getJson<AssetDetail>(`${DATA_BASE}/assets/${safeName}.json`).catch(() => null);
}

export async function fetchCalibration(): Promise<CalibrationData | null> {
  return getJson<CalibrationData>(`${DATA_BASE}/calibration.json`).catch(() => null);
}