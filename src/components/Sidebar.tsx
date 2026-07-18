import { NavLink } from 'react-router-dom';
import { Cpu, BarChart3, Activity } from 'lucide-react';

const links = [
  { to: '/dashboard', label: 'Asset Overview', icon: Cpu },
  { to: '/calibration', label: 'Accuracy & Trust', icon: BarChart3 },
];

export default function Sidebar() {
  return (
    <aside className="w-60 border-r border-border bg-surface shrink-0 flex flex-col h-full" role="navigation" aria-label="Main navigation">
      {/* Brand */}
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-border shrink-0">
        <Activity className="w-5 h-5 text-teal" aria-hidden="true" />
        <span className="font-heading font-semibold text-sm text-text-primary tracking-tight">
          Energy Monitoring System
        </span>
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-1 p-3">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-teal/10 text-teal'
                  : 'text-text-muted hover:text-text-primary hover:bg-surface-hover'
              }`
            }
          >
            <Icon className="w-4 h-4" aria-hidden="true" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Status footer */}
      <div className="mt-auto px-5 py-4 border-t border-border">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal opacity-35" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-teal" />
          </span>
          <span className="text-[11px] text-text-muted font-mono">Monitoring Active</span>
        </div>
        <p className="text-[9px] text-text-muted/50 mt-1 leading-tight">
          {new Date().toLocaleDateString()}
        </p>
      </div>
    </aside>
  );
}