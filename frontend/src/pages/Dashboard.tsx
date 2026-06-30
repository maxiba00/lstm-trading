import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useApi, apiPost } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import SignalBadge from "../components/SignalBadge";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
  ReferenceLine,
} from "recharts";

interface Account {
  equity: number;
  cash: number;
  portfolio_value: number;
  buying_power: number;
  pnl: number;
}

interface SignalRow {
  id: number;
  ticker: string;
  signal: string;
  predicted_return_pct: number;
  confidence: number;
  reason: string;
  created_at: string;
}

interface SignalStats {
  LONG?: number;
  SHORT?: number;
  HOLD?: number;
}

interface Distribution {
  return_bins: { bin: string; count: number }[];
  confidence_bins: { bin: string; count: number }[];
  total_signals: number;
  n_long: number;
  n_short: number;
  n_hold: number;
  avg_return_pct: number;
  avg_confidence: number;
  signal_alignment_pct: number;
}

interface TradeStats {
  total_closed_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_realized_pnl: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  total_orders: number;
}

export default function Dashboard() {
  const { data: account, loading: aLoading } = useApi<Account>("/trades/account");
  const { data: latest, loading: sLoading, refetch } = useApi<SignalRow[]>("/signals/latest");
  const { data: stats, refetch: refetchStats } = useApi<SignalStats>("/signals/stats");
  const { data: dist } = useApi<Distribution>("/signals/distribution");
  const { data: tradeStats } = useApi<TradeStats>("/trades/stats");
  const [pipelineState, setPipelineState] = useState<"idle" | "running" | "done" | "error">("idle");

  const chartData = stats
    ? Object.entries(stats).map(([k, v]) => ({ name: k, count: v }))
    : [];

  const handleRunNow = async () => {
    setPipelineState("running");
    try {
      await apiPost("/pipeline/run-now");
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        refetch();
        refetchStats();
        if (attempts >= 30) {
          clearInterval(poll);
          setPipelineState("done");
        }
      }, 3000);
      setPipelineState("done");
    } catch {
      setPipelineState("error");
    }
  };

  const fmt = (n: number, decimals = 2) =>
    n !== undefined ? n.toFixed(decimals) : "—";

  // Color return bins: negative = red, positive = green, near-zero = grey
  const returnBinColor = (bin: string) => {
    const val = parseFloat(bin);
    if (val > 0.5) return "#22c55e";
    if (val < -0.5) return "#ef4444";
    return "#64748b";
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <div className="flex items-center gap-3">
          {pipelineState === "running" && (
            <span className="text-xs text-slate-400 animate-pulse">Pipeline läuft… (~1 Min)</span>
          )}
          {pipelineState === "done" && (
            <span className="text-xs text-long">✓ Signals aktualisiert</span>
          )}
          {pipelineState === "error" && (
            <span className="text-xs text-short">Fehler — siehe Logs</span>
          )}
          <button
            onClick={handleRunNow}
            disabled={pipelineState === "running"}
            className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
          >
            <RefreshCw size={14} className={pipelineState === "running" ? "animate-spin" : ""} />
            Run Pipeline Now
          </button>
        </div>
      </div>

      {/* Account stats */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          label="Portfolio Value"
          value={aLoading ? "…" : `$${fmt(account?.portfolio_value ?? 0)}`}
        />
        <StatCard
          label="Cash"
          value={aLoading ? "…" : `$${fmt(account?.cash ?? 0)}`}
        />
        <StatCard
          label="Total P&L"
          value={aLoading ? "…" : `${(account?.pnl ?? 0) >= 0 ? "+" : ""}$${fmt(account?.pnl ?? 0)}`}
          positive={account ? account.pnl >= 0 : null}
        />
        <StatCard
          label="Buying Power"
          value={aLoading ? "…" : `$${fmt(account?.buying_power ?? 0)}`}
        />
      </div>

      {/* Trade performance stats */}
      {tradeStats && tradeStats.total_closed_trades > 0 && (
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            label="Closed Trades"
            value={String(tradeStats.total_closed_trades)}
          />
          <StatCard
            label="Win Rate"
            value={`${tradeStats.win_rate}%`}
            positive={tradeStats.win_rate >= 50}
          />
          <StatCard
            label="Realized P&L"
            value={`${tradeStats.total_realized_pnl >= 0 ? "+" : ""}$${fmt(tradeStats.total_realized_pnl)}`}
            positive={tradeStats.total_realized_pnl >= 0}
          />
          <StatCard
            label="Profit Factor"
            value={fmt(tradeStats.profit_factor)}
            positive={tradeStats.profit_factor >= 1}
          />
        </div>
      )}

      <div className="grid grid-cols-3 gap-6">
        {/* Signal distribution */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-slate-400 mb-4">Signal Distribution</h2>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={chartData} barSize={40}>
              <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 8 }}
                labelStyle={{ color: "#e2e8f0" }}
              />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {chartData.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={entry.name === "LONG" ? "#22c55e" : entry.name === "SHORT" ? "#ef4444" : "#64748b"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {dist && (
            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs text-slate-500">
              <div>Ø Return<br /><span className={`font-semibold ${dist.avg_return_pct >= 0 ? "text-long" : "text-short"}`}>{dist.avg_return_pct >= 0 ? "+" : ""}{dist.avg_return_pct.toFixed(2)}%</span></div>
              <div>Ø Konfidenz<br /><span className="font-semibold text-slate-300">{(dist.avg_confidence * 100).toFixed(0)}%</span></div>
              <div>Alignment<br /><span className="font-semibold text-slate-300">{dist.signal_alignment_pct}%</span></div>
            </div>
          )}
        </div>

        {/* Return distribution histogram */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-slate-400 mb-4">Prognose-Stärke (Return %)</h2>
          {dist && dist.return_bins.length > 0 ? (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={dist.return_bins} barSize={8}>
                <XAxis dataKey="bin" tick={{ fill: "#64748b", fontSize: 9 }} axisLine={false} tickLine={false}
                  interval={3} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} width={24} />
                <Tooltip
                  contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 8 }}
                  formatter={(v: number) => [v, "Signals"]}
                />
                <ReferenceLine x="0.0%" stroke="#475569" strokeDasharray="3 3" />
                <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                  {dist.return_bins.map((entry, i) => (
                    <Cell key={i} fill={returnBinColor(entry.bin)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-500 text-sm mt-8 text-center">Noch keine Signals.</p>
          )}
        </div>

        {/* Confidence distribution histogram */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-slate-400 mb-4">Konfidenz-Verteilung</h2>
          {dist && dist.confidence_bins.length > 0 ? (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={dist.confidence_bins} barSize={10}>
                <XAxis dataKey="bin" tick={{ fill: "#64748b", fontSize: 9 }} axisLine={false} tickLine={false}
                  interval={3} />
                <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} width={24} />
                <Tooltip
                  contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 8 }}
                  formatter={(v: number) => [v, "Signals"]}
                />
                <Bar dataKey="count" radius={[2, 2, 0, 0]} fill="#6366f1" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-500 text-sm mt-8 text-center">Noch keine Signals.</p>
          )}
        </div>
      </div>

      {/* Latest signals */}
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="text-sm font-medium text-slate-400 mb-4">Aktuelle Signals (non-HOLD)</h2>
        {sLoading ? (
          <p className="text-slate-500 text-sm">Loading…</p>
        ) : (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {(latest ?? [])
              .filter((s) => s.signal !== "HOLD")
              .slice(0, 10)
              .map((s) => (
                <div
                  key={s.id}
                  className="flex items-center justify-between py-2 border-b border-border last:border-0"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono font-semibold text-sm w-14">{s.ticker}</span>
                    <SignalBadge signal={s.signal} />
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className={s.predicted_return_pct >= 0 ? "text-long" : "text-short"}>
                      {s.predicted_return_pct >= 0 ? "+" : ""}
                      {s.predicted_return_pct.toFixed(2)}%
                    </span>
                    <span className="text-slate-500">
                      {(s.confidence * 100).toFixed(0)}% conf.
                    </span>
                  </div>
                </div>
              ))}
            {(latest ?? []).filter((s) => s.signal !== "HOLD").length === 0 && (
              <p className="text-slate-500 text-sm">Keine aktiven Signals.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
