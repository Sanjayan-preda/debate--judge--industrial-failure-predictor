import { useLoaderData } from 'react-router-dom';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { Target, BarChart3 } from 'lucide-react';
import type { CalibrationData } from '../types';

/* ── Colour palette tokens (mirrors @theme in index.css) ──────────── */
const TEAL = '#3FC7B0';
const TEXT_MUTED = '#8A919C';
const TEXT_SECONDARY = '#B0B5BD';
const SURFACE_BG = '#24282E';
const CARD_BG = '#1B1E22';
const GRID_LINE = 'rgba(255,255,255,0.05)';
const IDEAL_LINE = '#5A5F66';

/* ── Tooltip overrides ────────────────────────────────────────────── */
const tooltipStyle = {
  background: SURFACE_BG,
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 8,
  fontSize: 12,
  color: '#E8EAED',
  outline: 'none',
};

/* ── Helper: format a 0-1 value as percentage string ──────────────── */
const pct = (v: number) => `${(v * 100).toFixed(0)}%`;

/* ═══════════════════════════════════════════════════════════════════ */
/*  CALIBRATION CHART                                                 */
/* ═══════════════════════════════════════════════════════════════════ */

function CalibrationChart({ bins }: { bins: CalibrationData['calibration_curve'] }) {
  const hasData = bins.some((b) => b.count > 0);

  if (!hasData) {
    return (
      <div className="bg-surface border border-border rounded-xl p-6">
        <h2 className="font-heading text-sm font-semibold text-text-primary mb-2">
          Calibration
        </h2>
        <p className="text-text-muted text-xs leading-relaxed">
          No confirmed outcomes yet. As predictions are compared against actual
          results, this chart will show how well our confidence matches reality.
        </p>
      </div>
    );
  }

  // Build chart data: bin_mid as x, actual_rate as y, plus ideal line
  const chartData = bins.map((b) => ({
    label: b.bin_label,
    mid: b.bin_mid,
    actual: b.actual_rate,
    ideal: b.bin_mid,
    count: b.count,
  }));

  return (
    <div className="bg-surface border border-border rounded-xl p-6">
      <h2 className="font-heading text-sm font-semibold text-text-primary mb-1">
        Calibration
      </h2>
      <p className="text-text-muted text-xs mb-4">
        Predicted confidence vs actual outcome rate — the closer to the dashed
        line, the more accurate the system.
      </p>

      <ResponsiveContainer width="100%" height={280}>
        <LineChart
          data={chartData}
          margin={{ top: 8, right: 16, bottom: 8, left: 8 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={GRID_LINE} />
          <XAxis
            dataKey="mid"
            tick={{ fill: TEXT_MUTED, fontSize: 11 }}
            axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            tickLine={false}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            label={{
              value: 'Predicted confidence',
              position: 'bottom',
              fill: TEXT_MUTED,
              fontSize: 11,
              offset: -4,
            }}
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fill: TEXT_MUTED, fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            label={{
              value: 'Actual failure rate',
              angle: -90,
              position: 'insideLeft',
              fill: TEXT_MUTED,
              fontSize: 11,
              style: { textAnchor: 'middle' },
            }}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(_value: number, _name: string, props: { payload: { actual: number; ideal: number; count: number; label: string } }) => {
              const p = props.payload;
              return [
                <span key="actual">
                  Actual: {pct(p.actual)}
                  <br />
                  Ideal: {pct(p.ideal)}
                  <br />
                  <span style={{ color: TEXT_MUTED }}>
                    {p.count} prediction{p.count !== 1 ? 's' : ''} in this band
                  </span>
                </span>,
              ];
            }}
            labelFormatter={() => ''}
          />
          {/* Ideal calibration line (dashed, gray) */}
          <ReferenceLine
            segment={[
              { x: 0, y: 0 },
              { x: 1, y: 1 },
            ]}
            stroke={IDEAL_LINE}
            strokeDasharray="4 4"
            strokeWidth={1.5}
          />
          {/* Actual calibration line */}
          <Line
            type="monotone"
            dataKey="actual"
            stroke={TEAL}
            strokeWidth={2.5}
            dot={{ r: 4, fill: TEAL, strokeWidth: 0 }}
            activeDot={{ r: 6, fill: TEAL, strokeWidth: 0 }}
            name="Actual"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════ */
/*  AGENT TRUST SECTION                                               */
/* ═══════════════════════════════════════════════════════════════════ */

function AgentTrust({ agents }: { agents: CalibrationData['agent_trust'] }) {
  const hasData = agents.some((a) => a.total_count > 0);

  if (!hasData) {
    return (
      <div className="bg-surface border border-border rounded-xl p-6">
        <h2 className="font-heading text-sm font-semibold text-text-primary mb-2">
          Debate agent trust weighting
        </h2>
        <p className="text-text-muted text-xs leading-relaxed">
          Once predictions have confirmed outcomes, this section will show which
          debate perspectives are most reliable.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-6">
      <h2 className="font-heading text-sm font-semibold text-text-primary mb-1">
        Debate agent trust weighting
      </h2>
      <p className="text-text-muted text-xs mb-5">
        How often each agent's lean matched the actual outcome — higher is
        better.
      </p>

      <div className="flex flex-col gap-4">
        {agents.map((agent) => {
          const pctVal = agent.accuracy * 100;
          // Colour based on accuracy
          const barColor =
            pctVal >= 80
              ? TEAL
              : pctVal >= 60
                ? '#E8A33D'
                : '#E8564A';

          return (
            <div key={agent.agent_name}>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm text-text-primary font-medium">
                  {agent.label}
                </span>
                <span
                  className="font-mono text-sm tabular-nums"
                  style={{ color: barColor }}
                >
                  {pctVal.toFixed(0)}%
                </span>
              </div>
              {/* Progress bar */}
              <div className="relative h-2 bg-[#34383E] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out"
                  style={{
                    width: `${pctVal}%`,
                    backgroundColor: barColor,
                  }}
                />
              </div>
              <p className="text-[11px] text-text-muted mt-1">
                {agent.match_count} of {agent.total_count} correct
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════ */
/*  MAIN COMPONENT                                                    */
/* ═══════════════════════════════════════════════════════════════════ */

export default function Calibration() {
  const data = useLoaderData() as CalibrationData | null;

  const isEmpty = !data || data.total_predictions === 0;

  return (
    <div className="max-w-4xl space-y-6 animate-fade-in">
      <h1 className="font-heading text-xl font-semibold text-text-primary tracking-tight">
        System accuracy
      </h1>
      <p className="text-text-muted text-sm -mt-4">
        How well our predictions match reality, and which debate agents earn
        the most trust.
      </p>

      {/* ── Metric cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Brier score */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-teal/10 flex items-center justify-center shrink-0">
              <Target className="w-5 h-5 text-teal" aria-hidden="true" />
            </div>
            <div>
              <p className="text-[11px] text-text-muted font-medium uppercase tracking-wider">
                Brier score
              </p>
              <p className="font-heading text-2xl font-bold text-text-primary tabular-nums">
                {isEmpty ? '—' : data!.brier_score.toFixed(4)}
              </p>
            </div>
          </div>
          <p className="text-[11px] text-text-muted leading-relaxed">
            Lower is better — measures how well confidence matches reality.
          </p>
        </div>

        {/* Predictions scored */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-amber/10 flex items-center justify-center shrink-0">
              <BarChart3 className="w-5 h-5 text-amber" aria-hidden="true" />
            </div>
            <div>
              <p className="text-[11px] text-text-muted font-medium uppercase tracking-wider">
                Predictions scored
              </p>
              <p className="font-heading text-2xl font-bold text-text-primary tabular-nums">
                {isEmpty ? '0' : data!.total_predictions.toLocaleString()}
              </p>
            </div>
          </div>
          <p className="text-[11px] text-text-muted leading-relaxed">
            Predictions with a confirmed outcome to compare against.
          </p>
        </div>
      </div>

      {/* ── Calibration chart ────────────────────────────────────────── */}
      <CalibrationChart
        bins={
          data?.calibration_curve ?? [
            { bin_label: '0–10%', bin_mid: 0.05, actual_rate: 0, count: 0 },
          ]
        }
      />

      {/* ── Agent trust ──────────────────────────────────────────────── */}
      <AgentTrust agents={data?.agent_trust ?? []} />
    </div>
  );
}