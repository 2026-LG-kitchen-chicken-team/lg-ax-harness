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
 assert.equal(node('#report-summary').innerHTML.split('Key decision').length-1,1);
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
 assert.ok(scopedBody.includes('적용 전에 확인할 조건'));
 assert.equal(scopedBody.split('Global dimension prerequisite').length-1,2,'Global and local scope remain explicit');
 assert.equal(normalized.evidence[0].body,'Short quoted evidence','Registered body must not replace the quotation/keyword denominator');
 assert.ok(html.includes('id="report-appendix"'));
 assert.ok(html.includes('id="include-appendix"'));
 assert.ok(!html.includes('id="include-appendix" checked'));
 assert.ok(html.includes("const all=$('#include-appendix').checked"));
 assert.ok(html.includes('body:not(.print-with-appendix) .report-appendix'));
 assert.ok(html.includes('body:not(.print-with-appendix) .planner-detail'));
 assert.ok(!html.includes("printDetails=$$('#paper details:not([open])')"),'Printing does not force every appendix open by default');
 const callbacks={},toggles=[],details=[{open:false},{open:false}];
 const printCode=scripts[1].slice(scripts[1].indexOf('let printDetails=[];'),scripts[1].indexOf("$('#show-sample').addEventListener"));
 new Function('window','$','$$','document',printCode)({addEventListener:(name,fn)=>callbacks[name]=fn},node,()=>details,{body:{classList:{toggle:(name,value)=>toggles.push([name,value]),remove(){}}}});
 callbacks.beforeprint();assert.ok(details.every(d=>!d.open));assert.deepEqual(toggles.at(-1),['print-with-appendix',false]);callbacks.afterprint();
 node('#include-appendix').checked=true;callbacks.beforeprint();assert.ok(details.every(d=>d.open));assert.deepEqual(toggles.at(-1),['print-with-appendix',true]);callbacks.afterprint();assert.ok(details.every(d=>!d.open));
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
