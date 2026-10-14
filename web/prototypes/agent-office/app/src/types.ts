// Shapes written by observe.py (events.jsonl lines and live.js). Unknown or missing values stay null, never 0.
export type Phase = 'start' | 'end' | 'fail' | 'point'

export interface OfficeEvent {
  v: number
  id: string
  ts: string
  ts_basis?: string
  src?: string
  hook: string
  session: string | null
  prompt_id: string | null
  agent_id: string | null
  actor: string
  tool: string | null
  call: string | null
  kind: string
  node: string | null
  op: string | null
  ops?: string[]
  phase: Phase
  basis: string
  detail: Record<string, unknown> | null
  keys?: string[]
  input_keys?: string[]
}

export interface WorkflowEvent {
  kind: string
  observed_at: string
  [key: string]: unknown
}

export type CountKey = 'pains' | 'existing_features' | 'remaining_pains' | 'concepts' | 'evidence_refs'

export interface Candidate {
  result_version: number | null
  created_at: string | null
  status?: string | null
  counts?: Partial<Record<CountKey, number | null>>
  contract_valid?: boolean | null
  structural_valid?: boolean | null
  acceptance_ready?: boolean | null
  semantic_status?: string | null
}

export interface DbSnapshot {
  available: boolean
  reason?: string
  read_at?: string
  workflow?: {
    research_id: string
    started_at: string | null
    budget_seconds: number | null
    research_stopped_at: string | null
    finished_at: string | null
  } | null
  workflow_events?: WorkflowEvent[]
  request?: { question: string | null; turn_id: string | null; status: string | null } | null
  turn?: {
    turn_id: string
    status: string | null
    revision_count: number | null
    result_version: number | null
    valid: boolean | null
    created_at: string | null
  } | null
  results?: number | null
  candidates?: Candidate[]
  evidence_delivered?: number | null
  evidence_reviews?: number | null
  cancelled?: boolean | null
  latest_export?: { name: string | null; modified_at: string | null; count: number | null } | null
}

// The result viewer's data file (web/prototypes/visual-viewer build_view.py -> view-data.js); only these fields are read.
export interface ResultView {
  kind?: string
  generated_at?: string
  context?: { file?: { name?: string }; status?: { text?: string; tone?: string }[] }
}

export interface LiveFile {
  kind: string
  version: number
  written_at: string
  harness_version?: string | null
  events: OfficeEvent[]
  db?: DbSnapshot | null
}

export type Mode = 'live' | 'replay' | 'demo'

declare global {
  interface Window {
    LGAX_OFFICE_LIVE?: LiveFile
    LGAX_VIEW?: ResultView
  }
}
