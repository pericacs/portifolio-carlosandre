// Only the disposable Docker environment created by verify-production.py.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
const base=process.env.RECOVERY_BASE_URL;assert(base&&new URL(base).hostname==='127.0.0.1');
(async()=>{
 const browser=await chromium.launch(),context=await browser.newContext(),page=await context.newPage(),errors=[];
 const out=process.env.RECOVERY_OUTPUT;await fs.mkdir(out,{recursive:true});
 const report={result:'running',screenshots:[],comparisons:[]};page.on('pageerror',e=>errors.push(e.message));
 async function screenshot(label,width){await page.setViewportSize({width,height:1000});await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(x=>x.decode().catch(()=>{})));});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));const file=path.join(out,label+'-'+width+'.png');report.screenshots.push(file);return page.screenshot({path:file,fullPage:true,animations:'disabled'});}
 async function api(url,method='GET',data){const headers={Origin:base};if(method!=='GET')headers['X-CSRF-Token']=(await (await context.request.get(base+'/api/admin/auth/csrf')).json()).csrfToken;const r=await context.request.fetch(base+'/api/admin'+url,{method,headers,data});assert(r.ok(),method+' '+url+': '+r.status()+' '+await r.text());return r.json();}
 async function create(title,slug,order,featured=true,publishedDate='2026-10-01'){return api('/cms/artigos','POST',{data:{title,slug,description:'Resumo de controle '+title,body:'<p>Conteúdo de controle preservado.</p>',categories:['Dados'],tags:['Engenharia'],cover:'/images/avallow-fintech.png',readingMode:'Interno',visible:true,featured,publishedDate,sortOrder:order}});}
 async function publish(row){return api('/cms/artigos/'+row.id+'/publish','POST',{version:row.version});}
 async function home(){const response=await page.goto(base+'/',{waitUntil:'networkidle'});assert(response.headers()['cache-control'].includes('no-store'));return page.locator('#artigos .home-article-card');}
 try{
  const credentials=JSON.parse(await fs.readFile(process.env.RECOVERY_FIXTURE,'utf8'));await page.goto(base+'/admin/login');await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL(base+'/admin');
  const oldA=await publish(await create('Artigo anterior A','artigo-anterior-a',5,true,'2026-10-07')),oldB=await publish(await create('Artigo anterior B','artigo-anterior-b',0,true,'2026-10-13'));
  let cards=await home();assert.equal(await cards.count(),2);
  await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.fonts.ready);
  const protectedSections=['projetos','experiencia','competencias','videos'],baseline={};
  const signature=locator=>locator.evaluate(node=>{const style=getComputedStyle(node);return {text:node.textContent,images:[...node.querySelectorAll('img')].map(x=>[x.getAttribute('src'),x.getAttribute('alt')]),links:[...node.querySelectorAll('a')].map(x=>x.getAttribute('href')),styles:['fontFamily','fontSize','color','backgroundColor','padding','margin','display','gridTemplateColumns','gap'].map(key=>style[key])};});
  for(const id of protectedSections)baseline[id]=await signature(page.locator('#'+id));
  await screenshot('home-before',1440);await screenshot('home-before',390);
  const source=process.env.DOCX_REFERENCE||path.resolve('.private/docx-import-check/reference.docx');const bytes=await fs.readFile(source);
  const csrf=(await api('/auth/csrf')).csrfToken;
  const response=await context.request.post(base+'/api/admin/docx/preview',{headers:{Origin:base,'X-CSRF-Token':csrf},multipart:{file:{name:'reference.docx',mimeType:'application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer:bytes}}});assert.equal(response.status(),201);
  const stage=await response.json();assert.equal(stage.sections,10);assert.equal(stage.images.length,4);
  const data={...stage.data,spotlight:true,featured:false};await api('/docx/staging/'+stage.token+'/render','POST',{data});
  const draft=(await api('/docx/staging/'+stage.token+'/commit','POST',{data,reviewed:true})).entry;
  assert.equal(draft.status,'draft');assert.equal(await (await home()).filter({hasText:'O SPLIT DO MAL'}).count(),0);
  let split=await publish(draft);
  await page.goto(base+'/artigos',{waitUntil:'networkidle'});assert.equal(await page.getByRole('heading',{name:'O SPLIT DO MAL',exact:true}).count(),1);
  assert.equal(await (await home()).count(),2);
  await page.goto(base+'/admin/artigos/'+split.id);await page.getByRole('button',{name:'Publicação',exact:true}).click();
  const feature=page.getByLabel('Destaque na Home',{exact:true});await feature.waitFor();assert(!(await feature.isChecked()));await feature.check();await page.getByLabel('Ordem da listagem de artigos',{exact:true}).fill('-20');
  await screenshot('admin-home-controls',1440);
  await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo.'}).waitFor();
  assert.equal((await context.request.get(base+'/api/content')).headers()['cache-control'],'no-store');
  const publicBefore=(await (await context.request.get(base+'/api/content')).json()).modules.artigos.find(x=>x.id===split.id);assert.equal(publicBefore.featured,false);
  await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();
  cards=await home();assert.equal(await cards.count(),3);assert.equal(await cards.first().locator('h3').innerText(),'O SPLIT DO MAL');
  const card=cards.filter({hasText:'O SPLIT DO MAL'});await card.scrollIntoViewIfNeeded();await card.locator('img').evaluate(x=>x.decode());assert.equal(await card.locator('img').getAttribute('src'),data.cover);assert.equal(await card.locator('h3 a').getAttribute('href'),'/artigos/o-split-do-mal');
  const anonymous=await browser.newContext();const publicImage=await anonymous.request.get(base+data.cover);assert.equal(publicImage.status(),200);assert.equal(require('node:crypto').createHash('sha256').update(await publicImage.body()).digest('hex'),stage.images.find(x=>x.url===data.cover).sha256);await anonymous.close();
  assert.deepEqual(await card.locator('.tags span').allTextContents(),data.categories);
  assert.equal(await card.locator('p').innerText(),data.description);assert(await card.locator('img').evaluate(x=>x.complete&&x.naturalWidth>0));
  for(const width of [1440,390])await screenshot('home-featured',width);
  await page.setViewportSize({width:1440,height:1000});
  for(const id of protectedSections){assert.deepEqual(await signature(page.locator('#'+id)),baseline[id],id+' content/style changed');report.comparisons.push({section:id,contentAndStyles:'unchanged'});}
  let next=await create('Novo destaque A','novo-destaque-a',30,true,'2026-10-20');assert.equal(await (await home()).count(),3);next=await publish(next);
  await publish(await create('Novo destaque B','novo-destaque-b',10,true,'2026-10-21'));cards=await home();assert.equal(await cards.count(),5);assert.deepEqual(await cards.locator('h3').allTextContents(),['Novo destaque B','Novo destaque A','O SPLIT DO MAL','Artigo anterior B','Artigo anterior A']);
  await page.goto(base+'/admin/artigos/'+next.id);await page.getByRole('button',{name:'Publicação',exact:true}).click();await page.getByLabel('Ordem da listagem de artigos',{exact:true}).fill('-30');await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();
  assert.equal(await (await home()).first().locator('h3').innerText(),'Novo destaque B');
  await page.goto(base+'/admin/artigos/'+next.id);await page.getByRole('button',{name:'Publicação',exact:true}).click();await page.getByLabel('Destaque na Home',{exact:true}).uncheck();await page.getByRole('button',{name:'Publicar',exact:true}).click();await page.getByRole('status').filter({hasText:'Publicado.'}).waitFor();assert.equal(await (await home()).count(),4);
  await page.goto(base+'/artigos/novo-destaque-a');await page.getByRole('heading',{name:'Novo destaque A',exact:true}).waitFor();
  assert.deepEqual((await api('/cms/artigos/'+oldA.id)).published_data,oldA.published_data);assert.deepEqual((await api('/cms/artigos/'+oldB.id)).published_data,oldB.published_data);
  const final=await api('/cms/artigos/'+split.id);assert.equal(final.published_data.featured,true);assert.equal(final.published_data.spotlight,true);assert.equal(final.published_data.cover,data.cover);assert.equal(final.id,split.id);
  assert.deepEqual(errors,[]);report.result='passed';report.splitId=split.id;report.realDocx={sections:stage.sections,images:stage.images.length};report.checks=['CMS feature and order controls','draft does not change Home','publish updates warmed Home','more than three featured articles','publication chronology overrides manual order; removal without unpublishing','unchanged other sections and publications'];await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(error){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true}).catch(()=>{});throw error;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
