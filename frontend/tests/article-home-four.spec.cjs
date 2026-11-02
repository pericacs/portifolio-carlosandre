const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),assert=require('node:assert/strict');
const base='http://127.0.0.1:8097';
(async()=>{
 const browser=await chromium.launch(),context=await browser.newContext(),page=await context.newPage(),created=[];
 async function api(url,method='GET',data){const headers={Origin:base};if(method!=='GET')headers['X-CSRF-Token']=(await (await context.request.get(base+'/api/admin/auth/csrf')).json()).csrfToken;const r=await context.request.fetch(base+'/api/admin'+url,{method,headers,data});assert(r.ok(),await r.text());return r.json();}
 try{
  const credentials=JSON.parse(await fs.readFile('.private/visual-cms/credentials.json','utf8'));await page.goto(base+'/admin/login');await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);await page.getByRole('button',{name:'Entrar no painel',exact:true}).click();await page.waitForURL(base+'/admin');
  for(let n=1;n<=5;n++){
   let row=await api('/cms/artigos','POST',{data:{title:'Controle cronológico '+n,slug:'qa-home-four-'+n+'-'+Date.now(),publishedDate:'2030-01-0'+n,sortOrder:-n,body:'<p>Conteúdo temporário exclusivo do teste isolado.</p>',description:'Resumo integral de controle da ordenação e responsividade.',featured:n%2===0,spotlight:n%2===1,tags:[]}});created.push(row.id);row=await api('/cms/artigos/'+row.id+'/publish','POST',{version:row.version});
  }
  const expected=[5,4,3,2].map(n=>'Controle cronológico '+n);
  for(const width of [1440,768,390]){
   await page.setViewportSize({width,height:1000});await page.goto(base+'/',{waitUntil:'networkidle'});
   assert.deepEqual(await page.locator('#artigos h3').allTextContents(),expected);
   const cards=page.locator('#artigos .home-article-card');assert.equal(await cards.count(),4);
   const positions=await cards.evaluateAll(ns=>ns.map(n=>({x:n.getBoundingClientRect().x,y:n.getBoundingClientRect().y,height:n.getBoundingClientRect().height})));
   const columns=width===1440?4:width===768?2:1;
   assert.equal(new Set(positions.slice(0,columns).map(x=>x.y)).size,1);
   assert.equal(new Set(positions.slice(0,columns).map(x=>x.height)).size,1);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   assert.equal(await cards.locator('[class*=tags] span').count(),0,'no invented tags');
  }
  await page.goto(base+'/artigos',{waitUntil:'networkidle'});assert.deepEqual((await page.locator('main article h3').allTextContents()).slice(0,5),[5,4,3,2,1].map(n=>'Controle cronológico '+n));
  const draft=await api('/cms/artigos','POST',{data:{title:'Controle de substituição no CMS',slug:'qa-replacement-'+Date.now(),body:'<p>Rascunho temporário de controle editorial.</p>'}});created.push(draft.id);
  await page.goto(base+'/admin/artigos/'+draft.id,{waitUntil:'networkidle'});await page.getByRole('button',{name:'Publicação',exact:true}).click();await page.locator('#field-featured').check();await page.locator('#field-spotlight').check();
  const warnings=await page.locator('[role=status]').allTextContents();assert(warnings.join(' ').includes('Controle cronológico 4'));assert(warnings.join(' ').includes('Controle cronológico 5'));
  await page.getByRole('button',{name:'Mídia',exact:true}).click();await page.locator('#field-coverPosition').selectOption('Topo');await page.getByRole('button',{name:'Salvar rascunho',exact:true}).click();await page.getByRole('status').filter({hasText:'Rascunho salvo'}).waitFor();
  const saved=await api('/cms/artigos/'+draft.id);assert.equal(saved.data.coverPosition,'Topo');assert.equal(saved.published_data,null);
  const owners=(await api('/cms/article-settings')).owners;assert.equal(owners.featured[0].title,'Controle cronológico 4');assert.equal(owners.spotlight[0].title,'Controle cronológico 5');
  await fs.writeFile('docs/screenshots/visual-cms/four-articles-report.json',JSON.stringify({result:'passed',widths:[1440,768,390],publishedFixtures:5,homeCount:4,ordering:'publication date descending, flags and manual order ignored',cards:'aligned with equal row heights',tags:'no invented tags',cms:'both replacement titles shown; cover alignment persists; draft keeps published ownership'},null,2));
 }finally{for(const id of created){const row=await api('/cms/artigos/'+id);await api('/cms/artigos/'+id+'?version='+row.version,'DELETE');}await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
