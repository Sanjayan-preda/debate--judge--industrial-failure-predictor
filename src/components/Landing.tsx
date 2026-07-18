import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Activity, Cloud, Cpu, ShieldCheck } from 'lucide-react';

/* ── Animated gauge (hero visual centerpiece) ────────────────────────── */

function HeroGauge() {
  const ref = useRef(true);
  const [angle, setAngle] = useState(-90);

  useEffect(() => {
    const mql = window.matchMedia('(prefers-reduced-motion: reduce)');
    ref.current = mql.matches;
    if (!mql.matches) {
      // Sweep from 0 to ~65% after mount
      const t = setTimeout(() => setAngle(-90 + 0.65 * 180), 400);
      return () => clearTimeout(t);
    } else {
      setAngle(-90 + 0.65 * 180);
    }
  }, []);

  const needleColor = '#E8A33D';
  const cx = 80;
  const cy = 80;
  const r = 48;
  const strokeW = 6;

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

  return (
    <svg
      width={160}
      height={160}
      viewBox="0 0 160 160"
      className="shrink-0"
      role="img"
      aria-label="Confidence gauge showing a moderate failure probability"
    >
      {/* Background arc */}
      <path d={arcPath(-90, 90, 0)} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={strokeW} strokeLinecap="round" />
      {/* Coloured segments */}
      <path d={arcPath(-90, -18, 0)} fill="none" stroke="#3FC7B0" strokeWidth={strokeW} strokeLinecap="round" opacity={0.25} />
      <path d={arcPath(-18, 54, 0)} fill="none" stroke="#E8A33D" strokeWidth={strokeW} strokeLinecap="round" opacity={0.85} />
      <path d={arcPath(54, 90, 0)} fill="none" stroke="#E8564A" strokeWidth={strokeW} strokeLinecap="round" opacity={0.25} />
      {/* Labels */}
      <text x={cx - r - 4} y={cy + 4} textAnchor="end" dominantBaseline="middle" className="fill-text-muted text-[10px] font-mono">0%</text>
      <text x={cx + r + 4} y={cy + 4} textAnchor="start" dominantBaseline="middle" className="fill-text-muted text-[10px] font-mono">100%</text>
      {/* Needle */}
      <line x1={cx} y1={cy} x2={tipX} y2={tipY} stroke={needleColor} strokeWidth={2.5} strokeLinecap="round"
        style={{ transition: 'all 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)' }} />
      {/* Centre dot */}
      <circle cx={cx} cy={cy} r={3.5} fill={needleColor} />
      {/* Value */}
      <text x={cx} y={cy + r * 0.5} textAnchor="middle" className="fill-text-primary font-heading font-bold" style={{ fontSize: 18 }}>
        65%
      </text>
      <text x={cx} y={cy + r * 0.5 + 15} textAnchor="middle" className="fill-text-muted text-[9px]">
        moderate risk
      </text>
    </svg>
  );
}

/* ── Step card ────────────────────────────────────────────────────────── */

interface StepCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  index: number;
}

function StepCard({ icon, title, description, index }: StepCardProps) {
  return (
    <div className="flex flex-col items-center text-center gap-3 p-6 rounded-xl bg-surface border border-border animate-fade-in" style={{ animationDelay: `${index * 80}ms` }}>
      <div className="w-12 h-12 rounded-xl bg-teal/10 flex items-center justify-center shrink-0">
        {icon}
      </div>
      <h3 className="font-heading text-sm font-semibold text-text-primary">{title}</h3>
      <p className="text-xs text-text-secondary leading-relaxed">{description}</p>
    </div>
  );
}

/* ── Landing page ─────────────────────────────────────────────────────── */

