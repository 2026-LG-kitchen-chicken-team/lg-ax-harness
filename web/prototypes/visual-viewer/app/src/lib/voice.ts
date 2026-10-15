// The viewer (K 업무형) reads in report style (보고서체): sentences the harness writes in 합니다체 end in short forms
// ("저장했습니다" → "저장함", "없습니다" → "없음", "불편입니다" → "불편"). Only 합니다체/하세요 endings change, so the
// question, quotes and model-written result text (한다체) keep their wording; quotes are also skipped by key.
import { useSkin } from './skin'
import type { View } from '../types'

const BASE = 0xac00
const FINAL_L = 8 // ㄹ
const FINAL_M = 16 // ㅁ
const FINAL_B = 17 // ㅂ
const isSyllable = (c: string) => c >= '가' && c <= '힣'
const finalOf = (c: string) => (c.charCodeAt(0) - BASE) % 28
const withFinal = (c: string, f: number) => String.fromCharCode(c.charCodeAt(0) - finalOf(c) + f)

// ㄹ-stem verbs drop ㄹ before ㅂ니다; their noun forms keep it.
const L_STEMS: Record<string, string> = { 엽니다: '엶', 만듭니다: '만듦', 압니다: '앎', 붑니다: '붊', 겁니다: '것임' }
// Verbs whose stem ends in 이 ("보이다" → "보입니다"): not the copula "입니다", so they become "보임", not "보".
const I_VERBS = ['보', '쓰', '놓', '쌓', '줄', '붙', '먹', '덮', '깎', '끓', '높', '낮']

const END = '(?=[\\s.,!?:;()\\]}*"\'”’`」]|$)'

export function reportVoice(text: string): string {
  if (!text || !/니다|세요/.test(text)) return text
  let s = text
  s = s.replace(new RegExp('아닙니다' + END, 'g'), '아님')
  s = s.replace(new RegExp(`(${I_VERBS.join('|')})입니다` + END, 'g'), '$1임')
  s = s.replace(new RegExp('입니다' + END, 'g'), '')
  s = s.replace(new RegExp('(엽|만듭|압|붑|겁)니다' + END, 'g'), (m) => L_STEMS[m] || m)
  s = s.replace(new RegExp('(?:되었|됐)습니다' + END, 'g'), '됨')
  s = s.replace(new RegExp('했습니다' + END, 'g'), '함')
  s = s.replace(new RegExp('습니다' + END, 'g'), '음')
  s = s.replace(new RegExp('([가-힣])니다' + END, 'g'), (m, c: string) => (isSyllable(c) && finalOf(c) === FINAL_B ? withFinal(c, FINAL_M) : m))
  s = s.replace(new RegExp('([가-힣])으세요' + END, 'g'), (_m, c: string) => `${c}을 것`)
  s = s.replace(new RegExp('([가-힣])세요' + END, 'g'), (m, c: string) => (isSyllable(c) && finalOf(c) === 0 ? `${withFinal(c, FINAL_L)} 것` : m))
  return s
}

// UI sentences (search, empty states): report style inside the view.
export function useVoice(): (text: string) => string {
  return useSkin()?.id === 'ops' ? reportVoice : (text) => text
}

// Keys whose text is quoted or written by the model/user and must stay exactly as saved.
const KEEP = new Set(['quote', 'quotes', 'question', 'href', 'url', 'id', 'source_id', 'value', 'mono', 'tone', 'type', 'key'])

function walk(x: unknown, parentType: string | null): unknown {
  if (typeof x === 'string') return reportVoice(x)
  if (Array.isArray(x)) return x.map((v) => walk(v, parentType))
  if (x && typeof x === 'object') {
    const o = x as Record<string, unknown>
    const type = typeof o.type === 'string' ? o.type : parentType
    if (type === 'quotes') return o // quote blocks are review text
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(o)) {
      // The cover's title is the user's question as written.
      out[k] = KEEP.has(k) || (type === 'hero' && k === 'title') ? v : walk(v, type)
    }
    return out
  }
  return x
}

export function voiceView(view: View | null): View | null {
  return view ? (walk(view, null) as View) : view
}
