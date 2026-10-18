import test from 'node:test';
import assert from 'node:assert/strict';
import {deriveReleaseView} from '../src/release.js';
import {observerWork} from '../src/factory-work-view.js';
import {factoryLayout,roomPresentation} from '../src/factory-layout.js';
import {officeSnapshot} from '../src/office-records.js';
import {stripModel} from '../src/office-store.js';
import {cliActivity} from '../src/cli-activity.js';
import {plannerStatus} from '../src/planner-status.js';
const NOW=Date.parse('2026-10-18T01:00:00Z'),iso=n=>new Date(NOW+n).toISOString();
const event=(id,patch={})=>({v:1,id,ts:iso(-2000),ts_basis:'hook_received',src:'claude',hook:'PreToolUse',session:'S',prompt_id:'P',agent_id:null,actor:'main',tool:'Bash',call:id,kind:'skill_op',node:'evidence-retrieval',op:'retrieve_reviews',ops:[],phase:'start',basis:'command_based_mapping',detail:{mapping_version:2},...patch});
const request=()=>event('request',{kind:'request',node:'main',op:null,tool:null,call:null,phase:'point',basis:'observed',hook:'UserPromptSubmit',ts:iso(-5000)});
const end=(start,detail={})=>event(start.id+'-end',{...start,id:start.id+'-end',hook:'PostToolUse',phase:'end',ts:iso(-1000),detail:{...start.detail,...detail}});
const view=(events,now=NOW)=>deriveReleaseView({schema_version:1,source:{kind:'lgax_release_observer',engine:'claude',release:'product-v0.19.0',observed_at:new Date(now).toISOString(),source_updated_at:new Date(now).toISOString(),observer_status:'observing'},events:[request(),...events],db:null},{status:'connected',lastReceivedAt:new Date(now).toISOString()},now);
test('two background Bash launch receipts keep both actual Skill rooms enlarged until their own task completion',()=>{
 const a=event('a'),b=event('b',{node:'feature-comparison',op:'retrieve_product_facts'});
 const records=[a,b,end(a,{background:true,background_task_id:'task-a'}),end(b,{background:true,background_task_id:'task-b'})];
 let v=view(records),work=observerWork(v);
 assert.deepEqual(v.activeSkills,['evidence-retrieval','feature-comparison']);
 assert.deepEqual(work.skillActiveNodes,['retrieve','compare']);
 const layout=factoryLayout({activeIds:work.activeNodes,roomIds:work.roomIds});
 assert.ok(layout.zones.retrieve.scale>layout.zones.validate.scale);assert.ok(layout.zones.compare.scale>layout.zones.validate.scale);
 const notice=event('notice',{kind:'notification',phase:'point',node:'main',tool:null,call:null,op:null,basis:'observed',hook:'UserPromptSubmit',detail:{background_task_id:'task-a',task_status:'completed'},ts:iso(-100)});
 v=view([...records,notice]);work=observerWork(v);
 assert.deepEqual(v.activeSkills,['feature-comparison']);assert.equal(work.rooms.retrieve.animate,false);assert.equal(work.rooms.compare.animate,true);
});
test('three parallel calls remain independently active and a completed tool response is not a background task end',()=>{
 const defs=[['evidence-retrieval','retrieve_reviews'],['feature-comparison','retrieve_product_facts'],['concept-writing','validate_constraints']];
 const calls=defs.map(([node,op],i)=>event('call-'+i,{node,op}));
 const records=calls.flatMap((c,i)=>[c,end(c,{background:true,background_task_id:'task-'+i})]);
 assert.equal(view(records).activeSkills.length,3);
 const done=event('task-read',{kind:'tool',node:'main',op:null,phase:'end',hook:'PostToolUse',basis:'observed',tool:'TaskOutput',detail:{background_task_id:'task-1',task_status:'failed'},ts:iso(-100)});
 const v=view([...records,done]);assert.equal(v.activeSkills.length,2);assert.equal(v.skills.find(s=>s.id==='feature-comparison').status,'failed');
});
test('a normal main final response does not fabricate completion of an already-launched background task',()=>{
 const a=event('a');const stop=event('stop',{kind:'turn_end',node:'main',call:null,tool:null,op:null,phase:'point',hook:'Stop',basis:'observed',ts:iso(-100)});
 assert.deepEqual(view([a,end(a,{background:true,background_task_id:'task-a'}),stop]).activeSkills,['evidence-retrieval']);
});
test('an approval wait remains explicit after 22 minutes without making an active Skill or finishing the command',()=>{
 const a=event('a'),permission=event('permission',{kind:'permission',node:'main',call:null,op:null,phase:'point',hook:'PermissionRequest',basis:'observed',ts:iso(-1500),detail:{reason:'permission_prompt'}});
 const v=view([a,permission],NOW+22*60e3),work=observerWork(v);
 assert.equal(v.awaiting,true);assert.deepEqual(v.activeSkills,[]);assert.match(v.header.text,/승인/);assert.match(v.nextAction,/허용.*거절/);
 assert.equal(work.rooms.retrieve.animate,false);assert.equal(work.rooms.retrieve.statusLabel,'승인 대기');assert.equal(plannerStatus(v,work).state,'input');
 const done=view([a,permission,end(a)]);assert.equal(done.awaiting,false);assert.equal(done.skills[0].status,'completed');
});
test('a mixed shell operation list never claims parallel Skill execution',()=>{
 const mixed=event('mixed',{ops:[{skill:'evidence-retrieval',op:'retrieve_reviews'},{skill:'feature-comparison',op:'retrieve_product_facts'}]});
 assert.deepEqual(view([mixed]).activeSkills,[]);
});

