// Run only against the disposable instance created by scripts/verify-production.py --visual.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const sharp=require(process.env.SHARP_MODULE||'sharp');
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
const base=process.env.RECOVERY_BASE_URL,reference=process.env.RECOVERY_REFERENCE_URL;
assert(base&&reference&&base!==reference,'Distinct local test and read-only reference URLs required');
assert(['127.0.0.1','localhost'].includes(new URL(base).hostname));
assert(['127.0.0.1','localhost'].includes(new URL(reference).hostname));
(async()=>{
 const fixture=JSON.parse(await fs.readFile(process.env.RECOVERY_FIXTURE,'utf8'));
 const out=process.env.RECOVERY_OUTPUT;await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true});const report={visual:[],flows:[]};
 try{
  const request=await browser.newContext();
  const expected=await (await request.request.get(reference+'/api/content')).json();
  const actual=await (await request.request.get(base+'/api/content')).json();
  const stable=v=>Array.isArray(v)?v.map(stable):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).sort(([a],[b])=>a.localeCompare(b)).map(([k,x])=>[k,stable(x)])):v;
  assert.deepEqual(stable(actual),stable(expected),'Public CMS content must remain identical');
  const routes=['/','/sobre','/experiencia','/cases','/artigos','/privacidade','/projetos/smartfamily'];
  for(const [module,prefix] of [['artigos','/artigos/'],['videos','/videos/'],['cases','/cases/']]){
   const item=(actual.modules[module]||[]).find(x=>x.visible!==false&&!x.planned&&x.slug);if(item)routes.push(prefix+item.slug);
  }
  for(const width of [1440,390])for(const route of routes){
   const screenshots=[];
   for(const [label,url] of [['reference',reference],['restored',base]]){
    const ctx=await browser.newContext({viewport:{width,height:1000},deviceScaleFactor:1,reducedMotion:'reduce'});
    const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
    const response=await page.goto(url+route,{waitUntil:'networkidle'});assert.equal(response.status(),200,`${label} ${route}`);
    await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].filter(x=>x.complete).map(x=>x.decode().catch(()=>{})));});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow ${route} ${width}`);
    assert.deepEqual(errors,[],`JS errors ${route}`);
    const file=path.join(out,`${route==='/'?'home':route.slice(1).replaceAll('/','-')}-${width}-${label}.png`);
    screenshots.push(await page.screenshot({path:file,fullPage:true,animations:'disabled',caret:'hide'}));
    await ctx.close();
   }
   const a=await sharp(screenshots[0]).ensureAlpha().raw().toBuffer({resolveWithObject:true});
   const b=await sharp(screenshots[1]).ensureAlpha().raw().toBuffer({resolveWithObject:true});
   assert.deepEqual(a.info,b.info,`Dimensions changed ${route} ${width}`);
   let pixels=0;for(let i=0;i<a.data.length;i+=4)if(Math.max(...[0,1,2].map(c=>Math.abs(a.data[i+c]-b.data[i+c])))>12)pixels++;
   const ratio=pixels/(a.info.width*a.info.height);report.visual.push({route,width,changedPixelRatio:ratio});
   assert(ratio<=0.001,`Visual difference ${(ratio*100).toFixed(4)}% ${route} ${width}`);
  }
  const ctx=await browser.newContext(),page=await ctx.newPage();
  await page.goto(base+'/admin');await page.waitForURL('**/admin/login');
  await page.locator('[name=email]').fill(fixture.email);await page.locator('[name=password]').fill(fixture.password);
  await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL(base+'/admin');
  assert.equal((await ctx.request.get(base+'/api/admin/auth/me')).status(),200);
  await page.screenshot({path:path.join(out,'admin-restored.png'),fullPage:true});
  const security=await (await ctx.request.get(base+'/api/admin/auth/csrf')).json();
  const headers={Origin:base,'X-CSRF-Token':security.csrfToken};
  assert.equal((await ctx.request.post(base+'/api/admin/cms/categorias',{data:{data:{}},headers:{Origin:'https://invalid.example'}})).status(),403);
  let row=await (await ctx.request.post(base+'/api/admin/cms/categorias',{headers,data:{data:{title:'Recovery test',slug:'recovery-test-'+Date.now(),icon:'code',color:'blue',visible:true,featured:false,sortOrder:999}}})).json();assert(row.id);
  row=await (await ctx.request.put(base+'/api/admin/cms/categorias/'+row.id,{headers,data:{version:row.version,data:{...row.data,title:'Recovery updated'}}})).json();assert.equal(row.title,'Recovery updated');
  assert.equal((await ctx.request.put(base+'/api/admin/cms/categorias/'+row.id,{headers,data:{version:1,data:row.data}})).status(),409);
  row=await (await ctx.request.post(base+`/api/admin/cms/categorias/${row.id}/publish`,{headers,data:{version:row.version}})).json();assert.equal(row.status,'published');
  assert.equal((await ctx.request.delete(base+`/api/admin/cms/categorias/${row.id}?version=${row.version}`,{headers})).status(),200);
  const image=await sharp({create:{width:64,height:32,channels:3,background:'#2050aa'}}).png().toBuffer();
  const upload=await ctx.request.post(base+'/api/admin/cms/media',{headers,multipart:{file:{name:'recovery.png',mimeType:'image/png',buffer:image}}});assert.equal(upload.status(),201);
  const asset=await upload.json();assert.equal((await ctx.request.get(base+asset.url)).status(),200);
  const anonymous=await browser.newContext();assert.equal((await anonymous.request.get(base+asset.url)).status(),401);
  await anonymous.close();assert.equal((await ctx.request.delete(base+'/api/admin/cms/media/'+asset.id,{headers})).status(),200);
  const document=await ctx.request.get(base+'/documents/carlos-andre-curriculo-publico.docx');assert.equal(document.status(),200);assert.equal((await document.body()).subarray(0,2).toString(),'PK');
  await page.goto(base+'/#contato',{waitUntil:'networkidle'});const form=page.locator('#formulario');
  await form.locator('[name=name]').fill('Recovery local test');await form.locator('[name=email]').fill('recovery@example.com');await form.locator('[name=interest]').selectOption('Consultoria e arquitetura');await form.locator('[name=message]').fill('Teste local de recebimento duravel, sem SMTP configurado.');await form.locator('[name=consent]').check();
  await page.waitForTimeout(2200);await form.getByRole('button',{name:'Enviar mensagem',exact:true}).click();await form.getByRole('status').waitFor();
  const received=await (await ctx.request.get(base+'/api/admin/messages?q=recovery%40example.com')).json();assert.equal(received.items.length,1);assert.equal(received.items[0].notified_at,null);
  const retry=await (await ctx.request.post(base+`/api/admin/messages/${received.items[0].id}/retry-notification`,{headers})).json();assert.equal(retry.notification,'pending');
  assert.equal((await (await ctx.request.get(base+'/api/admin/messages?q=recovery%40example.com')).json()).total,1);
  await ctx.request.post(base+'/api/admin/auth/logout',{headers});assert.equal((await ctx.request.get(base+'/api/admin/dashboard')).status(),401);
  report.flows=['Public CMS parity','Responsive public routes','Login and SSR admin','CSRF rejection','CRUD and publish','Optimistic concurrency','Private upload authorization','Curriculum download','Contact durability','Pending email retry without duplicate contacts','Logout'];
  await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify({visualComparisons:report.visual.length,maxChangedPixelRatio:Math.max(...report.visual.map(x=>x.changedPixelRatio)),flows:report.flows,result:'passed'}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
