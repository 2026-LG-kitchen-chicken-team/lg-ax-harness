// Right panel: what the clicked room or person is, what it is doing at this moment, and what it did so far.
import type { ReactNode } from 'react'
import { NODE, ROLE_IDS, SKILL_IDS } from '../lib/catalog'
import { RESULT_VIEW_URL } from '../lib/data'
import { AREA_KO, BASIS_KO, PROGRAM_KO, STATUS_KO, clock, dayClock, opKo, secs } from '../lib/labels'
import type { ResultView } from '../types'
import type { SessionModel, Span } from '../lib/model'
import { feedAt, pointLabel, type Snapshot } from '../lib/state'
import { statusText } from '../scene/Room'

const KIND_KO = { main: '메인 Agent', role: '선택 연구 역할', skill: '업무 Skill', place: '사무실 시설' }
const STATUS_TAG: Record<string, string> = { active: '작업 중', done: '방금 끝남', fail: '실패·거절', idle: '대기', off: '호출 안 됨' }

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-1.5">
      <h3 className="text-[11px] font-semibold tracking-wide text-[var(--dim)]">{title}</h3>
      {children}
    </section>
  )
}

function Row({ k, v, tone }: { k: string; v: ReactNode; tone?: 'ok' | 'bad' | 'warn' | 'dim' }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-[12px]">
      <span className="text-[var(--dim)]">{k}</span>
      <span className={`text-right ${tone ? `tone-${tone}` : ''}`}>{v}</span>
    </div>
  )
}

function Basis({ basis }: { basis: string }) {
  const short = basis === 'command_based_mapping' ? '명령 추정' : basis === 'instruction_loaded' ? '지침 읽음' : basis === 'db_recorded' ? 'DB' : basis === 'demo' ? '데모' : '관측'
  return <span className={`basis basis-${basis}`} title={BASIS_KO[basis] ?? basis}>{short}</span>
}

function count<T>(items: T[], key: (x: T) => string | null | undefined): [string, number][] {
  const m = new Map<string, number>()
  for (const x of items) {
    const k = key(x)
    if (k) m.set(k, (m.get(k) ?? 0) + 1)
  }
  return [...m.entries()].sort((a, b) => b[1] - a[1])
}

function spansFor(model: SessionModel, id: string, t: number): Span[] {
  return model.spans.filter((s) => s.start <= t && (s.target === id || (ROLE_IDS.includes(id) && s.actor === id) || (id === 'main' && s.actor === 'main')))
}

