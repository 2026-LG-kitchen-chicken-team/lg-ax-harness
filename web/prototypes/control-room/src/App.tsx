import {
  Component,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  Check,
  ChevronRight,
  CircleDot,
  Database,
  FileJson,
  Focus,
  GitBranch,
  Layers3,
  Pause,
  Play,
  RotateCcw,
  ShieldCheck,
  Upload,
  X,
  Zap,
} from "lucide-react";
import ControlScene from "./Scene";
import { nodes } from "./catalog";
import {
  createDemoTrace,
  parseHarnessTrace,
  type HarnessTrace,
  type TraceEvent,
} from "./harness";

const statusNames: Record<string, string> = {
  idle: "대기",
  active: "작업 중",
  done: "완료",
  held: "보류",
  error: "오류",
  unknown: "실행 미기록",
};
const skillNames: Record<string, string> = {
  "evidence-retrieval": "근거 조회",
  "web-evidence-collection": "웹 수집",
  "needs-structuring": "불편 구조화",
  "feature-comparison": "기능 대조",
  "concept-writing": "기획 작성",
  "review-and-revise": "검토·수정",
};
const labelOf = (id: string) => nodes.find((n) => n.id === id)?.label ?? id;
const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0")}`;

class SceneBoundary extends Component<
  { children: ReactNode },
  { error: boolean }
> {
  state = { error: false };
  static getDerivedStateFromError() {
    return { error: true };
  }
  render() {
    return this.state.error ? (
      <div className="scene-fallback">
        <Layers3 size={36} />
        <h2>3D 화면을 열 수 없습니다</h2>
        <p>
          브라우저의 하드웨어 가속을 확인해 주세요. 역할과 실행 기록은
          오른쪽에서 볼 수 있습니다.
        </p>
      </div>
    ) : (
      this.props.children
    );
  }
}

