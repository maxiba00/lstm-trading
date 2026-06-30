import { useState } from "react";
import { useApi, apiPost } from "../hooks/useApi";
import SignalBadge from "../components/SignalBadge";

interface SignalRow {
  id: number;
  ticker: string;
  signal: string;
  current_price: number;
  predicted_price: number;
  predicted_return_pct: number;
  confidence: number;
  mc_std: number;
  reason: string;
  min_return_pct: number;
  min_confidence: number;
  created_at: string;
}

interface AppSettings {
  position_size_usd: number;
}

export default function Signals() {
  const [filter, setFilter] = useState("ALL");
  const { data, loading } = useApi<SignalRow[]>("/signals/?limit=200");
  const { data: settings } = useApi<AppSettings>("/settings/");
  const [placingId, setPlacingId] = useState<number | null>(null);
  const [placedIds, setPlacedIds] = useState<number[]>([]);

  const allRows = data ?? [];
  const holdRows = allRows.filter((s) => s.signal === "HOLD");
  const activeRows = allRows.filter((s) => s.signal !== "HOLD");

  const rows = filter === "HOLD"
    ? holdRows
    : filter === "ALL"
    ? activeRows
    : allRows.filter((s) => s.signal === filter);

  const handleOrder = async (s: SignalRow) => {
    setPlacingId(s.id);
    try {
      const res = await apiPost("/trades/order", {
        ticker: s.ticker,
        side: s.signal === "LONG" ? "buy" : "sell",
        notional: settings?.position_size_usd ?? 1000,
        signal_id: s.id,
      }) as Record<string, unknown>;
      if (!res?.error) {
        setPlacedIds((prev) => [...prev, s.id]);
      } else {
        alert(res.error as string);
      }
    } finally {
      setPlacingId(null);
    }
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Signal History</h1>
        <div className="flex gap-2">
          {["ALL", "LONG", "SHORT", "HOLD"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                filter === f
                  ? "bg-accent text-white"
                  : "bg-surface border border-border text-slate-400 hover:text-slate-200"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        {loading ? (
          <p className="p-6 text-slate-500 text-sm">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3">Ticker</th>
                <th className="text-left px-4 py-3">Signal</th>
                <th className="text-right px-4 py-3">Current</th>
                <th className="text-right px-4 py-3">Predicted</th>
                <th className="text-right px-4 py-3">Return</th>
                <th className="text-right px-4 py-3">Confidence</th>
                <th className="text-right px-4 py-3">MC Std</th>
                <th className="text-left px-4 py-3">Reason</th>
                <th className="text-right px-4 py-3">Date</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id} className="border-b border-border/50 hover:bg-border/20 transition-colors">
                  <td className="px-4 py-3 font-mono font-semibold">{s.ticker}</td>
                  <td className="px-4 py-3"><SignalBadge signal={s.signal} /></td>
                  <td className="px-4 py-3 text-right font-mono">${s.current_price.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">${s.predicted_price.toFixed(2)}</td>
                  <td className={`px-4 py-3 text-right font-mono font-semibold ${s.predicted_return_pct >= 0 ? "text-long" : "text-short"}`}>
                    {s.predicted_return_pct >= 0 ? "+" : ""}{s.predicted_return_pct.toFixed(2)}%
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-1.5 rounded-full bg-border overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full"
                          style={{ width: `${s.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-slate-400">{(s.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-500 font-mono text-xs">{s.mc_std.toFixed(4)}</td>
                  <td className="px-4 py-3 text-slate-400 max-w-xs truncate">{s.reason}</td>
                  <td className="px-4 py-3 text-right text-slate-500 text-xs">
                    {new Date(s.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {s.signal === "HOLD" ? null : placedIds.includes(s.id) ? (
                      <span className="text-xs text-long">Placed</span>
                    ) : (
                      <button
                        onClick={() => handleOrder(s)}
                        disabled={placingId === s.id}
                        className={`text-xs px-2.5 py-1 rounded border transition-colors disabled:opacity-50 ${
                          s.signal === "LONG"
                            ? "border-long/40 text-long hover:bg-long/10"
                            : "border-short/40 text-short hover:bg-short/10"
                        }`}
                      >
                        {placingId === s.id ? "…" : "Order"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {filter !== "HOLD" && holdRows.length > 0 && (
                <tr className="border-b border-border/30 bg-border/5">
                  <td colSpan={10} className="px-4 py-2 text-xs text-slate-500 italic">
                    {holdRows.length} signal{holdRows.length > 1 ? "s" : ""} on HOLD / below threshold —{" "}
                    <button
                      onClick={() => setFilter("HOLD")}
                      className="underline hover:text-slate-300"
                    >
                      details anzeigen
                    </button>
                  </td>
                </tr>
              )}
              {rows.length === 0 && filter !== "HOLD" && (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-slate-500">
                    No signals yet. Run the pipeline to generate signals.
                  </td>
                </tr>
              )}
              {rows.length === 0 && filter === "HOLD" && (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-slate-500">
                    Keine HOLD-Signals vorhanden.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
