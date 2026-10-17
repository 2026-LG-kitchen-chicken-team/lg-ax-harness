// Fixed labels only. Public CLI commentary reports a task; it is not a Skill call.
import {skillOperation,operationText} from './skill-operations.js';
const skills=new Set(['evidence-retrieval','web-evidence-collection','needs-structuring','feature-comparison','concept-writing','review-and-revise']);
const stages=new Set(['retrieve','structure','compare','concept','validate']);
const identifier=x=>typeof x==='string'&&/^[A-Za-z0-9_.:-]{1,200}$/.test(x);
const stamp=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T/.test(x)&&Number.isFinite(Date.parse(x));
const number=x=>Number.isSafeInteger(x)&&x>=0&&x<=1e6;
const callCategories=new Set(['skill','instruction','web','browser','shell','file','tool']);
const callStates=new Set(['running','completed','failed','cancelled','unknown']);
const TOOL_TASKS=Object.freeze({
 browser:['브라우저에서 자료를 확인하고 있어요','브라우저 자료 확인'],
 web:['웹에서 자료를 검색하거나 원문을 열고 있어요','웹 검색·원문 조회'],
 shell:['로컬 명령을 실행하고 있어요','로컬 명령 실행'],
 file:['파일을 확인하거나 수정하는 도구를 호출하고 있어요','파일 도구 호출'],
 tool:['CLI에서 도구를 호출하고 있어요','CLI 도구 호출'],
});
export const ACTIVITY_LABELS=Object.freeze({
 main_work:['메인 기획자가 요청을 처리하고 있습니다','메인 작업 기록'],
 check_setup:['하네스 지침과 실행 준비를 확인하고 있습니다','하네스 설치·실행 환경 검사'],
 check_storage:['로컬 파일과 SQLite 저장·조회를 확인하고 있습니다','파일·SQLite 저장·조회 검사'],
 read_skill_instructions:['Skill 지침을 조회하고 있습니다','Skill 지침 조회 명령'],
 research_sources:['자료와 웹 근거를 조사하고 있습니다','자료·웹 근거 조사'],
 structure_needs:['고객 상황과 불편을 정리하고 있습니다','고객 니즈 구조화'],
 compare_features:['고객 불편을 기존 제품 기능과 대조하고 있습니다','기존 기능·잔여 불편 대조'],
 write_concepts:['남은 불편을 해결할 콘셉트를 작성하고 있습니다','콘셉트·요구사항 작성'],
 review_results:['콘셉트와 연결 근거를 검토하고 있습니다','근거·결과 검토'],
 local_command:['로컬 명령을 처리하고 있습니다','로컬 명령'],
 web_lookup:['웹 자료를 확인하고 있습니다','웹 자료 조회'],
 readiness_finished:['실행 준비 확인','준비 확인 응답'],
 turn_finished:['메인 요청 처리','메인 최종 응답'],
});
export function normalizeActivity(raw){
 if(raw==null)return null;
 try{
  if(raw.kind!=='codex_native_activity'||!identifier(raw.session_id)||!identifier(raw.prompt_id)||!['working','finished','cancelled'].includes(raw.state)||!['general','readiness','planning'].includes(raw.intent)||!ACTIVITY_LABELS[raw.task_code]||!stamp(raw.last_event_at)||raw.reported_stage!=null&&!stages.has(raw.reported_stage)||!number(raw.command_count)||!number(raw.web_count))return null;
  const checks={};for(const key of ['installation','file','sqlite']){if(raw.checks?.[key]!=null){if(typeof raw.checks[key]!=='boolean')return null;checks[key]=raw.checks[key];}}
  if(!Array.isArray(raw.skill_reads)||raw.skill_reads.length>6||!Array.isArray(raw.installed_skills)||raw.installed_skills.length>6||!Array.isArray(raw.actions)||raw.actions.length>12)return null;
  const reads=raw.skill_reads.map(r=>{if(!skills.has(r.id)||!stamp(r.time)||r.basis!=='read_command_output')throw Error();return {id:r.id,time:r.time,basis:r.basis};});
  if(raw.installed_skills.some(x=>!skills.has(x)))return null;
  const actions=raw.actions.map(a=>{if(!identifier(a.id)||!stamp(a.time)||!ACTIVITY_LABELS[a.code]||!['reported','completed','failed','finished','cancelled'].includes(a.status)||a.stage!=null&&!stages.has(a.stage))throw Error();return {id:a.id,time:a.time,code:a.code,status:a.status,stage:a.stage||null};});
  if(raw.calls!=null&&(!Array.isArray(raw.calls)||raw.calls.length>64))return null;
  const calls=(raw.calls||[]).map(c=>{
   const op=skillOperation(c.operation);
   if(!identifier(c.id)||!callCategories.has(c.category)||!callStates.has(c.status)||!stamp(c.started_at)||c.ended_at!=null&&!stamp(c.ended_at)||c.observer_call_id!=null&&!identifier(c.observer_call_id)||!['native_tool_call','native_command_result'].includes(c.basis))throw Error();
   if(c.skill!=null&&(!skills.has(c.skill)||!op)||c.operation!=null&&(!op||!skills.has(c.skill)))throw Error();
   if(c.category==='skill'&&op?.kind!=='work'||c.category==='instruction'&&op?.kind!=='instruction')throw Error();
   if(c.status==='running'&&c.ended_at!=null||c.ended_at&&Date.parse(c.ended_at)<Date.parse(c.started_at))throw Error();
   return {id:c.id,category:c.category,status:c.status,started_at:c.started_at,ended_at:c.ended_at||null,skill:c.skill||null,operation:c.operation||null,observer_call_id:c.observer_call_id||null,basis:c.basis};
  });
  if(new Set(calls.map(c=>c.id)).size!==calls.length)return null;
  return {kind:raw.kind,session_id:raw.session_id,prompt_id:raw.prompt_id,state:raw.state,intent:raw.intent,task_code:raw.task_code,reported_stage:raw.reported_stage||null,last_event_at:raw.last_event_at,checks,installed_skills:[...new Set(raw.installed_skills)],skill_reads:reads,command_count:raw.command_count,web_count:raw.web_count,actions,calls};
 }catch{return null;}
}
export function activityPresentation(raw,session,prompt,connected,now){
 if(!raw||raw.session_id!==session||raw.prompt_id!==prompt)return null;
 const age=now-Date.parse(raw.last_event_at),fresh=connected&&age>=-5000&&age<120000;
 const working=raw.state==='working'&&fresh;
 const ready=raw.intent==='readiness'&&raw.state==='finished'&&['installation','file','sqlite'].every(k=>raw.checks[k]===true);
 const running=working?(raw.calls||[]).filter(c=>c.status==='running'):[];
 const current=running.findLast(c=>c.category==='skill')||running.at(-1)||null;
 const line=current?(operationText(current.operation)||TOOL_TASKS[current.category]?.[0]||'Skill 설명서를 확인하고 있어요'):ACTIVITY_LABELS[raw.task_code][0];
 const reported=raw.reported_stage&&working;
 let text=working?line:raw.state==='working'?`마지막 작업: ${ACTIVITY_LABELS[raw.task_code][1]} · 후속 상태 확인 필요`:raw.state==='cancelled'?'CLI 요청이 취소됐습니다':ready?'실행 준비 확인 완료 · 상품기획 요청 대기':raw.intent==='readiness'?'준비 확인 응답 완료 · 검사 결과 확인':'CLI 요청 응답 완료 · 작업 결과 확인';
 const commandIds=new Set((raw.calls||[]).flatMap(c=>[c.observer_call_id,'exec-'+c.observer_call_id]).filter(Boolean));
 const actions=raw.actions.filter(a=>!commandIds.has(a.id)).map(a=>({...a,ts:a.time,actor:'main',basis:a.status==='reported'?'cli_report':'command_result',message:`${ACTIVITY_LABELS[a.code][1]} · ${{reported:'CLI 진행 보고',completed:'명령 완료',failed:'명령 실패',finished:'응답 완료',cancelled:'취소'}[a.status]}`}));
 for(const c of raw.calls||[]){
  const label=skillOperation(c.operation)?.label||TOOL_TASKS[c.category]?.[1]||'Skill 지침 조회';
  actions.push({id:'call-'+c.id,time:c.ended_at||c.started_at,ts:c.ended_at||c.started_at,actor:'main',basis:c.basis,code:c.category,status:c.status,message:`${label} · ${{running:'호출 중',completed:'호출 완료',failed:'명령 실패',cancelled:'취소',unknown:'종료 결과 확인 필요'}[c.status]}`});
 }
 actions.sort((a,b)=>Date.parse(a.time)-Date.parse(b.time));
 return {...raw,working,ready,reported:!!reported,current,text,actions,next:working?current?.category==='instruction'?'설명서 조회가 끝나면 CLI가 필요한 작업을 이어갑니다. 지침 조회는 Skill 업무 실행과 구분됩니다.':'실행 중인 명령의 결과를 기다립니다. 오류가 나면 CLI의 오류와 다음 기록을 확인하세요.':raw.state==='working'?'마지막 기록 이후의 CLI 상태를 확인하세요. 종료 결과를 아직 받지 못했습니다.':raw.state==='cancelled'?'CLI에서 재개할 작업을 선택하거나 새 요청을 입력하세요.':ready?'CLI에 제품군과 원하는 상품기획 요청을 입력하세요.':'CLI의 최종 응답과 검사 결과를 확인하세요.'};
}

