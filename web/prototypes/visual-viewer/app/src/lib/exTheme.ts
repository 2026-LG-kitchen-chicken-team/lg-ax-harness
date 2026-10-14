// D (dark exhibition) and F (A's sidebar + D's layout) share the exhibition layout. D is dark; F draws the same layout
// in A's light colours. Shared components keep D's dark classes and pass them through cx(): outside F it changes
// nothing, inside F each dark class is swapped for its light counterpart from this table (A's zinc greys and tones).
import { createContext, useContext } from 'react'

export type ExTheme = 'dark' | 'light'
export const ExThemeContext = createContext<ExTheme>('dark')
export const useLight = () => useContext(ExThemeContext) === 'light'

const LIGHT: Record<string, string> = {
  // text: white at an opacity → a zinc grey with readable contrast on white
  'text-white': 'text-zinc-950', 'hover:text-white': 'hover:text-zinc-950', 'hover:text-white/70': 'hover:text-zinc-700',
  'text-white/85': 'text-zinc-800', 'text-white/80': 'text-zinc-800', 'text-white/75': 'text-zinc-700', 'text-white/70': 'text-zinc-700',
  'text-white/60': 'text-zinc-600', 'text-white/55': 'text-zinc-600', 'text-white/50': 'text-zinc-500', 'text-white/45': 'text-zinc-500',
  'text-white/40': 'text-zinc-500', 'text-white/35': 'text-zinc-400', 'text-white/30': 'text-zinc-400', 'text-white/25': 'text-zinc-300',
  'text-zinc-100': 'text-zinc-950', 'text-zinc-300': 'text-zinc-600', 'text-zinc-400': 'text-zinc-500',
  // lines and surfaces
  'border-white/10': 'border-zinc-200', 'border-white/15': 'border-zinc-200', 'border-white/20': 'border-zinc-300',
  'ring-white/10': 'ring-zinc-200', 'bg-white/5': 'bg-white', 'decoration-white/20': 'decoration-zinc-300', 'decoration-white/30': 'decoration-zinc-300',
  // D's amber accent → A's black; tone colours → A's 600 tones
  'text-amber-300': 'text-zinc-950', 'text-amber-200': 'text-amber-600', 'text-rose-300': 'text-rose-600', 'text-rose-400': 'text-rose-600',
  'text-sky-300': 'text-blue-600', 'text-sky-200': 'text-blue-600', 'text-violet-300': 'text-violet-600', 'text-violet-200': 'text-violet-600',
  'text-emerald-300': 'text-emerald-600', 'text-emerald-200': 'text-emerald-600',
  'border-rose-400/60': 'border-rose-300',
  // pain strips: dark gradient → soft rose card
  'from-rose-500/25': 'from-rose-100', 'from-rose-500/40': 'from-rose-200', 'via-zinc-900': 'via-rose-50', 'to-zinc-950': 'to-white',
}

const same = (s: string) => s
const toLight = (s: string) => s.split(/\s+/).map((c) => LIGHT[c] ?? c).join(' ')
export function useCx(): (s: string) => string {
  return useLight() ? toLight : same
}
