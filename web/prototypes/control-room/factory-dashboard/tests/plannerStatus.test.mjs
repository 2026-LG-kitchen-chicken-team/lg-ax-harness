import test from 'node:test';
import assert from 'node:assert/strict';
import {plannerStatus} from '../src/planner-status.js';
import {resultMetadata} from '../src/office-records.js';

// Synthetic identity/status contracts only; these are not native model runs.
const binding={session_id:'business-session',turn_id:'business-turn',request_key:'request',result_version:2};
const event=(kind,detail={})=>({id:kind,kind,actor:'main',agent_id:null,detail});
const work={mainWorking:false,activeNodes:[],line:'메인 기획 AI가 작업하고 있어요'};
const delivery={binding,business_status:'completed',display_ready:true,report_data_ready:true};
const office={mode:'live',result:{value:{delivery}}};
const ready={origin:'office_live',connectionStatus:'connected',bindingState:'matched',binding,
 currentEvents:[event('request'),event('turn_end')],mainActive:false,agents:[],spans:[],observationFresh:false,
 database:{turn:{status:'completed',result_version:2,valid:true},request:{status:'needs_input'},candidates:[{result_version:2,contract_valid:true,structural_valid:true,acceptance_ready:false}]}};

test('current plan requires native final, bound current stored result and verified viewer delivery',()=>{
 const status=plannerStatus(ready,work,office);
 assert.equal(status.state,'ready');assert.equal(status.result.label,'기획안 보기');assert.equal(status.current,true);
 // Semantic acceptance_ready remains false and is not relabelled by display readiness.
 assert.equal(ready.database.candidates[0].acceptance_ready,false);
 for(const changed of [
  {...ready,currentEvents:[event('request')]},
  {...ready,mainActive:true},
  {...ready,bindingState:'unmatched'},
  {...ready,agents:[{active:true}]},
  {...ready,database:{...ready.database,turn:{...ready.database.turn,valid:false}}},
  {...ready,database:{...ready.database,turn:{...ready.database.turn,result_version:3}}},
  {...ready,connectionStatus:'error'},
 ])assert.equal(plannerStatus(changed,work,office).current,false);
});

test('another request, another version, legacy file and replay cannot announce a new current plan',()=>{
 for(const item of [
  {delivery:{...delivery,binding:{...binding,request_key:'old-request'}}},
  {delivery:{...delivery,binding:{...binding,result_version:1}}},
  {delivery:{...delivery,display_ready:false}},
  {generated_at:'2026-10-18T12:00:00Z'},
 ])assert.equal(plannerStatus(ready,work,{...office,result:{value:item}}).current,false);
 const replay=plannerStatus(ready,work,{...office,mode:'replay'});
 assert.equal(replay.current,false);assert.equal(replay.result.label,'최근 기획안 보기');
 assert.equal(plannerStatus(ready,work,{...office,result:{value:{delivery:{...delivery,display_ready:false}}}}).result,null);
});

test('held, input, cancellation and terminal failure have distinct actions while preserving old results',()=>{
 for(const [business,state]of [['held','held'],['needs_input','input'],['cancelled','cancelled'],['failed','failed']]){
  const view={...ready,database:{...ready.database,turn:{...ready.database.turn,status:business}}};
  const s=plannerStatus(view,work,office);assert.equal(s.state,state);assert.equal(s.current,false);assert.equal(s.result.current,false);
 }
 assert.equal(plannerStatus({...ready,currentEvents:[event('turn_cancelled')]},work,office).state,'cancelled');
 assert.equal(plannerStatus({...ready,currentEvents:[event('turn_end',{response_status:'failed'})]},work,office).state,'failed');
 assert.equal(plannerStatus({...ready,database:null,currentEvents:[event('turn_end',{response_status:'needs_input'})]},work,office).state,'input');
 assert.equal(plannerStatus({...ready,database:null,currentEvents:[event('turn_end',{response_status:'awaiting_approval'})]},work,office).state,'input');
});

test('quiet main work and a recovered tool error do not become failure, an input request or a guessed stage',()=>{
 const view={...ready,database:null,bindingState:'unavailable',mainActive:true,observationFresh:true,
  currentEvents:[event('request'),{...event('tool'),phase:'fail'}]};
 const status=plannerStatus(view,{...work,mainWorking:true},office);
 assert.equal(status.state,'working');assert.equal(status.title,'메인 기획 AI가 작업하고 있어요');
 assert.equal(status.action,null);assert.equal(status.current,false);
 const old=plannerStatus({...view,mainActive:false,observationFresh:false},work,office);
 assert.equal(old.state,'connection');assert.notEqual(old.state,'input');
});

test('a screen read failure keeps the recent plan available without declaring work failed or completed',()=>{
 const result=plannerStatus({...ready,connectionStatus:'error'},work,office);
 assert.equal(result.state,'connection');assert.equal(result.current,false);
 assert.equal(result.result.label,'최근 기획안 보기');
 assert.equal(plannerStatus({...ready,database:null},work,null).result,null);
});

test('viewer metadata keeps only known safe delivery fields and does not promote unverified display data',()=>{
 const raw={kind:'lgax-view',pages:[{}],delivery:{...delivery,raw_command:'PRIVATE'}};
 const meta=resultMetadata(raw);assert.deepEqual(meta.delivery,delivery);assert.ok(!JSON.stringify(meta).includes('PRIVATE'));
 assert.equal(resultMetadata({...raw,delivery:{...delivery,binding:{...binding,request_key:'invalid/path'}}}).delivery,undefined);
 assert.equal(resultMetadata({...raw,delivery:{...delivery,display_ready:'true'}}).delivery.display_ready,false);
 assert.equal(resultMetadata({...raw,delivery:{...delivery,binding:{...binding,result_version:99}}}).delivery,undefined);
 assert.equal(plannerStatus(ready,work,{...office,result:{value:{delivery:{...delivery,report_data_ready:false}}}}).action,null);
});