// A display projection of real native calls, never written back into office logs.
// Once the installed observer has the same command receipt, use that original
// event instead, so a command is not counted twice or left open after it ends.
export function nativeSkillEvents(activity,events){
 if(!activity)return [];
 const output=[];
 for(const call of activity.calls||[]){
  if(!['skill','instruction'].includes(call.category)||!call.skill||call.observer_call_id&&events.some(e=>e.call===call.observer_call_id))continue;
  const base={v:1,src:'codex',session:activity.session_id,prompt_id:activity.prompt_id,agent_id:null,actor:'main',kind:'skill_op',node:call.skill,op:call.operation,ops:[{skill:call.skill,op:call.operation}],tool:'shell',call:'native:'+call.id,basis:'command_based_mapping',ts_basis:'codex_log',detail:{}};
  output.push({...base,id:'native:'+call.id+':start',ts:call.started_at,hook:'PreToolUse',phase:'start'});
  if(call.status!=='running')output.push({...base,id:'native:'+call.id+':end',ts:call.ended_at||call.started_at,hook:call.status==='failed'?'PostToolUseFailure':'PostToolUse',phase:call.status==='failed'?'fail':'end',detail:call.status==='unknown'?{reason:'native_result_unconfirmed'}:call.status==='cancelled'?{interrupted:true}: {}});
 }
 return output;
}
