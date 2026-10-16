"""Execute the real TS reader/controller/hooks with fake transport and clocks; no browser or AI."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "web/prototypes/agent-office/app"

PROGRAM = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = process.argv[2];
const name = process.argv[3];
const { stripTypeScriptTypes } = require('node:module');
assert.equal(typeof stripTypeScriptTypes, 'function', 'Node 22.13+ is required to execute actual TS behavior');
const modules = new Map();
const hooks = (() => {
  const slots = []; let cursor = 0; let effects = [];
  return {
    api: {
      Component: class { constructor(props) { this.props = props; } },
      createElement: (type, props, ...children) => ({ type, props: props ?? {}, children }),
      useState(init) { const i = cursor++; if (!slots[i]) slots[i] = { value: typeof init === 'function' ? init() : init };
        return [slots[i].value, (next) => { slots[i].value = typeof next === 'function' ? next(slots[i].value) : next }]; },
      useRef(init) { const i = cursor++; return slots[i] ?? (slots[i] = { current: init }); },
      useCallback(fn) { cursor++; return fn; },
      useEffect(fn, deps) { const i = cursor++; const old = slots[i];
        if (!old || deps.some((d, n) => d !== old.deps[n])) effects.push(() => { old?.cleanup?.(); slots[i] = { deps, cleanup: fn() }; }); },
    },
    render(fn) { cursor = 0; effects = []; const result = fn(); const pending = effects; effects = []; pending.forEach((f) => f()); return result; },
    unmount() { slots.forEach((s) => s?.cleanup?.()); },
  };
})();
function load(file) {
  if (modules.has(file)) return modules.get(file).exports;
  const source = fs.readFileSync(file, 'utf8');
  let code = stripTypeScriptTypes(source, { mode: 'transform', disableWarning: true });
  code = code.replace(/import\s*\{([^}]+)\}\s*from\s*['"]([^'"]+)['"];?/g, (_, names, id) => `const { ${names} } = require(${JSON.stringify(id)});`);
  const names = [...code.matchAll(/export\s+(?:function|class|const|let)\s+(\w+)/g)].map((m) => m[1]);
  code = code.replace(/export\s+(?=(?:function|class|const|let)\s)/g, '') + '\nObject.assign(exports, {' + names.join(',') + '});';
  const module = { exports: {} }; modules.set(file, module);
  const localRequire = (id) => id === 'react' ? hooks.api : load(path.resolve(path.dirname(file), id + '.ts'));
  new Function('require', 'module', 'exports', code)(localRequire, module, module.exports);
  return module.exports;
}
global.window = {};
const lib = path.join(root, 'web/prototypes/agent-office/app/src/lib');
const c = load(path.join(lib, 'readController.ts'));
const data = load(path.join(lib, 'data.ts'));
function fakeClock() {
  let now = 1000, id = 0; const jobs = new Map();
  return {
    now: () => now,
    set(fn, delay) { const key = ++id; jobs.set(key, { at: now + delay, fn }); return key; },
    clear(key) { jobs.delete(key); },
    advance(ms) { const target = now + ms; let count = 0;
      while (true) { const due = [...jobs].filter(([, v]) => v.at <= target).sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break; assert.ok(count++ < 100, 'bounded fake timers'); jobs.delete(due[0]); now = due[1].at; due[1].fn(); }
      now = target;
    },
    count: () => jobs.size,
  };
}
const event = { v: 1, id: 'synthetic-event', ts: '2026-10-16T12:00:00Z', hook: 'UserPromptSubmit', kind: 'request',
  session: 'synthetic-session', actor: 'main', agent_id: null, tool: null, call: null, node: null, op: null, phase: 'point', basis: 'observed', detail: null };
const liveFile = (detail = 'A') => ({ kind: 'lgax-agent-office-live', version: 1, written_at: 'same-time', events: [{ ...event, detail: { note: detail } }] });
const viewFile = (revision = 'A') => ({ kind: 'lgax-view', generated_at: 'same-time', result_identity: revision,
  pages: [{ id: 'overview' }], context: { file: { name: 'same-export' }, status: [{ text: 'completed' }] }, report: { turn_id: revision } });
function harness(validate = data.validLiveFile) {
  const clock = fakeClock(); const requests = []; const states = []; let cancels = 0;
  const transport = (ok, fail) => { requests.push({ ok, fail }); return () => { cancels++; }; };
  const controller = c.createReadController({ scheduler: clock, transport, interval: 1000, timeout: 2000, onState: (s) => states.push(s) });
  const succeed = (index, raw) => { const loaded = data.loadedValue(raw, validate); loaded ? requests[index].ok(loaded) : requests[index].fail('invalid'); };
  return { clock, requests, states, controller, succeed, cancels: () => cancels };
}
switch (name) {
  case 'default_and_explicit_modes': {
    assert.equal(c.observationMode(null), 'live'); assert.equal(c.observationMode('unknown'), 'live');
    assert.equal(c.observationMode('demo'), 'demo'); assert.equal(c.observationMode('replay'), 'replay');
    const h = harness(); h.controller.start(); h.succeed(0, { ...liveFile(), events: [] });
    assert.match(c.observationNotice(h.controller.getState(), false), /실제 실행 기록을 기다/);
    h.clock.advance(1000); h.succeed(1, liveFile()); assert.equal(h.controller.getState().value.events.length, 1);
    assert.equal(c.observationMode('demo'), 'demo'); h.controller.stop(); break;
  }
  case 'preserve_failure_and_automatic_recovery': {
    const h = harness(); h.controller.start(); h.succeed(0, liveFile()); const old = h.controller.getState();
    h.clock.advance(1000); h.requests[1].fail('unavailable'); const failed = h.controller.getState();
    assert.equal(failed.value, old.value); assert.equal(failed.lastSuccessAt, old.lastSuccessAt); assert.equal(failed.status, 'error');
    assert.match(c.observationNotice(failed, true), /AI 업무 실패를 뜻하지 않습니다/);
    h.clock.advance(1000); h.succeed(2, liveFile('B')); const recovered = h.controller.getState();
    assert.equal(recovered.error, null); assert.equal(recovered.value.events[0].detail.note, 'B');
    assert.ok(recovered.lastSuccessAt > old.lastSuccessAt); h.controller.stop(); break;
  }
  case 'no_overlapping_reads': {
    const h = harness(); h.controller.start(); assert.equal(h.controller.refresh(), false);
    h.clock.advance(1000); assert.equal(h.requests.length, 1); h.succeed(0, liveFile());
    assert.equal(h.controller.refresh(), true); assert.equal(h.requests.length, 2);
    assert.equal(h.controller.refresh(), false); h.controller.stop(); break;
  }
  case 'timeout_and_late_response': {
    const h = harness(); h.controller.start(); h.clock.advance(2000);
    assert.equal(h.controller.getState().error, 'timeout'); assert.equal(h.cancels(), 1);
    h.clock.advance(1000); h.succeed(1, liveFile('new')); h.succeed(0, liveFile('old'));
    assert.equal(h.controller.getState().value.events[0].detail.note, 'new'); h.controller.stop(); break;
  }
  case 'unmount_cancels_and_ignores_callbacks': {
    const h = harness(); h.controller.start(); const n = h.states.length; h.controller.stop();
    h.succeed(0, liveFile()); h.clock.advance(10000);
    assert.equal(h.states.length, n); assert.equal(h.requests.length, 1); assert.equal(h.clock.count(), 0); break;
  }
  case 'exact_identity_repeated_and_changed_records': {
    const h = harness(); h.controller.start(); h.succeed(0, liveFile('A')); const first = h.controller.getState().value;
    h.clock.advance(1000); h.succeed(1, liveFile('A')); assert.equal(h.controller.getState().value, first);
    h.clock.advance(1000); h.succeed(2, liveFile('B')); assert.notEqual(h.controller.getState().value, first);
    assert.equal(h.controller.getState().value.events[0].detail.note, 'B'); h.controller.stop(); break;
  }
  case 'invalid_record_keeps_valid_snapshot': {
    const h = harness(); h.controller.start(); h.succeed(0, liveFile()); const first = h.controller.getState().value;
    h.clock.advance(1000); h.succeed(1, { kind: 'lgax-agent-office-live', events: [null] });
    assert.equal(h.controller.getState().error, 'invalid'); assert.equal(h.controller.getState().value, first); h.controller.stop(); break;
  }
  case 'result_identity_and_stale_link_recovery': {
    const h = harness(data.resultMetadata); h.controller.start(); h.succeed(0, viewFile('A')); const first = h.controller.getState().value;
    h.clock.advance(1000); h.succeed(1, viewFile('B')); assert.equal(h.controller.getState().value.result_identity, 'B');
    assert.notEqual(h.controller.getState().value, first); const second = h.controller.getState().value;
    h.clock.advance(1000); h.requests[2].fail('unavailable'); assert.equal(h.controller.getState().value, second);
    h.clock.advance(1000); h.succeed(3, viewFile('C')); assert.equal(h.controller.getState().error, null); h.controller.stop(); break;
  }
  case 'result_optional_identity_full_payload_fallback': {
    const first = viewFile('A'); delete first.result_identity;
    const second = viewFile('B'); delete second.result_identity;
    const a = data.loadedValue(first, data.resultMetadata), b = data.loadedValue(second, data.resultMetadata);
    assert.equal(a.value.generated_at, b.value.generated_at); assert.equal(a.value.context.file.name, b.value.context.file.name);
    assert.notEqual(a.identity, b.identity); assert.equal(a.identity.length, b.identity.length); break;
  }
  case 'metadata_sanitizes_bad_display_fields': {
    assert.equal(data.resultMetadata({ kind: 'lgax-view', pages: [] }), null);
    const v = data.resultMetadata({ kind: 'lgax-view', pages: [{ id: 'x' }], context: { file: { name: {} }, status: [null, { text: {} }, { text: 'ready', tone: 5 }] } });
    assert.equal(v.context.file, undefined); assert.equal(v.context.status.length, 1); assert.equal(v.context.status[0].tone, undefined); break;
  }
  case 'synchronous_transport_cleanup': {
    const clock = fakeClock(); let cancels = 0;
    const controller = c.createReadController({ scheduler: clock, interval: 1000, transport: (ok) => {
      ok(data.loadedValue(liveFile(), data.validLiveFile)); return () => { cancels++; };
    }, onState: () => {} });
    controller.start(); assert.equal(controller.getState().status, 'ready'); assert.equal(cancels, 1);
    controller.stop(); assert.equal(clock.count(), 0); break;
  }
  case 'real_live_hook_wait_failure_recovery_unmount': {
    const clock = fakeClock(); const requests = [];
    const env = { scheduler: clock, transport: (ok, fail) => { requests.push({ ok, fail }); return () => {}; } };
    const render = () => hooks.render(() => data.useLiveFile(true, env));
    assert.equal(render().value, null); assert.equal(requests.length, 1);
    requests[0].ok(data.loadedValue(liveFile(), data.validLiveFile)); let state = render(); assert.equal(state.value.events.length, 1);
    const last = state.lastSuccessAt; clock.advance(1000); requests[1].fail('unavailable'); state = render();
    assert.equal(state.lastSuccessAt, last); assert.equal(state.value.events.length, 1); assert.equal(state.error, 'unavailable');
    clock.advance(1000); requests[2].ok(data.loadedValue(liveFile('B'), data.validLiveFile)); assert.equal(render().error, null);
    hooks.unmount(); const count = requests.length; clock.advance(10000); assert.equal(requests.length, count); break;
  }
  case 'real_result_hook_preserves_metadata_on_error': {
    const clock = fakeClock(); const requests = [];
    const env = { scheduler: clock, transport: (ok, fail) => { requests.push({ ok, fail }); return () => {}; } };
    const render = () => hooks.render(() => data.useResultView(env)); render();
    requests[0].ok(data.loadedValue(viewFile('A'), data.resultMetadata)); const first = render().value;
    clock.advance(4000); requests[1].fail('unavailable'); assert.equal(render().value, first);
    clock.advance(4000); requests[2].ok(data.loadedValue(viewFile('B'), data.resultMetadata)); assert.equal(render().value.result_identity, 'B');
    hooks.unmount(); assert.equal(clock.count(), 0); break;
  }
  case 'scene_failure_is_optional_and_actionable': {
    const { SceneBoundary, SceneUnavailable } = load(path.join(root, 'web/prototypes/agent-office/app/src/ui/SceneBoundary.ts'));
    const scene = { synthetic: 'scene' }; let notice = 0; const boundary = new SceneBoundary({ children: scene, onUnavailable: () => notice++ });
    assert.equal(boundary.render(), scene); boundary.state = SceneBoundary.getDerivedStateFromError(new Error('private-GPU-stack'));
    assert.equal(boundary.render().type, SceneUnavailable);
    boundary.componentDidCatch(); assert.equal(notice, 1);
    const fallback = JSON.stringify(SceneUnavailable());
    assert.match(fallback, /진행 목록/); assert.match(fallback, /결과 링크/); assert.doesNotMatch(fallback, /private-GPU-stack/); break;
  }
  case 'real_script_adapter_missing_assignment_timeout_cleanup': {
    const clock = fakeClock(); const tags = [];
    // Plain IO stubs, not a DOM/browser implementation or rendering environment.
    global.document = { currentScript: null, createElement: () => ({ remove() { this.removed = true; } }), head: { appendChild: (tag) => tags.push(tag) } };
    const assign = (tag, value) => { document.currentScript = tag; window.LGAX_OFFICE_LIVE = value; document.currentScript = null; };
    const env = { scheduler: clock }; const render = () => hooks.render(() => data.useLiveFile(true, env));
    render(); assert.equal(tags.length, 1); assert.equal(window.LGAX_OFFICE_LIVE, undefined);
    tags[0].onload(); assert.equal(render().error, 'invalid'); assert.equal(tags[0].removed, true);
    clock.advance(1000); assign(tags[1], liveFile('A')); tags[1].onload();
    const first = render().value; assert.equal(first.events[0].detail.note, 'A');
    clock.advance(1000); const late = tags[2].onload; clock.advance(5000);
    assert.equal(tags[2].onload, null); assert.equal(tags[2].removed, true); assert.equal(render().error, 'timeout');
    clock.advance(1000); assign(tags[2], liveFile('old')); late(); assert.equal(render().value, first);
    assert.equal(window.LGAX_OFFICE_LIVE, undefined);
    assign(tags[3], liveFile('B')); tags[3].onload(); assert.equal(render().value.events[0].detail.note, 'B');
    hooks.unmount(); assert.equal(clock.count(), 0); break;
  }
  case 'script_assignment_is_request_bound_for_both_globals': {
    for (const [key, validate, payload] of [['LGAX_OFFICE_LIVE', data.validLiveFile, liveFile], ['LGAX_VIEW', data.resultMetadata, viewFile]]) {
      const clock = fakeClock(); const tags = [];
      global.document = { currentScript: null, createElement: () => ({ remove() { this.removed = true; } }), head: { appendChild: (tag) => tags.push(tag) } };
      const assign = (tag, value) => { document.currentScript = tag; window[key] = value; document.currentScript = null; };
      const transport = data.scriptTransport('local.js', key, validate);
      const controller = c.createReadController({ scheduler: clock, transport, interval: 1000, timeout: 2000, onState: () => {} });
      controller.start(); const late = tags[0].onload; clock.advance(2000); assert.equal(controller.getState().error, 'timeout');
      clock.advance(1000); assign(tags[0], payload('old')); late(); tags[1].onload();
      assert.equal(controller.getState().error, 'invalid'); assert.equal(controller.getState().value, null);
      clock.advance(1000); assign(tags[2], payload('new')); assign(tags[0], payload('old')); tags[2].onload();
      assert.equal(controller.getState().status, 'ready'); assert.equal(controller.getState().value.result_identity ?? controller.getState().value.events[0].detail.note, 'new');
      controller.stop(); assert.equal(Object.hasOwn(window, key), false); assert.equal(clock.count(), 0);
    }
    break;
  }
  case 'script_global_descriptors_restore_on_cleanup_and_append_error': {
    for (const accessor of [false, true]) {
      const tags = []; const old = liveFile('seed'); let writes = 0;
      const descriptor = accessor ? { configurable: true, enumerable: false, get: () => old, set: () => writes++ }
        : { configurable: true, enumerable: false, writable: true, value: old };
      Object.defineProperty(window, 'LGAX_OFFICE_LIVE', descriptor);
      const expected = Object.getOwnPropertyDescriptor(window, 'LGAX_OFFICE_LIVE');
      global.document = { currentScript: null, createElement: () => ({ remove() { this.removed = true; } }), head: { appendChild: (tag) => tags.push(tag) } };
      const transport = data.scriptTransport('local.js', 'LGAX_OFFICE_LIVE', data.validLiveFile);
      let accepted = null; const cleanup = transport((value) => accepted = value, () => {});
      assert.equal(window.LGAX_OFFICE_LIVE, old); document.currentScript = tags[0]; window.LGAX_OFFICE_LIVE = liveFile('new'); document.currentScript = null;
      tags[0].onload(); assert.equal(accepted.value.events[0].detail.note, 'new'); cleanup(); cleanup();
      assert.deepEqual(Object.getOwnPropertyDescriptor(window, 'LGAX_OFFICE_LIVE'), expected); assert.equal(writes, 0);
      document.head.appendChild = () => { throw new Error('synthetic append failure'); };
      assert.throws(() => transport(() => {}, () => {}), /observation read failed/);
      assert.deepEqual(Object.getOwnPropertyDescriptor(window, 'LGAX_OFFICE_LIVE'), expected);
      delete window.LGAX_OFFICE_LIVE;
    }
    break;
  }
  default: throw new Error('Unknown case ' + name);
}
console.log(JSON.stringify({ case: name, ok: true, scope: 'actual TS hooks/controller with fake IO; no browser/DOM/network/model' }));
"""


