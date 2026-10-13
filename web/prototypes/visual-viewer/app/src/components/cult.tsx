/*! @license
 * Parts of this file are adapted from Cult UI (https://www.cult-ui.com, github.com/nolly-studio/cult-ui):
 * texture-card, texture-overlay (paperGrain), dynamic-island, expandable.
 *
 * MIT License
 * Copyright (c) 2023 Jordan-Gilliam
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of
 * the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
 * THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
// Changes: simplified for a read-only viewer (no animation queue, no measuring helper; height animates to 'auto'),
// keyboard toggles, reduced motion respected by motion's defaults.
import type { HTMLAttributes, ReactNode } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { cn } from '../lib/utils'

/* texture-card: layered hairline borders that read as a pressed paper card. */
export function TextureCard({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('rounded-[24px] border border-white/60 bg-gradient-to-b from-[#f7f3ec] to-white/70', className)} {...props}>
      <div className="h-full rounded-[23px] border border-black/10">
        <div className="h-full rounded-[22px] border border-white/50">
          <div className="h-full rounded-[21px] border border-stone-950/15">
            <div className="h-full w-full rounded-[20px] border border-white/50">{children}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function TextureSeparator() {
  return <div className="border border-b-stone-300/60 border-l-transparent border-r-transparent border-t-white" />
}

/* texture-overlay (paperGrain). */
export function PaperGrain({ className, opacity = 0.6 }: { className?: string; opacity?: number }) {
  return (
    <div aria-hidden style={{ opacity }}
      className={cn('pointer-events-none absolute inset-0 bg-[repeating-linear-gradient(0deg,rgba(0,0,0,0.06)_0px,transparent_1px,transparent_3px),repeating-linear-gradient(90deg,rgba(0,0,0,0.05)_0px,transparent_1px,transparent_4px),repeating-linear-gradient(45deg,rgba(0,0,0,0.03)_0px,transparent_1px,transparent_5px)]', className)} />
  )
}

/* dynamic-island: a black pill that springs between a compact and a large size. */
export function Island({ open, onToggle, compact, large }: { open: boolean; onToggle: () => void; compact: ReactNode; large: ReactNode }) {
  return (
    <motion.button type="button" onClick={onToggle} aria-expanded={open}
      className="no-print relative mx-auto block overflow-hidden bg-black text-left text-white shadow-lg ring-1 ring-black/10 hover:shadow-xl"
      initial={false}
      animate={{ width: open ? 560 : 340, height: open ? 196 : 44, borderRadius: open ? 36 : 46 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}>
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.div key={open ? 'large' : 'compact'} className="absolute inset-0"
          initial={{ opacity: 0, scale: 0.9, y: 5 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.95 }}
          transition={{ type: 'spring', stiffness: 400, damping: 30 }}>
          {open ? large : compact}
        </motion.div>
      </AnimatePresence>
    </motion.button>
  )
}

/* expandable: a card whose extra content opens in place. */
export function ExpandCard({ open, onToggle, head, children, className, ...props }: {
  open: boolean; onToggle: () => void; head: ReactNode; children: ReactNode; className?: string
} & Omit<HTMLAttributes<HTMLDivElement>, 'children'>) {
  return (
    <div className={cn('rounded-2xl bg-white/90 p-1.5 shadow-[0_1px_0_rgba(255,255,255,.8)_inset,0_8px_24px_-12px_rgba(60,40,20,.25)] ring-1 ring-stone-900/10', className)} {...props}>
      <div role="button" tabIndex={0} aria-expanded={open} onClick={onToggle}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}
        className="cursor-pointer rounded-xl p-3 outline-none focus-visible:ring-2 focus-visible:ring-amber-500">
        {head}
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div key="body" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 200, damping: 24 }} className="overflow-hidden">
            <div className="px-3 pb-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
