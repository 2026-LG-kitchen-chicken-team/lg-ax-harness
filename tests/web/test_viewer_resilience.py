"""Actual TS loader/hook and static React contracts; no browser or model is launched."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "web/prototypes/visual-viewer/app"


class ViewerResilienceTests(unittest.TestCase):
    def test_saved_view_loading_recovery_and_report_snapshot(self):
        node = shutil.which("node")
        self.assertIsNotNone(node)
        script = r'''
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const dir = process.argv[1];
fs.writeFileSync(path.join(dir, 'package.json'), '{"type":"module"}');
function walk(folder) { for (const e of fs.readdirSync(folder, {withFileTypes:true})) {
 const file = path.join(folder,e.name);
 if(e.isDirectory()) walk(file);
 else if(file.endsWith('.js')) {
  let code = fs.readFileSync(file,'utf8').replace(/from (['"])(\.[^'"]+)\1/g, (all,q,p) => /\.[a-z]+$/.test(p) ? all : `from ${q}${p}.js${q}`);
  if(['useView.js','report.js'].includes(e.name)) code = code.replace(/from ['"]react['"]/, `from '${e.name === 'useView.js' ? './' : '../lib/'}test-hooks.js'`);
  code = code.replace("import template from 'virtual:jinha-report';", `const template = '<html><script id="embedded-report" type="application/json">null</script></html>';`);
  fs.writeFileSync(file,code);
 }
}}
walk(dir);
fs.writeFileSync(path.join(dir,'lib/test-hooks.js'), `
export const useState = initial => {const h=globalThis.hooks,i=h.i++;if(!(i in h.slots))h.slots[i]=typeof initial==='function'?initial():initial;return[h.slots[i],v=>{h.slots[i]=typeof v==='function'?v(h.slots[i]):v}];};
export const useRef = value => {const h=globalThis.hooks,i=h.i++;return h.slots[i]??=( {current:value} );};
export const useCallback = value => value;
export const useMemo = (fn,deps) => {const h=globalThis.hooks,i=h.i++,old=h.slots[i];if(!old||deps.some((v,k)=>v!==old.deps[k]))h.slots[i]={deps,value:fn()};return h.slots[i].value;};
export const useEffect = (fn,deps) => {const h=globalThis.hooks,i=h.i++,old=h.slots[i];if(!old||deps.some((v,k)=>v!==old[k])){h.slots[i]=deps;h.pending.push(()=>{h.clean[i]?.();h.clean[i]=fn()});}};
export const useLayoutEffect = useEffect;
`);
const freshHooks = () => globalThis.hooks={i:0,slots:[],pending:[],clean:[]};
const render = fn => {hooks.i=0;const tree=fn();for(const effect of hooks.pending.splice(0))effect();return tree};
const unmount = () => {for(const clean of hooks.clean)clean?.()};
const view = text => ({kind:'lgax-view',schema:1,generated_at:'2026-10-16T12:00:00',focus:'story',pages:[{id:'story',title:'합성 시험',blocks:[{type:'text',text}]}]});
const a=view('가'),b=view('나');
(async()=>{
const state = await import(pathToFileURL(path.join(dir,'lib/viewState.js')));
assert.notEqual(state.viewIdentity(a),state.viewIdentity(b));
assert.equal(JSON.stringify(a).length,JSON.stringify(b).length);
for(const invalid of [{...a,pages:[]},{...a,generated_at:123},{...a,focus:'missing'},{...a,pages:[...a.pages,...a.pages]}, {...a,pages:[{id:'x',title:'x',blocks:[null]}]}, {...a,pages:[{id:'x',title:'x',blocks:[{type:'list',items:{}}]}]}, {...a,pages:[{id:'x',title:'x',blocks:[{type:'table',columns:[null]}]}]}]) assert.equal(state.isLgaxView(invalid),false);
assert.equal(state.fragmentId('#%'), '');
assert.equal(state.fragmentId('#%EC%9B%90%EB%AC%B8'), '원문');
assert.equal(state.pageTarget(a,'missing','missing'),'story');
assert.equal(state.pageTarget({...a,pages:[{id:'evidence',title:'합성 단독 화면',blocks:[]}]},'evidence','dashboard'),'evidence');
assert.equal(state.pageTarget(null,'evidence','dashboard'),null);
const full=view('등록 원문 '+ '가'.repeat(1024*1024) +' 전문 끝');
assert.equal(state.isLgaxView(full),true);assert.ok(state.viewIdentity(full).endsWith(' 전문 끝"}]}]}'));
let current=state.initialViewState(null), pending=[], timers=[], cancellations=0, changes=[];
const loader=state.createViewLoader({initial:current,update:s=>current=s,transport:(done,fail)=>{pending.push({done,fail});return()=>cancellations++},schedule:f=>{timers.push(f);return f},clear:()=>{},changed:(manual,changed)=>changes.push({manual,changed})});
assert.equal(loader.load(),true);assert.equal(current.phase,'loading');assert.equal(loader.load(true),false);
pending[0].done(undefined);assert.equal(current.phase,'waiting');
loader.load();pending[1].done(a);assert.equal(current.phase,'ready');assert.equal(current.view,a);
loader.load();pending[2].done(b);assert.equal(current.view,b);
loader.load();pending[3].fail();assert.equal(current.phase,'error');assert.equal(current.view,b);
loader.load(true);const late=pending[4];timers.at(-1)();assert.equal(current.phase,'error');
loader.load(true);late.done(a);assert.equal(current.busy,true);pending[5].done(b);assert.equal(current.phase,'ready');
assert.deepEqual(changes.at(-1),{manual:true,changed:false});
loader.load();loader.replace(a);pending[6].done(b);assert.equal(current.view,a);
loader.load();const before=current;loader.dispose();pending[7].done(b);assert.equal(current,before);assert.equal(loader.load(),false);assert.ok(cancellations>=8);

// Run the actual hook and classic-script transport with fake DOM/time/file I/O, without executing a browser.
let scripts=[], timeouts=new Map(), intervals=new Map(), tick=0, readers=[], toasts=[];
globalThis.location={protocol:'file:',hostname:''};
globalThis.window={LGAX_VIEW:a,setTimeout:(f,ms)=>{timeouts.set(++tick,{f,ms});return tick},clearTimeout:id=>timeouts.delete(id),setInterval:f=>{intervals.set(++tick,f);return tick},clearInterval:id=>intervals.delete(id)};
globalThis.document={currentScript:null,createElement:()=>({remove(){this.removed=true}}),head:{appendChild:s=>scripts.push(s)}};
globalThis.FileReader=class {constructor(){readers.push(this)}readAsText(){}abort(){this.aborted=true}};
const {useView}=await import(pathToFileURL(path.join(dir,'lib/useView.js')));
freshHooks(); const hook=()=>useView(msg=>toasts.push(msg));
let actual=render(hook);actual=render(hook);assert.equal(actual.busy,true);assert.equal(scripts.length,1);
actual.reload();assert.equal(scripts.length,1);
const deliver=(script,value)=>{document.currentScript=script;window.LGAX_VIEW=value;document.currentScript=null;script.onload?.()};
deliver(scripts[0],b);actual=render(hook);assert.equal(actual.view,b);assert.equal(actual.phase,'ready');
actual.reload();const old=scripts.at(-1), oldLoad=old.onload;
[...timeouts.values()].find(t=>t.ms===8000).f();actual=render(hook);assert.equal(actual.phase,'error');assert.equal(actual.view,b);
actual.reload();const newer=scripts.at(-1);document.currentScript=old;window.LGAX_VIEW=a;document.currentScript=null;oldLoad();assert.equal(render(hook).busy,true);
deliver(newer,b);actual=render(hook);assert.equal(actual.phase,'ready');
actual.openFile({name:'private-path-do-not-show.json'});readers.at(-1).result='{ broken';readers.at(-1).onload();assert.equal(render(hook).view,b);assert.ok(!toasts.at(-1).includes('private-path'));
actual.openFile({});readers.at(-1).result=JSON.stringify({...a,pages:[]});readers.at(-1).onload();assert.equal(render(hook).view,b);
actual.openFile({});const first=readers.at(-1);actual.openFile({});first.result=JSON.stringify(a);first.onload();assert.equal(render(hook).view,b);
readers.at(-1).result=JSON.stringify(a);readers.at(-1).onload();actual=render(hook);actual=render(hook);assert.equal(actual.fromFile,true);assert.equal(intervals.size,0);assert.equal(actual.view.pages[0].blocks[0].text,'가');
actual.reload();actual=render(hook);actual=render(hook);assert.equal(actual.fromFile,false);assert.equal(intervals.size,1);
const after=scripts.at(-1), afterLoad=after.onload;unmount();assert.equal(intervals.size,0);afterLoad();assert.equal(after.removed,true);

// A report is a copied single-turn snapshot; later results cannot mutate or silently replace it.
const withReport={...a,report:{turn_id:'T1',export:{turns:[{state:{turn_id:'T1'},result:{text:'원문 </script>'}}]},plan:{sections:[]}}};
const snapshot=state.reportSnapshot(withReport);assert.ok(snapshot);
const rebuilt=state.reportSnapshot({...withReport,generated_at:'2026-10-16T12:00:01'});assert.notEqual(rebuilt.identity,snapshot.identity);assert.equal(rebuilt.sourceIdentity,snapshot.sourceIdentity);
withReport.report.export.turns[0].result.text='changed';assert.equal(snapshot.source.export.turns[0].result.text,'원문 </script>');
assert.equal(state.reportSnapshot({...a,report:{...withReport.report,turn_id:'T2'}}),null);
assert.equal(state.reportSnapshot({...a,report:{...withReport.report,export:{turns:[]}}}),null);
const {ReadNotice,Empty}=await import(pathToFileURL(path.join(dir,'components/shell.js')));
const waiting=renderToStaticMarkup(Empty({phase:'waiting',busy:false,reload(){}}));
const failed=renderToStaticMarkup(Empty({phase:'error',busy:false,reload(){}}));
assert.ok(waiting.includes('첫 결과를 기다리고'));assert.ok(failed.includes('다시 불러오기'));assert.ok(!failed.includes('JSON'));
assert.ok(renderToStaticMarkup(ReadNotice({phase:'error',busy:false,reload(){}})).includes('최근에 확인한 저장 결과'));
const {ReportView,reportHtml}=await import(pathToFileURL(path.join(dir,'components/report.js')));
assert.ok(reportHtml(snapshot.source).includes('\\u003c/script\\u003e'));
const listeners=new Map();globalThis.document.body={style:{overflow:''}};window.addEventListener=(type,fn)=>listeners.set(type,fn);window.removeEventListener=(type,fn)=>{if(listeners.get(type)===fn)listeners.delete(type)};
freshHooks();let report=render(()=>ReportView({source:snapshot.source,close(){},outdated:true,latest(){}}));
let markup=renderToStaticMarkup(report);assert.ok(markup.includes('이전 저장 결과'));assert.ok(markup.includes('최신 보고서 보기'));assert.ok(markup.includes('보고서를 준비하고'));
let iframe=React.Children.toArray(report.props.children).find(c=>c.type==='iframe');assert.equal(iframe.props.onLoad,undefined,'Document load is not report readiness');
const frameWindow={};iframe.props.ref.current={contentWindow:frameWindow};
const instance=iframe.props.srcDoc.match(/data-report-instance="([^"]+)"/)[1];
const message=data=>listeners.get('message')({source:frameWindow,data});
const ready={type:'lgax-report-ready',turn_id:'T1',instance};
listeners.get('message')({source:{},data:ready});message({...ready,turn_id:'T2'});message({...ready,instance:'old'});
report=render(()=>ReportView({source:snapshot.source,close(){}}));assert.ok(renderToStaticMarkup(report).includes('보고서를 준비하고'));
message(ready);report=render(()=>ReportView({source:snapshot.source,close(){}}));assert.ok(!renderToStaticMarkup(report).includes('보고서를 준비하고'));
message({...ready,type:'lgax-report-error',error:'private internal details'});report=render(()=>ReportView({source:snapshot.source,close(){}}));assert.ok(renderToStaticMarkup(report).includes('보고서 다시 열기'));assert.ok(!renderToStaticMarkup(report).includes('private internal'));
const retry=React.Children.toArray(report.props.children).find(c=>c.props?.role==='status'&&React.Children.toArray(c.props.children).some(x=>x.type==='button'));
const oldFrameError=iframe.props.onError;
React.Children.toArray(retry.props.children).find(c=>c.type==='button').props.onClick();
report=render(()=>ReportView({source:snapshot.source,close(){}}));iframe=React.Children.toArray(report.props.children).find(c=>c.type==='iframe');const retryInstance=iframe.props.srcDoc.match(/data-report-instance="([^"]+)"/)[1];assert.notEqual(retryInstance,instance);
iframe.props.ref.current={contentWindow:frameWindow};message(ready);assert.ok(renderToStaticMarkup(render(()=>ReportView({source:snapshot.source,close(){}}))).includes('보고서를 준비하고'));
message({...ready,instance:retryInstance});oldFrameError();assert.ok(!renderToStaticMarkup(render(()=>ReportView({source:snapshot.source,close(){}}))).includes('보고서 다시 열기'));
unmount();assert.equal(document.body.style.overflow,'');assert.equal(listeners.has('message'),false);
console.log('PASS: exact payload, validation/hash, serialized reads, timeout/late/dispose, actual hook script/file/recovery, report snapshot/turn/escaping, static status/frame controls');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
        with tempfile.TemporaryDirectory(prefix="viewer-contract-", dir=APP) as compiled:
            result = subprocess.run([node, str(APP / "node_modules/typescript/bin/tsc"),
                "--target", "es2022", "--module", "es2022", "--moduleResolution", "bundler",
                "--jsx", "react-jsx", "--skipLibCheck", "--rootDir", str(APP / "src"),
                "--outDir", compiled, str(APP / "src/lib/useView.ts"),
                str(APP / "src/components/shell.tsx"), str(APP / "src/components/report.tsx"),
                str(APP / "src/report.d.ts")], cwd=ROOT, capture_output=True,
                text=True, encoding="utf-8", timeout=45)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([node, "-e", script, compiled], cwd=APP,
                                    capture_output=True, text=True, encoding="utf-8", timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
