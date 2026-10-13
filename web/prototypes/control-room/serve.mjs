import http from "node:http";
import { readFile, realpath, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { extname, resolve, sep } from "node:path";

// Built preview: local-only, read-only, no npm dependencies or model calls.
const root = await realpath(fileURLToPath(new URL("./dist/", import.meta.url)));
const port = Number(process.argv[2] ?? 5174);
if (!Number.isInteger(port) || port < 1024 || port > 65535)
  throw new Error("Port must be 1024..65535");
const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
};
const server = http.createServer(async (request, response) => {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405);
    response.end();
    return;
  }
  try {
    const rawPath = decodeURIComponent(
      new URL(request.url, "http://127.0.0.1").pathname,
    );
    const candidate = resolve(
      root,
      `.${rawPath === "/" ? "/index.html" : rawPath}`,
    );
    if (candidate !== root && !candidate.startsWith(root + sep)) {
      response.writeHead(403);
      response.end();
      return;
    }
    const path = await realpath(candidate);
    if (!path.startsWith(root + sep) || !(await stat(path)).isFile()) {
      response.writeHead(403);
      response.end();
      return;
    }
    const body = await readFile(path);
    response.writeHead(200, {
      "Content-Type": mime[extname(path)] ?? "application/octet-stream",
      "Content-Length": body.byteLength,
      "Cache-Control": "no-cache",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
    });
    response.end(request.method === "HEAD" ? undefined : body);
  } catch {
    response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Not found");
  }
});
server.on("error", (error) => {
  process.stderr.write(`${error.message}\n`);
  process.exitCode = 1;
});
server.listen(port, "127.0.0.1", () =>
  process.stdout.write(
    `LG AX Control Room · http://127.0.0.1:${port}/\nLocal preview. Press Ctrl+C to stop.\n`,
  ),
);
