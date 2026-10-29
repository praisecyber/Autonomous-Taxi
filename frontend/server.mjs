/** Local frontend server. All application data travels over HTTP/WebSocket to the API. */
import http from 'node:http';
import { readFile, realpath } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const publicRoot = await realpath(fileURLToPath(new URL('./public/', import.meta.url)));
const port = Number(process.env.TAXI_FRONTEND_PORT || 3000);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid TAXI_FRONTEND_PORT');
const backend = new URL(process.env.TAXI_API_URL || 'http://127.0.0.1:8000');
if (backend.protocol !== 'http:' || !['127.0.0.1', 'localhost'].includes(backend.hostname) ||
    backend.username || backend.password || backend.pathname !== '/' || backend.search || backend.hash) {
  throw new Error('TAXI_API_URL must be a local HTTP backend origin, for example http://127.0.0.1:8000');
}
const pages = new Map([['/', 'index.html'], ['/operator', 'index.html'], ['/admin', 'admin.html'], ['/account', 'account.html']]);
const types = new Map([['.html', 'text/html; charset=utf-8'], ['.js', 'text/javascript; charset=utf-8'], ['.css', 'text/css; charset=utf-8']]);
const localHosts = new Set([`127.0.0.1:${port}`, `localhost:${port}`]);
const isApi = path => path.startsWith('/api/') || path === '/openapi.json' || path === '/docs' || path.startsWith('/docs/') || path === '/redoc';
function fail(response, code, message) {
  if (response.headersSent) { response.destroy(); return; }
  response.writeHead(code, {'Content-Type': 'text/plain; charset=utf-8', 'Cache-Control': 'no-store'});
  response.end(message);
}
function upstreamRequest(request) {
  // Preserve the browser-facing Host and Origin, so backend CSRF checks see the same origin.
  // Do not trust or forward client-supplied reverse-proxy identity headers.
  const headers = {...request.headers};
  for (const key of Object.keys(headers)) {
    if (key === 'forwarded' || key.startsWith('x-forwarded-')) delete headers[key];
  }
  return http.request({hostname: backend.hostname, port: backend.port || 80,
    method: request.method, path: request.url, headers});
}
const server = http.createServer(async (request, response) => {
  if (!localHosts.has(request.headers.host)) { fail(response, 403, 'Local frontend host required'); return; }
  let path;
  try { path = decodeURIComponent(new URL(request.url, 'http://localhost').pathname); }
  catch { fail(response, 400, 'Invalid path'); return; }
  if (isApi(path)) {
    const upstream = upstreamRequest(request);
    upstream.on('response', apiResponse => {
      response.writeHead(apiResponse.statusCode, apiResponse.headers);
      apiResponse.pipe(response);
      apiResponse.on('error', () => response.destroy());
    });
    upstream.on('error', () => {
      if (response.headersSent) { response.destroy(); return; }
      response.writeHead(502, {'Content-Type':'application/json', 'Cache-Control':'no-store'});
      response.end(JSON.stringify({detail:'Backend API unavailable'}));
    });
    upstream.setTimeout(30_000, () => upstream.destroy(new Error('Backend timeout')));
    request.on('aborted', () => upstream.destroy());
    response.on('close', () => { if (!response.writableFinished) upstream.destroy(); });
    request.pipe(upstream);
    return;
  }
  if (!['GET', 'HEAD'].includes(request.method)) { fail(response, 405, 'Method not allowed'); return; }
  const file = pages.get(path) || (path.startsWith('/static/') ? path.slice('/static/'.length) : null);
  if (!file || file.includes('\0') || !types.has(extname(file))) { fail(response, 404, 'Not found'); return; }
  try {
    const candidate = resolve(publicRoot, file);
    if (!candidate.startsWith(publicRoot + sep)) { fail(response, 404, 'Not found'); return; }
    const actual = await realpath(candidate);
    if (!actual.startsWith(publicRoot + sep)) { fail(response, 404, 'Not found'); return; }
    const data = await readFile(actual);
    response.writeHead(200, {'Content-Type':types.get(extname(file)), 'Content-Length':data.length,
      'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff', 'Referrer-Policy':'same-origin'});
    response.end(request.method === 'HEAD' ? undefined : data);
  } catch { fail(response, 404, 'Not found'); }
});
server.on('upgrade', (request, socket, head) => {
  if (!localHosts.has(request.headers.host) || request.url !== '/ws/telemetry') {
    socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'); return;
  }
  const upstream = upstreamRequest(request);
  upstream.on('upgrade', (response, apiSocket, apiHead) => {
    socket.write(`HTTP/1.1 ${response.statusCode} ${response.statusMessage}\r\n`);
    for (let i=0; i<response.rawHeaders.length; i+=2) socket.write(`${response.rawHeaders[i]}: ${response.rawHeaders[i+1]}\r\n`);
    socket.write('\r\n');
    if (apiHead.length) socket.write(apiHead);
    if (head.length) apiSocket.write(head);
    socket.pipe(apiSocket).pipe(socket);
    socket.on('error', () => apiSocket.destroy());
    apiSocket.on('error', () => socket.destroy());
    socket.on('close', () => apiSocket.destroy());
    apiSocket.on('close', () => socket.destroy());
  });
  upstream.on('response', response => {
    response.resume(); socket.end(`HTTP/1.1 ${response.statusCode} Rejected\r\nConnection: close\r\n\r\n`);
  });
  upstream.on('error', () => socket.end('HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n'));
  socket.on('error', () => upstream.destroy());
  upstream.end();
});
server.listen(port, '127.0.0.1', () => process.stdout.write(`Frontend listening on port ${port}; API target ${backend.origin}\n`));