export default function App() {
  const [trace, setTrace] = useState<HarnessTrace>(() => createDemoTrace());
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const [speed, setSpeed] = useState(1);
  const [selected, setSelected] = useState("main");
  const [panel, setPanel] = useState<"activity" | "inventory">("activity");
  const [notice, setNotice] = useState("");
  const [showNotes, setShowNotes] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [pastedJson, setPastedJson] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const notesDialog = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!showNotes && !importOpen) return;
    const previous =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    notesDialog.current?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setShowNotes(false);
        setImportOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = [
        ...(notesDialog.current?.querySelectorAll<HTMLElement>(
          "button:not([disabled]), a[href], input, textarea, select, [tabindex='0']",
        ) ?? []),
      ];
      const first = focusable[0],
        last = focusable.at(-1);
      if (
        event.shiftKey &&
        (document.activeElement === first ||
          document.activeElement === notesDialog.current)
      ) {
        event.preventDefault();
        last?.focus();
      } else if (
        !event.shiftKey &&
        (document.activeElement === last ||
          document.activeElement === notesDialog.current)
      ) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", keyboard);
    return () => {
      document.removeEventListener("keydown", keyboard);
      if (previous?.isConnected) previous.focus();
    };
  }, [showNotes, importOpen]);

  useEffect(() => {
    if (!playing) return;
    let frame = 0;
    let last = performance.now();
    let pending = 0;
    const tick = (now: number) => {
      pending += Math.min((now - last) / 1000, 0.2) * speed;
      last = now;
      if (pending >= 0.05) {
        const step = pending;
        pending = 0;
        setTime((current) => {
          const next = Math.min(current + step, trace.duration);
          return next;
        });
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [playing, speed, trace.duration]);

  useEffect(() => {
    if (time >= trace.duration && playing) setPlaying(false);
  }, [time, trace.duration, playing]);

  const observed = useMemo(
    () => trace.events.filter((e) => e.at <= time),
    [trace.events, time],
  );
  const latest = observed.filter((e) => e.kind !== "metadata").at(-1);
  const states = useMemo(() => {
    const result: Record<string, string> = Object.fromEntries(
      nodes.map((n) => [n.id, trace.mode === "demo" ? "idle" : "unknown"]),
    );
    for (const event of observed) {
      if (event.kind !== "metadata" && result[event.target] !== undefined)
        result[event.target] = event.status;
    }
    return result;
  }, [observed, trace.mode]);
  const metadataEvents = trace.events.filter((e) => e.kind === "metadata");
  const node = nodes.find((n) => n.id === selected) ?? nodes[0];
  const currentNodeEvents = observed.filter(
    (e) => e.source === selected || e.target === selected,
  );
  const nodeEvent = currentNodeEvents
    .filter((e) => e.kind !== "metadata")
    .at(-1);
  const recent = [...observed]
    .reverse()
    .filter((e) => e.kind !== "metadata")
    .slice(0, 7);
  const running = nodes.filter(
    (n) => n.kind === "agent" && states[n.id] === "active",
  ).length;
  const visibleSkills = nodes.filter((n) => n.kind === "skill");
  const phase =
    trace.mode === "recorded"
      ? states.main === "held"
        ? "RECORDED · HELD"
        : latest
          ? "RECORDED EVENT"
          : "RECORDED METADATA"
      : latest?.kind === "complete"
        ? "DELIVERED"
        : states.main === "held"
          ? "REVIEW GATE"
          : latest?.kind === "review" || latest?.kind === "revision"
            ? "REVIEW"
            : "ORCHESTRATING";

  function seek(next: number) {
    setTime(Math.max(0, Math.min(next, trace.duration)));
  }
  function resetDemo() {
    setTrace(createDemoTrace());
    setTime(0);
    setSelected("main");
    setPlaying(true);
    setNotice("");
  }
  function loadTraceJson(value: string) {
    if (new Blob([value]).size > 25 * 1024 * 1024)
      throw new Error("25MB 이하의 JSON을 사용해 주세요.");
    const parsed = parseHarnessTrace(JSON.parse(value));
    setTrace(parsed);
    setTime(0);
    setPlaying(false);
    setSelected("main");
    setImportOpen(false);
    setShowNotes(true);
    setNotice("");
  }
  async function importFile(file?: File) {
    if (!file) return;
    try {
      if (file.size > 25 * 1024 * 1024)
        throw new Error("25MB 이하의 세션 export JSON을 선택해 주세요.");
      loadTraceJson(await file.text());
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "파일을 읽을 수 없습니다.",
      );
    }
    if (fileInput.current) fileInput.current.value = "";
  }
  function exportTrace() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(trace, null, 2)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "control-room-trace.json";
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="#"
          aria-label="LG AX 관제실 처음으로"
          onClick={(e) => {
            e.preventDefault();
            setSelected("main");
          }}
        >
          <span className="brand-mark">
            <CircleDot size={22} />
          </span>
          <span>
            LG AX <b>HARNESS</b>
          </span>
        </a>
        <div className="topbar-divider" />
        <div className="workspace-name">
          Agent control room <span>PROTOTYPE</span>
        </div>
        <div className="topbar-actions">
          <span className="version">
            <i /> product-v0.10.0
          </span>
          <button
            className="icon-button"
            title="실행 기록 내려받기"
            aria-label="실행 기록 내려받기"
            onClick={exportTrace}
          >
            <ArrowDownToLine size={17} />
          </button>
          <button
            className="import-button"
            onClick={() => {
              setShowNotes(false);
              setImportOpen(true);
              setPlaying(false);
            }}
          >
            <Upload size={14} />
            <span>세션 불러오기</span>
          </button>
        </div>
        <input
          type="file"
          ref={fileInput}
          accept="application/json,.json"
          className="visually-hidden"
          aria-label="하네스 세션 export JSON"
          onChange={(e) => void importFile(e.target.files?.[0])}
        />
      </header>

      <div className="workspace">
        <nav className="rail" aria-label="관제실 보기">
          <button
            className={
              panel === "activity" ? "rail-button active" : "rail-button"
            }
            aria-label="실행 흐름"
            title="실행 흐름"
            aria-pressed={panel === "activity"}
            onClick={() => setPanel("activity")}
          >
            <Activity size={20} />
          </button>
          <button
            className={
              panel === "inventory" ? "rail-button active" : "rail-button"
            }
            aria-label="역할과 스킬 목록"
            title="역할과 스킬 목록"
            aria-pressed={panel === "inventory"}
            onClick={() => setPanel("inventory")}
          >
            <GitBranch size={20} />
          </button>
          <div className="rail-line" />
          <button
            className="rail-button"
            title="기록 범위 안내"
            aria-label="기록 범위 안내"
            onClick={() => setShowNotes((v) => !v)}
          >
            <FileJson size={19} />
          </button>
          <span className="rail-caption">AX / 26</span>
        </nav>

        <main className="main-space">
          <div className="mission-bar">
            <div className="mission-icon">
              <Focus size={19} />
            </div>
            <div className="mission-copy">
              <span className="eyebrow">CURRENT MISSION</span>
              <h1>{trace.title}</h1>
            </div>
            <button
              className={`mode-badge ${trace.mode}`}
              onClick={() => setShowNotes((v) => !v)}
            >
              <span />
              {trace.mode === "demo" ? "DEMO REPLAY" : "RECORDED SESSION"}
              <ChevronRight size={12} />
            </button>
          </div>

          <div className="stage-layout">
            <section className="stage" aria-label="3D 에이전트 관제 장면">
              <div className="stage-heading">
                <span className="eyebrow">AGENT TOPOLOGY</span>
                <h2>
                  상품기획 관제실<span>01</span>
                </h2>
                <p>하나의 메인. 세 개의 연구 역할. 여섯 개의 스킬.</p>
              </div>
              <div className="stage-status">
                <span className={`status-light ${states.main}`} />
                {phase}
              </div>
              <SceneBoundary>
                <ControlScene
                  time={time}
                  events={trace.events}
                  selected={selected}
                  onSelect={setSelected}
                  statuses={states}
                  motion={playing}
                />
              </SceneBoundary>
              <div className="scene-legend">
                <span>
                  <i className="legend-main" />
                  메인
                </span>
                <span>
                  <i className="legend-agent" />
                  선택 연구 역할
                </span>
                <span>
                  <i className="legend-skill" />
                  업무 스킬
                </span>
              </div>
              <div className="stage-footnote">
                <span className="crosshair">+</span> 노드를 선택해 작업을
                확인하세요 <span className="stage-hint">DRAG TO ORBIT</span>
              </div>
            </section>

            <aside className="inspector">
              <div className="inspector-head">
                <span className="eyebrow">
                  {panel === "activity"
                    ? "NODE INSPECTOR"
                    : "HARNESS INVENTORY"}
                </span>
                <span className="tiny-dots">•••</span>
              </div>
              {panel === "activity" ? (
                <>
                  <div
                    className="node-profile"
                    style={
                      { "--node-color": node.color } as React.CSSProperties
                    }
                  >
                    <div className="node-symbol">
                      {node.kind === "core" ? (
                        <CircleDot size={30} />
                      ) : node.kind === "agent" ? (
                        <GitBranch size={27} />
                      ) : (
                        <Zap size={27} />
                      )}
                    </div>
                    <div>
                      <span className="node-kind">
                        {node.kind === "core"
                          ? "MAIN ORCHESTRATOR"
                          : node.kind === "agent"
                            ? "RESEARCH AGENT"
                            : "BUSINESS SKILL"}
                      </span>
                      <h3>{node.label}</h3>
                      <span className="node-subtitle">{node.subtitle}</span>
                    </div>
                  </div>
                  <div className={`node-status ${states[node.id]}`}>
                    <i />
                    {statusNames[states[node.id]] ?? "미기록"}
                    <span>
                      {node.kind === "agent"
                        ? "선택적 실행"
                        : node.kind === "skill"
                          ? "메인이 호출"
                          : "전체 흐름 조율"}
                    </span>
                  </div>
                  <p className="node-description">{node.description}</p>
                  <div className="active-task">
                    <span className="eyebrow">CURRENT ACTIVITY</span>
                    <p>
                      {nodeEvent?.label ??
                        (trace.mode === "recorded"
                          ? "시각이 있는 관측 사건 없음"
                          : "새 실행 기록을 기다리고 있습니다")}
                    </p>
                    <span>
                      {nodeEvent?.detail ??
                        "역할 설치만으로 실제 실행을 표시하지 않습니다."}
                    </span>
                  </div>
                  <div className="signal-strip">
                    <span>
                      <Activity size={13} />{" "}
                      {
                        currentNodeEvents.filter((e) => e.kind !== "metadata")
                          .length
                      }{" "}
                      EVENTS
                    </span>
                    <span>
                      {trace.mode === "demo" ? "연출용 데이터" : "저장된 기록"}
                    </span>
                  </div>
                  <div className="activity-heading">
                    <h4>실행 흐름</h4>
                    <span>{clock(time)}</span>
                  </div>
                  {trace.mode === "recorded" && metadataEvents.length > 0 && (
                    <details className="metadata-panel" open={!latest}>
                      <summary>
                        시각 미기록 · 저장 상태 / 호출 ({metadataEvents.length})
                      </summary>
                      <div>
                        {metadataEvents.map((event) => (
                          <article key={event.id}>
                            <strong>{event.label}</strong>
                            <p>{event.detail}</p>
                          </article>
                        ))}
                      </div>
                    </details>
                  )}
                  <div className="event-list" aria-label="최근 실행 이벤트">
                    {recent.map((event: TraceEvent, index) => (
                      <button
                        key={event.id}
                        className={`event-row ${index === 0 ? "latest" : ""}`}
                        onClick={() => {
                          setSelected(event.target);
                          setPlaying(false);
                          seek(event.at);
                        }}
                      >
                        <span className={`event-pin ${event.status}`}>
                          {event.status === "done" ? (
                            <Check size={10} />
                          ) : (
                            <span />
                          )}
                        </span>
                        <span className="event-content">
                          <span className="event-route">
                            {labelOf(event.source)} <ArrowRight size={10} />{" "}
                            {labelOf(event.target)}
                          </span>
                          <strong>{event.label}</strong>
                        </span>
                        <time>{clock(event.at)}</time>
                      </button>
                    ))}
                    {recent.length === 0 && (
                      <p className="empty-events">
                        {trace.mode === "recorded"
                          ? "시각 미기록 항목은 저장 상태 / 호출 장부에서 확인하세요."
                          : "재생을 시작하면 이벤트가 표시됩니다."}
                      </p>
                    )}
                  </div>
                </>
              ) : (
                <div className="inventory-list">
                  {(["core", "agent", "skill"] as const).map((kind) => (
                    <div className="inventory-group" key={kind}>
                      <h3>
                        {kind === "core"
                          ? "메인 오케스트레이터"
                          : kind === "agent"
                            ? "선택 연구 역할"
                            : "업무 스킬"}
                        <span>
                          {nodes.filter((n) => n.kind === kind).length}
                        </span>
                      </h3>
                      {nodes
                        .filter((n) => n.kind === kind)
                        .map((item) => (
                          <button
                            key={item.id}
                            onClick={() => {
                              setSelected(item.id);
                              setPanel("activity");
                            }}
                          >
                            <span style={{ background: item.color }} />
                            <div>
                              <strong>{item.label}</strong>
                              <small>{item.subtitle}</small>
                            </div>
                            <ChevronRight size={13} />
                          </button>
                        ))}
                    </div>
                  ))}
                </div>
              )}
              <div className="inspector-footer">
                <ShieldCheck size={14} />
                {trace.mode === "demo"
                  ? "데모 재생 · 실제 AI 실행 아님"
                  : "세션 파일을 브라우저 안에서 읽음"}
              </div>
            </aside>
          </div>

          <section className="skill-band" aria-label="업무 스킬 상태">
            <div className="skill-band-title">
              <Layers3 size={16} />
              <span>
                SKILL
                <br />
                PIPELINE
              </span>
            </div>
            {visibleSkills.map((skill, index) => (
              <button
                key={skill.id}
                className={`skill-step ${states[skill.id]} ${selected === skill.id ? "selected" : ""}`}
                aria-pressed={selected === skill.id}
                onClick={() => {
                  setSelected(skill.id);
                  setPanel("activity");
                }}
              >
                <span className="step-number">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <span className="step-name">
                  {skillNames[skill.id] ?? skill.label}
                  <small>{statusNames[states[skill.id]]}</small>
                </span>
                {states[skill.id] === "done" ? (
                  <Check size={13} />
                ) : (
                  <span className="step-dot" />
                )}
              </button>
            ))}
          </section>

          <footer className="playback-bar">
            <div className="transport">
              <button
                className="play-button"
                aria-label={playing ? "재생 일시정지" : "재생 시작"}
                onClick={() => {
                  if (time >= trace.duration) setTime(0);
                  setPlaying((v) => !v);
                }}
              >
                {playing ? (
                  <Pause size={17} fill="currentColor" />
                ) : (
                  <Play size={17} fill="currentColor" />
                )}
              </button>
              <button
                className="icon-button"
                aria-label="처음으로 되감기"
                onClick={() => {
                  setTime(0);
                  setPlaying(false);
                }}
              >
                <RotateCcw size={16} />
              </button>
              <span className="timecode">
                {clock(time)}
                <i>/ {clock(trace.duration)}</i>
              </span>
            </div>
            <input
              className="timeline-slider"
              type="range"
              aria-label="재생 시각"
              min="0"
              max={trace.duration}
              step="0.1"
              value={time}
              onChange={(e) => {
                setPlaying(false);
                seek(Number(e.target.value));
              }}
              style={
                {
                  "--progress": `${(time / Math.max(trace.duration, 1)) * 100}%`,
                } as React.CSSProperties
              }
            />
            <select
              aria-label="재생 속도"
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
            >
              <option value="0.5">0.5×</option>
              <option value="1">1×</option>
              <option value="2">2×</option>
              <option value="4">4×</option>
            </select>
            {trace.mode === "demo" && (
              <div className="chapter-controls">
                <button
                  onClick={() => {
                    seek(13);
                    setPlaying(false);
                  }}
                >
                  위임
                </button>
                <button
                  onClick={() => {
                    seek(20);
                    setPlaying(false);
                  }}
                >
                  병렬 조사
                </button>
                <button
                  onClick={() => {
                    seek(57.8);
                    setPlaying(false);
                  }}
                >
                  검토
                </button>
                <button
                  onClick={() => {
                    seek(82);
                    setPlaying(false);
                  }}
                >
                  완료
                </button>
              </div>
            )}
          </footer>
          <div className="bottom-meta">
            <span>
              <i />
              {trace.mode === "demo"
                ? "연출용 데모 · 브라우저 내 재생"
                : "v0.10.0 export · 저장 기록 재생"}
            </span>
            <span>
              {trace.mode === "demo"
                ? `연구 역할 ${running} / 3`
                : "역할 호출 미관측"}{" "}
              <b>·</b> 근거 {trace.metrics.evidence ?? "미측정"} <b>·</b> 토큰{" "}
              {trace.metrics.tokens?.toLocaleString() ?? "미측정"}
            </span>
            <button onClick={resetDemo}>
              데모로 돌아가기 <ArrowRight size={11} />
            </button>
          </div>
        </main>
      </div>

      {notice && !importOpen && (
        <div className="toast" role="alert">
          <p>{notice}</p>
          <button aria-label="알림 닫기" onClick={() => setNotice("")}>
            <X size={15} />
          </button>
        </div>
      )}
      {importOpen && (
        <div className="notes-overlay" onClick={() => setImportOpen(false)}>
          <section
            className="notes-dialog import-dialog"
            ref={notesDialog}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="import-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button dialog-close"
              aria-label="불러오기 닫기"
              onClick={() => setImportOpen(false)}
            >
              <X size={18} />
            </button>
            <FileJson size={28} />
            <span className="eyebrow">LOCAL SESSION IMPORT</span>
            <h2 id="import-title">저장된 실행 기록 불러오기</h2>
            <p>
              v0.10.0 세션 export JSON 또는 이 화면에서 내려받은 trace를
              선택하세요. 파일 내용은 이 브라우저 안에서만 읽습니다.
            </p>
            <button
              className="import-file-button"
              onClick={() => fileInput.current?.click()}
            >
              <Upload size={16} /> JSON 파일 선택
            </button>
            <label className="json-label" htmlFor="trace-json">
              또는 JSON 붙여넣기
            </label>
            <textarea
              id="trace-json"
              value={pastedJson}
              onChange={(e) => setPastedJson(e.target.value)}
              spellCheck={false}
              placeholder={
                '{ "session_id": "…", "requests": […], "turns": […] }'
              }
            />
            {notice && (
              <p className="import-error" role="alert">
                {notice}
              </p>
            )}
            <button
              className="primary-button"
              disabled={!pastedJson.trim()}
              onClick={() => {
                try {
                  loadTraceJson(pastedJson);
                } catch (error) {
                  setNotice(
                    error instanceof Error
                      ? error.message
                      : "JSON을 읽을 수 없습니다.",
                  );
                }
              }}
            >
              기록 적용 <ChevronRight size={15} />
            </button>
          </section>
        </div>
      )}
      {showNotes && (
        <div className="notes-overlay" onClick={() => setShowNotes(false)}>
          <section
            className="notes-dialog"
            ref={notesDialog}
            tabIndex={-1}
            role="dialog"
            aria-modal="true"
            aria-labelledby="notes-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button dialog-close"
              aria-label="안내 닫기"
              onClick={() => setShowNotes(false)}
            >
              <X size={18} />
            </button>
            <FileJson size={28} />
            <span className="eyebrow">OBSERVATION SCOPE</span>
            <h2 id="notes-title">
              {trace.mode === "demo"
                ? "지금은 연출용 데모를 보고 있어요"
                : "저장된 세션 기록을 보고 있어요"}
            </h2>
            <p>
              {trace.mode === "demo"
                ? "v0.10.0의 실제 역할·스킬 구성을 사용한 시각 프로토타입입니다. 작업 내용, 위임, 메시지와 시간은 화면 검수를 위한 합성 데이터이며 실제 모델을 실행하지 않습니다."
                : "선택한 JSON 파일은 이 브라우저 안에서만 읽습니다. 기록에 있는 시각과 상태를 표시하며, 설치된 역할을 실제 호출로 바꾸지 않습니다."}
            </p>
            {trace.warnings.length > 0 && (
              <ul>
                {trace.warnings.map((warning, index) => (
                  <li key={index}>{warning}</li>
                ))}
              </ul>
            )}
            <div className="notes-facts">
              <span>
                <Database size={15} /> 근거·토큰의 미기록 값은 미측정
              </span>
              <span>
                <ShieldCheck size={15} /> 기존 하네스·훅·전역 설정 변경 없음
              </span>
            </div>
            <button
              className="primary-button"
              onClick={() => setShowNotes(false)}
            >
              관제실 보기 <ChevronRight size={15} />
            </button>
          </section>
        </div>
      )}
    </div>
  );
}
