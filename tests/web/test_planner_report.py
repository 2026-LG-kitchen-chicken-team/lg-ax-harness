"""Exercise generated report JS/data projection only, never a browser or model."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PlannerReportTests(unittest.TestCase):
    def test_built_report_keeps_full_appendix_but_only_planning_in_body(self):
        script = r'''
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');
(async()=>{
 const {jinhaReport}=await import(pathToFileURL(path.resolve('web/prototypes/visual-viewer/app/scripts/jinha-report.mjs')));
 const built=jinhaReport().load.call({addWatchFile(){}},'\0virtual:jinha-report');
 const html=JSON.parse(built.slice('export default '.length));
 const scripts=[...html.matchAll(/<script>\n([^]*?)\n<\/script>/g)].map(m=>m[1]);
 assert.equal(scripts.length,2);
 const adapterModule={exports:{}};
 new Function('module','URL',scripts[0])(adapterModule,URL);
 const Adapter=adapterModule.exports;
 const registry=new Map();
 const node=selector=>{if(!registry.has(selector))registry.set(selector,{innerHTML:'',textContent:'',value:'',hidden:false,checked:false,classList:{toggle(){},remove(){}},setAttribute(){},getAttribute(){return null;}});return registry.get(selector);};
 node('#embedded-report').textContent='{}';
 const doc={querySelector:node,querySelectorAll:()=>[],body:{classList:{toggle(){},remove(){}}}};
 const win={HarnessReportAdapter:Adapter};
 const prefix=scripts[1].slice(0,scripts[1].indexOf("document.addEventListener('click',event=>")).replace('(function(){','');
 const api=new Function('window','document','URL',prefix+'\nreturn {render,renderBusiness,renderFollowUp};')(win,doc,URL);
 const tail='FULL ORIGINAL TAIL <img src=x onerror="no">';
 const longBody='original material '.repeat(5000)+tail;
 const original={status:'completed',pains:[{id:'p',text:'Initial inconvenience',source_ids:['S']}],existing_features:[{id:'f',text:'Current feature',source_ids:['S']}],remaining_pains:[{id:'r',text:'Important remaining issue',source_ids:['S']}],concepts:[{id:'c',text:'Proposed planning',source_ids:['S'],requires_hardware:false,assumptions:['Only after the user chooses this option'],requirements:['Detailed requirement'],implementation_steps:['Create prototype','Measure all failures'],validation_plan:{method:'Same conditions',condition_controls:['Do not remove this condition'],evaluation_protocol:{denominator:'All assigned attempts',failures:'Include interruptions'}}}],assumptions:['Important product condition'],evidence_refs:[{source_id:'S',quote:'Short quoted evidence',sha256:'a'.repeat(64),origin:{source_url:'https://example.org/original'}}],decision_notes:[{text:'Key decision',basis:'ai_interpretation',source_ids:['S']}],validation_findings:['Internal review observation']};
 const data={export:{session_id:'session',requests:[],turns:[{state:{turn_id:'current',input:{question:'Plan this product',model_scope:[]},status:'completed',valid:true,latest_result:original}}]},report_plan_turn_id:'current',report_plan:{title:'',summary:[],sources:[],sections:[{title:'Research count',audience:'appendix',blocks:[{type:'paragraph',text:'Research-only count'}]}],appendix:{sources:[{source_id:'S',text:longBody,sha256:'b'.repeat(64),origin:{source_url:'https://example.org/full'}}],coverage:{selected:1}},diagnostics:{binding:{turn_id:'current'},investigation_events:[{kind:'internal'}]}}};
 const before=JSON.stringify(data);
 api.render(data);
 const body=node('#result-body').innerHTML,appendix=node('#registered-sources').innerHTML;
 assert.ok(body.includes('Important remaining issue'));
 assert.ok(body.includes('Current feature'));
 assert.ok(body.includes('Proposed planning'));
 assert.ok(body.includes('Only after the user chooses this option'));
 assert.ok(body.includes('Important product condition'));
 assert.ok(body.includes('class="planner-detail"'));
 const core=body.replace(/<details class="planner-detail">[^]*?<\/details>/g,'');
 assert.ok(core.includes('Detailed requirement'),'Requirements may carry material applicability conditions and stay in the core');
 assert.ok(core.includes('Create prototype'),'The first stored step is the next action, without re-ranking candidates');
 assert.ok(!core.includes('Measure all failures'),'Full implementation history stays in proposal detail');
 assert.ok(!core.includes('All assigned attempts'),'Full evaluation protocol stays in optional detail, not the default print');
 assert.ok(body.includes('All assigned attempts'));
 assert.ok(!body.includes('Initial inconvenience'),'Detailed initial pain stays in the optional research section');
 assert.ok(!body.includes('Research-only count'));
 assert.ok(!body.includes('Internal review observation'));
 assert.ok(!body.includes('FULL ORIGINAL TAIL'));
 assert.ok(!body.includes('"binding"'));
 assert.ok(node('#appendix-analysis').innerHTML.includes('Research-only count'));
 assert.ok(appendix.includes('FULL ORIGINAL TAIL &lt;img'));
 assert.ok(!appendix.includes('<img'));
 assert.ok(node('#diagnostic-data').textContent.includes('"binding"'));
 assert.ok(!node('#report-summary').innerHTML.includes('Key decision'));
 assert.ok(node('#report-summary').innerHTML.includes('Proposed planning'));
 assert.ok(node('#appendix-analysis').innerHTML.includes('Key decision'));
 assert.ok(node('#appendix-analysis').innerHTML.includes('인공지능 해석'));
 assert.ok(node('#appendix-analysis').innerHTML.includes('#evidence-1'),'Moved decision notes retain their source links');
 assert.equal(node('.report-opening').hidden,true,'Do not repeat the same proposal text on a second report cover');
 assert.ok(node('#report-summary').innerHTML.includes('#evidence-1'));
 assert.equal(JSON.stringify(data),before,'Rendering must not mutate stored results, refs or sources');
 const normalized=Adapter.normalize(data);
 assert.equal(normalized.appendix.sources[0].text,longBody);
 assert.equal(JSON.stringify(normalized.diagnostics),JSON.stringify(data.report_plan.diagnostics));
 // Equal wording in one candidate must not erase a condition applying to all candidates.
 const scoped=JSON.parse(JSON.stringify(data));
 scoped.export.turns[0].state.latest_result.concepts[0].assumptions=['Global dimension prerequisite'];
 scoped.export.turns[0].state.latest_result.concepts.push({...scoped.export.turns[0].state.latest_result.concepts[0],id:'c2',text:'Second candidate',assumptions:[]});
 scoped.export.turns[0].state.latest_result.assumptions=['Global dimension prerequisite'];
 const scopedBody=api.renderBusiness(Adapter.normalize(scoped));
 assert.ok(scopedBody.includes('전체 기획의 적용 조건'));
 assert.equal(scopedBody.split('Global dimension prerequisite').length-1,2,'Global and local scope remain explicit');
 assert.equal(normalized.evidence[0].body,'Short quoted evidence','Registered body must not replace the quotation/keyword denominator');
 // Additive presentation matches the planner web's saved wording, without
 // replacing the ProductResult or hiding its full operating mechanism.
 const shared=JSON.parse(JSON.stringify(data));
 const mechanism='The user selects a mode. The display then asks for a confirmation. No action is applied until confirmation; retain this final mechanism condition.';
 shared.export.turns[0].state.latest_result.concepts[0].text=mechanism;
 shared.export.turns[0].state.latest_result.concepts[0].requirements=['First saved requirement','Second requirement stays in default print'];
 shared.export.turns[0].state.latest_result.concepts[0].assumptions=['First applicability condition','Second applicability condition'];
 shared.export.turns[0].state.latest_result.concepts.push({id:'c2',text:'A different stored mechanism.',source_ids:['S'],requires_hardware:true,assumptions:[],requirements:[],implementation_steps:['Build second prototype']});
 shared.report_plan.presentation={title:'Shared report title',summary:['Shared concise overview'],concepts:{c:{title:'Shared concise proposal',summary:'Shared concise overview',background:['Shared linked background'],next_action:'Create prototype',follow_up:'Continue with the saved proposal and preserve its conditions.'},c2:{title:'Second proposal',summary:'Second saved summary'},not_current:{title:'Unrelated title must not appear'}},scope:{reviews:0,facts:2,other:3,models:1,as_of:'2026-10-18'}};
 const sharedBefore=JSON.stringify(shared);
 api.render(shared);
 const sharedBody=node('#result-body').innerHTML,sharedCore=sharedBody.replace(/<details class="planner-detail">[^]*?<\/details>/g,'');
 assert.equal(node('#report-title').textContent,'Shared report title');
 assert.ok(sharedCore.includes('Shared concise proposal'));
 assert.ok(sharedCore.includes('Shared concise overview'));
 assert.ok(sharedCore.includes(mechanism),'The entire stored mechanism is visible/default-printable, including its final condition');
 assert.ok(sharedCore.includes('<details class="planner-description" open>'));
 assert.ok(!sharedCore.includes('Unrelated title must not appear'));
 assert.ok(sharedCore.includes('Shared linked background'));
 assert.ok(sharedCore.includes('First saved requirement'));
 assert.ok(sharedBody.includes('class="planner-condition-detail"'));
 assert.ok(sharedCore.includes('Second requirement stays in default print'));
 assert.ok(sharedCore.includes('Second applicability condition'));
 assert.ok(sharedCore.includes('planner-comparison'));
 assert.ok(sharedCore.includes('href="#proposal-1"'));
 assert.ok(sharedCore.includes('href="#proposal-2"'));
 assert.ok(sharedCore.includes('Build second prototype'),'Absent presentation next_action falls back only to the saved first step');
 assert.ok(sharedBody.includes('Continue with the saved proposal and preserve its conditions.'));
 assert.ok(node('#report-scope').textContent.includes('후기 0건'),'Observed zero counts remain visible');
 assert.ok(node('#report-scope').textContent.includes('제품 자료 2건'));
 assert.ok(node('#report-scope').textContent.includes('기타 3건'));
 assert.ok(node('#report-scope').textContent.includes('모델 1개'));
 assert.ok(node('#report-scope').textContent.includes('2026-10-18'));
 assert.equal(node('.report-opening').hidden,true,'Saved aggregate summaries do not create a duplicate cover for the same proposals');
 assert.equal(JSON.stringify(shared),sharedBefore);
 const normalizedShared=Adapter.normalize(shared);
 assert.equal(normalizedShared.concepts[0].body,mechanism);
 assert.equal(normalizedShared.evidence[0].body,'Short quoted evidence');
 assert.equal(normalizedShared.appendix.sources[0].text,longBody);
 assert.equal(normalizedShared.presentation.concepts.not_current,undefined);
 // Canonical editable drafts and choice reasons survive report normalization,
 // remain bound to this result and are safe text, not generated HTML.
 const authored=JSON.parse(JSON.stringify(shared));
 authored.export.turns[0].state.latest_result.planning_decision={summary:'Choose the direct customer task first',selected_concept_ids:['c'],comparisons:[{concept_id:'c',reason:'Direct problem fit',tradeoff:'Internal owner still needed'},{concept_id:'c2',reason:'Different situation',tradeoff:'Extra hardware'}]};
 authored.export.turns[0].state.latest_result.concepts[0].work_draft={title:'Working draft <script>no</script>',columns:['Stage','Action'],rows:[['Start','<img src=x onerror="bad">'],['Then','Actual editable action']]};
 const authoredBefore=JSON.stringify(authored);
 api.render(authored);
 const authoredBody=node('#result-body').innerHTML;
 for(const text of ['Choose the direct customer task first','Direct problem fit','Internal owner still needed','착수 제안','Working draft &lt;script&gt;','Actual editable action'])assert.ok(authoredBody.includes(text),text);
 assert.ok(authoredBody.includes('&lt;img'));assert.ok(!authoredBody.includes('<img'));assert.ok(!authoredBody.includes('<script>'));
 assert.equal(JSON.stringify(authored),authoredBefore);
 const single=JSON.parse(JSON.stringify(authored));single.export.turns[0].state.latest_result.concepts=single.export.turns[0].state.latest_result.concepts.slice(0,1);single.export.turns[0].state.latest_result.planning_decision.comparisons=single.export.turns[0].state.latest_result.planning_decision.comparisons.slice(0,1);
 api.render(single);assert.ok(node('#result-body').innerHTML.includes('Direct problem fit'));assert.ok(node('#result-body').innerHTML.includes('Internal owner still needed'));
 const authoredNormalized=Adapter.normalize(authored);
 assert.equal(JSON.stringify(authoredNormalized.planningDecision),JSON.stringify(authored.export.turns[0].state.latest_result.planning_decision));
 assert.equal(JSON.stringify(authoredNormalized.concepts[0].workDraft),JSON.stringify(authored.export.turns[0].state.latest_result.concepts[0].work_draft));
 for(const mutate of [r=>r.planning_decision.selected_concept_ids=['not-current'],r=>r.planning_decision.comparisons[0].concept_id='not-current',r=>r.planning_decision.comparisons[0].reason={},r=>r.concepts[0].work_draft.rows=[['wrong-width']],r=>r.concepts[0].work_draft.columns=[{}]]){
   const invalid=JSON.parse(JSON.stringify(authored));mutate(invalid.export.turns[0].state.latest_result);assert.throws(()=>Adapter.normalize(invalid),Adapter.ReportDataError);
 }
 const uniform=JSON.parse(JSON.stringify(shared));uniform.export.turns[0].state.latest_result.concepts.forEach(c=>c.requires_hardware=false);
 assert.ok(!api.renderBusiness(Adapter.normalize(uniform)).includes('<th>추가 하드웨어</th>'),'Uniform hardware data does not create an unhelpful comparison column');
 const escaped=JSON.parse(JSON.stringify(shared));escaped.report_plan.presentation.concepts.c.title='<img src=x onerror="bad">';
 api.render(escaped);assert.ok(node('#result-body').innerHTML.includes('&lt;img'));assert.ok(!node('#result-body').innerHTML.includes('<img'));
 for(const mutate of [p=>p.summary='not an array',p=>p.concepts=[],p=>p.concepts.c.background='not an array',p=>p.concepts.c.next_action={},p=>p.scope.reviews=-1,p=>p.scope.facts=0.5,p=>p.scope.other=Infinity,p=>p.scope.models=Number.MAX_SAFE_INTEGER+1,p=>p.scope.as_of={}]){
   const bad=JSON.parse(JSON.stringify(shared));mutate(bad.report_plan.presentation);assert.throws(()=>Adapter.normalize(bad),Adapter.ReportDataError);
 }
 const mismatched=JSON.parse(JSON.stringify(shared));mismatched.report_plan_turn_id='not-current';
 const isolated=Adapter.normalize(mismatched);assert.equal(isolated.presentation,undefined);assert.equal(isolated.concepts[0].body,mechanism);
 // Evidence clicks open their actual ancestor details and stay in this report
 // instead of navigating the parent iframe/document. This is a pure DOM stub.
 const sourceDetails={tagName:'DETAILS',open:false,parentElement:null};let scrolls=0,prevented=0,rerenders=0,click;
 const destination={parentElement:sourceDetails,scrollIntoView:()=>scrolls++};
 const cite={getAttribute:()=>'#evidence-1'};
 const citationCode=scripts[1].slice(scripts[1].indexOf("document.addEventListener('click',event=>{const anchor="),scripts[1].indexOf("$('#evidence-filters').addEventListener"));
 new Function('document','$','$$','setTimeout','renderEvidence','let selectedFilter="all";'+citationCode)({addEventListener:(_,fn)=>click=fn,getElementById:id=>id==='evidence-1'?destination:null},node,()=>[],fn=>fn(),()=>rerenders++);
 click({preventDefault:()=>prevented++,target:{closest:selector=>selector==='a[href^="#"]'||selector==='.evidence-refs a'?cite:null}});
 assert.equal(node('#report-appendix').open,true);assert.equal(sourceDetails.open,true);assert.equal(scrolls,1);assert.equal(prevented,1);assert.equal(rerenders,1);
 assert.ok(html.includes('id="report-appendix"'));
 assert.ok(html.includes('id="include-appendix"'));
 assert.ok(!html.includes('id="include-appendix" checked'));
 assert.ok(html.includes("const all=$('#include-appendix').checked"));
 assert.ok(html.includes('body:not(.print-with-appendix) .report-appendix'));
 assert.ok(html.includes('body:not(.print-with-appendix) .planner-detail'));
 assert.ok(!html.includes("printDetails=$$('#paper details:not([open])')"),'Printing does not force every appendix open by default');
 const callbacks={},toggles=[],coreDetails=[{open:false},{open:false}],appendixDetails=[{open:false},{open:false}];
 const printCode=scripts[1].slice(scripts[1].indexOf('let printDetails=[];'),scripts[1].indexOf("$('#show-sample').addEventListener"));
 new Function('window','$','$$','document',printCode)({addEventListener:(name,fn)=>callbacks[name]=fn},node,selector=>selector.includes('planner-description')?coreDetails:appendixDetails,{body:{classList:{toggle:(name,value)=>toggles.push([name,value]),remove(){}}}});
 callbacks.beforeprint();assert.ok(coreDetails.every(d=>d.open),'Core description and conditions remain in default print');assert.ok(appendixDetails.every(d=>!d.open));assert.deepEqual(toggles.at(-1),['print-with-appendix',false]);callbacks.afterprint();assert.ok(coreDetails.every(d=>!d.open));
 node('#include-appendix').checked=true;callbacks.beforeprint();assert.ok([...coreDetails,...appendixDetails].every(d=>d.open));assert.deepEqual(toggles.at(-1),['print-with-appendix',true]);callbacks.afterprint();assert.ok([...coreDetails,...appendixDetails].every(d=>!d.open));
 // Other-turn plans remain rejected with the same original adapter contract.
 const other=JSON.parse(JSON.stringify(data));other.report_plan_turn_id='another';
 const rejected=Adapter.normalize(other);
 assert.equal(rejected.appendix,undefined);
 assert.ok(rejected.warnings.some(w=>w.includes('다른 실행')));
 const fs=require('node:fs');
 const {plannerReport}=await import(pathToFileURL(path.resolve('web/prototypes/visual-viewer/app/scripts/planner-report.mjs')));
 const vendor='web/prototypes/visual-viewer/app/vendor/jinha-report/';
 const once=(value,find,to)=>{assert.equal(value.split(find).length-1,1,'Changed vendor patch marker');return value.replace(find,()=>to);};
 assert.throws(()=>plannerReport({code:{adapter:fs.readFileSync(vendor+'report-data-adapter.js','utf8'),app:fs.readFileSync(vendor+'report-app.js','utf8').replace('function cards(','function changedCards(')},html:fs.readFileSync(vendor+'index.html','utf8'),css:'',once}),/changed function cards/);
 console.log('Planner report projection, full-source preservation, escaping, binding and default/opt-in print passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([shutil.which('node'), '-e', script], cwd=ROOT,
                                capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
