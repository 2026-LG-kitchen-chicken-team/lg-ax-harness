import test from 'node:test';
import assert from 'node:assert/strict';
import {deriveReleaseView} from '../src/release.js';
import {observerWork} from '../src/factory-work-view.js';
import {currentWorkSummary} from '../src/current-work-summary.js';
import {normalizeActivity} from '../src/releaseActivity.js';
import {factoryLayout} from '../src/factory-layout.js';
import {PRODUCT_SKILLS} from '../src/skill-catalog.js';
import {advanceResearcherClock} from '../src/researcher-motion.js';

const NOW=Date.parse('2026-10-17T13:10:00Z'),iso=n=>new Date(n).toISOString();
const request={v:1,id:'request',ts:iso(NOW-10000),ts_basis:'codex_log',src:'codex',hook:'UserPromptSubmit',session:'session',prompt_id:'turn',actor:'main',agent_id:null,tool:null,call:null,kind:'request',node:'main',op:null,ops:[],phase:'point',basis:'observed',detail:{}};
const call=(skill='evidence-retrieval',operation='retrieve_reviews',patch={})=>({id:'call-'+skill,category:'skill',status:'running',started_at:iso(NOW-1000),ended_at:null,skill,operation,observer_call_id:null,basis:'native_tool_call',...patch});
const activity=(calls,patch={})=>({kind:'codex_native_activity',session_id:'session',prompt_id:'turn',state:'working',intent:'general',task_code:'main_work',reported_stage:null,last_event_at:iso(NOW),checks:{},installed_skills:[],skill_reads:[],command_count:0,web_count:0,actions:[],calls,...patch});
function view(calls,{now=NOW,status='connected',activityPatch={},events=[]}={}){
 return deriveReleaseView({schema_version:1,source:{kind:'lgax_release_observer',engine:'codex',release:'product-v0.19.0',observer_status:'observing',observed_at:iso(now),source_updated_at:iso(NOW)},events:[request,...events],activity:activity(calls,activityPatch),db:null,notices:[]},{status,lastReceivedAt:iso(now)},now);
}

test('native Skill start drives the same room, concrete work sentence, progress and researcher clock',()=>{
 const v=view([call()]),w=observerWork(v),d=currentWorkSummary(v,w);
 assert.deepEqual(v.activeSkills,['evidence-retrieval']);assert.deepEqual(w.activeNodes,['retrieve']);
 assert.deepEqual(w.skillActiveNodes,['retrieve']);assert.match(w.line,/자료 조회/);
 assert.match(d.rooms[0].detailLine,/고객 리뷰/);assert.equal(d.rooms[0].actor,'메인 기획 AI');
 assert.equal(d.rooms[0].progress,'처리 중 · 진행 수 집계 전');assert.ok(advanceResearcherClock(1,{working:w.rooms.retrieve.animate,dt:.1})>1);
});

test('each of the six Skill entry points drives only its own workroom',()=>{
 const ops=['retrieve_reviews','validate_source_refs','retrieve_product_facts','validate_constraints','validate_result_contract','capture_web_page'];
 PRODUCT_SKILLS.forEach((s,i)=>{const w=observerWork(view([call(s.id,ops[i])]));assert.deepEqual(w.skillActiveNodes,[s.node]);assert.equal(w.rooms[s.node].animate,true);});
});

test('two and three simultaneous native Skill calls enlarge all corresponding rooms',()=>{
 const calls=[call(),call('feature-comparison','retrieve_product_facts'),call('web-evidence-collection','capture_web_page')];
 for(const count of [2,3]){
  const w=observerWork(view(calls.slice(0,count))),ids=w.activeNodes;
  assert.equal(ids.length,count);assert.match(w.line,new RegExp('SKILL '+count+'개'));
  const layout=factoryLayout({width:1400,height:900,roomIds:PRODUCT_SKILLS.map(s=>s.node),activeIds:['overview',...ids]});
  for(const id of ids)assert.ok(layout.zones[id].scale>layout.zones.structure.scale);
 }
});

test('instruction, administrative calls and public reports never animate Skill work',()=>{
 for(const calls of [[call('evidence-retrieval','get_work_instructions',{category:'instruction'})],[call('evidence-retrieval','workflow_status',{category:'shell'})],[]]){
  const w=observerWork(view(calls,{activityPatch:{reported_stage:'compare',intent:'planning',task_code:'compare_features'}}));
  assert.deepEqual(w.skillActiveNodes,[]);assert.deepEqual(w.activeNodes,[]);
 }
});

