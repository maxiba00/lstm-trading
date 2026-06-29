import clsx from "clsx";

interface Props {
  label: string;
  value: string | number;
  sub?: string;
  positive?: boolean | null;
}

export default function StatCard({ label, value, sub, positive }: Props) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">{label}</p>
      <p
        className={clsx(
          "text-2xl font-bold",
          positive === true && "text-long",
          positive === false && "text-short",
          positive === null || positive === undefined ? "text-slate-100" : ""
        )}
      >
        {value}
      </p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}
