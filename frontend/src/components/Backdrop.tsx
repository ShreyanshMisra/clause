/**
 * Backdrop - fixed, z-behind, aria-hidden warm gradient blob layer.
 *
 * Three slowly drifting blobs in Clause's coral/terracotta palette create a
 * soft gooey depth effect behind all page content. A grain overlay adds
 * subtle tactile texture without visual noise.
 *
 * CSS animations are defined in globals.css (blobDrift1/2/3, grainShift).
 * All blob motion uses transform-only properties for GPU compositing.
 */
export function Backdrop() {
  return (
    <div
      aria-hidden
      className="fixed inset-0 -z-10 overflow-hidden pointer-events-none select-none"
    >
      {/* ── Blob 1 - top-left warm coral ─────────────────────────────── */}
      <div
        className="absolute -top-40 -left-32 h-[32rem] w-[32rem] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 35% 35%, #D97757 0%, #E8833A 40%, transparent 72%)",
          filter: "blur(72px)",
          opacity: 0.45,
          animation: "blobDrift1 18s ease-in-out infinite",
          willChange: "transform",
        }}
      />

      {/* ── Blob 2 - right-center terracotta/amber ───────────────────── */}
      <div
        className="absolute top-1/3 -right-28 h-[36rem] w-[36rem] rounded-full"
        style={{
          background:
            "radial-gradient(circle at 65% 30%, #CC785C 0%, #E4B62C 45%, transparent 70%)",
          filter: "blur(80px)",
          opacity: 0.28,
          animation: "blobDrift2 24s ease-in-out infinite",
          willChange: "transform",
        }}
      />

      {/* ── Blob 3 - bottom-center cream highlight ───────────────────── */}
      <div
        className="absolute -bottom-24 left-1/4 h-[28rem] w-[42rem] rounded-full"
        style={{
          background:
            "radial-gradient(ellipse at 50% 60%, #D97757 0%, #FAF9F5 55%, transparent 75%)",
          filter: "blur(90px)",
          opacity: 0.22,
          animation: "blobDrift3 30s ease-in-out infinite",
          willChange: "transform",
        }}
      />

      {/* ── Subtle warm vignette framing ─────────────────────────────── */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 90% 80% at 50% 10%, transparent 60%, rgba(20,20,19,0.06) 100%)",
        }}
      />

      {/* ── Film grain texture overlay ────────────────────────────────── */}
      <svg
        className="absolute inset-0 h-full w-full"
        xmlns="http://www.w3.org/2000/svg"
        style={{
          opacity: 0.035,
          animation: "grainShift 0.9s steps(1) infinite",
          mixBlendMode: "multiply",
        }}
      >
        <filter id="clause-grain">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.72"
            numOctaves="4"
            stitchTiles="stitch"
          />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="110%" height="110%" filter="url(#clause-grain)" />
      </svg>
    </div>
  );
}