class OfficeResilienceTests(unittest.TestCase):
    def run_case(self, name):
        self.assertIsNotNone(shutil.which("node"), "Node is required for actual TS behavior tests")
        result = subprocess.run(["node", "-", str(ROOT), name], input=PROGRAM, text=True, encoding="utf-8",
                                capture_output=True, timeout=20, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"ok":true', result.stdout)


for case in (
    "default_and_explicit_modes", "preserve_failure_and_automatic_recovery", "no_overlapping_reads",
    "timeout_and_late_response", "unmount_cancels_and_ignores_callbacks", "exact_identity_repeated_and_changed_records",
    "invalid_record_keeps_valid_snapshot", "result_identity_and_stale_link_recovery",
    "result_optional_identity_full_payload_fallback", "metadata_sanitizes_bad_display_fields",
    "synchronous_transport_cleanup", "real_live_hook_wait_failure_recovery_unmount",
    "real_result_hook_preserves_metadata_on_error",
    "scene_failure_is_optional_and_actionable",
    "real_script_adapter_missing_assignment_timeout_cleanup",
    "script_assignment_is_request_bound_for_both_globals",
    "script_global_descriptors_restore_on_cleanup_and_append_error",
):
    setattr(OfficeResilienceTests, "test_" + case, lambda self, name=case: self.run_case(name))


if __name__ == "__main__":
    unittest.main()
