import { NavLink } from "react-router-dom";
import {
  LayoutDashboard, TrendingUp, Briefcase, Settings, Brain, Zap,
} from "lucide-react";
import clsx from "clsx";

const nav = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/signals", icon: TrendingUp, label: "Signals" },
  { to: "/portfolio", icon: Briefcase, label: "Portfolio" },
  { to: "/model", icon: Brain, label: "Model" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 bg-surface border-r border-border flex flex-col">
      <div className="px-5 py-5 border-b border-border flex items-center gap-2">
        <Zap size={20} className="text-accent" />
        <span className="font-semibold text-sm tracking-wide">LSTM Trading</span>
      </div>
      <nav className="flex-1 py-4 space-y-0.5 px-2">
        {nav.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-accent/10 text-accent-light"
                  : "text-slate-400 hover:text-slate-200 hover:bg-border/60"
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="px-5 py-4 border-t border-border">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <span className="text-xs text-slate-500">Paper Trading Active</span>
        </div>
      </div>
    </aside>
  );
}
