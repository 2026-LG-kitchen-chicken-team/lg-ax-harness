// Korean labels. Same wording as office.py label_of / watch so the terminal view and this page read alike.
import type { OfficeEvent } from '../types'
import { nodeName } from './catalog'

export const SKILL_KO: Record<string, string> = {
  'evidence-retrieval': '근거 조회', 'web-evidence-collection': '웹 수집', 'needs-structuring': '불편 구조화',
  'feature-comparison': '기능 대조', 'concept-writing': '콘셉트 작성', 'review-and-revise': '검토·수정',
}

// Short Korean reading of each product-tools operation name (the raw name is always shown next to it).
export const OP_KO: Record<string, string> = {
  doctor: '설치 점검', list_models: '모델 목록 보기', open_request: '요청 열기', open_request_bundle: '요청 시작',
  resolve_request: '요청 해석', resolve_request_bundle: '요청 해석', current_request: '현재 요청 확인',
  record_request_research: '조사 기록', open_product_workflow: '업무 시계 시작', record_workflow_event: '작업 일지 쓰기',
  workflow_status: '업무 시계 확인', evidence_inventory: '근거 목록 보기', read_evidence_batch: '근거 원문 읽기',
  record_evidence_review: '근거 검토 기록', evidence_coverage: '근거 범위 확인', prepare_planning_input: '기획 입력 준비',
  retrieve_reviews: '후기 조회', retrieve_product_facts: '제품 사양 조회', select_evidence: '근거 고르기',
  match_product_scope: '제품 범위 맞추기', set_request_scope_policy: '범위 정책 정하기',
  configure_web_research: '웹 조사 설정', fetch_web_page: '웹 페이지 받기', capture_web_page: '웹 페이지 캡처',
  import_web_evidence: '웹 근거 들여오기', import_web_evidence_bulk: '웹 근거 한꺼번에 들여오기',
  validate_source_refs: '출처 연결 확인', validate_constraints: '조건 확인',
  start_turn: 'turn 시작', prepare_review_packet: '검토 묶음 준비', verify_review_packet: '검토 묶음 확인',
  validate_result_contract: '결과 계약 검사', review_product_result: '후보 검토', save_result: '후보 저장',
  save_reviewed_result: '검토한 후보 저장', save_and_export: '저장·내보내기', prepare_web_result: '웹 전달 준비',
  deliver_result: '결과 전달', export_session: '세션 기록 내보내기', get_turn: 'turn 확인', record_usage: '사용량 기록',
  cancel_turn: 'turn 취소', begin_invocation: '실행 기록 시작', finish_invocation: '실행 기록 끝',
  unknown_operation: '알아보지 못한 작업',
}

export const PROGRAM_KO: Record<string, string> = {
  product_doctor: '설치 점검', ls: '파일 목록 보기', dir: '파일 목록 보기', 'get-childitem': '파일 목록 보기',
  cat: '파일 읽기', type: '파일 읽기', 'get-content': '파일 읽기', head: '파일 앞부분 보기', tail: '파일 끝부분 보기',
  find: '파일 찾기', grep: '내용 찾기', rg: '내용 찾기', 'select-string': '내용 찾기', wc: '줄 수 세기',
  'measure-object': '개수 세기', pwd: '위치 확인', cd: '폴더 이동', 'set-location': '폴더 이동', echo: '글자 출력',
  'write-output': '글자 출력', mkdir: '폴더 만들기', 'new-item': '파일·폴더 만들기', cp: '파일 복사', 'copy-item': '파일 복사',
  mv: '파일 옮기기', 'move-item': '파일 옮기기', rm: '파일 지우기', 'remove-item': '파일 지우기', python: '파이썬 실행',
  python3: '파이썬 실행', py: '파이썬 실행', uv: 'uv 실행', git: 'git', sed: '글자 바꾸기', awk: '글자 처리',
  jq: 'JSON 보기', curl: '웹 받아오기', wget: '웹 받아오기', 'invoke-webrequest': '웹 받아오기', sort: '정렬',
  uniq: '중복 정리', node: 'node 실행', npm: 'npm 실행', npx: 'npm 실행', 'test-path': '경로 확인',
  'get-item': '파일 정보 보기', 'out-file': '파일 쓰기', 'set-content': '파일 쓰기',
}

export const AREA_KO: Record<string, string> = {
  exports: '결과 내보내기', web_evidence: '웹 근거 보관', catalogs: '근거 목록', deliverables: '보고서', runtime: '작업 기록',
  skills: 'Skill 폴더', agents: '에이전트 설명', docs: '문서', data: '자료', tools: '도구 코드', web: '화면 파일',
  harness: '하네스 폴더', outside: '하네스 밖',
}

export const FILE_TOOL_KO: Record<string, string> = {
  Read: '파일 읽기', Write: '파일 쓰기', Edit: '파일 고치기', NotebookEdit: '노트 고치기', Grep: '내용 찾기', Glob: '파일 찾기',
}

