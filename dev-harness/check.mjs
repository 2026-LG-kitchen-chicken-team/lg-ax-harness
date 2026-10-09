import { mkdir, readdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import {
  REPO_ROOT, createRunId, failureExitCode, gitContext, isMain, parseOptions,
  runCommand, validateRunId, validateTool, writeJson,
} from './runner.mjs';

export async function runCheck({
  root = REPO_ROOT,
  tool = 'manual',
  change = null,
  runId = createRunId(),
  run = runCommand,
} = {}) {
  validateTool(tool);
  validateRunId(runId);
  if (change !== null && !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(change)) {
    throw new Error('--change must be an OpenSpec kebab-case change ID');
  }
  const startedAt = new Date().toISOString();
  const started = performance.now();
  const runDirectory = path.join(root, 'reports', runId);
  await mkdir(path.join(root, 'reports'), { recursive: true });
  await mkdir(runDirectory); // Refuse an existing run: evidence is never overwritten.
  const report = {
    schemaVersion: 1,
    kind: 'development-check',
    runId,
    tool,
    change,
    startedAt,
    endedAt: null,
    durationMs: null,
    status: 'failed',
    exitCode: 1,
    scope: ['openspec-validation', 'development-harness-tests'],
    notCovered: ['product-runtime-evaluation', 'dependency-audit', 'interactive-coding-tool-smoke'],
    git: { commitSha: null, branch: null, dirty: null },
    usage: { status: 'unavailable', inputTokens: null, outputTokens: null, totalTokens: null, cost: null },
    steps: [],
    error: null,
  };

  const record = async (name, command, args, options = {}) => {
    const result = await run(command, args, { cwd: root, ...options });
    const stdoutFile = `${name}.stdout.log`;
    const stderrFile = `${name}.stderr.log`;
    await writeFile(path.join(runDirectory, stdoutFile), result.stdout ?? '', 'utf8');
    await writeFile(path.join(runDirectory, stderrFile), result.stderr ?? '', 'utf8');
    const { stdout, stderr, ...metadata } = result;
    report.steps.push({
      name,
      ...metadata,
      stdoutPath: `reports/${runId}/${stdoutFile}`,
      stderrPath: `reports/${runId}/${stderrFile}`,
    });
  };

  try {
    report.git = await gitContext(root, run);
    await record('openspec', process.execPath, [
      path.join(root, 'dev-harness', 'openspec.mjs'),
      'validate', '--all', '--strict', '--no-interactive', '--json',
    ], {
      env: { ...process.env, OPENSPEC_TELEMETRY: '0', OPENSPEC_NO_COMPLETIONS: '1' },
    });

    const testDirectory = path.join(root, 'tests', 'dev-harness');
    const tests = (await readdir(testDirectory))
      .filter((file) => file.endsWith('.test.mjs'))
      .sort()
      .map((file) => path.join(testDirectory, file));
    if (tests.length === 0) throw new Error('No development-harness tests found');
    await record('tests', process.execPath, ['--test', ...tests]);

    const failure = report.steps.find((step) => step.status !== 'passed');
    report.status = failure ? 'failed' : 'passed';
    report.exitCode = failure ? failureExitCode(failure) : 0;
  } catch (error) {
    report.error = { message: error.message, code: error.code ?? null };
    const failure = report.steps.find((step) => step.status !== 'passed');
    report.exitCode = failure ? failureExitCode(failure) : 1;
  }
  report.endedAt = new Date().toISOString();
  report.durationMs = Math.round(performance.now() - started);
  const reportFile = path.join(runDirectory, 'check.json');
  await writeJson(reportFile, report);
  return { report, reportFile };
}

export async function main(argv = process.argv.slice(2)) {
  const options = parseOptions(argv, { values: ['tool', 'change'], flags: ['help'] });
  if (options.help) {
    console.log('Usage: npm run check -- [--tool codex|claude|manual|ci] [--change change-id]');
    return 0;
  }
  const { report, reportFile } = await runCheck({ tool: options.tool, change: options.change ?? null });
  console.log(JSON.stringify({ runId: report.runId, status: report.status, exitCode: report.exitCode, reportFile }, null, 2));
  return report.exitCode;
}

if (isMain(import.meta.url)) {
  main().then((code) => { process.exitCode = code; }).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
