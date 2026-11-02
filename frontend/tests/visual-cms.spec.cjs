// Real browser checks against scripts/verify-visual-cms.py's disposable stack.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const base='http://127.0.0.1:8097',phase=process.argv[2]||'after';
const out=path.resolve('docs/screenshots/visual-cms',phase);
(async()=>{
 await fs.mkdir(out,{recursive:true});
 const extension=path.resolve('scripts/browser-zoom-extension');
 const context=await chromium.launchPersistentContext('',{executablePath:process.env.QA_CHROME||(process.platform==='win32'?'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe':chromium.executablePath()),ignoreDefaultArgs:['--disable-extensions'],headless:true,reducedMotion:'reduce',args:['--disable-extensions-except='+extension,'--load-extension='+extension]});
 const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker');
 const page=await context.newPage();
 page.setDefaultTimeout(15000);
 const report={phase,screens:[],checks:[],pages:[],errors:[]};page.on('pageerror',e=>report.errors.push(e.message));
 try{
  const credentials=JSON.parse(await fs.readFile('.private/visual-cms/credentials.json','utf8'));
  await page.goto(base+'/admin/login');await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);await page.getByRole('button',{name:'Entrar no painel',exact:true}).click();await page.waitForURL(base+'/admin');
  const content=await (await context.request.get(base+'/api/content')).json(),articles=content.modules.artigos||[];
  const list=await (await context.request.get(base+'/api/admin/cms/artigos?limit=100')).json();
  const reference=list.items.find(x=>/binance|813/i.test(x.title))||list.items.find(x=>x.published_data)||list.items[0];
  console.log(JSON.stringify({phase,publicArticles:articles.map(x=>x.title),reference:reference?.title}));
  const routes=[['home','/'],['artigos','/artigos'],['cms','/admin/artigos/'+(reference?.id||'novo')]];
  for(const width of [1440,768,390])for(const [name,url] of routes){
   await page.setViewportSize({width,height:1000});await page.goto(base+url,{waitUntil:'networkidle'});
   await page.evaluate(async()=>{await document.fonts.ready;for(const img of document.images)img.loading='eager';await Promise.race([Promise.all([...document.images].map(x=>x.decode().catch(()=>{}))),new Promise(r=>setTimeout(r,5000))]);});
   const file=path.join(out,name+'-'+width+'.png');await page.screenshot({path:file,fullPage:true});report.screens.push(path.relative(process.cwd(),file));
   if(phase==='after'){
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),name+' overflow '+width);
    assert.equal(await page.getByText('Resultados declarados no currículo. A data final da Compass UOL está pendente de confirmação; vínculos simultâneos foram preservados.',{exact:true}).count(),0);
    if(name==='home'){
     assert.equal(await page.locator('#artigos .home-article-card').count(),Math.min(4,articles.length));
     assert.deepEqual(await page.locator('#artigos .home-article-card h3').allTextContents(),articles.slice(0,4).map(x=>x.title));
    }
    if(name==='artigos')assert.deepEqual(await page.locator('main article h3').allTextContents(),articles.map(x=>x.title));
    if(name!=='cms'){
     const covers=await page.locator('[data-article-cover]').evaluateAll(nodes=>nodes.map(n=>{const r=n.getBoundingClientRect(),img=n.querySelector('img');return {ratio:r.width/r.height,fit:img&&getComputedStyle(img).objectFit,loaded:!img||img.complete&&img.naturalWidth>0};}));
     for(const cover of covers){assert(Math.abs(cover.ratio-16/9)<.02);assert(cover.loaded);if(cover.fit)assert.equal(cover.fit,'contain');}
     report.checks.push({name,width,covers:'16:9, contain, original fully visible'});
    }else{
     await page.getByRole('button',{name:'Mídia',exact:true}).click();await page.screenshot({path:path.join(out,'cms-media-'+width+'.png'),fullPage:true});
     await page.getByRole('button',{name:'Publicação',exact:true}).click();assert(await page.getByText(/os quatro artigos publicados mais recentes/).count());await page.screenshot({path:path.join(out,'cms-publicacao-'+width+'.png'),fullPage:true});
    }
   }
  }
  if(phase==='after'&&process.env.QA_CAPTURE_ONLY){
   for(const [name,url] of routes)for(const zoom of [1,1.25,1.5,2]){
    await page.setViewportSize({width:1440,height:1000});await page.goto(base+url,{waitUntil:'networkidle'});
    await worker.evaluate(async({base,zoom})=>{const tabs=await chrome.tabs.query({});await chrome.tabs.setZoom(tabs.find(x=>x.url?.startsWith(base)).id,zoom);},{base,zoom});
    await page.screenshot({path:path.join(out,name+'-zoom-'+Math.round(zoom*100)+'.png'),fullPage:true});
    const actual=await page.evaluate(()=>({ratio:devicePixelRatio,width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1}));assert(Math.abs(actual.ratio-zoom)<.05);assert(!actual.overflow);report.pages.push({url,zoom,...actual});
   }
  }
  if(phase==='after'&&!process.env.QA_CAPTURE_ONLY){
   const publicRoutes=['/','/artigos','/sobre','/experiencia','/cases','/privacidade',...['projetos','cases','artigos','videos'].flatMap(m=>(content.modules[m]||[]).map(x=>'/'+m+'/'+x.slug))];
   const schemas=await (await context.request.get(base+'/api/admin/cms/schema')).json();
   const editors=[];for(const [module,schema] of Object.entries(schemas)){const rows=await (await context.request.get(base+'/api/admin/cms/'+module+'?limit=1')).json();if(rows.items[0])editors.push('/admin/'+module+'/'+rows.items[0].id);if(!schema.singleton)editors.push('/admin/'+module+'/novo');}
   const adminRoutes=[...editors,'/admin','/admin/auditoria','/admin/seguranca','/admin/login','/admin/recuperar-senha','/admin/redefinir-senha',...Object.keys(content.modules).map(m=>'/admin/'+m),...list.items.slice(0,1).map(x=>'/admin/artigos/'+x.id),'/admin/artigos/importar'];
   for(const url of [...new Set([...publicRoutes,...adminRoutes])])for(const [viewport,zoom] of [[1440,1],[1440,1.25],[1440,1.5],[1440,2],[768,1],[390,1]]){
    // Chrome tabs.setZoom changes actual browser zoom, including DPR and layout viewport.
    await page.setViewportSize({width:viewport,height:1000});
    const r=await page.goto(base+url,{waitUntil:'networkidle'});if(r.status()===404&&url.startsWith('/videos/'))continue;
    assert(r.ok(),url+' HTTP '+r.status());
    await worker.evaluate(async({base,zoom})=>{const tabs=await chrome.tabs.query({});const tab=tabs.find(x=>x.url?.startsWith(base));await chrome.tabs.setZoom(tab.id,zoom);},{base,zoom});
    await page.waitForTimeout(100);
    const actual=await page.evaluate(()=>({ratio:devicePixelRatio,width:innerWidth}));
    assert(Math.abs(actual.ratio-zoom)<.05,'Native zoom: '+JSON.stringify(actual));
    if(viewport===1440&&routes.some(x=>x[1]===url))await page.screenshot({path:path.join(out,(url==='/'?'home':url==='/artigos'?'artigos':'cms')+'-zoom-'+Math.round(zoom*100)+'.png'),fullPage:true});
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),url+' reflow '+zoom);
    const small=await page.locator('body').evaluateAll(roots=>[...new Set(roots.flatMap(root=>[...root.querySelectorAll('*')]))].filter(e=>e.childNodes.length&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden'&&parseFloat(getComputedStyle(e).fontSize)<16).slice(0,12).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,70),size:getComputedStyle(e).fontSize})));
    assert.deepEqual(small,[],url+' small text');report.pages.push({url,viewportWidth:viewport,zoom,viewport:actual.width,nativeZoom:actual.ratio,overflow:false,minFont:16});if(report.pages.length%40===0)console.log('Validated '+report.pages.length+' page/viewport/zoom combinations');
   }
   await worker.evaluate(async(base)=>{const tabs=await chrome.tabs.query({});await chrome.tabs.setZoom(tabs.find(x=>x.url?.startsWith(base)).id,1);},base);
   // Tags persist through the actual CMS editor, without touching a published article.
   await page.goto(base+'/admin/artigos/novo');await page.locator('#field-title').fill('Controle temporário de tags');
   await page.locator('#field-tags').fill('  Segurança   Digital  ');await page.getByRole('button',{name:'Adicionar tag',exact:true}).click();
   await page.locator('#field-tags').fill('seguranca digital');await page.getByRole('button',{name:'Adicionar tag',exact:true}).click();assert.equal(await page.getByRole('button',{name:/Remover tag/}).count(),1);
   await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo'}).waitFor();
   const draft=(await (await context.request.get(base+'/api/admin/cms/artigos?q=Controle%20temporário%20de%20tags')).json()).items[0];assert.deepEqual(draft.data.tags,['Segurança Digital']);
   await page.goto(base+'/admin/artigos/'+draft.id);await page.getByRole('button',{name:'Remover tag Segurança Digital',exact:true}).waitFor();
   const csrf=(await (await context.request.get(base+'/api/admin/auth/csrf')).json()).csrfToken;const deleted=await context.request.delete(base+'/api/admin/cms/artigos/'+draft.id+'?version='+draft.version,{headers:{Origin:base,'X-CSRF-Token':csrf}});assert(deleted.ok());
   report.checks.push('tags: create, normalize, deduplicate, save, reload; QA draft removed');
   assert.deepEqual(report.errors,[]);
  }
  report.result='passed';
 }catch(e){report.result='failed';report.failure=e.message;await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});throw e;}
 finally{await fs.writeFile(path.join(out,process.env.QA_CAPTURE_ONLY?'capture-report.json':'report.json'),JSON.stringify(report,null,2));await context.close();}
})().catch(e=>{console.error(e);process.exit(1)});
