import { useState } from 'react';
import { useLoaderData } from 'react-router-dom';
import { ArrowLeft, Cpu, ChevronDown, ChevronUp, Check, X, Clock, Activity, BarChart3, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AssetDetail as AssetDetailType } from '../types';
import RiskGauge from './RiskGauge';
import StatusDot from './StatusDot';

const viewLabels = [
  { key: 'view1_text', name: 'Vibration Analyst', icon: 'V' },
  { key: 'view2_text', name: 'Operations Expert', icon: 'O' },
  { key: 'view3_text', name: 'Impact Assessor', icon: 'I' },
  { key: 'view4_text', name: 'Quality Reviewer', icon: 'Q' },
];

const dismissReasons = [
  'Likely sensor glitch — known false reading',
  'Already inspected — no issue found',
  'Already scheduled for next maintenance',
  'Similar reading before — no failure occurred',
  'Different issue — already addressed',
];

export default function AssetDetail() {
  const detail = useLoaderData() as AssetDetailType;
  const [showReasoning, setShowReasoning] = useState(false);
  const [actionTaken, setActionTaken] = useState<string | null>(null);
  const [showDismissOptions, setShowDismissOptions] = useState(false);

  if (!detail) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-text-muted text-sm">Asset not found</p>
      </div>
    );
  }

  const judge = detail.judge_output;
  const prob = detail.failure_probability ?? judge?.failure_probability ?? 0;
  const conf = detail.confidence ?? judge?.confidence ?? 0;

  const riskLabel = prob >= 0.6
    ? 'High risk'
    : prob >= 0.3
      ? 'Moderate risk'
      : 'Low risk';

  const confidenceLabel = conf >= 0.8
    ? 'We are highly confident in this assessment.'
    : conf >= 0.5
      ? 'We are moderately confident in this assessment.'
      : 'We have low confidence in this assessment.';

  return (
    <div className="max-w-4xl space-y-6 animate-fade-in">
      {/* Back link */}
      <Link
        to="/dashboard"
        className="inline-flex items-center gap-1.5 text-sm text-text-muted hover:text-text-primary transition-colors"
      >
        <ArrowLeft className="w-4 h-4" aria-hidden="true" />
        Back to overview
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <Cpu className="w-6 h-6 text-text-muted shrink-0" aria-hidden="true" />
          <div>
            <h1 className="font-heading text-xl font-semibold text-text-primary tracking-tight truncate">
              {detail.asset_id}
            </h1>
            <p className="text-xs text-text-muted font-mono mt-0.5">
              Assessment #{detail.id} &middot; {new Date(detail.timestamp).toLocaleString()}
              {detail.sample_count && <span> &middot; {detail.sample_count.toLocaleString()} data points</span>}
            </p>
          </div>
        </div>
        <StatusDot risk={prob >= 0.6 ? 'high' : prob >= 0.3 ? 'medium' : 'low'} />
      </div>

      {/* Gauge + Sensor Data Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 flex justify-center md:justify-start">
          <RiskGauge probability={prob} confidence={conf} />
        </div>

        {/* Sensor metrics */}
        <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
          <h3 className="text-xs font-semibold font-heading text-text-primary flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-text-muted" aria-hidden="true" />
            Sensor Readings
          </h3>
          {detail.rms !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-muted">Vibration level (RMS)</span>
              <span className="text-sm font-mono font-medium text-text-primary">{detail.rms.toFixed(4)}</span>
            </div>
          )}
          {detail.kurtosis !== undefined && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-muted">Signal shape (Kurtosis)</span>
              <span className="text-sm font-mono font-medium text-text-primary">{detail.kurtosis.toFixed(4)}</span>
            </div>
          )}
          {detail.risk_level && (
            <div className="flex items-center justify-between pt-2 border-t border-border">
              <span className="text-xs text-text-muted">Risk Level</span>
              <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded-full ${
                detail.risk_level === 'high' ? 'bg-red-500/10 text-red-500' :
                detail.risk_level === 'medium' ? 'bg-amber-500/10 text-amber-500' :
                'bg-teal/10 text-teal'
              }`}>
                {detail.risk_level}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Health Check Reason */}
      {detail.gate_reason && (
        <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4 text-text-muted" aria-hidden="true" />
            <h2 className="font-heading text-sm font-semibold text-text-primary">Health Check</h2>
          </div>
          <p className="text-sm text-text-secondary leading-relaxed">{detail.gate_reason}</p>
        </div>
      )}

      {/* Assessment */}
      {judge && (
        <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-6 h-6 rounded-full bg-teal/10 text-teal flex items-center justify-center text-xs font-bold">
              E
            </span>
            <h2 className="font-heading text-sm font-semibold text-text-primary">Senior Evaluation</h2>
            {judge.disagreement_flag && (
              <span className="ml-auto flex items-center gap-1.5 text-xs text-amber bg-amber/10 px-2.5 py-1 rounded-full font-medium">
                <AlertTriangle className="w-3 h-3" aria-hidden="true" />
                Flagged for review
              </span>
            )}
          </div>
          <p className="text-sm text-text-secondary leading-relaxed">
            This asset shows a <strong className="text-text-primary">{riskLabel}</strong> of disruption{' '}
            with <strong className="text-text-primary">{Math.round(conf * 100)}%</strong> confidence.
            {confidenceLabel && (
              <span className="block mt-1 text-text-muted">{confidenceLabel}</span>
            )}
            {judge.disagreement_flag && (
              <span className="block mt-1 text-amber/80">
                The assessors had differing views on this reading — the senior evaluator has weighed all perspectives to reach this conclusion.
              </span>
            )}
          </p>
          <p className="text-sm text-text-secondary leading-relaxed">
            {judge.rationale || detail.gate_reason}
          </p>
        </div>
      )}

      {/* Action buttons */}
      {!actionTaken && (
        <div className="flex flex-wrap gap-3">
          <button
            onClick={() => setActionTaken('confirmed')}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-teal text-white text-sm font-medium rounded-lg hover:bg-teal-dim active:scale-[0.97] transition-all duration-150 focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-2"
          >
            <Check className="w-4 h-4" aria-hidden="true" />
            Confirm &amp; schedule maintenance
          </button>
          <button
            onClick={() => setShowDismissOptions(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-surface border border-border text-text-primary text-sm font-medium rounded-lg hover:bg-surface-hover active:scale-[0.97] transition-all duration-150 focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-2"
          >
            <X className="w-4 h-4" aria-hidden="true" />
            Dismiss
          </button>
          <button
            onClick={() => setActionTaken('snoozed')}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-surface border border-border text-text-primary text-sm font-medium rounded-lg hover:bg-surface-hover active:scale-[0.97] transition-all duration-150 focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-2"
          >
            <Clock className="w-4 h-4" aria-hidden="true" />
            Remind me later
          </button>
        </div>
      )}

      {/* Dismiss reason selector */}
      {showDismissOptions && (
        <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
          <p className="text-xs font-medium text-text-primary">Why are you dismissing this?</p>
          <div className="flex flex-col gap-1.5">
            {dismissReasons.map((reason) => (
              <button
                key={reason}
                onClick={() => {
                  setActionTaken(`dismissed: ${reason}`);
                  setShowDismissOptions(false);
                }}
                className="text-left text-sm text-text-secondary px-3 py-2 rounded-lg hover:bg-surface-hover hover:text-text-primary transition-colors active:scale-[0.98]"
              >
                {reason}
              </button>
            ))}
          </div>
          <button
            onClick={() => setShowDismissOptions(false)}
            className="text-xs text-text-muted hover:text-text-primary transition-colors"
          >
            Cancel
          </button>
        </div>
      )}

      {/* Action confirmation */}
      {actionTaken && (
        <div className="bg-surface border border-teal/20 rounded-xl p-4 flex items-center gap-3 animate-fade-in">
          <Check className="w-4 h-4 text-teal shrink-0" aria-hidden="true" />
          <p className="text-sm text-text-primary">
            {actionTaken === 'confirmed' && 'Maintenance has been scheduled. We\'ll track this asset for you.'}
            {actionTaken === 'snoozed' && 'We\'ll remind you about this assessment later.'}
            {actionTaken.startsWith('dismissed:') && `Dismissed — ${actionTaken.replace('dismissed: ', '')}`}
          </p>
          <button
            onClick={() => setActionTaken(null)}
            className="ml-auto text-xs text-text-muted hover:text-text-primary transition-colors"
          >
            Undo
          </button>
        </div>
      )}

      {/* Assessor reasoning — collapsible */}
      {judge && (
        <div>
          <button
            onClick={() => setShowReasoning((v) => !v)}
            className="flex items-center gap-2 text-sm font-heading font-semibold text-text-primary hover:text-teal transition-colors"
            aria-expanded={showReasoning}
            aria-controls="reasoning-panel"
          >
            {showReasoning ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}
            {showReasoning ? 'Hide assessment details' : 'Show assessment details'}
            {detail.view1_text && (
              <span className="text-[11px] text-text-muted font-mono font-normal ml-1">
                (4 assessor reports)
              </span>
            )}
          </button>
          {showReasoning && (
            <div id="reasoning-panel" className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 animate-fade-in">
              {detail.view1_text ? (
                viewLabels.map(({ key, name, icon }) => {
                  const text = detail[key as keyof AssetDetailType] as string | null;
                  return (
                    <div
                      key={key}
                      className="bg-surface border border-border rounded-xl p-4 space-y-2"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-teal/10 text-teal flex items-center justify-center text-[11px] font-bold font-mono" aria-hidden="true">
                          {icon}
                        </span>
                        <span className="text-xs font-medium text-text-primary">{name}</span>
                      </div>
                      <p className="text-xs text-text-secondary leading-relaxed">
                        {text ?? <span className="italic text-text-muted">No report recorded</span>}
                      </p>
                    </div>
                  );
                })
              ) : (
                <div className="col-span-full bg-surface border border-border rounded-xl p-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-teal/10 text-teal flex items-center justify-center text-[11px] font-bold font-mono">S</span>
                    <span className="text-xs font-medium text-text-primary">Standard Check</span>
                  </div>
                  <p className="text-xs text-text-secondary leading-relaxed">
                    This asset passed the initial health check — no advanced analysis was needed. The assessment is based on standard sensor thresholds (vibration level, signal shape, frequency bands).
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}