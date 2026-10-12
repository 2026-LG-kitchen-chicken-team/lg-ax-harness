// Interactions adapted from Skiper UI free components (https://skiper-ui.com), by @gurvinder-singh02:
//   skiper31 Text Scroll animation · skiper58 Text roll navigation · skiper52 ExpandOnHover · skiper89 Scroll progress.
// Skiper UI licence (free version): free to use and modify in personal and commercial projects; attribution to
// Skiper UI is required. The D view shows that attribution on screen.
// Changes here: text instead of images, keyboard focus, no lenis/number-flow/swiper, reduced motion shows the end state.
import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion, useMotionValueEvent, useReducedMotion, useScroll, useTransform, type MotionValue } from 'motion/react'
import { cn } from '../lib/utils'

/* skiper31 (CharacterV1): characters start spread out around the centre and settle as the section scrolls. */
function ScatterChar({ char, index, center, progress }: { char: string; index: number; center: number; progress: MotionValue<number> }) {
  const d = index - center
  const x = useTransform(progress, [0, 0.5], [d * 46, 0])
  const rotateX = useTransform(progress, [0, 0.5], [d * 40, 0])
  return (
    <motion.span aria-hidden className={cn('inline-block', char === ' ' && 'w-[0.3em]')} style={{ x, rotateX }}>
      {char}
    </motion.span>
  )
}

export function ScatterText({ text, progress, className }: { text: string; progress: MotionValue<number>; className?: string }) {
  const reduce = useReducedMotion()
  const total = Array.from(text).length
  const center = Math.floor(total / 2)
  if (reduce) return <span className={className}>{text}</span>
  // Characters move one by one, but each word stays in one unbreakable box so lines never split inside a word.
  let offset = 0
  const words = text.split(' ').map((w) => { const start = offset; offset += Array.from(w).length + 1; return { w, start } })
  return (
    <span className={className} style={{ perspective: '500px' }}>
      <span className="sr-only">{text}</span>
      {words.map(({ w, start }, k) => (
        <span key={k} aria-hidden>
          <span className="inline-block whitespace-nowrap">
            {Array.from(w).map((c, i) => <ScatterChar key={i} char={c} index={start + i} center={center} progress={progress} />)}
          </span>
          {k < words.length - 1 ? ' ' : null}
        </span>
      ))}
    </span>
  )
}

/* skiper58 TextRoll: on hover the letters roll up and a copy rolls in from below. */
const STAGGER = 0.035
export function TextRoll({ children, className, center = false }: { children: string; className?: string; center?: boolean }) {
  const letters = Array.from(children)
  const delay = (i: number) => (center ? STAGGER * Math.abs(i - (letters.length - 1) / 2) : STAGGER * i)
  return (
    <motion.span initial="initial" whileHover="hovered" whileFocus="hovered" className={cn('relative block overflow-hidden', className)} style={{ lineHeight: 0.85 }}>
      <span className="block" aria-hidden={false}>
        {letters.map((l, i) => (
          <motion.span key={i} className="inline-block" variants={{ initial: { y: 0 }, hovered: { y: '-100%' } }} transition={{ ease: 'easeInOut', delay: delay(i) }}>
            {l === ' ' ? ' ' : l}
          </motion.span>
        ))}
      </span>
      <span className="absolute inset-0" aria-hidden>
        {letters.map((l, i) => (
          <motion.span key={i} className="inline-block" variants={{ initial: { y: '100%' }, hovered: { y: 0 } }} transition={{ ease: 'easeInOut', delay: delay(i) }}>
            {l === ' ' ? ' ' : l}
          </motion.span>
        ))}
      </span>
    </motion.span>
  )
}

/* skiper52 HoverExpand_001: a row of narrow strips; the hovered or focused one widens and shows its content. */
export function HoverExpand<T>({ items, strip, open, className }: {
  items: T[]; strip: (item: T, active: boolean) => ReactNode; open: (item: T) => ReactNode; className?: string
}) {
  const [active, setActive] = useState(0)
  return (
    <div className={cn('flex w-full items-stretch justify-center gap-1.5', className)}>
      {items.map((it, i) => (
        <motion.div key={i} role="group" tabIndex={0} aria-expanded={active === i}
          className="relative h-[30rem] min-w-0 cursor-pointer overflow-hidden rounded-3xl text-left focus-visible:outline-2 focus-visible:outline-orange-400"
          initial={false}
          animate={{ flexGrow: active === i ? 7 : 1 }}
          style={{ flexBasis: 0 }}
          transition={{ duration: 0.35, ease: 'easeInOut' }}
          onHoverStart={() => setActive(i)} onFocus={() => setActive(i)} onClick={() => setActive(i)}>
          {strip(it, active === i)}
          <AnimatePresence>
            {active === i && (
              <motion.div key="open" className="absolute inset-0 flex flex-col justify-end p-7"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2, delay: 0.15 }}>
                {open(it)}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      ))}
    </div>
  )
}

/* skiper89 Scroll progress 001: a small draggable ring that fills as the page scrolls (percentage on hover). */
export function ScrollRing() {
  const { scrollYProgress } = useScroll()
  const [pct, setPct] = useState(0)
  const clamped = useTransform(scrollYProgress, (v) => Math.min(Math.max(v, 0), 1))
  useMotionValueEvent(clamped, 'change', (v) => setPct(Math.round(v * 100)))
  const r = 18
  return (
    <motion.div drag dragMomentum={false} className="group no-print fixed bottom-5 right-5 z-50 cursor-grab active:cursor-grabbing" title="스크롤 진행 · 끌어서 옮길 수 있음">
      <span className="absolute -top-1 left-1/2 -translate-x-1/2 -translate-y-full text-xs font-medium tabular-nums text-white/40 opacity-0 group-hover:opacity-100">{pct}%</span>
      <div className="flex size-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-orange-400 backdrop-blur">
        <svg className="size-10" viewBox="0 0 48 48" role="presentation">
          <circle cx="24" cy="24" r={r} stroke="currentColor" strokeWidth="3" className="opacity-25" fill="none" />
          <motion.circle cx="24" cy="24" r={r} stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round"
            style={{ pathLength: clamped, rotate: -90, transformOrigin: '50% 50%' }} />
        </svg>
      </div>
    </motion.div>
  )
}
