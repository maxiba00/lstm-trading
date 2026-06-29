import { useApi } from "../hooks/useApi";
import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip,
} from "recharts";

interface Position {
  ticker: string;
  qty: number;
  side: string;
  avg_entry: number;
  current_price: number;
  market_value: number;
  unrealized_pl: number;
  unrealized_plpc: number;
}

interface Order {
  order_id: string;
  ticker: string;
  side: string;
  notional: number;
  status: string;
  filled_avg_price: number;
  created_at: string;
}

const COLORS = ["#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#06b6d4", "#8b5cf6"];

export default function Portfolio() {
  const { data: positions, loading: pLoading } = useApi<Position[]>("/trades/positions");
  const { data: orders, loading: oLoading } = useApi<Order[]>("/trades/orders");

  const pieData = (positions ?? []).map((p) => ({
    name: p.ticker,
    value: Math.abs(p.market_value),
  }));

  const totalPL = (positions ?? []).reduce((s, p) => s + p.unrealized_pl, 0);

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Portfolio</h1>

      <div className="grid grid-cols-3 gap-6">
        {/* Positions table */}
        <div className="col-span-2 bg-surface border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-border text-sm font-medium text-slate-400">
            Open Positions ({(positions ?? []).length})
          </div>
          {pLoading ? (
            <p className="p-6 text-slate-500 text-sm">Loading…</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-slate-500 uppercase tracking-wider">
                  <th className="text-left px-4 py-3">Ticker</th>
                  <th className="text-left px-4 py-3">Side</th>
                  <th className="text-right px-4 py-3">Qty</th>
                  <th className="text-right px-4 py-3">Avg Entry</th>
                  <th className="text-right px-4 py-3">Current</th>
                  <th className="text-right px-4 py-3">Market Value</th>
                  <th className="text-right px-4 py-3">Unreal. P&L</th>
                </tr>
              </thead>
              <tbody>
                {(positions ?? []).map((p) => (
                  <tr key={p.ticker} className="border-t border-border/50 hover:bg-border/20">
                    <td className="px-4 py-3 font-mono font-semibold">{p.ticker}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-semibold ${p.side === "long" ? "text-long" : "text-short"}`}>
                        {p.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono">{p.qty.toFixed(4)}</td>
                    <td className="px-4 py-3 text-right font-mono">${p.avg_entry.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-mono">${p.current_price.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right font-mono">${p.market_value.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right font-semibold ${p.unrealized_pl >= 0 ? "text-long" : "text-short"}`}>
                      {p.unrealized_pl >= 0 ? "+" : ""}${p.unrealized_pl.toFixed(2)}
                      <span className="text-xs ml-1 opacity-70">({p.unrealized_plpc.toFixed(1)}%)</span>
                    </td>
                  </tr>
                ))}
                {(positions ?? []).length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      No open positions.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
          {(positions ?? []).length > 0 && (
            <div className="px-4 py-3 border-t border-border flex justify-end">
              <span className={`text-sm font-semibold ${totalPL >= 0 ? "text-long" : "text-short"}`}>
                Total Unrealized P&L: {totalPL >= 0 ? "+" : ""}${totalPL.toFixed(2)}
              </span>
            </div>
          )}
        </div>

        {/* Allocation pie */}
        <div className="bg-surface border border-border rounded-xl p-5">
          <h2 className="text-sm font-medium text-slate-400 mb-4">Allocation</h2>
          {pieData.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={3} dataKey="value">
                    {pieData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: number) => [`$${v.toFixed(2)}`, "Value"]}
                    contentStyle={{ background: "#1a1d27", border: "1px solid #2a2d3a", borderRadius: 8 }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-1.5 mt-2">
                {pieData.map((d, i) => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-sm" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="font-mono">{d.name}</span>
                    </div>
                    <span className="text-slate-400">${d.value.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-slate-500 text-sm">No positions.</p>
          )}
        </div>
      </div>

      {/* Recent orders */}
      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-border text-sm font-medium text-slate-400">
          Recent Orders
        </div>
        {oLoading ? (
          <p className="p-6 text-slate-500 text-sm">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3">Ticker</th>
                <th className="text-left px-4 py-3">Side</th>
                <th className="text-right px-4 py-3">Notional</th>
                <th className="text-right px-4 py-3">Fill Price</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {(orders ?? []).slice(0, 20).map((o) => (
                <tr key={o.order_id} className="border-t border-border/50 hover:bg-border/20">
                  <td className="px-4 py-3 font-mono font-semibold">{o.ticker}</td>
                  <td className={`px-4 py-3 text-xs font-semibold ${o.side === "buy" ? "text-long" : "text-short"}`}>
                    {o.side.toUpperCase()}
                  </td>
                  <td className="px-4 py-3 text-right font-mono">${o.notional.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right font-mono">
                    {o.filled_avg_price ? `$${o.filled_avg_price.toFixed(2)}` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      o.status === "filled" ? "bg-long/15 text-long" :
                      o.status === "canceled" ? "bg-short/15 text-short" :
                      "bg-slate-700/30 text-slate-400"
                    }`}>
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-slate-500 text-xs">
                    {new Date(o.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
