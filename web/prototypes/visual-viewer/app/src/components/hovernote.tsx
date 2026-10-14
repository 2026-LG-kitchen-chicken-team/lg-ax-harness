// A small trigger that shows secondary information (where a number comes from, file names, codes) on hover, focus or
// tap. K uses it to keep that information one step away instead of on the page. The note is drawn in document.body so
// scroll boxes and the sliding sidebar never clip it; it closes on scroll, blur, mouse leave or Escape.
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { Info } from 'lucide-react'
import { cn } from '../lib/utils'

type Pos = { left: number; top?: number; bottom?: number }

export function HoverNote({ children, note, className, label }: { children: ReactNode; note: ReactNode; className?: string; label?: string }) {
  const id = useId()
  const ref = useRef<HTMLButtonElement>(null)
  const [pos, setPos] = useState<Pos | null>(null)
  const show = () => {
    const el = ref.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const left = Math.max(8, Math.min(r.left, window.innerWidth - Math.min(352, window.innerWidth - 16) - 8))
    // Below the trigger, or above it near the bottom of the window.
    setPos(r.bottom > window.innerHeight - 180 ? { left, bottom: window.innerHeight - r.top + 8 } : { left, top: r.bottom + 8 })
  }
  const hide = () => setPos(null)
  useEffect(() => {
    if (!pos) return
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setPos(null) }
    window.addEventListener('scroll', hide, { passive: true, capture: true })
    window.addEventListener('keydown', esc)
    return () => { window.removeEventListener('scroll', hide, { capture: true }); window.removeEventListener('keydown', esc) }
  }, [pos])
  return (
    <>
      <button ref={ref} type="button" aria-describedby={pos ? id : undefined} aria-label={label}
        onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide} onClick={show}
        className={cn('cursor-help hover:bg-black/[0.05] focus-visible:outline-2 focus-visible:outline-offset-2', className)}>
        {children}
      </button>
      {pos && createPortal(
        <div id={id} role="tooltip" style={pos} data-side={pos.top != null ? 'below' : 'above'}
          className="lg-tip no-print pointer-events-none fixed z-[80] w-max max-w-[min(22rem,calc(100vw-1rem))] break-words rounded-xl border border-[#e3e8e3] bg-white px-3.5 py-2.5 text-[12.5px] leading-relaxed text-zinc-800 shadow-[0_14px_36px_-14px_rgb(0_0_0/0.3)]">
          {note}
        </div>,
        document.body,
      )}
    </>
  )
}

// K's small "출처" mark: where a number or judgement comes from, on hover, focus or tap.
export function SourceNote({ text }: { text: string }) {
  return (
    <HoverNote note={<>출처: {text}</>} className="inline-flex items-center gap-1 rounded px-1 text-[11px] text-zinc-400 hover:text-zinc-700">
      <Info className="size-3" aria-hidden />출처
    </HoverNote>
  )
}
