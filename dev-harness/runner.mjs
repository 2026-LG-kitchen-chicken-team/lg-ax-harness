import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { mkdir, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const TOOL_CONTEXTS = ['codex', 'claude', 'manual', 'ci'];

export function isMain(moduleUrl) {
  return Boolean(process.argv[1]) && path.resolve(process.argv[1]) === fileURLToPath(moduleUrl);
}

export function parseOptions(argv, { values = [], flags = [] } = {}) {
  const options = {};
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (!argument.startsWith('--')) throw new Error(`Unexpected argument: ${argument}`);
    const name = argument.slice(2);
    if (Object.hasOwn(options, name)) throw new Error(`Duplicate option: --${name}`);
    if (flags.includes(name)) {
      options[name] = true;
    } else if (values.includes(name)) {
      const value = argv[++index];
      if (!value || value.startsWith('--')) throw new Error(`--${name} needs a value`);
      options[name] = value;
    } else {
      throw new Error(`Unknown option: --${name}`);
    }
  }
  return options;
}

export function validateTool(tool = 'manual') {
  if (!TOOL_CONTEXTS.includes(tool)) throw new Error(`--tool must be one of: ${TOOL_CONTEXTS.join(', ')}`);
  return tool;
}

export function validateRunId(runId) {
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,95}$/.test(runId)) throw new Error('Invalid run ID');
  return runId;
}

export function createRunId(date = new Date()) {
  return `${date.toISOString().replace(/[-:.]/g, '')}-${randomUUID().slice(0, 8)}`;
}

export function failureExitCode(result) {
  if (Number.isInteger(result.exitCode) && result.exitCode > 0) return result.exitCode;
  return result.timedOut ? 124 : 1;
}

// Never runs an agent session: callers pass explicit local validation commands.
export function runCommand(command, args, {
  cwd = REPO_ROOT,
  env = process.env,
  timeoutMs = 120_000,
  maxOutputBytes = 1_048_576,
} = {}) {
  return new Promise((resolve) => {
    const startedAt = new Date().toISOString();
    const started = performance.now();
    const output = { stdout: [], stderr: [] };
    const sizes = { stdout: 0, stderr: 0 };
    const truncated = { stdout: false, stderr: false };
    let timer;
    let finished = false;
    let timedOut = false;
    const finish = (exitCode, signal, error = null) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      resolve({
        command,
        args,
        status: exitCode === 0 && !error && !timedOut ? 'passed' : 'failed',
        exitCode,
        signal,
        timedOut,
        error,
        startedAt,
        endedAt: new Date().toISOString(),
        durationMs: Math.round(performance.now() - started),
        stdout: Buffer.concat(output.stdout).toString('utf8'),
        stderr: Buffer.concat(output.stderr).toString('utf8'),
        outputTruncated: truncated,
      });
    };
    let child;
    try {
      child = spawn(command, args, { cwd, env, shell: false, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    } catch (error) {
      finish(null, null, { code: error.code ?? null, message: error.message });
      return;
    }
    for (const stream of ['stdout', 'stderr']) {
      child[stream].on('data', (chunk) => {
        const buffer = Buffer.from(chunk);
        const remaining = Math.max(0, maxOutputBytes - sizes[stream]);
        if (buffer.length > remaining) truncated[stream] = true;
        if (remaining > 0) {
          const kept = buffer.subarray(0, remaining);
          output[stream].push(kept);
          sizes[stream] += kept.length;
        }
      });
    }
    child.once('error', (error) => finish(null, null, { code: error.code ?? null, message: error.message }));
    child.once('close', (code, signal) => finish(code, signal));
    timer = setTimeout(() => {
      timedOut = true;
      child.kill();
    }, timeoutMs);
  });
}

export async function gitContext(root, run = runCommand) {
  const commit = await run('git', ['rev-parse', 'HEAD'], { cwd: root, timeoutMs: 10_000 });
  const branch = await run('git', ['branch', '--show-current'], { cwd: root, timeoutMs: 10_000 });
  const status = await run('git', ['status', '--porcelain'], { cwd: root, timeoutMs: 10_000 });
  return {
    commitSha: commit.status === 'passed' ? commit.stdout.trim() : null,
    branch: branch.status === 'passed' ? branch.stdout.trim() || null : null,
    dirty: status.status === 'passed' ? Boolean(status.stdout.trim()) : null,
  };
}

export async function writeJson(file, value) {
  await mkdir(path.dirname(file), { recursive: true });
  const temporary = `${file}.${randomUUID()}.tmp`;
  await writeFile(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  await rename(temporary, file);
}
