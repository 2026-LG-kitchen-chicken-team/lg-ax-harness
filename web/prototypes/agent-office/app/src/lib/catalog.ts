// The office floor follows product v0.10.0: one main agent, three optional research roles, six work Skills.
// Ids match observe.py (and the teammate control room's catalog.ts). Descriptions quote the installed files.
export type NodeKind = 'main' | 'role' | 'skill' | 'place'

export interface OfficeNode {
  id: string
  kind: NodeKind
  ko: string
  code: string
  color: string
  pos: [number, number] // floor x, z
  size: [number, number] // room width, depth
  description: string
  source: string
  ops?: string[]
  note?: string
}

const SKILL_OPS: Record<string, string[]> = {
  'evidence-retrieval': ['doctor', 'list_models', 'open_request', 'open_request_bundle', 'resolve_request', 'resolve_request_bundle',
    'current_request', 'record_request_research', 'open_product_workflow', 'record_workflow_event', 'workflow_status',
    'evidence_inventory', 'read_evidence_batch', 'record_evidence_review', 'evidence_coverage', 'prepare_planning_input',
    'retrieve_reviews', 'retrieve_product_facts', 'select_evidence', 'match_product_scope', 'set_request_scope_policy'],
  'web-evidence-collection': ['configure_web_research', 'fetch_web_page', 'capture_web_page', 'import_web_evidence', 'import_web_evidence_bulk'],
  'needs-structuring': ['select_evidence', 'validate_source_refs'],
  'feature-comparison': ['match_product_scope', 'retrieve_product_facts', 'select_evidence'],
  'concept-writing': ['validate_constraints', 'validate_source_refs'],
  'review-and-revise': ['start_turn', 'prepare_review_packet', 'verify_review_packet', 'validate_result_contract', 'review_product_result',
    'save_result', 'save_reviewed_result', 'save_and_export', 'prepare_web_result', 'get_completion_summary', 'deliver_result', 'export_session', 'current_request',
    'get_turn', 'record_usage', 'cancel_turn', 'begin_invocation', 'finish_invocation'],
}

const RESEARCH_RULE = '선택 역할 · 최대 2명 병렬 · 각 1회 180초 · 업무 시계가 420초 이상 남았을 때만'

