"""Material proposal conditions must survive a simpler default presentation."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / 'web/prototypes/visual-viewer/app'


class PlannerCardTests(unittest.TestCase):
    def test_material_conditions_and_full_text_survive_without_internal_ids(self):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        script = r'''
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
fs.writeFileSync(path.join(process.argv[1],'package.json'),'\u007b"type":"commonjs"\u007d');
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server');
const {STORY_BLOCKS}=require(path.join(process.argv[1],'components/story.js'));
const b={planner:true,items:[{id:'INTERNAL-CODE',n:1,title:'Stored proposal title',text:'Stored first sentence. Important complete explanation <img onerror="bad">',
chips:[{text:'하드웨어 필요'},{text:'내부 치수 필요'},{text:'기존 기능 중복: 미확인'}],
assumptions:['Only if the safety condition is met'],requirements:['Keep the entire safety requirement'],steps:['Check the exact model first'],sources:[{text:'SOURCE-CODE'}]}]};
const before=JSON.stringify(b),html=renderToStaticMarkup(React.createElement(STORY_BLOCKS.solutions,{b,copy(){}}));
for(const text of ['Stored proposal title','하드웨어 필요','내부 치수 필요','Only if the safety condition is met','Keep the entire safety requirement','Check the exact model first','Important complete explanation'])assert.ok(html.includes(text),text);
assert.ok(html.includes('&lt;img'));assert.ok(!html.includes('<img'));
assert.ok(!html.includes('INTERNAL-CODE'));assert.ok(html.includes('기존 기능 중복: 미확인'));
assert.ok(!html.includes('첫 문장'));assert.equal(JSON.stringify(b),before);
const noAssumptions={...b,items:[{...b.items[0],assumptions:[]}]};
const minimal=renderToStaticMarkup(React.createElement(STORY_BLOCKS.solutions,{b:noAssumptions,copy(){}}));
assert.ok(minimal.includes('하드웨어 필요'));assert.ok(minimal.includes('내부 치수 필요'));
'''
        with tempfile.TemporaryDirectory(prefix='planner-cards-', dir=APP) as compiled:
            built = subprocess.run([node, str(APP/'node_modules/typescript/bin/tsc'), '--target', 'es2022',
                '--module', 'commonjs', '--jsx', 'react-jsx', '--skipLibCheck', '--rootDir', str(APP/'src'),
                '--outDir', compiled, str(APP/'src/components/story.tsx')], cwd=ROOT, capture_output=True,
                text=True, encoding='utf-8', timeout=30)
            self.assertEqual(built.returncode, 0, built.stdout+built.stderr)
            result = subprocess.run([node, '-e', script, compiled], cwd=APP, capture_output=True,
                text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
