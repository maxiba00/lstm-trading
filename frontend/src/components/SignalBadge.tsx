import clsx from "clsx";

export default function SignalBadge({ signal }: { signal: string }) {
  return (
    <span
      className={clsx(
        "px-2.5 py-0.5 rounded-full text-xs font-semibold",
        signal === "LONG" && "bg-long/15 text-long",
        signal === "SHORT" && "bg-short/15 text-short",
        signal === "HOLD" && "bg-hold/15 text-slate-400"
      )}
    >
      {signal}
    </span>
  );
}
