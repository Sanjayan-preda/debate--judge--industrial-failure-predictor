import { useLoaderData } from 'react-router-dom';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ScatterChart,
  Scatter,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { BarChart3, Target } from 'lucide-react';
import type { CalibrationData } from '../types';

export default function Calibration() {
  const data = useLoaderData() as CalibrationData | null;

  if (!data || data.total_predictions === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <BarChart3 className="w-10 h-10 text-text-muted" aria-hidden="true" />
        <p className="text-text-muted text-sm">No accuracy data yet</p>
        <p className="text-text-muted/60 text-xs">
          Run at least a few assessments to see accuracy metrics.
        </p>
      </div>
    );
  }

  const bins = data.calibration_curve ?? [];
  const points = data.points ?? [];

  return (
    <div className="max-w-4xl space-y-6 animate-fade-in">
      <h1 className="font-heading text-xl font-semibold text-text-primary tracking-tight">
        Accuracy &amp; Trust
      </h1>

      {/* Brier score card */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal/10 flex items-center justify-center shrink-0">
            <Target className="w-5 h-5 text-teal" aria-hidden="true" />
          </div>
          <div>
            <p className="text-[11px] text-text-muted font-medium uppercase tracking-wider">Accuracy Score</p>
            <p className="font-heading text-2xl font-bold text-text-primary tabular-nums">
              {data.brier_score.toFixed(4)}
            </p>
          </div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-amber/10 flex items-center justify-center shrink-0">
            <BarChart3 className="w-5 h-5 text-amber" aria-hidden="true" />
          </div>
          <div>
            <p className="text-[11px] text-text-muted font-medium uppercase tracking-wider">Assessments</p>
            <p className="font-heading text-2xl font-bold text-text-primary tabular-nums">
              {data.total_predictions}
            </p>
          </div>
        </div>
        <div className="bg-surface border border-border rounded-xl p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-teal/10 flex items-center justify-center shrink-0">
            <span className="text-teal font-bold text-lg font-mono">✓</span>
          </div>
          <div>
            <p className="text-[11px] text-text-muted font-medium uppercase tracking-wider">Performance Rating</p>
            <p className="text-sm text-text-primary">
              {data.brier_score < 0.1 ? 'Excellent' : data.brier_score < 0.2 ? 'Good' : 'Needs improvement'}
            </p>
          </div>
        </div>
      </div>

      {/* Calibration curve */}
      {bins.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-4">
          <h2 className="font-heading text-sm font-semibold text-text-primary mb-4">Calibration Curve</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={bins} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="bin_label"
                tick={{ fill: '#8B8B9E', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                tickLine={false}
                label={{ value: 'Predicted risk range', position: 'bottom', fill: '#8B8B9E', fontSize: 11, offset: -4 }}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: '#8B8B9E', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                label={{ value: 'Actual disruption rate', angle: -90, position: 'insideLeft', fill: '#8B8B9E', fontSize: 11, style: { textAnchor: 'middle' } }}
              />
              <Tooltip
                contentStyle={{
                  background: '#1A1A24',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 8,
                  fontSize: 12,
                  color: '#E4E4ED',
                }}
                formatter={(value: number) => `${(value * 100).toFixed(1)}%`}
              />
              <ReferenceLine
                y={0.5}
                stroke="rgba(255,255,255,0.08)"
                strokeDasharray="4 4"
              />
              <Bar dataKey="actual_rate" fill="#3FC7B0" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Scatter: predicted vs actual */}
      {points.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-4">
          <h2 className="font-heading text-sm font-semibold text-text-primary mb-4">Predicted Risk vs Actual Outcome</h2>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis
                dataKey="predicted_probability"
                domain={[0, 1]}
                tick={{ fill: '#8B8B9E', fontSize: 11 }}
                axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
                tickLine={false}
                tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
                label={{ value: 'Predicted risk', position: 'bottom', fill: '#8B8B9E', fontSize: 11, offset: -4 }}
              />
              <YAxis
                dataKey="actual_outcome"
                domain={[0, 1]}
                tick={{ fill: '#8B8B9E', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v: number) => v === 0 ? 'No disruption' : 'Disruption'}
                label={{ value: 'Actual outcome', angle: -90, position: 'insideLeft', fill: '#8B8B9E', fontSize: 11, style: { textAnchor: 'middle' } }}
              />
              <Tooltip
                contentStyle={{
                  background: '#1A1A24',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 8,
                  fontSize: 12,
                  color: '#E4E4ED',
                }}
                formatter={(value: number) => (value * 100).toFixed(1) + '%'}
              />
              <Scatter
                data={points}
                fill="#3FC7B0"
                opacity={0.6}
                r={5}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}