import type { CSSProperties } from "react";
import { Finding } from "@/lib/api";
import { SEVERITY_COLORS } from "@/app/theme";

export function ClauseCard({
  f,
  onClick,
  active = false,
}: {
  f: Finding;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`w-full rounded-2xl p-5 text-left backdrop-blur-sm transition-all duration-200 border ${
        active
          ? "bg-white shadow-lg -translate-y-0.5 ring-2"
          : "bg-white/70 shadow-sm border-white/40 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0"
      }`}
      style={
        active
          ? ({ borderColor: SEVERITY_COLORS[f.severity], ["--tw-ring-color" as string]: SEVERITY_COLORS[f.severity] } as CSSProperties)
          : undefined
      }
    >
      <div className="flex items-center gap-2">
        <span
          className="h-3 w-3 flex-shrink-0 rounded-full ring-2 ring-white/60"
          style={{ background: SEVERITY_COLORS[f.severity] }}
        />
        <span className="font-semibold text-[var(--ink)] truncate">{f.category}</span>
        <span className="ml-auto text-xs capitalize text-[var(--ink-subtle)] font-medium px-2 py-0.5 rounded-full bg-black/5 flex-shrink-0">
          {f.severity}
        </span>
      </div>
      <p className="mt-2 line-clamp-2 text-sm text-[var(--ink-muted)] leading-relaxed">
        {f.explanation}
      </p>
      {f.quoted_text && (
        <p className="mt-2 line-clamp-1 text-xs text-[var(--ink-subtle)] italic border-l-2 pl-2"
          style={{ borderColor: SEVERITY_COLORS[f.severity] }}>
          &ldquo;{f.quoted_text}&rdquo;
        </p>
      )}
      {f.statute_citation && (
        <p className="mt-2 text-xs text-[var(--accent-deep)] font-medium">
          {f.statute_citation}
        </p>
      )}
      {f.damages_estimate !== null && f.damages_estimate !== undefined && f.damages_estimate > 0 && (
        <p className="mt-1 text-xs font-semibold" style={{ color: "var(--sev-favorable)" }}>
          Est. recovery: ${f.damages_estimate.toLocaleString()}
        </p>
      )}
    </button>
  );
}
