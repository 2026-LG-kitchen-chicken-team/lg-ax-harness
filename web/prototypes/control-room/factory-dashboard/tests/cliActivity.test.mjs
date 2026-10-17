import test from 'node:test';
import assert from 'node:assert/strict';
import {cliActivity,publicSentence,activityLine} from '../src/cli-activity.js';
test('compact feed never prints commands, code, URLs or local paths',()=>{
 for(const text of ['python tool.py # 고객 자료','{"후기":100}','확인 https://example.com','파일 C:\\Users\\x\\data.json','```긴 코드```'])assert.equal(publicSentence(text),'');
 assert.ok(publicSentence('고객 후기를 확인하고 있어요.').includes('고객 후기'));
 assert.ok(Array.from(publicSentence('가'.repeat(500))).length<=88);
});
test('operation status distinguishes starting, failure, and completion',()=>{
 assert.match(activityLine({op:'fetch_web_page',phase:'start'}),/하고 있어요$/);
 assert.match(activityLine({op:'fetch_web_page',phase:'error'}),/못했어요$/);
 assert.match(activityLine({op:'fetch_web_page',phase:'end'}),/했어요$/);
 assert.equal(activityLine({message:'mcp__cua_repl__js 호출 관측'}),'작업 도구를 사용한 기록을 받았어요');
 assert.equal(activityLine({message:'네이티브 turn 취소 관측 · Tool 종료 결과는 별도 확인'}),'요청이 취소됐어요. 마지막 기록을 보관해요');
});
test('latest feed is bounded, deduplicated and does not infer active skills',()=>{
 const summary={rooms:[{id:'evidence-retrieval',label:'자료 조회',reporting:true}],title:'진행 상황을 확인해요',active:true};
 const model=cliActivity(summary,{connectionStatus:'stale',recentEvents:[{id:1,op:'fetch_web_page',phase:'end'},{id:2,op:'fetch_web_page',phase:'end'},{id:3,op:'get_work_instructions'},{id:4,op:'save_and_export'},{id:5,op:'workflow_status'}]});
 assert.equal(model.status,'연결 지연');assert.equal(model.skills.length,0);assert.equal(model.recent.length,3);
});
test('preview is labelled and cannot manufacture a CLI history',()=>{
 const model=cliActivity({preview:true,active:true,title:'동작 예시를 보고 있어요',rooms:[{id:'evidence-retrieval',label:'자료 조회'}]},{recentEvents:[{id:1,op:'save_and_export'}]});
 assert.equal(model.status,'모의 실행');assert.equal(model.recent.length,0);assert.equal(model.lastAt,null);assert.equal(model.skills[0].label,'자료 조회');
});
test('actual native Skill lifecycles feed the short history without command text',()=>{
 const model=cliActivity({rooms:[],title:'자료를 확인해요'},{connectionStatus:'connected',activity:{calls:[{id:'a',operation:'retrieve_reviews',category:'skill',status:'completed',started_at:'2026-10-17T13:41:10Z',ended_at:'2026-10-17T13:41:13Z'},{id:'b',operation:'retrieve_product_facts',category:'skill',status:'running',started_at:'2026-10-17T13:41:15Z'}]}});
 assert.equal(model.recent[0].text,'공식 제품 기능을 조회하고 있어요');
 assert.equal(model.recent[1].text,'고객 후기를 조회했어요');
 assert.equal(model.skills.length,0);
 assert.match(activityLine({op:'retrieve_reviews',status:'unknown'}),/확인 중/);
 assert.match(activityLine({op:'retrieve_reviews',phase:'fail'}),/못했어요/);
});

test('cancelled native Skill calls are never described as completed work',()=>{
 for(const status of ['cancelled','stopped']){
  const model=cliActivity({rooms:[],title:'자료를 확인해요'},{connectionStatus:'connected',activity:{calls:[{id:'cancelled-review',operation:'retrieve_reviews',category:'skill',status,started_at:'2026-10-17T13:41:10Z',ended_at:'2026-10-17T13:41:13Z'}]}});
  assert.match(model.recent[0].text,/취소/);
  assert.doesNotMatch(model.recent[0].text,/조회했어요/);
 }
});
