const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const sharp=require(process.env.SHARP_MODULE||'sharp'),assert=require('node:assert/strict'),fs=require('node:fs/promises'),path=require('node:path'),{execFileSync}=require('node:child_process');
const patch=require('../src/data/avallow.json'),before=process.env.AVALLOW_BEFORE,after=process.env.AVALLOW_AFTER,out=process.env.AVALLOW_OUTPUT;
assert([before,after].every(x=>new URL(x).hostname==='127.0.0.1')&&before!==after);
(async()=>{
 const browser=await chromium.launch({headless:true}),ctx=await browser.newContext({reducedMotion:'reduce'}),page=await ctx.newPage(),report={comparisons:[]},snapshots=new Map();
 async function capture(base,label,width){
  await page.setViewportSize({width,height:1000});await page.goto(base,{waitUntil:'networkidle'});await page.evaluate(async()=>{await document.fonts.ready;await Promise.all([...document.images].map(x=>x.decode().catch(()=>{})));});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const cards=page.locator('#projetos .project-card'),boxes=await cards.evaluateAll(xs=>xs.map(x=>{const b=x.getBoundingClientRect();return {x:b.x,y:b.y,width:b.width,height:b.height,html:x.outerHTML};}));
  const png=await page.screenshot({path:path.join(out,label+'-'+width+'.png'),fullPage:true,animations:'disabled'});
  await page.locator('#projetos').screenshot({path:path.join(out,label+'-projects-'+width+'.png')});
  return {boxes,png};
 }
 try{
  for(const width of [1440,390])snapshots.set(width,await capture(before,'before',width));
  await page.goto(after+'/admin/login');const credentials=JSON.parse(await fs.readFile(process.env.AVALLOW_FIXTURE,'utf8'));
  await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);await page.getByRole('button',{name:'Entrar no painel'}).click();await page.waitForURL(after+'/admin');
  const security=await (await ctx.request.get(after+'/api/admin/auth/csrf')).json(),headers={Origin:after,'X-CSRF-Token':security.csrfToken};
  const items=await (await ctx.request.get(after+'/api/admin/cms/projetos')).json();
  const rows=items.items||items,target=rows.find(x=>x.slug==='onstar-scd');assert(target);
  const others=rows.filter(x=>x.id!==target.id);
  const update=()=>JSON.parse(execFileSync(process.env.AVALLOW_PYTHON,['scripts/update-avallow.py','--container',process.env.AVALLOW_CONTAINER,'--expected-version',String(target.version),'--apply'],{encoding:'utf8'}));
  assert.equal(update().status,'draft_updated');assert.equal(update().status,'already_updated');
  let row=await (await ctx.request.get(after+'/api/admin/cms/projetos/'+target.id)).json();
  for(const [key,value] of Object.entries(patch))assert.deepEqual(row.data[key],value);
  assert.equal(row.slug,'onstar-scd');assert.equal(row.data._legacy.name,'OnStar SCD');
  let history=await (await ctx.request.get(after+`/api/admin/cms/projetos/${target.id}/revisions`)).json();assert(history.some(x=>x.version===1)&&history.some(x=>x.action==='update_avallow_card'));
  // Ordinary CMS save proves fields remain editable before explicit publication.
  const saved=await ctx.request.put(after+'/api/admin/cms/projetos/'+target.id,{headers,data:{version:row.version,data:{...row.data,publicationReviewed:true}}});assert.equal(saved.status(),200);row=await saved.json();
  const published=await ctx.request.post(after+`/api/admin/cms/projetos/${target.id}/publish`,{headers,data:{version:row.version}});assert.equal(published.status(),200);
  row=await published.json();for(const [key,value] of Object.entries(patch))assert.deepEqual(row.published_data[key],value);
  for(const old of others){const current=await (await ctx.request.get(after+'/api/admin/cms/projetos/'+old.id)).json();assert.equal(current.version,old.version);}
  for(const width of [1440,390]){
   const actual=await capture(after,'after',width),prior=snapshots.get(width);
   const cards=page.locator('#projetos .project-card');assert.deepEqual(await cards.locator('h3').allTextContents(),['SmartFamily','Beloria','AVALLOW','Orquestrador IA']);
   const avallow=cards.nth(2),status=avallow.locator('.project-status');assert.equal(await status.textContent(),'Em desenvolvimento');
   assert.equal(await avallow.locator('.project-body>p').textContent(),patch.description);assert.deepEqual(await avallow.locator('.tags span').allTextContents(),patch.tags);
   const styles=await cards.evaluateAll(xs=>[xs[1],xs[2]].map(x=>{const el=x.querySelector('.project-status'),c=getComputedStyle(el);return ['backgroundColor','color','fontSize','fontWeight','lineHeight','padding','minHeight'].map(k=>c[k]);}));assert.deepEqual(styles[0],styles[1]);
   assert(await status.evaluate(el=>el.previousElementSibling.classList.contains('project-status-image')));
   assert.equal(await avallow.locator('.project-status-image').innerText(),'');assert.equal(await avallow.locator('.project-status-image img').getAttribute('src'),patch.cover);
   for(const i of [0,1,3])assert.deepEqual(actual.boxes[i],prior.boxes[i],'Other card changed');
   const a=await sharp(prior.png).ensureAlpha().raw().toBuffer({resolveWithObject:true}),b=await sharp(actual.png).ensureAlpha().raw().toBuffer({resolveWithObject:true});assert.deepEqual(a.info,b.info,'Page dimensions changed');
   const box=actual.boxes[2];let outside=0;
   for(let y=0;y<a.info.height;y++)for(let x=0;x<a.info.width;x++){
    if(x>=Math.floor(box.x)-2&&x<=Math.ceil(box.x+box.width)+2&&y>=Math.floor(box.y)-2&&y<=Math.ceil(box.y+box.height)+2)continue;
    const i=(y*a.info.width+x)*4;if([0,1,2].some(c=>Math.abs(a.data[i+c]-b.data[i+c])>12))outside++;
   }
   assert.equal(outside,0,'Pixels outside AVALLOW changed');report.comparisons.push({width,changedPixelsOutsideAvallow:outside});
  }
  report.result='passed';report.historyPreserved=true;report.cmsPublication=true;await fs.writeFile(path.join(out,'report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
