import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Fragment, type ReactNode } from 'react'
import type { Tone } from '../types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const TONES: Tone[] = ['blue', 'green', 'red', 'orange', 'purple', 'gray']
export const tone = (t?: string): Tone => (TONES.includes(t as Tone) ? (t as Tone) : 'gray')

export const TONE_HEX: Record<Tone, string> = {
  blue: '#2563eb', green: '#16a34a', red: '#e11d48', orange: '#f59e0b', purple: '#7c3aed', gray: '#a1a1aa',
}

// Badge / soft surface classes per tone (shadcn-like subtle tints).
export const TONE_SOFT: Record<Tone, string> = {
  blue: 'bg-blue-50 text-blue-700 ring-blue-600/15',
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  red: 'bg-rose-50 text-rose-700 ring-rose-600/15',
  orange: 'bg-amber-50 text-amber-800 ring-amber-600/20',
  purple: 'bg-violet-50 text-violet-700 ring-violet-600/15',
  gray: 'bg-zinc-100 text-zinc-700 ring-zinc-500/15',
}
export const TONE_TEXT: Record<Tone, string> = {
  blue: 'text-blue-600', green: 'text-emerald-600', red: 'text-rose-600',
  orange: 'text-amber-600', purple: 'text-violet-600', gray: 'text-zinc-500',
}
export const TONE_DOT: Record<Tone, string> = {
  blue: 'bg-blue-500', green: 'bg-emerald-500', red: 'bg-rose-500',
  orange: 'bg-amber-500', purple: 'bg-violet-500', gray: 'bg-zinc-400',
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
