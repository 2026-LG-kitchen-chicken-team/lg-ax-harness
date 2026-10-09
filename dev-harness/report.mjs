import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { REPO_ROOT, isMain, parseOptions, validateRunId } from './runner.mjs';

export async function readCheckReport({ root = REPO_ROOT, runId = null } = {}) {
  let reportFile;
  if (runId !== null) {
    validateRunId(runId);
    reportFile = path.join(root, 'reports', runId, 'check.json');
  } else {
    const directory = path.join(root, 'reports');
    const entries = await readdir(directory, { withFileTypes: true }).catch((error) => {
      if (error.code === 'ENOENT') return [];
      throw error;
    });
    const candidates = [];
    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      const file = path.join(directory, entry.name, 'check.json');
      try {
        const metadata = await stat(file);
        if (metadata.isFile()) candidates.push({ file, modified: metadata.mtimeMs });
      } catch (error) {
        if (error.code !== 'ENOENT') throw error;
      }
    }
    candidates.sort((a, b) => b.modified - a.modified || b.file.localeCompare(a.file));
    reportFile = candidates[0]?.file;
    if (!reportFile) throw new Error('No completed check report found. Run npm run check first.');
  }
  const report = JSON.parse(await readFile(reportFile, 'utf8'));
  if (report.schemaVersion !== 1 || report.kind !== 'development-check'
      || !['passed', 'failed'].includes(report.status) || !Array.isArray(report.steps)) {
    throw new Error(`Invalid check report: ${reportFile}`);
  }
  return { report, reportFile };
}

export function summarizeReport(report, reportFile) {
  return {
    runId: report.runId,
    tool: report.tool,
    change: report.change,
    status: report.status,
    exitCode: report.exitCode,
    startedAt: report.startedAt,
    endedAt: report.endedAt,
    durationMs: report.durationMs,
    git: report.git,
    scope: report.scope,
    notCovered: report.notCovered,
    usage: report.usage,
    steps: report.steps.map(({ name, status, exitCode, durationMs, timedOut, error, stdoutPath, stderrPath }) => ({
      name, status, exitCode, durationMs, timedOut, error, stdoutPath, stderrPath,
    })),
    error: report.error,
    reportFile,
  };
}

export async function main(argv = process.argv.slice(2)) {
  const options = parseOptions(argv, { values: ['run'], flags: ['help'] });
  if (options.help) {
    console.log('Usage: npm run report -- [--run run-id]');
    return 0;
  }
  const { report, reportFile } = await readCheckReport({ runId: options.run ?? null });
  console.log(JSON.stringify(summarizeReport(report, reportFile), null, 2));
  return 0;
}

if (isMain(import.meta.url)) {
  main().then((code) => { process.exitCode = code; }).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
