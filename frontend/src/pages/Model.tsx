import { useEffect, useState } from "react";
import { useApi, apiPost } from "../hooks/useApi";
import { Brain, CheckCircle } from "lucide-react";

interface ModelStatus {
  trained_count: number;
  trained_tickers: string[];
  available_tickers: string[];
}

interface TrainingStatus {
  is_training: boolean;
  current_ticker: string | null;
  queue: string[];
  completed: string[];
  failed: string[];
}

interface ModelRun {
  id: number;
  ticker: string;
  rmse: number;
  directional_accuracy: number;
  n_features: number;
  train_samples: number;
  epochs_run: number;
  created_at: string;
}

export default function Model() {
  const { data: status, loading: sLoading, refetch } = useApi<ModelStatus>("/model/status");
  const { data: runs, loading: rLoading, refetch: refetchRuns } = useApi<ModelRun[]>("/model/runs");
  const { data: trainingStatus, refetch: refetchTrainingStatus } = useApi<TrainingStatus>("/model/training-status");
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [epochs, setEpochs] = useState(100);
  const [lstmUnits, setLstmUnits] = useState(50);
  const [dropout, setDropout] = useState(0.3);
  const [includeWiki, setIncludeWiki] = useState(true);
  const [includeTrends, setIncludeTrends] = useState(false);
  const [includeSentiment, setIncludeSentiment] = useState(true);
  const [includeFred, setIncludeFred] = useState(true);

  const isTraining = trainingStatus?.is_training ?? false;

  // Always poll training status; also refresh model list when training completes
  useEffect(() => {
    const interval = setInterval(() => {
      refetchTrainingStatus();
      if (isTraining) {
        refetch();
        refetchRuns();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [isTraining]);

  const untrainedTickers = (status?.available_tickers ?? []).filter(
    (t) => !(status?.trained_tickers ?? []).includes(t)
  );
  const nextBatch = untrainedTickers.slice(0, 10);

  const handleTrain = async () => {
    const tickers = selectedTickers.length ? selectedTickers : nextBatch.length ? nextBatch : undefined;
    await apiPost("/model/train", {
      tickers,
      epochs,
      lstm_units: lstmUnits,
      dropout,
      include_wiki: includeWiki,
      include_trends: includeTrends,
      include_sentiment: includeSentiment,
      include_fred: includeFred,
    });
    refetchTrainingStatus();
  };

  const toggleTicker = (t: string) => {
    setSelectedTickers((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
    );
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold">Model Management</h1>

      <div className="grid grid-cols-3 gap-6">
        {/* Training config */}
        <div className="col-span-1 bg-surface border border-border rounded-xl p-5 space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <Brain size={16} className="text-accent" />
            <h2 className="text-sm font-medium">Train Models</h2>
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider">LSTM Units</label>
            <input
              type="number"
              value={lstmUnits}
              onChange={(e) => setLstmUnits(Number(e.target.value))}
              className="mt-1 w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider">Epochs</label>
            <input
              type="number"
              value={epochs}
              onChange={(e) => setEpochs(Number(e.target.value))}
              className="mt-1 w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 uppercase tracking-wider">Dropout Rate</label>
            <input
              type="number"
              step="0.05"
              min="0"
              max="0.5"
              value={dropout}
              onChange={(e) => setDropout(Number(e.target.value))}
              className="mt-1 w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-accent"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs text-slate-500 uppercase tracking-wider">Features</label>
            {[
              { label: "Wikipedia Pageviews", val: includeWiki, set: setIncludeWiki },
              { label: "Google Trends (rate-limited, langsam)", val: includeTrends, set: setIncludeTrends },
              { label: "News Sentiment", val: includeSentiment, set: setIncludeSentiment },
              { label: "FRED Makro (VIX, Zinsen, 10Y)", val: includeFred, set: setIncludeFred },
            ].map(({ label, val, set }) => (
              <label key={label} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={val}
                  onChange={(e) => set(e.target.checked)}
                  className="accent-accent"
                />
                <span className="text-sm text-slate-300">{label}</span>
              </label>
            ))}
          </div>

          <button
            onClick={handleTrain}
            disabled={isTraining}
            className="w-full py-2 bg-accent hover:bg-accent/80 disabled:opacity-50 rounded-lg text-sm font-medium transition-colors"
          >
            {isTraining
              ? "Training running…"
              : selectedTickers.length
              ? `Train ${selectedTickers.length} selected`
              : nextBatch.length
              ? `Train next ${nextBatch.length} untrained`
              : "All models trained ✓"}
          </button>

          {isTraining && trainingStatus && (
            <div className="text-xs space-y-1.5 bg-bg border border-border rounded-lg p-3">
              <p className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
                <span className="font-mono font-semibold text-accent-light">
                  {trainingStatus.current_ticker}
                </span>
                <span className="text-slate-500">training now…</span>
              </p>
              <p className="text-slate-500">
                Done: <span className="text-long">{trainingStatus.completed.length}</span>
                {" · "}Queued: <span className="text-slate-400">{trainingStatus.queue.length}</span>
                {trainingStatus.failed.length > 0 && (
                  <> · Failed: <span className="text-short">{trainingStatus.failed.length}</span></>
                )}
              </p>
              <p className="text-slate-600">
                ~20–60 min per ticker — this view updates automatically.
              </p>
            </div>
          )}
        </div>

        {/* Ticker selection */}
        <div className="col-span-2 bg-surface border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-slate-400">
              Select Tickers{" "}
              <span className="text-accent">{sLoading ? "…" : `${status?.trained_count ?? 0} trained`}</span>
            </h2>
            <button
              onClick={() => setSelectedTickers([])}
              className="text-xs text-slate-500 hover:text-slate-300"
            >
              Clear
            </button>
          </div>
          {sLoading ? (
            <p className="text-slate-500 text-sm">Loading…</p>
          ) : (
            <div className="flex flex-wrap gap-2 max-h-64 overflow-y-auto">
              {(status?.available_tickers ?? []).map((t) => {
                const trained = status?.trained_tickers?.includes(t);
                const selected = selectedTickers.includes(t);
                return (
                  <button
                    key={t}
                    onClick={() => toggleTicker(t)}
                    className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold border transition-colors ${
                      selected
                        ? "bg-accent/20 border-accent text-accent-light"
                        : trained
                        ? "bg-long/10 border-long/30 text-long/80"
                        : "bg-bg border-border text-slate-400 hover:border-slate-500"
                    }`}
                  >
                    {trained && !selected && <CheckCircle size={10} className="inline mr-1 mb-0.5" />}
                    {t}
                  </button>
                );
              })}
            </div>
          )}
          <p className="text-xs text-slate-600 mt-3">Grün = trainiert. Klicken zum (Neu-)Trainieren. Kein Selection = nächste {nextBatch.length} untrainierte.</p>
        </div>
      </div>

      {/* Model run history */}
      <div className="bg-surface border border-border rounded-xl overflow-hidden">
        <div className="px-5 py-3 border-b border-border text-sm font-medium text-slate-400">Training History</div>
        {rLoading ? (
          <p className="p-6 text-slate-500 text-sm">Loading…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-500 uppercase tracking-wider">
                <th className="text-left px-4 py-3">Ticker</th>
                <th className="text-right px-4 py-3">RMSE</th>
                <th className="text-right px-4 py-3">Dir. Accuracy</th>
                <th className="text-right px-4 py-3">Features</th>
                <th className="text-right px-4 py-3">Train Samples</th>
                <th className="text-right px-4 py-3">Epochs</th>
                <th className="text-right px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody>
              {(runs ?? []).map((r) => (
                <tr key={r.id} className="border-t border-border/50 hover:bg-border/20">
                  <td className="px-4 py-3 font-mono font-semibold">{r.ticker}</td>
                  <td className="px-4 py-3 text-right font-mono">{r.rmse.toFixed(6)}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${r.directional_accuracy >= 0.5 ? "text-long" : "text-short"}`}>
                    {(r.directional_accuracy * 100).toFixed(1)}%
                  </td>
                  <td className="px-4 py-3 text-right">{r.n_features}</td>
                  <td className="px-4 py-3 text-right">{r.train_samples.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">{r.epochs_run}</td>
                  <td className="px-4 py-3 text-right text-slate-500 text-xs">
                    {new Date(r.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
              {(runs ?? []).length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    No training runs yet.
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