export const NODES: OfficeNode[] = [
  {
    id: 'main', kind: 'main', ko: '메인 기획자', code: 'product-planning', color: '#38e1ff', pos: [0, 0.5], size: [6.2, 6.0],
    description: '기존 실행기의 메인 Agent 1개가 업무 Skill 6개를 필요에 따라 적용한다. 연구 역할(자식)은 조회·분석만 하고 등록·coverage·후보·저장은 메인 단일 작성자다.',
    source: 'agents/product-planning.md (product-planning-v7.5)',
  },
  {
    id: 'product_official_researcher', kind: 'role', ko: '공식 자료 조사', code: 'product-official-researcher', color: '#7c8cff', pos: [-12.2, -8.4], size: [4.6, 4.0],
    description: '메인이 정확 모델의 사양·설명서·현 기능·안전/사용 조건을 별도 조사/대조할 때 선택한다. 개발 Agent가 아니다.',
    source: 'agents/product-official-researcher.md', note: RESEARCH_RULE,
  },
  {
    id: 'product_review_researcher', kind: 'role', ko: '후기 조사·분석', code: 'product-review-researcher', color: '#c77dff', pos: [-6.9, -8.4], size: [4.6, 4.0],
    description: '메인이 실제 후기를 별도 조사/분석할 필요가 있을 때 선택한다. 개발 Agent가 아니다.',
    source: 'agents/product-review-researcher.md', note: RESEARCH_RULE,
  },
  {
    id: 'product_evidence_reviewer', kind: 'role', ko: '독립 근거 검토', code: 'product-evidence-reviewer', color: '#ff7ad9', pos: [-1.6, -8.4], size: [4.6, 4.0],
    description: '메인이 위임한 현재 요청의 상품기획 후보를 실제 원문과 독립 대조한다. 읽기만 수행하고 파일·자료·DB·후보·사용자 설정을 수정하지 않는다.',
    source: 'agents/product-evidence-reviewer.md', note: '선택 역할 · 최대 1명 1회 90초 · 최종 전달 90초 예약',
  },
  {
    id: 'evidence-retrieval', kind: 'skill', ko: '근거 조회', code: 'evidence-retrieval', color: '#2ee6a6', pos: [6.2, -4.6], size: [4.4, 3.8],
    description: '질문에서 지정하거나 해석한 제품군 또는 정확 모델의 실제 리뷰·공식 사양·설명서를 정확한 버전으로 조회할 때 사용한다.',
    source: '.claude/skills/evidence-retrieval/SKILL.md', ops: SKILL_OPS['evidence-retrieval'],
  },
  {
    id: 'web-evidence-collection', kind: 'skill', ko: '웹 수집', code: 'web-evidence-collection', color: '#ffb547', pos: [11.2, -4.6], size: [4.4, 3.8],
    description: '저장 근거 부족·자료 갱신·모델 또는 문서 연결 불명확 시 실제 고객 후기 원문과 공식 제품 자료를 외부에서 확보할 때 사용한다.',
    source: '.claude/skills/web-evidence-collection/SKILL.md', ops: SKILL_OPS['web-evidence-collection'],
    note: '외부 검색·브라우저 Tool이 실제로 있을 때만 쓰는 조건부 Skill',
  },
  {
    id: 'needs-structuring', kind: 'skill', ko: '불편 구조화', code: 'needs-structuring', color: '#ff6b8b', pos: [16.2, -4.6], size: [4.4, 3.8],
    description: '확보한 실제 후기에서 현재 제품의 불편·사용 맥락·상충 의견을 원문 근거에 연결해 정리할 때 사용한다.',
    source: '.claude/skills/needs-structuring/SKILL.md', ops: SKILL_OPS['needs-structuring'],
    note: '도구 호출이 거의 없는 Skill. 저장된 후보의 불편 수로 결과를 보여 준다.',
  },
  {
    id: 'feature-comparison', kind: 'skill', ko: '기능 대조', code: 'feature-comparison', color: '#5aa9ff', pos: [16.2, 1.6], size: [4.4, 3.8],
    description: '원문으로 확인한 불편을 같은 정확 모델의 기존 기능·사용 조건과 대조해 남은 문제를 판단할 때 사용한다.',
    source: '.claude/skills/feature-comparison/SKILL.md', ops: SKILL_OPS['feature-comparison'],
    note: '도구 호출이 거의 없는 Skill. 저장된 후보의 기존 기능·남은 불편 수로 결과를 보여 준다.',
  },
  {
    id: 'concept-writing', kind: 'skill', ko: '콘셉트 작성', code: 'concept-writing', color: '#f5e663', pos: [11.2, 1.6], size: [4.4, 3.8],
    description: '실제 근거와 기존 기능 대조로 확인된 남은 불편에 대해 조건을 지키는 상품기획 콘셉트를 작성할 때 사용한다.',
    source: '.claude/skills/concept-writing/SKILL.md', ops: SKILL_OPS['concept-writing'],
    note: '도구 호출이 거의 없는 Skill. 저장된 후보의 콘셉트 수로 결과를 보여 준다.',
  },
  {
    id: 'review-and-revise', kind: 'skill', ko: '검토·수정', code: 'review-and-revise', color: '#a3ff5c', pos: [6.2, 1.6], size: [4.4, 3.8],
    description: '상품기획 후보의 원문 의미·모델·기존 기능 중복·가정·제약을 검토하고 최초 생성과 최대2회 수정을 저장할 때 사용한다.',
    source: '.claude/skills/review-and-revise/SKILL.md', ops: SKILL_OPS['review-and-revise'],
    note: '후보 기록: 최초 0 · 수정 1 · 수정 2. 세 번 기록 뒤 거절이면 한도 끝',
  },
  {
    id: 'reception', kind: 'place', ko: '접수창구', code: 'UserPromptSubmit', color: '#9fb4ff', pos: [-6.6, 6.8], size: [4.4, 3.2],
    description: '사용자 질문이 들어오는 곳. 훅은 질문이 왔다는 사실과 시각만 남기고 질문 원문은 남기지 않는다. 질문 글은 하네스 DB의 최신 요청(최대 300자)에서만 읽는다.',
    source: 'Claude Code UserPromptSubmit 훅 · runtime-data/product.sqlite (읽기 전용)',
  },
  {
    id: 'vault', kind: 'place', ko: '자료 보관소', code: 'product.sqlite', color: '#e7c27d', pos: [-12.2, 6.8], size: [4.6, 3.2],
    description: '하네스 DB. 업무 시계·작업 일지·turn 상태·후보 수·전달/검토한 근거 수를 읽기 전용으로 최대 0.2초만 확인한다.',
    source: 'runtime-data/product.sqlite (mode=ro)',
  },
  {
    id: 'console', kind: 'place', ko: '명령 콘솔', code: 'Bash · PowerShell', color: '#7dffcf', pos: [-6.6, 0.5], size: [4.0, 3.2],
    description: 'Skill 작업이 아닌 셸 명령. 명령 원문은 남기지 않고, 정해진 목록에 있는 프로그램 이름(ls·python·uv 등)만 남긴다.',
    source: 'Claude Code PreToolUse/PostToolUse 훅',
  },
  {
    id: 'shelf', kind: 'place', ko: '파일 서가', code: 'Read · Write · Edit · Grep · Glob', color: '#b4c6ff', pos: [-12.2, 0.5], size: [4.6, 3.2],
    description: '파일 도구가 다룬 폴더 구역(작업 기록·결과 내보내기·웹 근거 보관·Skill 폴더·문서 등)만 남긴다. 파일 이름과 내용은 남기지 않는다.',
    source: 'Claude Code PreToolUse/PostToolUse 훅',
  },
  {
    id: 'shipping', kind: 'place', ko: '출고실', code: 'save · export', color: '#a3ff5c', pos: [11.2, 7.4], size: [14.4, 3.0],
    description: '후보 저장·내보내기 결과. 저장 응답의 승인/거절과 turn 상태를 보여 준다. 승인은 계약 검사 통과이며 원문 의미·효과의 자동 증명이 아니다.',
    source: 'review-and-revise 저장 응답 (save.accepted · turn.status)',
  },
  {
    id: 'web', kind: 'place', ko: '바깥 웹 거리', code: 'WebFetch · WebSearch · 브라우저', color: '#ff9f43', pos: [3, -14.2], size: [34, 3.6],
    description: '외부 사이트. 실제로 열람한 사이트의 호스트 이름만 건물로 세운다. 주소의 경로·검색어는 남기지 않는다.',
    source: 'Claude Code PreToolUse/PostToolUse 훅 · 작업 일지 source_scan',
  },
]

