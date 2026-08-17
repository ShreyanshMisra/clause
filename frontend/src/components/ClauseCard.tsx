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

      {/* Expanded legal analysis — revealed when the card is the active one. */}
      {active && (f.legal_reasoning || f.statute_quote || f.recommended_action) && (
        <div className="mt-3 space-y-2 border-t border-black/5 pt-3">
          {f.legal_reasoning && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--ink-subtle)]">Why it matters</p>
              <p className="text-xs leading-relaxed text-[var(--ink-muted)]">{f.legal_reasoning}</p>
            </div>
          )}
          {f.statute_quote && (
            <p className="text-[11px] italic leading-relaxed text-[var(--ink-subtle)] border-l-2 pl-2"
              style={{ borderColor: SEVERITY_COLORS[f.severity] }}>
              {f.statute_quote}
            </p>
          )}
          {f.recommended_action && (
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--ink-subtle)]">Recommended action</p>
              <p className="text-xs leading-relaxed text-[var(--ink-muted)]">{f.recommended_action}</p>
            </div>
          )}
        </div>
      )}

      {f.damages_estimate !== null && f.damages_estimate !== undefined && f.damages_estimate > 0 && (
        <div className="mt-2">
          <p className="text-xs font-semibold" style={{ color: "var(--sev-favorable)" }}>
            Est. recovery: ${f.damages_estimate.toLocaleString()}
          </p>
          {active && f.damages_basis && (
            <p className="mt-0.5 text-[11px] leading-snug text-[var(--ink-subtle)]">{f.damages_basis}</p>
          )}
        </div>
      )}
    </button>
  );
}
