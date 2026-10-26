// End-to-end article synchronization only in verify-production.py's disposable stack.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const base=process.env.RECOVERY_BASE_URL;assert(base&&new URL(base).hostname==='127.0.0.1');
(async()=>{
 const browser=await chromium.launch(),context=await browser.newContext(),page=await context.newPage(),errors=[];
 const out=process.env.RECOVERY_OUTPUT;await fs.mkdir(out,{recursive:true});
 const report={result:'running',screenshots:[],comparisons:[]};page.on('pageerror',e=>errors.push(e.message));
 const signature=locator=>locator.evaluate(node=>{const style=getComputedStyle(node);return {text:node.textContent,images:[...node.querySelectorAll('img')].map(x=>[x.getAttribute('src'),x.getAttribute('alt')]),links:[...node.querySelectorAll('a')].map(x=>x.getAttribute('href')),styles:['fontFamily','fontSize','color','backgroundColor','padding','margin','display','gridTemplateColumns','gap'].map(key=>style[key])};});
 async function screenshot(label,width){await page.setViewportSize({width,height:1000});if(await page.locator('#artigos').count())await page.locator('#artigos').scrollIntoViewIfNeeded();await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(x=>x.decode().catch(()=>{})));});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));const file=path.join(out,label+'-'+width+'.png');report.screenshots.push(file);await page.screenshot({path:file,fullPage:true,animations:'disabled'});}
 async function api(url,method='GET',data){const headers={Origin:base};if(method!=='GET')headers['X-CSRF-Token']=(await (await context.request.get(base+'/api/admin/auth/csrf')).json()).csrfToken;const r=await context.request.fetch(base+'/api/admin'+url,{method,headers,data});assert(r.ok(),method+' '+url+': '+r.status()+' '+await r.text());return r.json();}
 async function create(title,slug,publishedDate,sortOrder,spotlight=false){return api('/cms/artigos','POST',{data:{title,slug,publishedDate,sortOrder,spotlight,featured:false,visible:true,body:'<p>Conteúdo de controle editorial preservado.</p>',description:'Resumo de controle '+title,cover:'/images/avallow-fintech.png',categories:['Segurança'],tags:['CMS'],readingMode:'Interno'}});}
 async function publish(row){return api('/cms/artigos/'+row.id+'/publish','POST',{version:row.version});}
 async function home(){const r=await page.goto(base+'/',{waitUntil:'networkidle'});assert(r.headers()['cache-control'].includes('no-store'));return page.locator('#artigos .home-article-card');}
 async function publications(){const r=await context.request.get(base+'/api/content');assert.equal(r.headers()['cache-control'],'no-store');return (await r.json()).modules.artigos;}
 try{
  const credentials=JSON.parse(await fs.readFile(process.env.RECOVERY_FIXTURE,'utf8'));await page.goto(base+'/admin/login');await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL(base+'/admin');
  const old=await publish(await create('Split Payment do bem e Split Payment do mal','oldest','2026-10-07',-999)),middle=await publish(await create('Engenharia de dados aplicada ao Split Payment do Bem','middle','2026-10-13',999));
  await home();await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.fonts.ready);
  const sections=['projetos','experiencia','competencias','videos'],baseline={};for(const id of sections)baseline[id]=await signature(page.locator('#'+id));
  await screenshot('home-before',1440);await screenshot('home-before',390);
  const bytes=await fs.readFile(process.env.DOCX_REFERENCE||path.resolve('.private/docx-import-check/reference.docx'));
  const csrf=(await api('/auth/csrf')).csrfToken,r=await context.request.post(base+'/api/admin/docx/preview',{headers:{Origin:base,'X-CSRF-Token':csrf},multipart:{file:{name:'reference.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:bytes}}});assert.equal(r.status(),201);
  const stage=await r.json(),data={...stage.data,featured:false,spotlight:false};assert.equal(stage.sections,10);assert.equal(stage.images.length,4);
  await api('/docx/staging/'+stage.token+'/render','POST',{data});const draft=(await api('/docx/staging/'+stage.token+'/commit','POST',{data,reviewed:true})).entry;
  assert.equal((await publications()).length,2);const split=await publish(draft);
  let cards=await home();assert.deepEqual(await cards.locator('h3').allTextContents(),[data.title,middle.title,old.title]);
  const title='O golpe de R$ 813 milhões não precisou de hacker';let newest=await create(title,'newest','',-10000,true);
  assert.equal((await publications()).length,3);assert.equal(await (await home()).filter({hasText:title}).count(),0);
  newest=await publish(newest);const date=newest.published_at.slice(0,10);
  let all=await publications();assert.deepEqual(all.map(x=>x.id),[newest.id,split.id,middle.id,old.id]);assert.equal(all[0].publishedDate,date);assert.equal(all[0].featured,false);
  cards=await home();assert.equal(await cards.count(),3);assert.deepEqual(await cards.locator('h3').allTextContents(),[title,data.title,middle.title]);
  assert.equal(await cards.first().locator('img').getAttribute('src'),newest.published_data.cover);assert.equal(await cards.first().locator('h3 a').getAttribute('href'),'/artigos/newest');
  assert.equal(await cards.first().locator('p').innerText(),newest.published_data.description);
  for(const width of [1440,390])await screenshot('home-recent',width);
  await page.setViewportSize({width:1440,height:1000});for(const id of sections){assert.deepEqual(await signature(page.locator('#'+id)),baseline[id]);report.comparisons.push({section:id,contentAndStyles:'unchanged'});}
  await page.goto(base+'/artigos',{waitUntil:'networkidle'});assert.equal(await page.getByRole('heading',{name:title,level:2,exact:true}).count(),1);assert.equal(await page.getByRole('heading',{name:title,level:3,exact:true}).count(),1);
  assert.deepEqual(await page.locator('main article h3').allTextContents(),[title,data.title,middle.title,old.title]);
  for(const width of [1440,390])await screenshot('listing-recent',width);
  // Backend pagination uses the exact sequence consumed by both pages.
  const a=await (await context.request.get(base+'/api/articles?limit=2&offset=0')).json(),b=await (await context.request.get(base+'/api/articles?limit=2&offset=2')).json();assert.equal(a.total,4);assert.deepEqual([...a.items,...b.items].map(x=>x.id),all.map(x=>x.id));
  const anonymous=await browser.newContext();assert.equal((await anonymous.request.get(base+data.cover)).status(),200);await anonymous.close();
  // Save pending edits through the existing editor; keep the previous public snapshot.
  await page.goto(base+'/admin/artigos/'+newest.id);await page.getByRole('button',{name:'Conteúdo',exact:true}).click();await page.locator('#field-description').fill('Resumo revisado pelo painel.');await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo.'}).waitFor();
  assert.equal((await publications())[0].description,newest.published_data.description);
  await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();
  all=await publications();assert.equal(all[0].id,newest.id);assert.equal(all[0].publishedDate,date);assert.equal(all[0].description,'Resumo revisado pelo painel.');
  assert.equal(await (await home()).first().locator('p').innerText(),'Resumo revisado pelo painel.');
  let current=await api('/cms/artigos/'+newest.id);current=await api('/cms/artigos/'+newest.id,'PUT',{version:current.version,data:{...current.data,spotlight:false,sortOrder:9999}});current=await publish(current);assert.equal((await publications())[0].id,newest.id);
  await api('/cms/artigos/'+newest.id+'/unpublish','POST',{version:current.version});assert.deepEqual(await (await home()).locator('h3').allTextContents(),[data.title,middle.title,old.title]);
  await page.goto(base+'/artigos');assert.equal(await page.getByRole('heading',{name:title,exact:true}).count(),0);
  assert.deepEqual((await api('/cms/artigos/'+old.id)).published_data,old.published_data);assert.deepEqual((await api('/cms/artigos/'+middle.id)).published_data,middle.published_data);
  assert.deepEqual(errors,[]);report.result='passed';report.checks=['shared chronology before pagination','Home always three newest without featured filter','spotlight also in normal grid','new publication automatically visible','draft edits preserve public snapshot','publish/edit/unpublish synchronization','flags/manual order do not affect recency','existing editor and other sections preserved'];await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(error){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});throw error;}finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
