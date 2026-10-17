import {SKILL_BY_ID} from './skill-catalog.js';

const actions={get_work_instructions:'작업에 필요한 설명서를 확인',retrieve_reviews:'고객 후기를 조회',retrieve_product_facts:'공식 제품 기능을 조회',read_evidence_batch:'수집한 원문을 확인',select_evidence:'질문에 맞는 근거를 선택',fetch_web_page:'공개 웹페이지를 조회',capture_web_page:'확인한 웹 자료를 보관',import_web_evidence:'조사 자료를 정리',import_web_evidence_bulk:'조사 자료를 정리',resolve_request_bundle:'후기와 제품 자료를 연결',match_product_scope:'제품 모델의 일치 여부를 확인',record_evidence_review:'근거 검토 내용을 기록',prepare_review_packet:'검토할 자료를 준비',review_product_result:'기획안과 근거를 검토',validate_result_contract:'결과의 누락 항목을 검사',save_and_export:'기획 결과를 저장',save_reviewed_result:'검토 결과를 저장',workflow_status:'조사 진행 상태를 확인',record_workflow_event:'조사 이력을 기록',open_product_workflow:'조사 요청을 접수',export_session:'작업 이력을 저장'};
const short=(value,max=88)=>Array.from(value).length>max?Array.from(value).slice(0,max-1).join('')+'…':value;
// Only a bounded, human-readable public status may reach the compact panel.
// Raw command text, JSON, URLs, paths and unknown metadata stay in the existing inspector.
export function publicSentence(value){
 if(typeof value!=='string')return '';
 const clean=value.replace(/\s+/g,' ').trim();
 if(!/[가-힣]/.test(clean)||/[{}<>`]|\b\w+__\w+|https?:\/\/|[A-Za-z]:[\\/]|(?:^|\s)(?:npm|python|powershell|git|uv)\s|(?:\/|\\)[\w.-]+(?:\/|\\)/i.test(clean))return '';
 return short(clean);
}
export function activityLine(event){
 const ops=event?.ops||[],op=event?.op||ops[0]?.op,action=actions[op];
 const phase=event?.phase||event?.status;
 const failed=event?.ok===false||['error','failed','failure'].includes(phase);
 const label=action||(event?.tool&&/web|search|browse/i.test(event.tool)?'웹 자료를 조회':'');
 if(label)return label+(failed?'하지 못했어요':phase==='start'||phase==='running'?'하고 있어요':'했어요');
 if(/취소/.test(event?.message||''))return '요청이 취소됐어요. 마지막 기록을 보관해요';
 if(/호출 관측|네이티브|\bturn\b|\bTool\b/i.test(event?.message||''))return '작업 도구를 사용한 기록을 받았어요';
 return publicSentence(event?.message)||'작업 기록을 받았어요';
}
export function cliActivity(summary,view={}){
 const preview=Boolean(summary.preview),status=preview?'모의 실행':view.connectionStatus==='connected'?'실제 기록':view.connectionStatus==='stale'?'연결 지연':'연결 대기';
 const events=(view.recentEvents||[]).slice(0,20),seen=new Set(),recent=[];
 for(const event of events){const text=activityLine(event);if(seen.has(text))continue;seen.add(text);recent.push({id:event.id||recent.length,text,time:event.time||event.ts||event.at});if(recent.length===3)break;}
 const rooms=summary.rooms||[],skills=rooms.filter(r=>r.confirmed||preview).map(r=>({id:r.id||r.node,label:r.label||SKILL_BY_ID[r.id]?.label||'Skill'}));
 const title=summary.active&&rooms.length===1?rooms[0].detailLine||summary.title:summary.title;
 return {preview,status,active:Boolean(summary.active),title:publicSentence(title)||'다음 작업 소식을 기다려요',skills,
  detail:preview?'화면 동작을 시험 중이에요. 실제 CLI 작업은 실행하지 않아요.':rooms.some(r=>r.reporting)&&!skills.length?'CLI가 전한 진행 소식이에요. 사용 Skill은 확인 중이에요.':!skills.length?'현재 사용 중인 Skill 명령은 확인되지 않았어요.':'실행 기록에서 확인한 Skill이에요.',
  recent:preview?[]:recent,lastAt:preview?null:events[0]?.time||events[0]?.ts||events[0]?.at,
  next:publicSentence(summary.next)||'새 작업 기록이 도착하면 여기에 표시해요'};
}
