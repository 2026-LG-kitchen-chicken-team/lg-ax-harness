import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Fragment, type ReactNode } from 'react'
import type { Tone } from '../types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const TONES: Tone[] = ['blue', 'green', 'red', 'orange', 'purple', 'gray', 'k1', 'k2', 'k3', 'k4']
export const tone = (t?: string): Tone => (TONES.includes(t as Tone) ? (t as Tone) : 'gray')

export const TONE_HEX: Record<Tone, string> = {
  blue: '#2563eb', green: '#16a34a', red: '#e11d48', orange: '#f59e0b', purple: '#7c3aed', gray: '#a1a1aa',
  k1: '#9ccfb0', k2: '#5fae80', k3: '#2f8f57', k4: '#1d5c39',
}

// Badge / soft surface classes per tone (shadcn-like subtle tints).
export const TONE_SOFT: Record<Tone, string> = {
  blue: 'bg-blue-50 text-blue-700 ring-blue-600/15',
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  red: 'bg-rose-50 text-rose-700 ring-rose-600/15',
  orange: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  purple: 'bg-violet-50 text-violet-700 ring-violet-600/15',
  gray: 'bg-zinc-100 text-zinc-700 ring-zinc-500/15',
  k1: 'bg-[#f0f7f2] text-[#3f7356] ring-[#9ccfb0]/45',
  k2: 'bg-[#e8f4ec] text-[#2f6b49] ring-[#5fae80]/35',
  k3: 'bg-[#dcefe3] text-[#22603c] ring-[#2f8f57]/30',
  k4: 'bg-[#d0e6d8] text-[#163d28] ring-[#1d5c39]/30',
}
export const TONE_DOT: Record<Tone, string> = {
  blue: 'bg-blue-500', green: 'bg-emerald-500', red: 'bg-rose-500',
  orange: 'bg-amber-500', purple: 'bg-violet-500', gray: 'bg-zinc-400',
  k1: 'bg-[#9ccfb0]', k2: 'bg-[#5fae80]', k3: 'bg-[#2f8f57]', k4: 'bg-[#1d5c39]',
}

const nf = new Intl.NumberFormat('ko-KR')
// Unovis tooltips take HTML strings; everything from the export is escaped first.
export const esc = (s: unknown) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] as string))
export const fmt = (v: unknown) => (typeof v === 'number' ? nf.format(v) : v == null ? '' : String(v))

// External links: HTTPS only. Relative paths (same folder) are allowed; other schemes are dropped.
export function safeHref(h?: string | null): string | null {
  if (!h) return null
  const s = String(h).trim()
  if (/^https:\/\//i.test(s)) return s
  if (/^[a-z][a-z0-9+.-]*:/i.test(s) || s.startsWith('//')) return null
  return s
}

// The builder's tiny markup: `code` and **bold**. Rendered as React nodes, never as HTML.
export function Md({ text }: { text?: string | null }): ReactNode {
  const s = String(text ?? '')
  const parts: ReactNode[] = []
  const re = /`([^`]+)`|\*\*([^*]+)\*\*/g
  let last = 0
  let m: RegExpExecArray | null
  let i = 0
  while ((m = re.exec(s))) {
    if (m.index > last) parts.push(<Fragment key={i++}>{s.slice(last, m.index)}</Fragment>)
    if (m[1] != null) parts.push(<code key={i++} className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em] text-emerald-700">{m[1]}</code>)
    else parts.push(<b key={i++} className="font-semibold">{m[2]}</b>)
    last = m.index + m[0].length
  }
  if (last < s.length) parts.push(<Fragment key={i++}>{s.slice(last)}</Fragment>)
  return <>{parts}</>
}
