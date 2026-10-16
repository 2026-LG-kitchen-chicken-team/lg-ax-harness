"""Test the built report bridge as pure JS; no browser, DOM engine or render."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ReportFrameStatusTests(unittest.TestCase):
    def test_actual_build_bridge_reports_completion_and_hides_internal_errors(self):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        script = r'''
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
(async()=>{
  const file=path.resolve('web/prototypes/visual-viewer/app/scripts/jinha-report.mjs');
  const {jinhaReport}=await import(pathToFileURL(file));
  const moduleSource=jinhaReport().load.call({addWatchFile(){}},'\0virtual:jinha-report');
  const html=JSON.parse(moduleSource.slice('export default '.length));
  assert.ok(html.includes("restoreTraceSelection();reportState('lgax-report-ready');"));
  const bridge=html.match(/const reportState=type=>\{[^\n]+\};/)[0];
  const notice=html.match(/const notice=\(message,error=false\)=>\{[^\n]+\};/)[0];
  const messages=[];
  const fields={
    'data-turn-id':'current-turn',
    'data-report-instance':'current-instance',
  };
  const nodes={'#load-notice':{},'#announcement':{}};
  const parent={postMessage:(data,target)=>messages.push({data,target})};
  const win={parent};
  const doc={getElementById:()=>({getAttribute:key=>fields[key]})};
  const api=new Function('window','document','$',bridge+'\n'+notice+'\nreturn {reportState,notice};')(win,doc,key=>nodes[key]);
  api.notice('C:/private/path.json SyntaxError token secret',true);
  assert.deepEqual(messages[0],{data:{type:'lgax-report-error',turn_id:'current-turn',instance:'current-instance'},target:'*'});
  assert.equal(nodes['#load-notice'].className,'load-error');
  assert.equal(nodes['#load-notice'].hidden,false);
  assert.equal(nodes['#announcement'].textContent,'보고서를 표시하지 못했어요. 업무 화면에서 다시 열어주세요.');
  assert.ok(!JSON.stringify(nodes).includes('private'));
  api.reportState('lgax-report-ready');
  assert.equal(messages[1].data.type,'lgax-report-ready');
  api.notice('저장된 결과를 열었습니다.');
  assert.equal(nodes['#announcement'].textContent,'저장된 결과를 열었습니다.');
  win.parent=win;
  api.reportState('lgax-report-ready');
  assert.equal(messages.length,2,'Standalone saved report must not post to itself');
  console.log('Built report bridge: ready/error, turn/instance identity, friendly error text and standalone isolation passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''
        result = subprocess.run([node, '-e', script], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
