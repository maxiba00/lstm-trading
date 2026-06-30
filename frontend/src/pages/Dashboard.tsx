import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { useApi, apiPost } from "../hooks/useApi";
import StatCard from "../components/StatCard";
import SignalBadge from "../components/SignalBadge";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
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

export default function Dashboard() {
  const { data: account, loading: aLoading } = useApi<Account>("/trades/account");
  const { data: latest, loading: sLoading, refetch } = useApi<SignalRow[]>("/signals/latest");
  const { data: stats, refetch: refetchStats } = useApi<SignalStats>("/signals/stats");
  const [pipelineState, setPipelineState] = useState<"idle" | "running" | "done" | "error">("idle");

  const chartData = stats
    ? Object.entries(stats).map(([k, v]) => ({ name: k, count: v }))
    : [];

  const handleRunNow = async () => {
    setPipelineState("running");
    try {
      await apiPost("/pipeline/run-now");
      // Poll until pipeline finishes (signals appear)
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
          label="Today's P&L"
          value={aLoading ? "…" : `${(account?.pnl ?? 0) >= 0 ? "+" : ""}$${fmt(account?.pnl ?? 0)}`}
          positive={account ? account.pnl >= 0 : null}
        />
        <StatCard
          label="Buying Power"
          value={aLoading ? "…" : `$${fmt(account?.buying_power ?? 0)}`}
        />
      </div>

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
        </div>

        {/* Latest signals */}
        <div className="col-span-2 bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-slate-400 mb-4">Latest Signals</h2>
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
                      <span
                        className={
                          s.predicted_return_pct >= 0 ? "text-long" : "text-short"
                        }
                      >
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
                <p className="text-slate-500 text-sm">No active signals yet.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
