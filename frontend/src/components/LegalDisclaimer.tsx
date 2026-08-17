/**
 * Fixed legal disclaimer pinned to the bottom-right on every page (mounted once in
 * the root layout). Kept subtle so it never competes with page content.
 */
export function LegalDisclaimer() {
  return (
    <p
      className="legal-disclaimer"
      style={{
        position: "fixed",
        bottom: "14px",
        right: "16px",
        zIndex: 50,
        maxWidth: "280px",
        margin: 0,
        textAlign: "right",
        fontSize: "10px",
        lineHeight: 1.4,
        letterSpacing: "0.005em",
        color: "var(--ink-subtle)",
        pointerEvents: "none",
      }}
    >
      Clause is not a law firm and this is not legal advice. This is for
      informational and demonstration purposes only.
    </p>
  );
}
