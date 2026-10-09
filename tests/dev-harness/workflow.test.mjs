import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, rm, utimes, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { runCheck } from '../../dev-harness/check.mjs';
import { GENERATED_COMMANDS, GENERATED_SKILLS, discoverCodingTool, inspectEnvironment } from '../../dev-harness/doctor.mjs';
import { readCheckReport, summarizeReport } from '../../dev-harness/report.mjs';
import { failureExitCode, parseOptions, runCommand, validateRunId, validateTool } from '../../dev-harness/runner.mjs';

async function temporaryRoot(t) {
  const parent = path.resolve(tmpdir());
  const root = await mkdtemp(path.join(parent, 'lg-ax-dev-harness-test-'));
  t.after(async () => {
    // Only remove the exact temporary directory created by this test.
    assert.equal(path.dirname(path.resolve(root)), parent);
    assert.ok(path.basename(root).startsWith('lg-ax-dev-harness-test-'));
    await rm(root, { recursive: true, force: true });
  });
  return root;
}

async function put(root, file, contents = '') {
  const target = path.join(root, file);
  await mkdir(path.dirname(target), { recursive: true });
  await writeFile(target, contents, 'utf8');
}

function commandResult(exitCode = 0, values = {}) {
  return {
    command: 'node', args: [], status: exitCode === 0 ? 'passed' : 'failed', exitCode,
    signal: null, timedOut: false, error: null,
    startedAt: '2026-10-09T00:00:00.000Z', endedAt: '2026-10-09T00:00:00.010Z',
    durationMs: 10, stdout: '', stderr: '', outputTruncated: { stdout: false, stderr: false },
    ...values,
  };
}

function fakeRunner({ specExit = 0, testExit = 0, specValues = {}, calls = [] } = {}) {
  return async (command, args, options) => {
    calls.push({ command, args, options });
    if (command === 'git') {
      if (args[0] === 'rev-parse') return commandResult(0, { stdout: 'a'.repeat(40) + '\n' });
      if (args[0] === 'branch') return commandResult(0, { stdout: 'main\n' });
      return commandResult(0, { stdout: '' });
    }
    if (args.includes('validate')) return commandResult(specExit, { command, args, stdout: 'spec output', stderr: 'spec diagnostics', ...specValues });
    if (args.includes('--test')) return commandResult(testExit, { command, args, stdout: 'test output' });
    throw new Error(`Unexpected command: ${command}`);
  };
}

async function readyEnvironment(root) {
  await put(root, 'package.json', JSON.stringify({ engines: { node: '>=20.19.0' }, devDependencies: { '@fission-ai/openspec': '1.14.1' } }));
  await put(root, 'node_modules/@fission-ai/openspec/package.json', JSON.stringify({ version: '1.14.1' }));
  for (const file of ['AGENTS.md', 'CLAUDE.md', 'package-lock.json', 'openspec/config.yaml', 'dev-harness/openspec.mjs', 'node_modules/@fission-ai/openspec/bin/openspec.js']) await put(root, file);
  for (const skill of GENERATED_SKILLS) {
    await put(root, `.agents/skills/${skill}/SKILL.md`);
    await put(root, `.claude/skills/${skill}/SKILL.md`);
  }
  for (const command of GENERATED_COMMANDS) await put(root, `.claude/commands/opsx/${command}.md`);
  for (const directory of ['openspec/specs', 'openspec/changes', 'tests/dev-harness']) await mkdir(path.join(root, directory), { recursive: true });
  await put(root, 'tests/dev-harness/example.test.mjs', '// Fixture is discovered but never executed by fakeRunner.');
}

test('runner captures real stdout, stderr and a nonzero exit code', async () => {
  const result = await runCommand(process.execPath, ['-e', 'console.log("output"); console.error("failure"); process.exit(7)']);
  assert.equal(result.status, 'failed');
  assert.equal(result.exitCode, 7);
  assert.match(result.stdout, /output/);
  assert.match(result.stderr, /failure/);
  assert.ok(result.durationMs >= 0);
});

