/** Maps clause severity levels to their CSS variable references. */
export const SEVERITY_COLORS: Record<string, string> = {
  illegal: "var(--sev-illegal)",
  high: "var(--sev-high)",
  medium: "var(--sev-medium)",
  favorable: "var(--sev-favorable)",
};

/** Resolved hex values for contexts that cannot use CSS variables (e.g. PDF canvas rendering). */
export const HIGHLIGHT_HEX: Record<string, string> = {
  red: "#E5484D",
  orange: "#E8833A",
  yellow: "#E4B62C",
  green: "#3FA372",
};
