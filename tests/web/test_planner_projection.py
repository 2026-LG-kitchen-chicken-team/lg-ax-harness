"""Exercise the actual display projection. No browser, network or model runs.

Large source collections stay in the saved payload but do not enlarge the default
planning body. Conditions and unsuccessful result states must survive selection.
"""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PlannerProjectionTests(unittest.TestCase):
    def run_js(self, script, payload=None):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        loader = r'''
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {plannerFirst}=require(path.join(process.argv[1],'lib/planner.js'));
const {pageTarget,fragmentId}=require(path.join(process.argv[1],'lib/viewState.js'));
const {pruneForPlanning}=require(path.join(process.argv[1],'lib/prune.js'));
const {mergeEvidencePages}=require(path.join(process.argv[1],'lib/merge.js'));
'''
        app=ROOT/'web/prototypes/visual-viewer/app'
        with tempfile.TemporaryDirectory(prefix='planner-projection-') as compiled:
            emitted=subprocess.run([node,str(app/'node_modules/typescript/bin/tsc'),
                '--target','es2022','--module','commonjs','--skipLibCheck',
                '--rootDir',str(app/'src'),'--outDir',compiled,*[str(app/'src/lib'/name) for name in ('planner.ts','viewState.ts','prune.ts','merge.ts')]],
                cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=30)
            self.assertEqual(emitted.returncode,0,emitted.stdout+emitted.stderr)
            done = subprocess.run([node, '-e', loader+script,compiled], cwd=ROOT, capture_output=True,
                                  input=json.dumps(payload,ensure_ascii=False) if payload is not None else None,
                                  text=True, encoding='utf-8', timeout=30)
        self.assertEqual(done.returncode, 0, done.stdout+done.stderr)

    def test_large_evidence_is_accessible_without_becoming_default_body(self):
        self.run_js(r'''
const raw='SOURCE_BODY_'.repeat(3000),secret='DIAGNOSTIC_RAW_JSON';
const sources=Array.from({length:240},(_,i)=>({source_id:'s'+i,text:raw+i}));
const view={kind:'lgax-view',schema:1,focus:'story',report:{export:{sources}},pages:[
 {id:'story',title:'Saved work',blocks:[{type:'hero',title:'Request'},
  {type:'story',key:'problem',blocks:[{type:'text',text:'Detailed comparison'}]},
  {type:'story',key:'flow',blocks:[{type:'flow',note:'Internal field explanation',nodes:[{text:'Only if the door is closed',column:'remaining'}]}]},
  {type:'story',key:'solution',blocks:[{type:'solutions',items:[{text:'Proposal under a recorded condition',assumptions:['Requires confirmed model dimensions'],requirements:['Entire requirement'],steps:['First step','Second step']}]}]},
  {type:'story',key:'trust',blocks:[{type:'tiles',items:[{value:secret}]},{type:'expander',title:'결과 가정',blocks:[{type:'text',text:'Critical condition'}]}]}]},
 {id:'evidence',title:'Sources',blocks:[{type:'text',text:raw}]},
 {id:'export',title:'Diagnostics',blocks:[{type:'code',text:secret}]}]};
const before=JSON.stringify(view),shown=plannerFirst(view),core=shown.pages.find(p=>p.id==='story');
assert.equal(JSON.stringify(view),before,'Do not mutate the export or input view');
assert.equal(shown.report,view.report,'Same complete report/export binding');
assert.equal(shown.report.export.sources.length,240);
assert.ok(shown.report.export.sources.every((s,i)=>s.text===raw+i));
const text=JSON.stringify(core);
assert.ok(!text.includes(raw));assert.ok(!text.includes(secret));
assert.ok(text.includes('Only if the door is closed'));
assert.ok(text.includes('Requires confirmed model dimensions'));
assert.ok(text.includes('Critical condition'));
assert.ok(shown.pages.find(p=>p.id==='planning-detail').blocks.some(b=>b.key==='problem'));
assert.equal(shown.pages.find(p=>p.id==='evidence').audience,'evidence');
assert.equal(shown.pages.find(p=>p.id==='export').audience,'diagnostic');
assert.equal(shown.pages.find(p=>p.id==='review-diagnostics').audience,'diagnostic');
''')

    def test_failed_or_pending_work_is_not_hidden_by_success_summary(self):
        self.run_js(r'''
for(const status of ['held','cancelled','invalid','needs_input']){
 const warning={type:'callout',tone:'warning',text:'Current request '+status+'; do not use the previous result'};
 const source={kind:'lgax-view',schema:1,pages:[{id:'story',title:'Work',blocks:[warning]},{id:'overview',title:'Request',blocks:[warning]}]};
 const shown=plannerFirst(source);
 assert.deepEqual(shown.pages.find(p=>p.id==='story').blocks[0],warning);
 assert.ok(shown.pages.find(p=>p.id==='overview').blocks.includes(warning));
}
const pending={kind:'lgax-view',schema:1,pages:[{id:'overview',title:'Waiting',blocks:[{type:'text',text:'Need exact model'}]}]};
assert.deepEqual(plannerFirst(pending).pages[0].blocks,pending.pages[0].blocks);
assert.equal(plannerFirst(pending).pages[0].audience,'planning');
assert.equal(plannerFirst(null),null);
''')

    def test_projection_does_not_route_by_product_or_question(self):
        self.run_js(r'''
for(const request of ['냉장고','전자레인지','식기세척기','arbitrary new product; custom scope']){
 const result={kind:'lgax-view',schema:1,pages:[{id:'story',title:request,blocks:[{type:'hero',title:request},{type:'story',key:'solution',blocks:[{type:'solutions',items:[{text:request+' original proposal'}]}]}]}]};
 const shown=plannerFirst(result);assert.equal(shown.pages[0].blocks[0].title,'상품기획안');
 assert.ok(JSON.stringify(shown).includes(request+' original proposal'));
}
''')

    def test_task_title_and_proposals_precede_process_without_mutating_saved_data(self):
        self.run_js(r'''
const view={kind:'lgax-view',schema:1,context:{file:{name:'internal.json',size:'200KB'},status:[{text:'기획 초안 완료'},{text:'유효'},{text:'의미 검토 전 · 인수 전'}]},pages:[
 {id:'story',title:'한눈에 보기',blocks:[{type:'hero',title:'PRIVATE TEST PROMPT /private/evaluation',chips:[{text:'기획 초안 완료'},{text:'유효'}],stats:[{value:99}]},
 {type:'callout',tone:'warning',text:'This result is not current'},
 {type:'story',key:'flow',blocks:[{type:'flow',text:'Recorded comparison'}]},
 {type:'story',key:'solution',blocks:[{type:'solutions',items:[{title:'Explicit stored heading',text:'Same saved proposal.',assumptions:['Critical condition']}]}]}]},
 {id:'overview',title:'An arbitrary product planning task',blocks:[{type:'text',text:'PRIVATE TEST PROMPT /private/evaluation'}]}]};
const original=JSON.stringify(view),shown=plannerFirst(view),main=shown.pages[0].blocks;
assert.equal(main[0].title,'An arbitrary product planning task');
assert.ok(!JSON.stringify(main).includes('PRIVATE TEST PROMPT'));
assert.ok(!JSON.stringify(main).includes('internal.json'));
assert.ok(!JSON.stringify(shown.context).includes('의미 검토 전'));
assert.ok(main.some(b=>b.text==='This result is not current'));
assert.ok(main.findIndex(b=>b.key==='solution')<main.findIndex(b=>b.type==='expander'));
assert.ok(JSON.stringify(main).includes('Explicit stored heading'));
assert.ok(JSON.stringify(main).includes('Critical condition'));
assert.ok(JSON.stringify(shown.pages.find(p=>p.id==='overview')).includes('PRIVATE TEST PROMPT'));
assert.equal(JSON.stringify(view),original);
''')

    def test_background_uses_only_recorded_remaining_problem_links(self):
        self.run_js(r'''
const input={kind:'lgax-view',schema:1,pages:[{id:'story',title:'Work',blocks:[
 {type:'story',key:'flow',blocks:[{type:'flow',nodes:[{id:'r1',column:'remaining',text:'Recorded linked background.'},{id:'r2',column:'remaining',text:'Unrelated background.'},{id:'f1',column:'feature',text:'Unlinked feature.'}]}]},
 {type:'story',key:'solution',blocks:[{type:'solutions',items:[{id:'c1',text:'Stored proposal.',links:[{text:'r1'}]},{id:'c2',text:'No recorded link.',links:[]}]}]}]}]};
const projected=plannerFirst(input),items=projected.pages[0].blocks.find(b=>b.key==='solution').blocks[0].items;
assert.deepEqual(items[0].background,['Recorded linked background.']);
assert.deepEqual(items[1].background,[]);
assert.equal(input.pages[0].blocks[1].blocks[0].items[0].background,undefined);
''')

    def test_appendix_navigation_resolves_the_displayed_pages(self):
        self.run_js(r'''
const shown=plannerFirst({kind:'lgax-view',schema:1,pages:[{id:'story',title:'Work',blocks:[
 {type:'story',key:'problem',blocks:[]},{type:'story',key:'trust',blocks:[]}]}]});
for(const fragment of ['#planning-detail','#story','#review-diagnostics','#planning-detail']){
 const id=fragmentId(fragment);
 assert.equal(pageTarget(shown,id,id),id,'Direct links and back/forward entries use the displayed page list');
}
assert.equal(pageTarget(shown,'missing','missing'),'story');
''')

    def test_actual_builder_preserves_conditions_for_three_product_families(self):
        from test_visual_viewer import Gen, FAMILIES, build_view, read_view
        for family, _label, model, review, fact in FAMILIES:
            with self.subTest(family=family), tempfile.TemporaryDirectory(prefix='planner-builder-') as folder:
                work=Path(folder)
                g=Gen(work/'workspace','data/business/lg-kitchen-v4')
                try:
                    bundle=g.bundle('[합성 시험 자료] 적용 조건이 있는 기획을 보여줘.',model_id=model)
                    value=g.author(bundle['candidate_template'],bundle['turn']['input']['model_scope'][0],review,fact)
                    concept=value['result']['concepts'][0]
                    concept['assumptions']=['해당 모델의 치수를 확인한 뒤에만 적용']
                    concept['requirements']=['제품이 정지한 상태에서만 안내를 제공한다']
                    value['result']['assumptions']=['전체 기획은 설치 환경을 확인한 뒤 적용']
                    saved=g.conv.save_and_export(value)
                    self.assertTrue(saved['save']['accepted'],saved['save'])
                    export=g.work/saved['export']['path']
                    frozen=export.read_bytes()
                    build_view.generate(export,None,'auto',out_dir=work/'view')
                    view=read_view(work/'view')
                    self.run_js(r'''
const original=JSON.parse(fs.readFileSync(0,'utf8')),before=JSON.stringify(original);
const shown=plannerFirst(pruneForPlanning(mergeEvidencePages(original)));
const core=JSON.stringify(shown.pages.find(p=>p.id==='story'));
assert.ok(core.includes('해당 모델의 치수를 확인한 뒤에만 적용'));
assert.ok(core.includes('제품이 정지한 상태에서만 안내를 제공한다'));
assert.ok(core.includes('전체 기획은 설치 환경을 확인한 뒤 적용'));
assert.equal(JSON.stringify(original),before);
assert.deepEqual(shown.report,original.report);
''',view)
                    self.assertEqual(export.read_bytes(),frozen)
                finally:
                    g.close()


if __name__ == '__main__':
    unittest.main()