export default function Landing() {
  return (
    <div className="min-h-dvh w-full bg-bg flex flex-col">
      {/* Subtle dot grid + vignette */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle, color-mix(in oklch, #8A919C 6%, transparent) 1px, transparent 1px)`,
          backgroundSize: '28px 28px',
          boxShadow: 'inset 0 0 280px rgba(0,0,0,0.45)',
        }}
        aria-hidden="true"
      />

      {/* ── Nav bar ──────────────────────────────────────────────────── */}
      <header className="relative z-10 flex items-center justify-between px-6 lg:px-12 h-16 border-b border-border shrink-0">
        <div className="flex items-center gap-2.5">
          <Activity className="w-5 h-5 text-teal" aria-hidden="true" />
          <span className="font-heading font-semibold text-sm text-text-primary tracking-tight">GreenGrid Predict</span>
        </div>
        <Link
          to="/dashboard"
          className="text-xs font-medium text-text-muted hover:text-text-primary transition-colors"
        >
          Dashboard &rarr;
        </Link>
      </header>

      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="relative z-10 flex flex-col lg:flex-row items-center justify-center gap-10 lg:gap-16 px-6 lg:px-12 py-16 lg:py-24 max-w-5xl mx-auto w-full">
        <div className="flex-1 min-w-0 space-y-5 text-center lg:text-left">
          <h1 className="font-heading text-3xl lg:text-4xl xl:text-5xl font-bold text-text-primary leading-tight tracking-tight">
            Catch equipment failure before it happens —<br />
            <span className="text-teal">before it costs you.</span>
          </h1>
          <p className="text-sm lg:text-base text-text-secondary leading-relaxed max-w-lg mx-auto lg:mx-0">
            Four analysts examine every signal from your renewable-energy assets. A
            lead judge weighs their arguments, agrees or disagrees, and gives you
            an honest confidence score — not just another alarm.
          </p>
          <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal text-bg text-sm font-semibold rounded-lg hover:brightness-110 active:scale-[0.97] transition-all duration-150 focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-2"
            >
              View live dashboard
              <ArrowRight className="w-4 h-4" aria-hidden="true" />
            </Link>
            <span className="text-[11px] text-text-muted font-mono">No sign-up &middot; live data</span>
          </div>
        </div>

        {/* Gauge */}
        <div className="shrink-0 flex flex-col items-center gap-2 p-8 rounded-2xl bg-surface border border-border">
          <HeroGauge />
          <p className="text-[11px] text-text-muted font-mono text-center leading-relaxed">
            Turbine WT-003 &middot; moderate risk<br />
            confidence 82%
          </p>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────── */}
      <section className="relative z-10 px-6 lg:px-12 py-16 lg:py-20 max-w-4xl mx-auto w-full">
        <div className="text-center mb-10">
          <h2 className="font-heading text-xl lg:text-2xl font-bold text-text-primary tracking-tight">How it works</h2>
          <p className="text-sm text-text-muted mt-2">From raw signal to a clear decision — in four steps.</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StepCard
            icon={<Cloud className="w-5 h-5 text-teal" aria-hidden="true" />}
            title="1. Listen"
            description="Vibration, temperature, and power data stream in from every sensor across your wind, solar, and hydro assets."
            index={0}
          />
          <StepCard
            icon={<Cpu className="w-5 h-5 text-teal" aria-hidden="true" />}
            title="2. Analyse"
            description="Four independent analysts each inspect the same data from a different angle — patterns, history, risk, and doubt."
            index={1}
          />
          <StepCard
            icon={<ShieldCheck className="w-5 h-5 text-teal" aria-hidden="true" />}
            title="3. Judge"
            description="A lead judge reads every analysis, reconciles disagreements, and produces a single score — with confidence attached."
            index={2}
          />
          <StepCard
            icon={<Activity className="w-5 h-5 text-teal" aria-hidden="true" />}
            title="4. Decide"
            description="You see the score, the reasoning, and the disagreement behind it. Confirm maintenance, snooze, or dismiss with context."
            index={3}
          />
        </div>
      </section>

      {/* ── Why this matters ─────────────────────────────────────────── */}
      <section className="relative z-10 px-6 lg:px-12 py-14 lg:py-18 max-w-4xl mx-auto w-full border-t border-border">
        <div className="text-center max-w-2xl mx-auto space-y-4">
          <h2 className="font-heading text-xl lg:text-2xl font-bold text-text-primary tracking-tight">Why this matters</h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            Every hour of unplanned downtime in renewable energy costs money and wastes clean power. Most predictive
            maintenance tools just scream louder — more alerts, more noise, more false alarms that get ignored.
          </p>
          <p className="text-sm text-text-secondary leading-relaxed">
            <strong className="text-text-primary">GreenGrid Predict</strong> is built differently. By modelling disagreement
            between multiple independent analyses, it surfaces <em>only</em> what deserves attention — and tells you
            honestly how sure it is. That means less wasted inspection time, fewer unnecessary shutdowns, and
            equipment that stays online longer.
          </p>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────── */}
      <section className="relative z-10 px-6 lg:px-12 py-12 pb-20 max-w-4xl mx-auto w-full text-center">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 px-6 py-3 bg-teal text-bg text-sm font-semibold rounded-lg hover:brightness-110 active:scale-[0.97] transition-all duration-150 focus-visible:outline-2 focus-visible:outline-teal focus-visible:outline-offset-2"
        >
          View live dashboard
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </Link>
        <p className="text-[11px] text-text-muted font-mono mt-3">
          No sign-up needed &middot; real predictions on sample data
        </p>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────── */}
      <footer className="relative z-10 mt-auto px-6 lg:px-12 py-5 border-t border-border">
        <p className="text-[10px] text-text-muted/50 text-center">
          GreenGrid Predict &middot; Multi-agent debate engine powered by Fireworks AI
        </p>
      </footer>

      {/* ── Staggered entrance CSS ───────────────────────────────────── */}
      <style>{`
        .animate-fade-in {
          opacity: 0;
          transform: translateY(12px);
          animation: fadeInUp 0.5s ease-out forwards;
        }
        @keyframes fadeInUp {
          to { opacity: 1; transform: translateY(0); }
        }
        @media (prefers-reduced-motion: reduce) {
          .animate-fade-in { opacity: 1; transform: none; animation: none; }
        }
      `}</style>
    </div>
  );
}
