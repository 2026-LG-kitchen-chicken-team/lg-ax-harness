"""Exercise the actual Lead component and its disclosure handler without a browser.

React hook slots are isolated for this component unit; JSX, Markdown escaping and
server rendering use the installed React implementation. Physical keyboard/zoom
acceptance remains a separate browser check.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "web/prototypes/visual-viewer/app"


class LeadAccessibilityTests(unittest.TestCase):
    def test_long_text_expands_in_page_flow_and_collapses_with_a_native_button(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node is required for the actual component contract")
        script = r'''
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const assert = require('node:assert/strict');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const compiled = process.argv[1];
const leadFile = path.join(compiled, 'components/lead.js');
fs.writeFileSync(path.join(compiled, 'package.json'), '{"type":"module"}');
let code = fs.readFileSync(leadFile, 'utf8');
code = code.replace(/from ['"]react['"]/, "from './react-hooks.js'")
  .replace(/from ['"][.][.]\/lib\/utils['"]/, "from '../lib/utils.js'");
fs.writeFileSync(leadFile, code);
globalThis.__leadSlot = false;
fs.writeFileSync(path.join(compiled, 'components/react-hooks.js'), `
export const useId = () => 'lead-contract';
export const useState = () => [globalThis.__leadSlot, next => {
  globalThis.__leadSlot = typeof next === 'function' ? next(globalThis.__leadSlot) : next;
}];`);
(async () => {
const {Lead} = await import(pathToFileURL(leadFile));
const tail = '마지막 조건: 청소 시 전원을 분리한다.';
const text = '[합성 시험 자료] ' + '긴 원문 조건 '.repeat(300).slice(0, 2000 - 11 - tail.length) + tail;
assert.equal(text.length, 2000);
const props = {text, summary: '짧은 모델 요약'};
const parts = tree => React.Children.toArray(tree.props.children);
const buttonOf = tree => parts(tree).find(x => x.type === 'button');
const bodyOf = tree => parts(tree).find(x => x.props.id === 'lead-contract');
let tree = Lead(props);
let button = buttonOf(tree);
assert.equal(button.props.type, 'button'); // Native Enter/Space activation; no hover dependency.
assert.equal(button.props['aria-expanded'], false);
assert.equal(button.props['aria-controls'], bodyOf(tree).props.id);
assert.equal(button.props.children, '전체 보기');
assert.equal(bodyOf(tree).props.style.display, 'none');
assert.match(button.props.className, /focus-visible:outline/);
button.props.onClick();
tree = Lead(props);
assert.equal(buttonOf(tree).props['aria-expanded'], true);
assert.equal(buttonOf(tree).props.children, '접기');
assert.equal(bodyOf(tree).props.style.display, 'block');
assert.equal(bodyOf(tree).props.children.props.text, text);
assert.ok(renderToStaticMarkup(bodyOf(tree)).includes(tail));
assert.match(bodyOf(tree).props.className, /whitespace-pre-wrap/);
assert.doesNotMatch(bodyOf(tree).props.className, /max-h|overflow-hidden|line-clamp|fixed/);
assert.equal(tree.props.onScroll, undefined); // No scrolling event closes an explicit disclosure.
buttonOf(tree).props.onClick();
tree = Lead(props);
assert.equal(buttonOf(tree).props['aria-expanded'], false);
assert.equal(bodyOf(tree).props.style.display, 'none');
assert.ok(buttonOf(Lead({text})), 'A clipped first sentence also needs the disclosure');
assert.equal(Lead({text: '짧은 전문'}).type.name, 'Md');
const escaped = renderToStaticMarkup(Lead({text: text + '<img onerror="bad">', summary: '요약'}));
assert.ok(escaped.includes('&lt;img'));
assert.ok(!escaped.includes('<img'));
const css = fs.readFileSync('src/index.css', 'utf8');
const paragraph = css.match(/\.skin-ops p:has\(> \.lg-lead\)\s*\{([^}]+)\}/)?.[1] || '';
assert.match(paragraph, /display:\s*block/);
assert.match(paragraph, /overflow:\s*visible/);
assert.match(paragraph, /-webkit-line-clamp:\s*unset/);
assert.ok(css.includes('> .lg-lead > .lg-lead-preview'), 'Only the preview can remain clamped');
console.log('Actual Lead disclosure: 2000-character tail, ARIA/button, expand/collapse, escaping and unclamped page flow passed.');
})().catch(error => {console.error(error);process.exitCode = 1});
'''
        with tempfile.TemporaryDirectory(prefix="lead-contract-", dir=APP) as compiled:
            compile_result = subprocess.run([node, str(APP / "node_modules/typescript/bin/tsc"),
                "--target", "es2022", "--module", "es2022", "--moduleResolution", "bundler",
                "--jsx", "react-jsx", "--skipLibCheck", "--rootDir", str(APP / "src"),
                "--outDir", compiled, str(APP / "src/components/lead.tsx")], cwd=ROOT,
                capture_output=True, text=True, encoding="utf-8", timeout=30)
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
            result = subprocess.run([node, "-e", script, compiled], cwd=APP, capture_output=True,
                                    text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
