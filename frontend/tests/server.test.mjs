import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { once } from 'node:events';

const listen = async server => { server.listen(0,'127.0.0.1'); await once(server,'listening'); return server.address().port; };
async function unusedPort() { const server=http.createServer(); const port=await listen(server); await new Promise(resolve=>server.close(resolve)); return port; }
const request = (port,path,headers={}) => new Promise((resolve,reject) => {
  http.get({hostname:'127.0.0.1',port,path,headers},response=>{
    let body=''; response.setEncoding('utf8'); response.on('data',chunk=>body+=chunk);
    response.on('end',()=>resolve({status:response.statusCode,headers:response.headers,body}));
  }).on('error',reject);
});

test('frontend serves assets and proxies API cookies, origins and failures', async () => {
  const api=http.createServer((req,res)=>{
    res.setHeader('Content-Type','application/json');
    res.setHeader('Set-Cookie','taxi_session=test-cookie; HttpOnly; SameSite=Strict; Path=/');
    res.end(JSON.stringify({url:req.url,host:req.headers.host,origin:req.headers.origin,
      cookie:req.headers.cookie,forwarded:req.headers['x-forwarded-host']}));
  });
  const backendPort=await listen(api), port=await unusedPort();
  const process=spawn('node',['frontend/server.mjs'],{env:{...globalThis.process.env,
    TAXI_FRONTEND_PORT:String(port),TAXI_API_URL:`http://127.0.0.1:${backendPort}`},stdio:['ignore','pipe','pipe']});
  try {
    await Promise.race([once(process.stdout,'data'),once(process,'exit').then(()=>{throw new Error('Frontend exited');}),
      new Promise((_,reject)=>{const timer=setTimeout(()=>reject(new Error('Frontend startup timeout')),5000);timer.unref();})]);
    for(const path of ['/','/admin','/account','/operator','/passenger','/diagnostics','/static/shared.css','/static/app.js']) assert.equal((await request(port,path)).status,200);
    const forwarded=await request(port,'/api/auth/me?q=test',{Origin:`http://127.0.0.1:${port}`,
      Cookie:'taxi_session=test-cookie','X-Forwarded-Host':'evil.example'});
    assert.equal(forwarded.status,200);
    const data=JSON.parse(forwarded.body);
    assert.equal(data.host,`127.0.0.1:${port}`);
    assert.equal(data.origin,`http://127.0.0.1:${port}`);
    assert.equal(data.cookie,'taxi_session=test-cookie');
    assert.equal(data.forwarded,undefined);
    assert.equal(data.url,'/api/auth/me?q=test');
    assert.ok(forwarded.headers['set-cookie'][0].includes('HttpOnly'));
    for(const path of ['/static/../../pyproject.toml','/static/%2e%2e/server.mjs','/server.mjs','/static/%00.html','/static/yolox_tiny.pth','/backend/taxi/perception/benchmark.py']) assert.equal((await request(port,path)).status,404);
    assert.equal((await request(port,'/',{Host:'evil.example'})).status,403);
    assert.equal((await request(port,'/%ZZ')).status,400);
    await new Promise(resolve=>api.close(resolve));
    const unavailable=await request(port,'/api/health');
    assert.equal(unavailable.status,502);
    assert.equal(JSON.parse(unavailable.body).detail,'Backend API unavailable');
    assert.equal((await request(port,'/')).status,200);
  } finally {
    process.kill(); await once(process,'exit');
    if(api.listening) await new Promise(resolve=>api.close(resolve));
  }
});