test('runner reports missing executables and times out stuck commands', async () => {
  const missing = await runCommand('lg-ax-nonexistent-command-for-test', []);
  assert.equal(missing.status, 'failed');
  assert.equal(missing.error.code, 'ENOENT');
  assert.equal(failureExitCode(missing), 1);
  const timeout = await runCommand(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { timeoutMs: 150 });
  assert.equal(timeout.status, 'failed');
  assert.equal(timeout.timedOut, true);
  assert.equal(failureExitCode(timeout), 124);
});

test('runner bounds captured output and records truncation', async () => {
  const result = await runCommand(process.execPath, ['-e', 'process.stdout.write("123456789")'], { maxOutputBytes: 5 });
  assert.equal(result.status, 'passed');
  assert.equal(result.stdout, '12345');
  assert.equal(result.outputTruncated.stdout, true);
});

test('CLI options reject mistakes and report IDs cannot traverse directories', () => {
  assert.deepEqual(parseOptions(['--tool', 'ci'], { values: ['tool'] }), { tool: 'ci' });
  assert.throws(() => parseOptions(['--tool'], { values: ['tool'] }), /needs a value/);
  assert.throws(() => parseOptions(['--unknown']), /Unknown option/);
  assert.throws(() => parseOptions(['--ci', '--ci'], { flags: ['ci'] }), /Duplicate/);
  assert.throws(() => validateTool('unsupported'), /must be one of/);
  for (const value of ['../outside', '..', '/absolute', 'a/b', 'a\\b']) assert.throws(() => validateRunId(value), /Invalid/);
});

test('an OpenSpec failure stays failed even when subsequent tests pass', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const calls = [];
  const { report, reportFile } = await runCheck({ root, runId: 'spec-failure', tool: 'codex', change: 'bootstrap-harness', run: fakeRunner({ specExit: 2, calls }) });
  assert.equal(report.status, 'failed');
  assert.equal(report.exitCode, 2);
  assert.deepEqual(report.steps.map((step) => step.status), ['failed', 'passed']);
  assert.equal(JSON.parse(await readFile(reportFile, 'utf8')).exitCode, 2);
  assert.equal(await readFile(path.join(root, report.steps[0].stderrPath), 'utf8'), 'spec diagnostics');
  const specCall = calls.find((call) => call.args.includes('validate'));
  assert.equal(specCall.args[0], path.join(root, 'dev-harness', 'openspec.mjs'));
  assert.equal(specCall.options.env.OPENSPEC_TELEMETRY, '0');
  assert.equal(specCall.options.env.OPENSPEC_NO_COMPLETIONS, '1');
});

test('a failing test returns its actual exit code', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const { report } = await runCheck({ root, runId: 'test-failure', run: fakeRunner({ testExit: 5 }) });
  assert.equal(report.status, 'failed');
  assert.equal(report.exitCode, 5);
});

test('timeout is preserved as a failed check with timeout exit code', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const { report } = await runCheck({ root, runId: 'timeout', run: fakeRunner({ specExit: null, specValues: { status: 'failed', timedOut: true, signal: 'SIGTERM' } }) });
  assert.equal(report.exitCode, 124);
  assert.equal(report.steps[0].exitCode, null);
  assert.equal(report.steps[0].timedOut, true);
});

test('successful development checks do not claim product evaluation or model usage', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const { report } = await runCheck({ root, runId: 'passed', tool: 'ci', run: fakeRunner() });
  assert.equal(report.status, 'passed');
  assert.equal(report.exitCode, 0);
  assert.equal(report.git.commitSha, 'a'.repeat(40));
  assert.equal(report.usage.totalTokens, null);
  assert.equal(report.usage.status, 'unavailable');
  assert.ok(report.notCovered.includes('product-runtime-evaluation'));
  assert.ok(report.notCovered.includes('dependency-audit'));
  await assert.rejects(runCheck({ root, runId: 'passed', run: fakeRunner() }), { code: 'EEXIST' });
});

