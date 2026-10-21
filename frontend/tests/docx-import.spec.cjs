// Only disposable instances from scripts/verify-production.py --docx.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const sharp=require(process.env.SHARP_MODULE||'sharp');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const base=process.env.RECOVERY_BASE_URL;
assert(base&&new URL(base).hostname==='127.0.0.1');
(async()=>{
 const credentials=JSON.parse(await fs.readFile(process.env.RECOVERY_FIXTURE,'utf8'));
 const out=process.env.RECOVERY_OUTPUT;await fs.mkdir(out,{recursive:true});
 const source=process.env.DOCX_REFERENCE||path.resolve('.private/docx-import-check/reference.docx');
 const browser=await chromium.launch({headless:true}),ctx=await browser.newContext(),page=await ctx.newPage();
 const report={result:'running',screenshots:[],comparisons:[]},errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('dialog',async dialog=>{errors.push('Unexpected '+dialog.type()+' dialog');await dialog.dismiss();});
 async function screenshot(label,width){
  await page.setViewportSize({width,height:1000});await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(x=>x.decode().catch(()=>{})));});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),label+' overflow');
  const file=path.join(out,label+'-'+width+'.png');report.screenshots.push(file);return page.screenshot({path:file,fullPage:true,animations:'disabled'});
 }
 try{
  await page.goto(base+'/admin');await page.waitForURL('**/admin/login');
  await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);
  await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL(base+'/admin');
  const initialSecurity=await (await ctx.request.get(base+'/api/admin/auth/csrf')).json(),initialHeaders={Origin:base,'X-CSRF-Token':initialSecurity.csrfToken};
  const legacy=await ctx.request.post(base+'/api/admin/cms/artigos',{headers:initialHeaders,data:{data:{title:'Artigo anterior de controle',slug:'artigo-anterior-controle',body:'<p>Conteúdo anterior mantido integralmente.</p>',description:'Referência sintética de regressão.',readingMode:'Interno',planned:false,visible:true}}});
  assert.equal(legacy.status(),201);const existing=await legacy.json();
  assert.equal((await ctx.request.post(base+`/api/admin/cms/artigos/${existing.id}/publish`,{headers:initialHeaders,data:{version:existing.version}})).status(),200);
  const before=await (await ctx.request.get(base+'/api/content')).json();
  const routes=['/','/artigos'];
  const article=(before.modules.artigos||[]).find(x=>x.slug&&!x.planned);if(article)routes.push('/artigos/'+article.slug);
  const baseline=new Map();
  for(const route of routes){await page.goto(base+route,{waitUntil:'networkidle'});for(const width of [1440,390])baseline.set(route+width,await screenshot('before-'+route.replaceAll('/','_'),width));}
  await page.goto(base+'/admin/artigos');await page.getByRole('link',{name:'Importar artigo do Word'}).click();
  assert(await page.getByRole('button',{name:'Confirmar e salvar rascunho'}).count()===0);
  let uploads=0;
  await page.route('**/api/admin/docx/preview',route=>{uploads++;return route.fulfill({status:413,contentType:'text/html',body:'<html><h1>413 Request Entity Too Large</h1></html>'});});
  await page.getByLabel('Documento DOCX').setInputFiles({name:'too-large.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:Buffer.alloc(8*1024*1024+1)});
  await page.getByRole('alert').filter({hasText:'8.388.608 bytes'}).waitFor();assert.equal(uploads,0);
  await page.getByLabel('Documento DOCX').setInputFiles(source);
  const uploadError=page.getByRole('alert').filter({hasText:'HTTP 413'});
  await uploadError.waitFor();assert(!(await uploadError.textContent()).includes('Unexpected token'));assert.equal(uploads,1);
  await page.unroute('**/api/admin/docx/preview');
  await page.getByLabel('Documento DOCX').setInputFiles(source);
  await page.getByLabel('Título',{exact:true}).waitFor();
  assert.equal(await page.getByLabel('Título',{exact:true}).inputValue(),'O SPLIT DO MAL');
  assert.equal(await page.getByLabel('Autor',{exact:true}).inputValue(),'Carlos André Cardoso dos Santos');
  assert(await page.getByRole('button',{name:'Confirmar e salvar rascunho'}).isDisabled());
  await page.getByRole('button',{name:'Atualizar prévia da página pública'}).click();
  const preview=page.getByRole('region',{name:'Prévia da página pública'});await preview.waitFor();
  assert.equal(await preview.locator('img').count(),4);
  assert.equal(await preview.locator('h2').count(),11);assert.equal(await preview.locator('h3').count(),2);
  assert.equal(await preview.locator('figcaption').count(),3);assert(await preview.locator('a[href^="https://"]').count()>=3);
  const pictures=await preview.locator('img').evaluateAll(imgs=>imgs.map(x=>({src:x.src,width:x.naturalWidth,height:x.naturalHeight})));
  const anonymous=await browser.newContext();assert.equal((await anonymous.request.get(pictures[0].src)).status(),401);await anonymous.close();
  for(const width of [1440,390])await screenshot('import-preview',width);
  await page.getByRole('checkbox',{name:'Revisei a prévia'}).check();
  let commitPosts=0;
  await page.route('**/api/admin/docx/staging/*/commit',async route=>{commitPosts++;const response=await route.fetch();assert.equal(response.status(),200);const receipt=await response.json();assert.equal(receipt.entryId,receipt.entry.id);await route.fulfill({status:200,contentType:'application/json',body:'{"broken":true}'});});
  await page.getByRole('button',{name:'Confirmar e salvar rascunho'}).evaluate(button=>{button.click();button.click();});await page.waitForURL(/\/admin\/artigos\/[0-9a-f-]+\?docx=saved$/);
  await page.getByRole('status').filter({hasText:'Artigo salvo.'}).waitFor();await screenshot('saved-editor',1440);
  assert.equal(commitPosts,1);await page.unroute('**/api/admin/docx/staging/*/commit');
  const id=new URL(page.url()).pathname.split('/').pop();
  const security=await (await ctx.request.get(base+'/api/admin/auth/csrf')).json(),headers={Origin:base,'X-CSRF-Token':security.csrfToken};
  let row=await (await ctx.request.get(base+'/api/admin/cms/artigos/'+id)).json();assert.equal(row.status,'draft');assert.equal(row.published_data,null);
  assert.deepEqual(await (await ctx.request.get(base+'/api/content')).json(),before);
  assert.equal((await (await ctx.request.get(base+'/api/admin/docx/history/'+id)).json()).length,1);
  for(const image of pictures){
   const uuid=new URL(image.src).pathname.split('/').pop(),response=await ctx.request.get(base+'/api/media/'+uuid);
   assert.equal(response.status(),200);assert.equal(require('node:crypto').createHash('sha256').update(await response.body()).digest('hex'),new URL(image.src).searchParams.get('v'));
  }
  await page.goto(base+`/admin/artigos/${id}/preview`,{waitUntil:'networkidle'});
  for(const width of [1440,390])await screenshot('draft-preview',width);
  // Explicit publication is tested only in this disposable database.
  const published=await ctx.request.post(base+`/api/admin/cms/artigos/${id}/publish`,{headers,data:{version:row.version}});assert.equal(published.status(),200);
  row=await published.json();await page.goto(base+'/artigos/'+row.slug,{waitUntil:'networkidle'});
  for(const width of [1440,390])await screenshot('article-public',width);
  assert.equal(await page.locator('figure img').count(),3);
  await page.locator('figure img').first().click();await page.getByRole('dialog',{name:'Imagem ampliada do artigo'}).waitFor();
  await page.getByRole('button',{name:'Fechar ×'}).click();
  assert(await page.locator('img').evaluateAll(imgs=>imgs.every(x=>x.naturalWidth>0&&Math.abs(x.width/x.height-x.naturalWidth/x.naturalHeight)<0.03)));
  for(const route of routes){await page.goto(base+route,{waitUntil:'networkidle'});for(const width of [1440,390]){
   // The article index intentionally gains the explicitly published test article.
   if(route==='/artigos')continue;
   const after=await screenshot('after-'+route.replaceAll('/','_'),width),prior=baseline.get(route+width);
   const a=await sharp(prior).ensureAlpha().raw().toBuffer({resolveWithObject:true}),b=await sharp(after).ensureAlpha().raw().toBuffer({resolveWithObject:true});
   assert.deepEqual(a.info,b.info);let changed=0;for(let i=0;i<a.data.length;i+=4)if([0,1,2].some(c=>Math.abs(a.data[i+c]-b.data[i+c])>12))changed++;
   const ratio=changed/(a.info.width*a.info.height);assert(ratio<0.001);report.comparisons.push({route,width,ratio});
  }}
  const archived=await ctx.request.post(base+`/api/admin/cms/artigos/${id}/archive`,{headers,data:{version:row.version}});assert.equal(archived.status(),200);
  await page.goto(base+'/admin/artigos/importar');await page.getByLabel('Documento DOCX').setInputFiles(source);
  await page.getByRole('button',{name:'Recuperar como rascunho'}).waitFor();await screenshot('archived-recovery',1440);
  await page.getByRole('button',{name:'Recuperar como rascunho'}).click();await page.waitForURL(base+`/admin/artigos/${id}?docx=saved`);
  await page.getByRole('status').filter({hasText:'Artigo salvo.'}).waitFor();await screenshot('recovered-editor',390);
  const recovered=await (await ctx.request.get(base+'/api/admin/cms/artigos/'+id)).json();assert.equal(recovered.status,'draft');assert.deepEqual(recovered.data,row.data);
  assert.equal((await (await ctx.request.get(base+'/api/admin/docx/history/'+id)).json()).length,1);
  await page.goto(base+'/admin/artigos/importar');await page.getByLabel('Documento DOCX').setInputFiles(source);
  await page.getByRole('button',{name:'Atualizar prévia da página pública'}).click();await page.getByRole('region',{name:'Prévia da página pública'}).waitFor();
  await page.getByRole('checkbox',{name:'Revisei a prévia'}).check();
  const committed=page.waitForResponse(response=>response.url().endsWith('/commit')&&response.request().method()==='POST');
  await page.getByRole('button',{name:'Confirmar e salvar rascunho'}).click();assert.equal((await committed).status(),200);
  await page.waitForURL(base+`/admin/artigos/${id}?docx=saved`);await page.getByRole('status').filter({hasText:'Artigo salvo.'}).waitFor();
  report.recovery=['lost-response','double-click','archived-same-id','normal-200'];
  assert.deepEqual(errors,[]);report.result='passed';report.sourceImages=pictures;report.entryId=id;
  await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
