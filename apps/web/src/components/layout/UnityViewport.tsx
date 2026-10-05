import { cn } from '@/utils/cn'

type UnityViewportProps = {
  className?: string
  /** Optional Unity WebGL build URL (iframe). Empty = placeholder. */
  src?: string
}

/**
 * Left-stage digital twin viewport.
 * Swap placeholder for Unity WebGL iframe when build is ready
 * (see unity-device-sim / architecture-services.md).
 */
export function UnityViewport({ className, src }: UnityViewportProps) {
  const embedUrl =
    src ??
    (typeof import.meta !== 'undefined'
      ? (import.meta.env.VITE_UNITY_WEBGL_URL as string | undefined)
      : undefined)

  return (
    <section
      className={cn(
        'relative min-h-0 min-w-0 flex-1 overflow-hidden bg-[#05080d]',
        className,
      )}
      aria-label="Unity digital twin"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(31,213,249,0.1),transparent_58%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,transparent,rgba(0,0,0,0.35)_85%)]" />

      {embedUrl ? (
        <iframe
          title="Unity WebGL"
          src={embedUrl}
          className="relative z-1 h-full w-full border-0"
          allow="autoplay; fullscreen; gamepad; keyboard-map"
          referrerPolicy="no-referrer-when-downgrade"
        />
      ) : (
        <div className="relative z-[1] flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
          <div className="h-24 w-24 rounded-full border border-cyan-400/25 bg-cyan-400/5 shadow-[0_0_48px_rgba(31,213,249,0.15)]" />
          <p className="font-display text-sm font-semibold tracking-wide text-cyan-200/90">
            Unity Digital Twin
          </p>
          <p className="max-w-sm text-xs leading-relaxed text-white/45">
            Mô hình nhà 3D sẽ hiển thị khi bản mô phỏng được kết nối.
          </p>
          <div className="mt-2 grid w-full max-w-md grid-cols-3 gap-2 opacity-40">
            {Array.from({ length: 6 }).map((_, i) => (
              <div
                key={i}
                className="h-16 rounded-lg border border-white/10 bg-white/[0.03]"
              />
            ))}
          </div>
        </div>
      )}

      <div className="pointer-events-none absolute bottom-3 left-3 z-[2] rounded-md border border-white/10 bg-black/40 px-2.5 py-1 text-[10px] font-medium tracking-wide text-white/55 backdrop-blur-sm">
        3D · publisher of truth
      </div>
    </section>
  )
}