export function Inspector({ id, model, snap, resultView, onClose }: { id: string; model: SessionModel; snap: Snapshot; resultView: ResultView | null; onClose: () => void }) {
  const node = NODE[id]
  if (!node) return null
  const st = snap.nodes[id]
  const t = snap.t
  const spans = spansFor(model, id, t)
  const feed = feedAt(model, t, 400).filter((f) => f.node === id || (id === 'main' && ['main', 'reception'].includes(f.node))).slice(0, 14)
  const db = model.dbMatched ? model.db : null
  return (
    <aside className="panel pointer-events-auto flex max-h-full w-full flex-col overflow-hidden">
      <header className="flex items-start gap-3 border-b border-[var(--line)] px-4 py-3" style={{ ['--c' as string]: node.color }}>
        <span className="mt-1 h-3 w-3 shrink-0 rounded-full" style={{ background: node.color, boxShadow: `0 0 12px ${node.color}` }} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h2 className="truncate text-[16px] font-bold">{node.ko}</h2>
            <span className={`tag tag-${st?.status ?? 'idle'}`}>{STATUS_TAG[st?.status ?? 'idle']}</span>
          </div>
          <div className="truncate font-mono text-[11px] text-[var(--dim)]">{KIND_KO[node.kind]} · {node.code}</div>
        </div>
        <button className="btn btn-sm" onClick={onClose} aria-label="닫기">닫기</button>
      </header>
      <div className="flex flex-col gap-4 overflow-y-auto px-4 py-3">
        <div className="now-box" style={{ ['--c' as string]: node.color }}>
          <div className="text-[11px] text-[var(--dim)]">지금 ({clock(t)})</div>
          <div className="text-[14px] font-semibold leading-snug">{statusText(st?.status, st?.activity ?? null, st?.since ?? null, t)}</div>
          {st?.active.length ? (
            <ul className="mt-1 flex flex-col gap-0.5">
              {st.active.map((s) => (
                <li key={s.key} className="flex items-center gap-2 text-[12px]">
                  <span className="live-dot" style={{ background: node.color }} />
                  <span className="flex-1 truncate">{s.label}</span>
                  <span className="font-mono text-[var(--dim)]">{secs(t - s.start)}</span>
                  <Basis basis={s.basis} />
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <Section title="하는 일">
          <p className="text-[12.5px] leading-relaxed">{node.description}</p>
          {node.note && <p className="text-[11.5px] leading-relaxed text-[var(--accent2)]">{node.note}</p>}
          <p className="font-mono text-[10.5px] text-[var(--dim)]">출처: {node.source}</p>
        </Section>

        <Section title="이 기록에서 (재생 위치까지)">
          <Row k="호출" v={`${st?.calls ?? 0}건`} />
          <Row k="실패·거절" v={`${st?.fails ?? 0}건`} tone={st?.fails ? 'bad' : undefined} />
          {id !== 'main' && <Row k="걸린 시간 합" v={secs(st?.busyMs ?? 0)} />}
        </Section>

        {SKILL_IDS.includes(id) && <SkillOps id={id} spans={spans} t={t} />}
        {ROLE_IDS.includes(id) && <RolePresence id={id} model={model} t={t} spans={spans} />}
        {id === 'main' && <MainInfo model={model} t={t} />}
        {(id === 'review-and-revise' || id === 'shipping') && <Saves model={model} snap={snap} />}
        {id === 'shipping' && <ResultCard model={model} view={resultView} />}
        {id === 'vault' && <Vault model={model} t={t} />}
        {id === 'reception' && (
          <Section title="질문">
            <Row k="받은 질문" v={`${model.points.filter((p) => p.kind === 'request' && p.t <= t).length}건`} />
            {db?.request?.question ? (
              <p className="quote">{db.request.question}<span className="mt-1 block text-[10.5px] text-[var(--dim)]">하네스 DB의 최신 요청(최대 300자) · 상태 {STATUS_KO[db.request.status ?? ''] ?? db.request.status ?? '미확인'}</span></p>
            ) : (
              <p className="text-[12px] text-[var(--dim)]">훅은 질문 원문을 남기지 않습니다. 이 세션 시간대의 DB 요청이 없어 질문 글은 보여 줄 수 없습니다.</p>
            )}
          </Section>
        )}
        {id === 'web' && <WebInfo model={model} t={t} />}
        {id === 'console' && (
          <Section title="실행한 프로그램 (이름만)">
            {count(spans.flatMap((s) => ((s.detail.programs as string[] | undefined) ?? []).map((p) => ({ p }))), (x) => x.p).map(([p, n]) => (
              <Row key={p} k={PROGRAM_KO[p] ?? (p === 'other' ? '목록 밖 프로그램' : p)} v={`${n}회`} />
            ))}
            {!spans.length && <p className="text-[12px] text-[var(--dim)]">아직 없음</p>}
          </Section>
        )}
        {id === 'shelf' && (
          <Section title="다룬 폴더 구역 (파일 이름은 남기지 않음)">
            {count(spans, (s) => (typeof s.detail.skill === 'string' ? `skill:${s.detail.skill}` : (s.detail.area as string) ?? s.tool)).map(([a, n]) => (
              <Row key={a} k={a.startsWith('skill:') ? `${a.slice(6)} 참고 문서` : AREA_KO[a] ?? a} v={`${n}회`} />
            ))}
            {!spans.length && <p className="text-[12px] text-[var(--dim)]">아직 없음</p>}
          </Section>
        )}

        <Section title="최근 기록">
          {feed.length ? (
            <ul className="flex flex-col gap-1">
              {feed.map((f) => (
                <li key={f.key} className={`feed-row tone-${f.tone}`}>
                  <span className="font-mono text-[10.5px] text-[var(--dim)]">{clock(f.t)}</span>
                  <span className="flex-1">{f.label}</span>
                  <Basis basis={f.basis} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[12px] text-[var(--dim)]">재생 위치까지 이 곳의 기록이 없습니다.</p>
          )}
        </Section>
      </div>
    </aside>
  )
}

function SkillOps({ id, spans, t }: { id: string; spans: Span[]; t: number }) {
  const node = NODE[id]
  const ops = count(spans.filter((s) => s.kind === 'skill_op'), (s) => s.op)
  const loads = spans.filter((s) => s.kind === 'skill_load').length
  const unused = (node.ops ?? []).filter((o) => !ops.some(([k]) => k === o))
  return (
    <Section title="작업 (명령 경로로 알아낸 것)">
      {loads > 0 && <Row k="SKILL.md 읽음" v={`${loads}회`} />}
      {ops.map(([op, n]) => {
        const fails = spans.filter((s) => s.op === op && s.end != null && s.end <= t && (s.status === 'fail' || s.detail.accepted === false)).length
        return <Row key={op} k={`${opKo(op)} · ${op}`} v={`${n}회${fails ? ` · 실패/거절 ${fails}` : ''}`} tone={fails ? 'bad' : undefined} />
      })}
      {!ops.length && <p className="text-[12px] text-[var(--dim)]">재생 위치까지 이 Skill의 명령 실행이 없습니다.</p>}
      {unused.length > 0 && (
        <details className="text-[11.5px] text-[var(--dim)]">
          <summary className="cursor-pointer">쓸 수 있지만 아직 안 쓴 작업 {unused.length}개</summary>
          <p className="mt-1 font-mono leading-relaxed">{unused.join(' · ')}</p>
        </details>
      )}
    </Section>
  )
}

function RolePresence({ id, model, t, spans }: { id: string; model: SessionModel; t: number; spans: Span[] }) {
  const stays = model.presences.filter((p) => p.actor === id && p.start <= t)
  const delegations = model.spans.filter((s) => s.kind === 'delegate' && s.node === id && s.start <= t)
  return (
    <Section title="위임과 근무">
      {!stays.length && !delegations.length && <p className="text-[12px] text-[var(--dim)]">이 기록에서 메인이 이 역할을 부르지 않았습니다. 역할 3개는 필요할 때만 고르는 구성입니다.</p>}
      {delegations.map((d) => (
        <Row key={d.key} k={`${clock(d.start)} 메인이 맡김`} v={d.detail.background ? '백그라운드' : '기다림'} />
      ))}
      {stays.map((p) => (
        <Row key={p.agentId} k={`${clock(p.start)} 시작 · ID ${p.agentId.slice(0, 8)}`} v={p.end != null && p.end <= t ? `${secs(p.end - p.start)} 일함` : `${secs(t - p.start)}째`} />
      ))}
      {count(spans.filter((s) => s.actor === id), (s) => s.tool).map(([tool, n]) => (
        <Row key={tool} k={`도구 ${tool}`} v={`${n}회`} />
      ))}
    </Section>
  )
}

function MainInfo({ model, t }: { model: SessionModel; t: number }) {
  const turns = model.turns.filter((x) => x.start <= t)
  const mine = model.spans.filter((s) => s.actor === 'main' && s.start <= t)
  const busy = mine.reduce((a, s) => a + Math.max(0, Math.min(t, s.end ?? t) - s.start), 0)
  const talk = turns.reduce((a, x) => a + Math.max(0, Math.min(t, x.end ?? t) - x.start), 0)
  return (
    <Section title="메인">
      <Row k="질문·메시지 받음" v={`${turns.length}건`} />
      <Row k="도구 쓰는 시간" v={secs(busy)} />
      <Row k="답변 중 도구 없이 보낸 시간" v={talk ? secs(Math.max(0, talk - busy)) : '미측정'} />
      <p className="text-[11px] leading-relaxed text-[var(--dim)]">"생각 중"은 답변 중인데 도구를 쓰지 않는 시간입니다. 모델 내부 상태를 본 것이 아닙니다.</p>
    </Section>
  )
}

function Saves({ model, snap }: { model: SessionModel; snap: Snapshot }) {
  const db = model.dbMatched ? model.db : null
  const cands = model.candidates.filter((c) => c.t <= snap.t)
  return (
    <Section title="후보 저장 (최초 · 수정1 · 수정2)">
      {snap.saves.length ? snap.saves.map((s, i) => (
        <Row key={s.span.key} k={`${clock(s.t)} ${['최초', '수정1', '수정2'][i] ?? `${i + 1}번째`} · ${s.span.op}`}
          v={s.accepted == null ? '응답 미확인' : `${s.accepted ? '승인' : '거절'}${s.reason ? ` · ${s.reason}` : ''}${s.turnStatus ? ` · ${STATUS_KO[s.turnStatus] ?? s.turnStatus}` : ''}`}
          tone={s.accepted === true ? 'ok' : s.accepted === false ? 'bad' : 'warn'} />
      )) : <p className="text-[12px] text-[var(--dim)]">재생 위치까지 저장 시도가 없습니다.</p>}
      {cands.map((c) => (
        <div key={c.result_version ?? c.t} className="cand">
          <div className="flex justify-between text-[12px]"><span>후보 v{c.result_version ?? '?'} (DB)</span><span className="font-mono text-[var(--dim)]">{clock(c.t)}</span></div>
          <div className="grid grid-cols-4 gap-1 text-center text-[11px]">
            {(['pains', 'existing_features', 'remaining_pains', 'concepts'] as const).map((k) => (
              <div key={k} className="cand-cell"><b>{c.counts?.[k] ?? '미측정'}</b><span>{{ pains: '불편', existing_features: '기존 기능', remaining_pains: '남은 불편', concepts: '콘셉트' }[k]}</span></div>
            ))}
          </div>
          <div className="text-[10.5px] text-[var(--dim)]">계약 {c.contract_valid == null ? '미확인' : c.contract_valid ? '통과' : '실패'} · 구조 {c.structural_valid == null ? '미확인' : c.structural_valid ? '통과' : '실패'} · 승인 준비 {c.acceptance_ready == null ? '미확인' : c.acceptance_ready ? '됨' : '안 됨'}</div>
        </div>
      ))}
      {db?.turn && (
        <Row k="turn 최신 상태 (DB)" v={`${STATUS_KO[db.turn.status ?? ''] ?? db.turn.status} · 수정 ${db.turn.revision_count ?? '미측정'}/2`} tone={db.turn.status === 'completed' ? 'ok' : 'warn'} />
      )}
      <p className="text-[11px] leading-relaxed text-[var(--dim)]">승인은 저장 계약 검사 통과이며 원문 의미·효과를 자동으로 증명하지 않습니다.</p>
    </Section>
  )
}

function ResultCard({ model, view }: { model: SessionModel; view: ResultView | null }) {
  const latest = model.db?.latest_export
  const generated = view?.generated_at ? Date.parse(view.generated_at) : NaN
  return (
    <Section title="결과 화면 (시각자료 뷰어)">
      {view ? (
        <div className="result-card">
          <div className="text-[12px]">{view.context?.file?.name ?? 'export 이름 미확인'}</div>
          <div className="text-[11px] text-[var(--dim)]">{Number.isFinite(generated) ? `화면을 만든 시각 ${dayClock(generated)}` : '만든 시각 미확인'}</div>
          {view.context?.status?.length ? (
            <div className="flex flex-wrap gap-1">{view.context.status.map((s, i) => <span key={i} className="chip">{s.text}</span>)}</div>
          ) : null}
          <a className="btn btn-result mt-1 self-start" href={RESULT_VIEW_URL} target="_blank" rel="noopener">결과 화면 열기</a>
          <p className="text-[10.5px] leading-relaxed text-[var(--dim)]">뷰어는 가장 최근 export를 그립니다. 이 재생 위치의 결과와 다를 수 있습니다.</p>
        </div>
      ) : (
        <p className="text-[12px] leading-relaxed text-[var(--dim)]">이 하네스에 결과 화면이 아직 없습니다. 시각자료 뷰어를 설치(<code>viewer.py install</code>)하면 결과가 저장될 때 여기서 열 수 있습니다.</p>
      )}
      {latest?.name && (
        <Row k="가장 최근 export (DB 확인 때)" v={`${latest.name.slice(0, 22)}${latest.name.length > 22 ? '…' : ''}${latest.modified_at ? ` · ${clock(Date.parse(latest.modified_at))}` : ''}`} />
      )}
    </Section>
  )
}

function Vault({ model, t }: { model: SessionModel; t: number }) {
  const db = model.db
  if (!db?.available) return <Section title="DB"><p className="text-[12px] text-[var(--dim)]">DB를 읽지 못했습니다{db?.reason ? ` (${db.reason})` : ''}.</p></Section>
  if (!model.dbMatched) return <Section title="DB"><p className="text-[12px] text-[var(--dim)]">DB의 최신 기록은 이 세션 시간대의 것이 아닙니다. 다른 세션을 고르면 보일 수 있습니다.</p></Section>
  const wf = model.points.filter((p) => p.kind === 'wf' && p.t <= t)
  return (
    <Section title={`DB (읽은 시각 ${db.read_at ? clock(Date.parse(db.read_at)) : '미확인'})`}>
      {model.workflow && <Row k="업무 시계 예산" v={model.workflow.budgetMs != null ? secs(model.workflow.budgetMs) : '미측정'} />}
      <Row k="전달한 근거 (최신)" v={db.evidence_delivered == null ? '미측정' : `${db.evidence_delivered}건`} />
      <Row k="근거 검토 기록 (최신)" v={db.evidence_reviews == null ? '미측정' : `${db.evidence_reviews}건`} />
      <Row k="저장된 후보 (최신)" v={db.results == null ? '미측정' : `${db.results}개`} />
      {db.cancelled && <Row k="취소" v="취소됨" tone="bad" />}
      <h4 className="mt-1 text-[11px] text-[var(--dim)]">작업 일지 (재생 위치까지)</h4>
      {wf.length ? wf.map((p) => (
        <div key={p.key} className="feed-row tone-db"><span className="font-mono text-[10.5px] text-[var(--dim)]">{clock(p.t)}</span><span className="flex-1">{pointLabel(p)}</span></div>
      )) : <p className="text-[12px] text-[var(--dim)]">아직 없음</p>}
      <p className="text-[11px] leading-relaxed text-[var(--dim)]">'최신'은 DB를 마지막으로 읽은 때의 값입니다. 작업 일지·후보는 DB에 적힌 시각에 맞춰 재생합니다.</p>
    </Section>
  )
}

function WebInfo({ model, t }: { model: SessionModel; t: number }) {
  const spans = model.spans.filter((s) => s.target === 'web' && s.start <= t)
  const by = count(spans, (s) => s.host)
  const scans = model.points.filter((p) => p.wf?.kind === 'source_scan' && p.t <= t)
  return (
    <Section title="사이트 (호스트 이름만)">
      {by.map(([h, n]) => <Row key={h} k={h === 'search' ? '웹 검색' : h === 'browser' ? '브라우저 도구' : h} v={`${n}회`} />)}
      {!by.length && <p className="text-[12px] text-[var(--dim)]">재생 위치까지 웹 열람이 없습니다.</p>}
      {scans.length > 0 && <h4 className="mt-1 text-[11px] text-[var(--dim)]">작업 일지의 자료 훑기 (DB)</h4>}
      {scans.map((p) => <div key={p.key} className="feed-row tone-db"><span className="font-mono text-[10.5px] text-[var(--dim)]">{clock(p.t)}</span><span className="flex-1">{pointLabel(p)}</span></div>)}
    </Section>
  )
}
