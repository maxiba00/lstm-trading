import { useState, useEffect } from "react";
import { useApi, apiPut } from "../hooks/useApi";
import { Save } from "lucide-react";

interface AppSettings {
  min_return_pct: number;
  min_confidence: number;
  allow_short: boolean;
  position_size_usd: number;
  max_positions: number;
  stop_loss_pct: number;
  run_time: string;
  eodhd_api_key: string;
}

function Slider({
  label, value, min, max, step, unit, onChange, description,
}: {
  label: string; value: number; min: number; max: number; step: number;
  unit: string; onChange: (v: number) => void; description?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <label className="text-sm font-medium text-slate-200">{label}</label>
          {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
        </div>
        <span className="text-sm font-mono font-semibold text-accent-light">
          {value}{unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-border rounded-full appearance-none cursor-pointer accent-accent"
      />
      <div className="flex justify-between text-xs text-slate-600">
        <span>{min}{unit}</span>
        <span>{max}{unit}</span>
      </div>
    </div>
  );
}

export default function Settings() {
  const { data, loading, refetch } = useApi<AppSettings>("/settings/");
  const [form, setForm] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setForm({ ...data });
  }, [data]);

  const handleSave = async () => {
    if (!form) return;
    setSaving(true);
    try {
      await apiPut("/settings/", form);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      refetch();
    } finally {
      setSaving(false);
    }
  };

  if (loading || !form) {
    return <div className="p-6 text-slate-500 text-sm">Loading settings…</div>;
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Settings</h1>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 bg-accent hover:bg-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
        >
          <Save size={14} />
          {saved ? "Saved!" : saving ? "Saving…" : "Save Settings"}
        </button>
      </div>

      {/* Signal thresholds */}
      <div className="bg-surface border border-border rounded-xl p-6 space-y-6">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Signal Thresholds</h2>

        <Slider
          label="Minimum Predicted Return"
          description="Signal is only triggered if |predicted return| exceeds this value."
          value={form.min_return_pct}
          min={0.1}
          max={5}
          step={0.1}
          unit="%"
          onChange={(v) => setForm({ ...form, min_return_pct: v })}
        />

        <Slider
          label="Minimum Confidence"
          description="Monte Carlo Dropout confidence required to trigger a signal."
          value={Math.round(form.min_confidence * 100)}
          min={10}
          max={95}
          step={5}
          unit="%"
          onChange={(v) => setForm({ ...form, min_confidence: v / 100 })}
        />

        <div className="flex items-center justify-between py-2 border-t border-border">
          <div>
            <p className="text-sm font-medium text-slate-200">Allow Short Selling</p>
            <p className="text-xs text-slate-500 mt-0.5">Generate SHORT signals for predicted downturns.</p>
          </div>
          <button
            onClick={() => setForm({ ...form, allow_short: !form.allow_short })}
            className={`relative w-11 h-6 rounded-full transition-colors ${
              form.allow_short ? "bg-accent" : "bg-border"
            }`}
          >
            <span
              className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
                form.allow_short ? "translate-x-5" : ""
              }`}
            />
          </button>
        </div>
      </div>

      {/* Position sizing */}
      <div className="bg-surface border border-border rounded-xl p-6 space-y-6">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Position Sizing</h2>

        <Slider
          label="Position Size"
          description="Dollar amount invested per signal."
          value={form.position_size_usd}
          min={100}
          max={10000}
          step={100}
          unit=" USD"
          onChange={(v) => setForm({ ...form, position_size_usd: v })}
        />

        <Slider
          label="Max Simultaneous Positions"
          description="Pipeline stops placing new trades once this limit is reached."
          value={form.max_positions}
          min={1}
          max={50}
          step={1}
          unit=""
          onChange={(v) => setForm({ ...form, max_positions: v })}
        />

        <Slider
          label="Stop Loss"
          description="Automatically close position if loss exceeds this percentage."
          value={form.stop_loss_pct}
          min={0.5}
          max={10}
          step={0.5}
          unit="%"
          onChange={(v) => setForm({ ...form, stop_loss_pct: v })}
        />
      </div>

      {/* Schedule & API */}
      <div className="bg-surface border border-border rounded-xl p-6 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Schedule & API Keys</h2>

        <div>
          <label className="text-sm font-medium text-slate-200">Daily Run Time (ET, Mon–Fri)</label>
          <p className="text-xs text-slate-500 mt-0.5">Pipeline runs after US market close.</p>
          <input
            type="time"
            value={form.run_time}
            onChange={(e) => setForm({ ...form, run_time: e.target.value })}
            className="mt-2 w-40 bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-slate-200">EODHD API Key</label>
          <p className="text-xs text-slate-500 mt-0.5">For news sentiment data.</p>
          <input
            type="password"
            value={form.eodhd_api_key}
            onChange={(e) => setForm({ ...form, eodhd_api_key: e.target.value })}
            placeholder="Your EODHD API key"
            className="mt-2 w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent font-mono"
          />
        </div>
      </div>

      {/* Current thresholds summary */}
      <div className="bg-accent/5 border border-accent/20 rounded-xl p-4">
        <p className="text-xs text-slate-400 mb-2 font-medium uppercase tracking-wider">Active Signal Rule</p>
        <p className="text-sm text-slate-300">
          Signal = <span className="text-long font-semibold">LONG</span> if predicted return &gt;{" "}
          <span className="text-accent-light font-mono">+{form.min_return_pct}%</span> AND confidence ≥{" "}
          <span className="text-accent-light font-mono">{Math.round(form.min_confidence * 100)}%</span>
          {form.allow_short && (
            <>
              {" "}· <span className="text-short font-semibold">SHORT</span> if predicted return &lt;{" "}
              <span className="text-accent-light font-mono">-{form.min_return_pct}%</span> AND confidence ≥{" "}
              <span className="text-accent-light font-mono">{Math.round(form.min_confidence * 100)}%</span>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
