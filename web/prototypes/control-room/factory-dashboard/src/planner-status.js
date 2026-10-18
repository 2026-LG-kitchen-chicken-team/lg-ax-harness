import {sameBinding} from './office-records.js';

const RESULT_URL='../visual-viewer/index.html';
const main=e=>e.actor==='main'&&!e.agent_id;
const terminal=e=>main(e)&&['turn_end','turn_cancelled','request','handback_delivered','notification'].includes(e.kind);
const failures=new Set(['failed','error','timeout','timed_out','incomplete']);
const cancellations=new Set(['cancelled','canceled','interrupted','stopped']);

/** Human-facing projection of observed state. It never infers a percentage, ETA,
 * an input request from quiet time, or completion from the mere presence of a file. */
export function plannerStatus(view,work,office=null){
 const events=view.currentEvents||[],marker=events.filter(terminal).at(-1),db=view.database;
 const metadata=office?.result?.value||null,delivery=metadata?.delivery;
 const replay=office?.mode==='replay'||view.origin==='office_replay';
 const currentCandidate=db?.candidates?.findLast(c=>c.result_version===db.turn?.result_version);
 const joined=Boolean(view.bindingState==='matched'&&db?.turn?.valid===true&&
  currentCandidate?.contract_valid===true&&currentCandidate?.structural_valid===true&&
  delivery?.display_ready===true&&sameBinding(view.binding,delivery.binding)&&
  db.turn.result_version===delivery.binding.result_version);
 const children=new Set();let laterChild=false;
 for(const [i,e]of events.entries()){
  if(e.kind==='delegate'&&e.detail?.launched_agent_id)children.add(e.detail.launched_agent_id);
  if(e.kind==='subagent'&&e.phase==='start'&&e.agent_id)children.add(e.agent_id);
  if(marker&&i>events.lastIndexOf(marker)&&e.kind==='subagent'&&['end','fail'].includes(e.phase)&&children.has(e.agent_id))laterChild=true;
 }
 const ended=marker?.kind==='turn_end'&&!laterChild&&!view.mainActive&&!(view.agents||[]).some(a=>a.active)&&
  !(view.spans||[]).some(s=>s.status==='open'&&events.some(e=>e.id===s.start?.id));
 const nativeStatus=marker?.detail?.response_status||marker?.detail?.turn_status;
 const business=['needs_input','awaiting_input','awaiting_approval'].includes(nativeStatus)?nativeStatus:db?.turn?.status||db?.request?.status;
 const cancelled=marker?.kind==='turn_cancelled'||marker?.detail?.interrupted===true||
  cancellations.has(marker?.detail?.response_status)||cancellations.has(marker?.detail?.turn_status)||
  view.activity?.state==='cancelled'||db?.cancelled===true||business==='cancelled';
 const failed=failures.has(marker?.detail?.response_status)||failures.has(marker?.detail?.turn_status)||failures.has(business);
 const current=Boolean(view.connectionStatus==='connected'&&!replay&&joined&&ended&&!cancelled&&!failed&&business==='completed'&&delivery.business_status==='completed');
 const previous=Boolean(metadata&&(!delivery||delivery.display_ready===true));
 const result=current?{href:RESULT_URL,label:'기획안 보기',current:true}:previous?{href:RESULT_URL,label:'최근 기획안 보기',current:false}:null;
 const mode=replay?'지난 실행 재생':view.origin==='office_live'?'실시간 작업':'실행 기록';
 const status={mode,state:'waiting',title:'AI 화면에서 상품기획을 요청해 주세요',action:null,result,current:false};
 if(current)return {...status,state:'ready',title:'기획안이 준비됐어요',action:delivery.report_data_ready?'기획안에서 내용을 살펴보고 보고서로 이어 볼 수 있어요.':null,current:true};
 if(cancelled)return {...status,state:'cancelled',title:'이번 작업을 취소했어요',action:'AI 화면에서 이어 할 작업을 입력해 주세요.'};
 if(view.awaiting)return {...status,state:'input',title:'CLI에서 명령 실행 승인을 기다려요',action:'CLI의 권한 요청에서 허용 또는 거절을 선택해 주세요.'};
 if(failed&&ended)return {...status,state:'failed',title:'이번 작업을 마치지 못했어요',action:'AI 화면의 안내를 확인하고 다시 요청해 주세요.'};
 if(['needs_input','awaiting_input','awaiting_approval'].includes(business))return {...status,state:'input',title:business==='awaiting_approval'?'AI 화면에서 승인을 기다려요':'AI 화면에서 추가 입력을 기다려요',action:'AI가 요청한 내용을 확인하고 답해 주세요.'};
 if(view.connectionStatus==='error'||view.connectionStatus==='stale'||view.connectionStatus==='disconnected'&&events.length)return {...status,state:'connection',title:'작업 소식 연결을 다시 확인하고 있어요',action:'AI 화면에서는 작업을 계속 확인할 수 있어요. 기존 기록은 그대로 보관돼요.'};
 if(ended&&business==='held')return {...status,state:'held',title:'이번 요청의 정리 내용을 AI 화면에서 확인해 주세요',action:'AI가 안내한 조건을 확인하고 다음 작업을 요청해 주세요.'};
 if(ended&&joined&&business==='completed')return {...status,state:'recorded',title:replay?'저장된 작업을 끝까지 재생했어요':'AI 답변이 끝났어요',action:replay?'최근 기획안은 재생 중인 시점의 결과와 다를 수 있어요.':'AI 화면에서 답변을 확인해 주세요.'};
 if(ended&&business==='completed'&&office)return {...status,state:'recorded',title:'AI 답변이 끝났어요',action:'기획안 화면 연결을 확인하고 있어요. AI 화면에서는 답변을 읽을 수 있어요.'};
 if(ended)return {...status,state:'recorded',title:'AI 답변이 끝났어요',action:'AI 화면에서 답변을 확인해 주세요.'};
 if(work.mainWorking||work.activeNodes?.length)return {...status,state:'working',title:work.line};
 if(events.length&&!view.observationFresh)return {...status,state:'connection',title:'새 작업 소식을 기다리고 있어요',action:'AI 화면에서 현재 작업을 확인할 수 있어요.'};
 return status;
}
