// The harness writes field names next to Korean words for traceability ("기획 초안 완료(completed)",
// "결과 가정 1개 (assumptions)", "turn 목록"). The screen shows the Korean words only. The field names stay where they are kept for
// reference (chip tips, source notes, folded table details); build_view.py's data is unchanged.
import type { View } from '../types'

// "(completed)", "(held)", "(assumptions)", "(status · valid)": lowercase field names (three letters or more) only, so
// page and item references such as "(p10)" or "(c1)" stay.
const CODE_PAREN = /\s*\((?:[a-z]{3}[a-z0-9_.]*)(?:\s*[·,/]\s*[a-z]{3}[a-z0-9_.]*)*\)/g
const HEADINGS: Record<string, string> = { 'turn 목록': '질문 목록', '세션 export': '세션 기록 파일', 'turn별 등록 근거': '질문별 등록 근거' }
const COLUMN_LABELS: Record<string, string> = { turn: '번호' }

// Text kept exactly: what users, reviews and the model wrote; links and ids; and where codes are meant to be read.
const KEEP = new Set(['quote', 'quotes', 'question', 'href', 'url', 'id', 'source_id', 'value', 'tip', 'source', 'key', 'type', 'tone', 'summary'])

// Field=value pairs that sentences carry ("valid=true", "semantic_status: **unverified**"), in Korean.
const PHRASES: [RegExp, string][] = [
  [/semantic_status:\s*\*\*unverified\*\*/g, '**의미 검토 전**'],
  [/acceptance_ready:\s*\*\*false\*\*/g, '**인수 전**'],
  [/\bvalid=true\b/g, '유효'],
  [/\bvalid=false\b/g, '무효'],
  [/\bturn\b/g, '질문'],
  [/\binsights\b/g, '해석 파일'],
]

export const plainText = (s: string) => PHRASES.reduce((t, [re, to]) => t.replace(re, to), s.replace(CODE_PAREN, ''))

function walk(x: unknown, type: string | null): unknown {
  if (typeof x === 'string') return plainText(x)
  if (Array.isArray(x)) return x.map((v) => walk(v, type))
  if (x && typeof x === 'object') {
    const o = x as Record<string, unknown>
    const t = typeof o.type === 'string' ? o.type : type
    // Quote blocks: the quotes themselves are kept (KEEP); their status chips and notes are not quotes.
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(o)) {
      if (KEEP.has(k) || (t === 'hero' && k === 'title')) out[k] = v
      else if ((t === 'section' || t === 'heading') && k === 'text' && typeof v === 'string' && HEADINGS[v]) out[k] = HEADINGS[v]
      else if (k === 'label' && typeof v === 'string' && COLUMN_LABELS[v] && 'key' in o) out[k] = COLUMN_LABELS[v]
      else out[k] = walk(v, t)
    }
    return out
  }
  return x
}

export function plainView(view: View | null): View | null {
  return view ? (walk(view, null) as View) : view
}