export const NODE: Record<string, OfficeNode> = Object.fromEntries(NODES.map((n) => [n.id, n]))
export const ROLE_IDS = ['product_official_researcher', 'product_review_researcher', 'product_evidence_reviewer']
export const SKILL_IDS = ['evidence-retrieval', 'web-evidence-collection', 'needs-structuring', 'feature-comparison', 'concept-writing', 'review-and-revise']
export const SAVE_OPS = new Set(['save_and_export', 'save_reviewed_result', 'save_result'])
// Rooms whose result is read from the saved candidate (they make almost no tool calls of their own).
export const COUNT_ROOMS: { node: string; keys: { key: 'pains' | 'existing_features' | 'remaining_pains' | 'concepts'; ko: string }[] }[] = [
  { node: 'needs-structuring', keys: [{ key: 'pains', ko: '불편' }] },
  { node: 'feature-comparison', keys: [{ key: 'existing_features', ko: '기존 기능' }, { key: 'remaining_pains', ko: '남은 불편' }] },
  { node: 'concept-writing', keys: [{ key: 'concepts', ko: '콘셉트' }] },
]

export const FLOOR = { minX: -15.6, maxX: 19.6, minZ: -11, maxZ: 9.4 }

export function nodeName(id: string | null | undefined): string {
  if (!id) return ''
  if (id === 'other_subagent') return 'Claude Code 보조 작업'
  return NODE[id]?.ko ?? id
}