test('completion, failure, cancellation, stale observations and wrong request stop room movement',()=>{
 for(const state of ['completed','failed','cancelled','unknown']){
  const v=view([call('evidence-retrieval','retrieve_reviews',{status:state,ended_at:iso(NOW)})]),w=observerWork(v);
  assert.deepEqual(w.skillActiveNodes,[]);assert.equal(w.rooms.retrieve.animate,false);
  assert.equal(advanceResearcherClock(1,{working:w.rooms.retrieve.animate,dt:.1}),1);
  assert.equal(v.skills[0].status,{completed:'completed',failed:'failed',cancelled:'cancelled',unknown:'unknown'}[state]);
  if(state==='unknown'){assert.match(v.skills[0].task,/종료 결과 확인 필요/);assert.equal(w.rooms.retrieve.statusLabel,'종료 확인 필요');}
 }
 for(const options of [{status:'disconnected'},{now:NOW+130000},{activityPatch:{prompt_id:'other'}}])assert.deepEqual(observerWork(view([call()],options)).skillActiveNodes,[]);
});

test('native receipt replaces a temporary start without duplicating or reopening its command',()=>{
 const c=call('evidence-retrieval','retrieve_reviews',{status:'completed',ended_at:iso(NOW),observer_call_id:'actual-command'});
 const base={...request,kind:'skill_op',node:'evidence-retrieval',op:'retrieve_reviews',call:'actual-command',basis:'command_based_mapping',hook:'PreToolUse'};
 const v=view([c],{events:[{...base,id:'a',phase:'start',ts:iso(NOW-1000)},{...base,id:'b',phase:'end',ts:iso(NOW)}]});
 assert.equal(v.spans.filter(s=>s.start.kind==='skill_op').length,1);assert.deepEqual(v.activeSkills,[]);
});

test('a printed Skill path misclassified by an old observer is not active work',()=>{
 const c=call(null,null,{category:'shell',observer_call_id:'printed-command'});
 const old={...request,id:'old-match',kind:'skill_op',phase:'start',hook:'PreToolUse',call:'printed-command',node:'evidence-retrieval',op:'retrieve_reviews',basis:'command_based_mapping',ts:iso(NOW-1000)};
 assert.deepEqual(view([c],{events:[old]}).activeSkills,[]);
});

test('a native exit closes a partial observer start without waiting for its delayed end',()=>{
 const c=call('evidence-retrieval','retrieve_reviews',{status:'completed',ended_at:iso(NOW),observer_call_id:'actual-command'});
 const start={...request,id:'partial-start',kind:'skill_op',node:'evidence-retrieval',op:'retrieve_reviews',call:'actual-command',basis:'command_based_mapping',hook:'PreToolUse',phase:'start',ts:iso(NOW-1000)};
 const v=view([c],{events:[start]});assert.deepEqual(v.activeSkills,[]);
 assert.equal(v.spans.filter(s=>s.start.kind==='skill_op').length,1);
 assert.equal(v.skills[0].status,'completed');
});

test('an old request receipt with a reused command ID cannot demote current Skill work',()=>{
 const c=call(null,null,{category:'shell',observer_call_id:'reused-command'});
 const start={...request,id:'current-start',kind:'skill_op',node:'evidence-retrieval',op:'retrieve_reviews',call:'reused-command',basis:'command_based_mapping',hook:'PreToolUse',phase:'start',ts:iso(NOW-1000)};
 const v=view([c],{events:[start],activityPatch:{session_id:'old-session',prompt_id:'old-turn'}});
 assert.deepEqual(v.activeSkills,['evidence-retrieval']);assert.equal(v.activity,null);
});

test('browser work is understandable without inventing a Skill or copying commands',()=>{
 const v=view([call(null,null,{category:'browser'})]),w=observerWork(v);
 assert.match(w.line,/브라우저/);assert.deepEqual(w.skillActiveNodes,[]);
 const raw=activity([call()]);raw.calls[0].command='PRIVATE';raw.calls[0].token='SECRET';
 assert.ok(!JSON.stringify(normalizeActivity(raw)).includes('PRIVATE'));assert.ok(!JSON.stringify(normalizeActivity(raw)).includes('SECRET'));
 assert.equal(normalizeActivity(activity([call('invented','retrieve_reviews')])),null);
});
