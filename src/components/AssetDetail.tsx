import { useState } from 'react';
import { useLoaderData } from 'react-router-dom';
import { ArrowLeft, Cpu, ChevronDown, ChevronUp, Check, X, Clock } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { AssetDetail as AssetDetailType } from '../types';
import RiskGauge from './RiskGauge';
import StatusDot from './StatusDot';

const viewLabels = [
  { key: 'view1_text', name: 'Signal Analyst', icon: 'S' },
  { key: 'view2_text', name: 'Domain Expert', icon: 'D' },
  { key: 'view3_text', name: 'Risk Assessor', icon: 'R' },
  { key: 'view4_text', name: 'Skeptic', icon: 'K' },
];

const dismissReasons = [
  'Known false alarm — sensor glitch',
  'Already inspected — no issue found',
  'Scheduled for next maintenance anyway',
  'Similar reading before — no failure occurred',
  'Different fault — already addressed',
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

  const riskLabel = judge
    ? judge.failure_probability >= 0.6
      ? 'High risk'
      : judge.failure_probability >= 0.3
        ? 'Moderate risk'
        : 'Low risk'
    : 'Unknown';

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
              Prediction #{detail.id} &middot; {new Date(detail.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
        {judge && <StatusDot risk={judge.failure_probability >= 0.6 ? 'high' : judge.failure_probability >= 0.3 ? 'medium' : 'low'} />}
      </div>

      {/* Gauge */}
      {judge && (
        <div className="flex justify-center">
          <RiskGauge probability={judge.failure_probability} confidence={judge.confidence} />
        </div>
      )}

      {/* Assessment — natural language, no jargon */}
      {judge && (
        <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
          <div className="flex items-center gap-2 mb-2">
            <span className="w-6 h-6 rounded-full bg-teal/10 text-teal flex items-center justify-center text-xs font-bold">
              A
            </span>
            <h2 className="font-heading text-sm font-semibold text-text-primary">Assessment</h2>
          </div>
          <p className="text-sm text-text-secondary leading-relaxed">
            This is a <strong className="text-text-primary">{riskLabel}</strong> prediction{' '}
            with <strong className="text-text-primary">{Math.round(judge.confidence * 100)}%</strong> confidence.
          </p>
          <p className="text-sm text-text-secondary leading-relaxed">{judge.rationale}</p>
        </div>
      )}

      {/* Action buttons */}
      {judge && !actionTaken && (
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
            Snooze
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
            {actionTaken === 'confirmed' && 'Confirmed — maintenance has been scheduled.'}
            {actionTaken === 'snoozed' && 'Snoozed — you\'ll be reminded about this prediction later.'}
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

      {/* Persona reasoning — collapsible */}
      <div>
        <button
          onClick={() => setShowReasoning((v) => !v)}
          className="flex items-center gap-2 text-sm font-heading font-semibold text-text-primary hover:text-teal transition-colors"
          aria-expanded={showReasoning}
          aria-controls="reasoning-panel"
        >
          {showReasoning ? <ChevronUp className="w-4 h-4" aria-hidden="true" /> : <ChevronDown className="w-4 h-4" aria-hidden="true" />}
          {showReasoning ? 'Hide reasoning' : 'Show reasoning'}
        </button>
        {showReasoning && (
          <div id="reasoning-panel" className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 animate-fade-in">
            {viewLabels.map(({ key, name, icon }) => {
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
                    {text ?? <span className="italic text-text-muted">No argument recorded</span>}
                  </p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}