test('a call-bound approval wait stops only its own parallel Skill',()=>{
 const a=event('call-a'),b=event('call-b',{node:'feature-comparison',op:'retrieve_product_facts'});
 const permission=event('permission',{kind:'permission',node:'main',call:a.call,op:null,phase:'point',hook:'PermissionRequest',basis:'observed',ts:iso(-1500),detail:{reason:'permission_prompt'}});
 const v=view([a,b,permission]),work=observerWork(v);
 assert.equal(v.awaiting,true);assert.deepEqual(v.activeSkills,['feature-comparison']);
 assert.equal(work.rooms.retrieve.animate,false);assert.equal(work.rooms.retrieve.statusLabel,'승인 대기');assert.equal(work.rooms.compare.animate,true);
 const done=view([a,b,permission,end(a)]);assert.equal(done.awaiting,false);assert.deepEqual(done.activeSkills,['feature-comparison']);
});

test('an unmatched approval call cannot stop another command or another helper identity',()=>{
 const a=event('call-a');
 const permission=event('permission',{kind:'permission',node:'main',call:'unrelated-call',op:null,phase:'point',hook:'PermissionRequest',basis:'observed',ts:iso(-1500),detail:{reason:'permission_prompt'}});
 assert.deepEqual(view([a,permission]).activeSkills,['evidence-retrieval']);
 const child=event('child-call',{actor:'other_subagent',agent_id:'helper-a'});
 assert.deepEqual(view([child,{...permission,actor:'other_subagent',agent_id:'helper-b',call:child.call}]).activeSkills,['evidence-retrieval']);
});
test('cancellation and held result receipts stop motion and keep their distinct status',()=>{
 const a=event('a');
 for(const [detail,status,label]of [[{interrupted:true},'cancelled','취소'],[{turn_status:'held',accepted:true},'held','보류']]){
  const v=view([a,end(a,detail)]),w=observerWork(v);assert.equal(v.skills[0].status,status);assert.equal(w.rooms.retrieve.animate,false);assert.match(w.rooms.retrieve.statusLabel,new RegExp(label));
 }
});
test('a notification from another session cannot finish this session background call',()=>{
 const a=event('a'),other=event('other',{session:'OTHER',kind:'notification',node:'main',call:null,op:null,phase:'point',basis:'observed',detail:{background_task_id:'task-a',task_status:'completed'}});
 assert.deepEqual(view([a,end(a,{background:true,background_task_id:'task-a'}),other]).activeSkills,['evidence-retrieval']);
});
test('the compact work panel identifies replay and does not show raw tool names',()=>{
 const model=cliActivity({active:false,rooms:[],title:'지난 작업을 보고 있어요',recent:[]},{origin:'office_replay',connectionStatus:'connected',recentEvents:[{id:'raw',kind:'tool',tool:'mcp__Claude_Browser__javascript_tool',message:'브라우저에서 자료를 확인하고 있어요'}]});
 assert.equal(model.status,'기록 재생');assert.ok(!JSON.stringify(model).includes('mcp__'));
});
test('file observation and replay timelines keep background launches open just like the HTTP reader',()=>{
 const a=event('a'),records=[request(),a,end(a,{background:true,background_task_id:'task-a'}),event('stop',{kind:'turn_end',phase:'point',node:'main',op:null,tool:null,call:null,basis:'observed',hook:'Stop',ts:iso(-500)})];
 const snapshot=officeSnapshot({events:records,origin:'office_replay',session:'S',at:NOW,now:NOW});
 const v=deriveReleaseView(snapshot,{status:'connected',lastReceivedAt:iso(0)},NOW);
 assert.equal(snapshot.source.observer_status,'observing');assert.deepEqual(v.activeSkills,['evidence-retrieval']);
 const strip=stripModel(snapshot.events,null);assert.equal(strip.spans.find(s=>s.lane==='skills').end,null);
});
test('presentation grace keeps a recently enlarged room stable without changing actual execution flags',()=>{
 const first=roomPresentation(['retrieve'],0,{}),ended=roomPresentation([],100,first.until);
 assert.deepEqual(ended.ids,['retrieve']);assert.deepEqual(roomPresentation([],901,ended.until).ids,[]);
 const actual=view([event('a'),end(event('a'))]);assert.deepEqual(actual.activeSkills,[]);assert.equal(observerWork(actual).rooms.retrieve.animate,false);
});
