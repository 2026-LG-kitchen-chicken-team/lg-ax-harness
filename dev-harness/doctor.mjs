import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { REPO_ROOT, isMain, parseOptions, runCommand } from './runner.mjs';

export const GENERATED_SKILLS = [
  'openspec-propose', 'openspec-apply-change', 'openspec-archive-change',
  'openspec-explore', 'openspec-sync-specs', 'openspec-update-change',
];
export const GENERATED_COMMANDS = ['propose', 'apply', 'archive', 'explore', 'sync', 'update'];

export function meetsNodeRequirement(version, requirement) {
  const actual = /^v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?$/.exec(version);
  const minimum = /^>=(\d+)\.(\d+)\.(\d+)$/.exec(requirement);
  if (!actual || !minimum) throw new Error(`Unsupported Node version requirement: ${requirement}`);
  for (let index = 1; index <= 3; index += 1) {
    const difference = Number(actual[index]) - Number(minimum[index]);
    if (difference !== 0) return difference > 0;
  }
  return true;
}

export async function discoverCodingTool(name, { root = REPO_ROOT, platform = process.platform, run = runCommand } = {}) {
  // Names are fixed, never user input; cmd.exe is needed for npm .cmd shims on Windows.
  if (!['codex', 'claude'].includes(name)) throw new Error('Unknown coding tool');
  const discovery = platform === 'win32'
    ? await run('where.exe', [name], { cwd: root, timeoutMs: 10_000 })
    : await run('/bin/sh', ['-c', `command -v ${name}`], { cwd: root, timeoutMs: 10_000 });
  if (discovery.status !== 'passed' || !discovery.stdout.trim()) {
    return { status: 'unavailable', path: null, version: null, readiness: 'cli-unavailable', smokeVerified: false };
  }
  const version = platform === 'win32'
    ? await run('cmd.exe', ['/d', '/c', name, '--version'], { cwd: root, timeoutMs: 10_000 })
    : await run(name, ['--version'], { cwd: root, timeoutMs: 10_000 });
  return {
    status: version.status === 'passed' ? 'available' : 'version-failed',
    path: discovery.stdout.trim().split(/\r?\n/)[0],
    version: version.status === 'passed' ? (version.stdout.trim() || version.stderr.trim()).split(/\r?\n/)[0] || null : null,
    readiness: version.status === 'passed' ? 'cli-ready' : 'cli-version-failed',
    smokeVerified: false,
  };
}

export async function inspectEnvironment({ root = REPO_ROOT, ci = false, nodeVersion = process.version, run = runCommand } = {}) {
  const checks = [];
  const add = (name, passed, detail) => checks.push({ name, status: passed ? 'passed' : 'failed', detail });
  let manifest;
  try {
    manifest = JSON.parse(await readFile(path.join(root, 'package.json'), 'utf8'));
    add('node-version', meetsNodeRequirement(nodeVersion, manifest.engines?.node), {
      actual: nodeVersion, required: manifest.engines?.node,
    });
  } catch (error) {
    add('node-version', false, { actual: nodeVersion, error: error.message });
  }
  try {
    const installed = JSON.parse(await readFile(path.join(root, 'node_modules', '@fission-ai', 'openspec', 'package.json'), 'utf8'));
    const required = manifest?.devDependencies?.['@fission-ai/openspec'];
    add('openspec-version', Boolean(required) && installed.version === required, {
      actual: installed.version, required: required ?? null,
    });
  } catch (error) {
    add('openspec-version', false, { error: error.message, remedy: 'Run npm ci.' });
  }
  const files = [
    'AGENTS.md', 'CLAUDE.md', 'package-lock.json', 'openspec/config.yaml', 'dev-harness/openspec.mjs',
    'node_modules/@fission-ai/openspec/bin/openspec.js',
    ...GENERATED_SKILLS.flatMap((name) => [`.agents/skills/${name}/SKILL.md`, `.claude/skills/${name}/SKILL.md`]),
    ...GENERATED_COMMANDS.map((name) => `.claude/commands/opsx/${name}.md`),
  ];
  for (const file of files) {
    const present = await stat(path.join(root, file)).then((metadata) => metadata.isFile()).catch((error) => {
      if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return false;
      throw error;
    });
    add(`file:${file}`, present, { path: file });
  }
  for (const directory of ['openspec/specs', 'openspec/changes', 'tests/dev-harness']) {
    const present = await stat(path.join(root, directory)).then((metadata) => metadata.isDirectory()).catch((error) => {
      if (error.code === 'ENOENT' || error.code === 'ENOTDIR') return false;
      throw error;
    });
    add(`directory:${directory}`, present, { path: directory });
  }
  const skipped = { status: 'skipped', path: null, version: null, readiness: 'not-required-in-ci', smokeVerified: false };
  const codingTools = ci ? { codex: { ...skipped }, claude: { ...skipped } } : {
    codex: await discoverCodingTool('codex', { root, run }),
    claude: await discoverCodingTool('claude', { root, run }),
  };
  return {
    schemaVersion: 1,
    kind: 'environment-doctor',
    mode: ci ? 'ci' : 'local',
    status: checks.every((check) => check.status === 'passed') ? 'passed' : 'failed',
    checks,
    codingTools,
    smoke: { status: 'not-run', note: 'CLI discovery only. Interactive instruction loading and authentication require a separate smoke check.' },
    notCovered: ['product-runtime-evaluation', 'dependency-audit'],
  };
}

export async function main(argv = process.argv.slice(2)) {
  const options = parseOptions(argv, { flags: ['ci', 'help'] });
  if (options.help) {
    console.log('Usage: npm run doctor -- [--ci]');
    return 0;
  }
  const result = await inspectEnvironment({ ci: options.ci ?? false });
  console.log(JSON.stringify(result, null, 2));
  return result.status === 'passed' ? 0 : 1;
}

if (isMain(import.meta.url)) {
  main().then((code) => { process.exitCode = code; }).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
