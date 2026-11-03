const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{execFileSync}=require('node:child_process');
const base='http://127.0.0.1:8098',phase=process.argv[2]||'after';
const root=path.resolve('docs/screenshots/home-ux-02'),out=path.join(root,phase),state=path.resolve('.private/home-ux-02');
const hash=value=>crypto.createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const protectedSections=['.site-header','#projetos','#consultoria','#competencias','#artigos','#videos','#contato','.footer'];
async function signature(page,selector){return page.locator(selector).evaluateAll(roots=>roots.map(root=>({text:root.innerText,images:[...root.querySelectorAll('img')].map(e=>[e.getAttribute('src'),e.getAttribute('alt')]),links:[...root.querySelectorAll('a')].map(e=>e.getAttribute('href')),styles:[root,...root.querySelectorAll('*')].filter(e=>!['SCRIPT','STYLE','LINK','NOSCRIPT'].includes(e.tagName)&&e.getClientRects().length).map(e=>{const s=getComputedStyle(e);return ['fontSize','fontFamily','lineHeight','color','backgroundColor','padding','margin','display','gridTemplateColumns','gap','width','height'].map(k=>s[k]);})})));}
async function ready(page){await page.evaluate(async()=>{await document.fonts.ready;for(const img of document.images)img.loading='eager';await Promise.race([Promise.all([...document.images].map(x=>x.decode().catch(()=>{}))),new Promise(r=>setTimeout(r,3000))]);});}
(async()=>{
 await fs.mkdir(out,{recursive:true});const extension=path.resolve('scripts/browser-zoom-extension');
 const context=await chromium.launchPersistentContext('',{executablePath:process.env.QA_CHROME||(process.platform==='win32'?'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe':chromium.executablePath()),ignoreDefaultArgs:['--disable-extensions'],headless:true,reducedMotion:'reduce',args:['--disable-extensions-except='+extension,'--load-extension='+extension]});
 const worker=context.serviceWorkers()[0]||await context.waitForEvent('serviceworker'),page=await context.newPage();page.setDefaultTimeout(15000);
 const report={phase,screens:[],layouts:[],regressions:[],errors:[]};page.on('pageerror',e=>report.errors.push(e.message));
 const baseline=phase==='after'?JSON.parse(await fs.readFile(path.join(state,'baseline-dom.json'),'utf8')):{sections:{},projects:{}};
 async function zoom(value){await worker.evaluate(async({base,value})=>{const tabs=await chrome.tabs.query({});await chrome.tabs.setZoom(tabs.find(x=>x.url?.startsWith(base)).id,value);},{base,value});await page.waitForTimeout(80);assert(Math.abs(await page.evaluate(()=>devicePixelRatio)-value)<.05);}
 try{
  const response=await context.request.get(base+'/api/content');assert(response.ok());const content=await response.text();
  if(phase==='before')baseline.contentHash=hash(content);else assert.equal(hash(content),baseline.contentHash,'CMS public snapshots must stay unchanged');
  for(const width of [1440,768,390]){
   await page.setViewportSize({width,height:1000});await page.goto(base+'/',{waitUntil:'networkidle'});await zoom(1);await ready(page);
   const full=path.join(out,'home-'+width+'.png');await page.screenshot({path:full,fullPage:true});report.screens.push(path.relative(process.cwd(),full));
   await page.locator('#inicio').screenshot({path:path.join(out,'hero-'+width+'.png')});await page.locator('#experiencia').screenshot({path:path.join(out,'trajectory-'+width+'.png')});
   baseline.sections[width]??={};
   for(const selector of protectedSections){const actual=hash(await signature(page,selector));if(phase==='before')baseline.sections[width][selector]=actual;else{assert.equal(actual,baseline.sections[width][selector],selector+' visual regression at '+width);report.regressions.push({selector,width,unchanged:true});}}
   if(phase==='after'){
    const panels=page.locator('[aria-label="Áreas de atuação e propósito"]> *'),cards=page.locator('#experiencia [data-experience]');
    assert.equal(await panels.count(),5);assert.deepEqual(await panels.locator('strong').allTextContents(),['Produtos Digitais','Dados & IA','Consultoria Estratégica','Parcerias & Investimentos']);
    assert.deepEqual(await cards.evaluateAll(es=>es.map(e=>e.dataset.experience)),['compass-cef','rpe-tech','alibin','others']);
    assert.deepEqual(await cards.last().locator('li a').evaluateAll(es=>es.map(e=>e.textContent)),['Fastconnect Founder · CEO · Principal Solution Architect','Manager Systems','Cetil Sistemas de Informação','SENAI/SC','Unimed','Someday']);
    const geometry=await panels.evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y+scrollY,height:r.height};}));
    const cardGeometry=await cards.evaluateAll(es=>es.map(e=>({x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y+scrollY})));
    if(width===1440){assert.equal(new Set(geometry.map(x=>x.y)).size,1);assert.equal(new Set(geometry.map(x=>x.height)).size,1);assert.equal(new Set(cardGeometry.map(x=>x.y)).size,1);}
    if(width===768)assert.equal(new Set(cardGeometry.slice(0,2).map(x=>x.y)).size,1);
    if(width===390)assert.equal(new Set(cardGeometry.map(x=>x.x)).size,1);
    const visuals=await page.locator('#inicio').evaluate(root=>{const image=root.querySelector('img'),title=root.querySelector('h1'),panels=root.querySelector('[aria-label="Áreas de atuação e propósito"]');return {imageTop:image.getBoundingClientRect().top+scrollY,titleTop:title.getBoundingClientRect().top+scrollY,imageBottom:image.getBoundingClientRect().bottom+scrollY,panelTop:panels.getBoundingClientRect().top+scrollY,loaded:image.complete&&image.naturalWidth>0};});
    assert(visuals.loaded);assert(visuals.panelTop>=visuals.imageBottom-1);if(width===1440)assert(visuals.imageTop<=visuals.titleTop,'Photo must be raised to title level');
    report.layouts.push({width,panels:geometry,cards:cardGeometry,...visuals});
   }
   await page.goto(base+'/experiencia',{waitUntil:'networkidle'});await ready(page);await page.screenshot({path:path.join(out,'experience-full-'+width+'.png'),fullPage:true});
   const timeline=await page.locator('.timeline').textContent();if(phase==='before')baseline['timeline-'+width]=hash(timeline);else assert.equal(hash(timeline),baseline['timeline-'+width],'All professional data must stay unchanged');
   assert.equal(await page.locator('.timeline>article').count(),9);
  }
  for(const slug of ['smartfamily','onstar-scd','beloria']){
   await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/projetos/'+slug,{waitUntil:'networkidle'});await ready(page);const fingerprint=hash(await signature(page,'body'));
   if(phase==='before')baseline.projects[slug]=fingerprint;else{assert.equal(fingerprint,baseline.projects[slug],slug+' presentation must stay unchanged');report.regressions.push({project:slug,unchanged:true});}
  }
  if(phase==='after'){
   const original=execFileSync('git',['show','875b689:frontend/public/images/carlos-andre-executivo.png'],{maxBuffer:16*1024*1024});
   const current=await fs.readFile('frontend/public/images/carlos-andre-executivo.png');assert(original.equals(current),'Original portrait bytes must stay unchanged');
   report.regressions.push({portraitSha256:crypto.createHash('sha256').update(current).digest('hex'),originalUnchanged:true});
   for(const [width,factor] of [[1440,1],[1440,1.25],[1440,1.5],[1440,2],[768,1],[390,1]])for(const route of ['/','/experiencia']){
    await page.setViewportSize({width,height:1000});await page.goto(base+route,{waitUntil:'networkidle'});await zoom(factor);await ready(page);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),route+' overflow at '+width+' / '+factor);
    const small=await page.locator('body').evaluateAll(roots=>roots.flatMap(root=>[...root.querySelectorAll('*')]).filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden'&&[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<16).map(e=>({tag:e.tagName,text:e.textContent.slice(0,50),size:getComputedStyle(e).fontSize})));
    assert.deepEqual(small,[],route+' font regression at '+width+' / '+factor);
    if(width===1440){await page.screenshot({path:path.join(out,(route==='/'?'home':'experience')+'-zoom-'+Math.round(factor*100)+'.png'),fullPage:true});}
    report.layouts.push({route,width,zoom:factor,cssWidth:await page.evaluate(()=>innerWidth),overflow:false,minFont:16});
   }
   await page.setViewportSize({width:390,height:1000});await page.goto(base+'/',{waitUntil:'networkidle'});await zoom(1);
   await page.getByRole('button',{name:'Abrir menu',exact:true}).click();assert.equal(await page.getByRole('button',{name:'Fechar menu',exact:true}).count(),1);await page.locator('#main-nav').getByRole('link',{name:'Projetos',exact:true}).click();assert.equal(new URL(page.url()).hash,'#projetos');
   for(const [label,fragment] of [['Conheça meus projetos','#projetos'],['Fale comigo','#contato'],['Explore os vídeos','#videos']]){await page.getByRole('link',{name:label,exact:true}).click();assert.equal(new URL(page.url()).hash,fragment);}
   await page.locator('#experiencia details').first().locator('summary').click();assert(await page.locator('#experiencia details').first().getAttribute('open')!==null);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   await page.getByRole('link',{name:'Conheça minha trajetória',exact:true}).click();await page.waitForURL(base+'/experiencia');for(const id of ['compass-cef','rpe-tech','alibin','fastconnect','manager-systems','cetil','senai','unimed','someday'])assert.equal(await page.locator('#'+id).count(),1);
   await page.goto(base+'/#experiencia');await page.getByRole('link',{name:'Fastconnect Founder · CEO · Principal Solution Architect',exact:true}).click();await page.waitForURL(base+'/experiencia#fastconnect');
   await page.goto(base+'/');const firstCTA=page.getByRole('link',{name:'Conheça meus projetos',exact:true});await firstCTA.focus();await page.keyboard.press('Tab');assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Fale comigo');
   const credentials=JSON.parse(await fs.readFile(path.join(state,'credentials.json'),'utf8'));await page.goto(base+'/admin/login');await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);await page.getByRole('button',{name:'Entrar no painel',exact:true}).click();await page.waitForURL(base+'/admin');await page.goto(base+'/admin/artigos',{waitUntil:'networkidle'});assert.equal(await page.getByRole('heading',{name:'Artigos',exact:true}).count(),1);assert.equal(await page.locator('p[role=alert]').count(),0);
   const dataAfter=await (await context.request.get(base+'/api/content')).text();assert.equal(hash(dataAfter),baseline.contentHash);
   report.regressions.push('CMS snapshots, all nine experiences, navigation, CTAs, Fastconnect anchor, expandable results/technologies preserved');
   assert.deepEqual(report.errors,[]);
  }else await fs.writeFile(path.join(state,'baseline-dom.json'),JSON.stringify(baseline));
  report.result='passed';
 }catch(error){report.result='failed';report.failure=error.message;await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});throw error;}
 finally{await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));await context.close();}
})().catch(error=>{console.error(error);process.exit(1)});
