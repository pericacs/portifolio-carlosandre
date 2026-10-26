// No server, credentials or data writes: exercise the actual shared API client.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const ts=require(process.env.TYPESCRIPT_MODULE||'typescript');
const source=fs.readFileSync(path.join(__dirname,'../src/components/cms/api.ts'),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText;
function client(responses){
 const calls=[],redirects=[],exports={};
 vm.runInNewContext(compiled,{exports,FormData,fetch:async(...args)=>{calls.push(args);assert(responses.length,'Unexpected extra fetch');return responses.shift();},window:{location:{assign:x=>redirects.push(x)}}});
 return {api:exports.api,calls,redirects};
}
const json=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json'}});
(async()=>{
 let c=client([json({ok:true})]);assert.equal((await c.api('/test')).ok,true);
 for(const type of ['text/html','application/json']){
  c=client([new Response(type==='text/html'?'<html>nginx 413</html>':'{"detail":"Too large"}',{status:413,headers:{'content-type':type}})]);
  await assert.rejects(c.api('/docx/preview'),e=>e.message.includes('HTTP 413')&&e.message.includes('8 MB')&&!e.message.includes('Unexpected token')&&!e.message.includes('<html>'));
 }
 c=client([new Response('<html>Bad Gateway</html>',{status:502,headers:{'content-type':'text/html'}})]);await assert.rejects(c.api('/test'),/resposta inesperada \(HTTP 502\)/);
 c=client([new Response('<html>Broken JSON</html>',{status:200,headers:{'content-type':'application/json'}})]);await assert.rejects(c.api('/test'),/resposta inválida \(HTTP 200\)/);
 c=client([new Response('<html>Login</html>',{status:401})]);await assert.rejects(c.api('/test'),/Sessão expirada/);assert.deepEqual(c.redirects,['/admin/login']);
 c=client([new Response('Cloudflare error 1010',{status:403,headers:{'content-type':'text/plain'}})]);await assert.rejects(c.api('/docx/preview','POST',new FormData()),/HTTP 403/);assert.equal(c.calls.length,1);
 c=client([json({csrfToken:'synthetic-csrf'}),json({ok:true},201)]);const form=new FormData();await c.api('/docx/preview','POST',form);assert.equal(c.calls[1][1].headers['X-CSRF-Token'],'synthetic-csrf');assert.equal(c.calls[1][1].headers['Content-Type'],undefined);assert.equal(c.calls[1][1].body,form);
 c=client([json({})]);await assert.rejects(c.api('/test','POST',{}),/validar a sessão/);assert.equal(c.calls.length,1);
 c=client([new Response(null,{status:204})]);assert.equal(await c.api('/test'),null);
 c=client([json({detail:{code:'docx_staging_expired',message:'Revisão expirada; retome.'}},410)]);await assert.rejects(c.api('/docx/staging/test/commit'),e=>e.status===410&&e.code==='docx_staging_expired'&&e.message==='Revisão expirada; retome.');
 console.log('PASS: 11 API response/CSRF cases (413 HTML/JSON, non-JSON, invalid JSON, login, multipart, 204)');
})().catch(e=>{console.error(e);process.exit(1)});