export const BASIS_KO: Record<string, string> = {
  observed: '훅에서 직접 관측',
  command_based_mapping: '명령 경로로 알아냄 (실행 성공·의미 검토의 증거 아님)',
  instruction_loaded: 'Skill 설명서를 읽은 것 (그 Skill로 일했다는 증거 아님)',
  db_recorded: '하네스 DB에 적힌 시각·값 (읽기 전용 확인)',
  demo: '데모용 가상 기록',
}

export const STATUS_KO: Record<string, string> = {
  held: '보류', needs_input: '정보 필요', completed: '완료', accepted: '승인', rejected: '거절', failed: '실패',
  draft: '초안', in_progress: '진행 중', cancelled: '취소', reviewed: '검토됨', valid: '유효', invalid: '무효',
}

export const WORKFLOW_KO: Record<string, string> = {
  research_plan: '조사 계획', source_scan: '자료 훑기', research_stop: '조사 멈춤', analysis_scope: '분석 범위',
  checkpoint: '중간 점검', finish: '업무 끝',
}

export function opKo(op: string | null | undefined): string {
  return op ? OP_KO[op] ?? op : ''
}

export function isBrowserTool(tool: string | null | undefined): boolean {
  return !!tool && /claude-in-chrome|Claude_Browser|playwright|browser/i.test(tool)
}

export function shortTool(tool: string): string {
  return tool.startsWith('mcp__') ? tool.split('__').pop() || tool : tool
}

export function labelOf(e: OfficeEvent): string {
  const { kind, node, phase } = e
  const detail = e.detail ?? {}
  const who = nodeName(node)
  if (kind === 'skill_op') {
    const base = `${SKILL_KO[node ?? ''] ?? node} · ${opKo(e.op)}`
    if (phase === 'end' && typeof detail.accepted === 'boolean') {
      const extra = [detail.reason, detail.turn_status].filter((x) => typeof x === 'string' && x)
      return `${base} ${detail.accepted ? '승인됨' : '거절됨'}${extra.length ? ` (${extra.join(', ')})` : ''}`
    }
    return base + (phase === 'fail' ? ' 실패' : phase === 'end' ? ' 끝' : '')
  }
  if (kind === 'delegate') {
    if (phase === 'start') return `${who}에 맡김`
    if (phase === 'end') return detail.background ? `${who} 백그라운드로 시작` : `${who} 돌려받음`
    return `${who} 맡기기 실패`
  }
  if (kind === 'subagent') {
    if (node === 'other_subagent') {
      const t = typeof detail.agent_type === 'string' ? ` (${detail.agent_type})` : ''
      return `Claude Code 보조 작업 ${phase === 'start' ? '시작' : '끝'}${t}`
    }
    return `${who} ${phase === 'start' ? '시작' : '끝'}`
  }
  if (kind === 'handback') return `${who} 결과 돌려줌${phase === 'end' ? ' 완료' : ''}`
  if (kind === 'handback_delivered') return '메인이 연구 결과 받음'
  if (kind === 'notification') return '작업 알림 받음'
  if (kind === 'skill_load') return `${who} 지침 읽음`
  if (kind === 'web') return typeof detail.host === 'string' ? `웹 열람 · ${detail.host}` : '웹 검색'
  if (kind === 'shell') {
    const names = ((detail.programs as string[] | undefined) ?? []).filter((p) => p !== 'other').map((p) => PROGRAM_KO[p] ?? p)
    return '명령 실행' + (names.length ? ' · ' + [...new Set(names)].join(', ') : '')
  }
  if (kind === 'file') {
    let area = AREA_KO[String(detail.area ?? '')] ?? ''
    if (typeof detail.skill === 'string') area = `${SKILL_KO[detail.skill] ?? detail.skill} 참고 문서`
    return (FILE_TOOL_KO[e.tool ?? ''] ?? e.tool ?? '') + (area ? ` · ${area}` : '')
  }
  if (kind === 'tool') {
    const tool = e.tool ?? ''
    if (isBrowserTool(tool)) return `브라우저 · ${shortTool(tool)}`
    if (FILE_TOOL_KO[tool]) return FILE_TOOL_KO[tool]
    return `${shortTool(tool)} 사용`
  }
  return ({ request: '새 질문', turn_end: '답변 끝', session: `세션 ${phase === 'start' ? '시작' : '끝'}` } as Record<string, string>)[kind] ?? kind
}

export function secs(ms: number | null | undefined): string {
  if (ms == null || !Number.isFinite(ms)) return '미측정'
  const s = ms / 1000
  if (s < 10) return `${s.toFixed(1)}초`
  if (s < 60) return `${Math.round(s)}초`
  const m = Math.floor(s / 60)
  return `${m}분 ${Math.round(s - m * 60)}초`
}

export function clock(ms: number): string {
  const d = new Date(ms)
  return [d.getHours(), d.getMinutes(), d.getSeconds()].map((n) => String(n).padStart(2, '0')).join(':')
}

export function dayClock(ms: number): string {
  const d = new Date(ms)
  return `${d.getMonth() + 1}/${d.getDate()} ${clock(ms)}`
}

export function mmss(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}
