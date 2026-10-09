import { spawnSync } from 'node:child_process';
import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const cli = path.join(root, 'node_modules/@fission-ai/openspec/bin/openspec.js');

if (!existsSync(cli)) {
  console.error('OpenSpec 의존성이 없습니다. npm ci를 먼저 실행하세요.');
  process.exit(1);
}

// OpenSpec init can migrate old global prompts. Never let this project delete them.
const command = args.find((argument) => !argument.startsWith('-'));
if (['init', 'update', 'experimental'].includes(command)) {
  const prompts = path.join(process.env.CODEX_HOME || path.join(homedir(), '.codex'), 'prompts');
  const legacy = existsSync(prompts)
    ? readdirSync(prompts).filter((name) => /^(opsx-|openspec-).*\.md$/.test(name))
    : [];
  if (legacy.length > 0) {
    console.error('기존 전역 OpenSpec 프롬프트가 있습니다. 전역 파일을 변경할 수 있는 자동 migration을 실행하지 않습니다.');
    process.exit(1);
  }
}

const result = spawnSync(process.execPath, [cli, ...args], {
  cwd: root,
  stdio: 'inherit',
  env: {
    ...process.env,
    OPENSPEC_TELEMETRY: '0',
    OPENSPEC_NO_COMPLETIONS: '1',
    XDG_CONFIG_HOME: path.join(root, '.cache/openspec/config'),
    XDG_DATA_HOME: path.join(root, '.cache/openspec/data'),
  },
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