test('missing tests and unexpected command errors produce failed JSON evidence', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  await rm(path.join(root, 'tests/dev-harness/example.test.mjs'));
  const missing = await runCheck({ root, runId: 'no-tests', run: fakeRunner() });
  assert.equal(missing.report.status, 'failed');
  assert.match(missing.report.error.message, /No development-harness tests/);
  const broken = await runCheck({ root, runId: 'runner-error', run: async () => { throw new Error('runner unavailable'); } });
  assert.equal(broken.report.status, 'failed');
  assert.match(broken.report.error.message, /runner unavailable/);
  assert.equal(JSON.parse(await readFile(broken.reportFile, 'utf8')).status, 'failed');
});

test('report reads a chosen run or the most recently completed run', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const first = await runCheck({ root, runId: 'first', run: fakeRunner() });
  const second = await runCheck({ root, runId: 'second', run: fakeRunner({ testExit: 3 }) });
  await utimes(first.reportFile, new Date(1000), new Date(1000));
  await utimes(second.reportFile, new Date(2000), new Date(2000));
  assert.equal((await readCheckReport({ root })).report.runId, 'second');
  assert.equal((await readCheckReport({ root, runId: 'first' })).report.runId, 'first');
  const summary = summarizeReport(second.report, second.reportFile);
  assert.equal(summary.status, 'failed');
  assert.equal(summary.steps[1].exitCode, 3);
  await assert.rejects(readCheckReport({ root, runId: '../outside' }), /Invalid run ID/);
});

test('corrupt newest evidence is reported instead of silently showing an older pass', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const previous = await runCheck({ root, runId: 'previous', run: fakeRunner() });
  await utimes(previous.reportFile, new Date(1000), new Date(1000));
  await put(root, 'reports/newest/check.json', '{broken');
  await assert.rejects(readCheckReport({ root }), SyntaxError);
});

test('report clearly fails when no completed evidence exists', async (t) => {
  const root = await temporaryRoot(t);
  await assert.rejects(readCheckReport({ root }), /No completed check report/);
});

test('CI doctor does not require or invoke coding CLIs', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const result = await inspectEnvironment({ root, ci: true, nodeVersion: 'v22.23.2', run: async () => { throw new Error('A coding CLI must not run in CI'); } });
  assert.equal(result.status, 'passed');
  assert.equal(result.codingTools.codex.status, 'skipped');
  assert.equal(result.codingTools.claude.status, 'skipped');
  assert.equal(result.smoke.status, 'not-run');
});

test('local doctor separates absent coding CLIs from a valid project environment', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  const result = await inspectEnvironment({ root, nodeVersion: 'v22.23.2', run: async () => commandResult(1) });
  assert.equal(result.status, 'passed');
  assert.equal(result.codingTools.codex.readiness, 'cli-unavailable');
  assert.equal(result.codingTools.claude.readiness, 'cli-unavailable');
  assert.equal(result.codingTools.codex.smokeVerified, false);
});

test('doctor flags old Node, a mismatched dependency and missing generated delivery', async (t) => {
  const root = await temporaryRoot(t);
  await readyEnvironment(root);
  await put(root, 'node_modules/@fission-ai/openspec/package.json', JSON.stringify({ version: '1.0.0' }));
  await rm(path.join(root, '.agents/skills/openspec-explore/SKILL.md'));
  const result = await inspectEnvironment({ root, ci: true, nodeVersion: 'v20.18.0' });
  assert.equal(result.status, 'failed');
  assert.equal(result.checks.find((check) => check.name === 'node-version').status, 'failed');
  assert.equal(result.checks.find((check) => check.name === 'openspec-version').status, 'failed');
  assert.equal(result.checks.find((check) => check.name === 'file:.agents/skills/openspec-explore/SKILL.md').status, 'failed');
});

test('Windows discovery handles npm command shims without starting an agent session', async () => {
  const calls = [];
  const result = await discoverCodingTool('codex', {
    platform: 'win32',
    run: async (command, args) => {
      calls.push({ command, args });
      return commandResult(0, { stdout: command === 'where.exe' ? 'C:\\bin\\codex.cmd\r\n' : 'codex-cli 0.162.0\r\n' });
    },
  });
  assert.equal(result.readiness, 'cli-ready');
  assert.equal(result.version, 'codex-cli 0.162.0');
  assert.equal(result.smokeVerified, false);
  assert.deepEqual(calls[1], { command: 'cmd.exe', args: ['/d', '/c', 'codex', '--version'] });
});
