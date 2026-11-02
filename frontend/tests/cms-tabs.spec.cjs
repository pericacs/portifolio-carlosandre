const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('node:fs/promises'),assert=require('node:assert/strict');
const base='http://127.0.0.1:8097';
(async()=>{
 const browser=await chromium.launch(),context=await browser.newContext(),page=await context.newPage(),checks=[];
 try{
  const credentials=JSON.parse(await fs.readFile('.private/visual-cms/credentials.json','utf8'));await page.goto(base+'/admin/login');await page.locator('[name=email]').fill(credentials.email);await page.locator('[name=password]').fill(credentials.password);await page.getByRole('button',{name:'Entrar no painel',exact:true}).click();await page.waitForURL(base+'/admin');
  const schema=await (await context.request.get(base+'/api/admin/cms/schema')).json(),editors=[];
  for(const module of Object.keys(schema)){const rows=(await (await context.request.get(base+'/api/admin/cms/'+module+'?limit=100')).json()).items;const first=rows[0];if(first)editors.push([module,first.id]);if(module==='projetos'){const smart=rows.find(x=>x.slug==='smartfamily');if(smart&&smart.id!==first?.id)editors.push([module,smart.id]);}}
  for(const [module,id] of editors)for(const width of [1440,768,720,390]){
   await page.setViewportSize({width,height:1000});await page.goto(base+'/admin/'+module+'/'+id,{waitUntil:'networkidle'});
   const buttons=page.locator('nav[aria-label="Abas do formulário"] button');
   for(let index=0;index<await buttons.count();index++){
    const label=await buttons.nth(index).innerText();await buttons.nth(index).click();
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),module+' '+label+' '+width+' overflow');
    const small=await page.locator('form').evaluateAll(nodes=>nodes.flatMap(n=>[...n.querySelectorAll('*')]).filter(e=>e.getClientRects().length&&[...e.childNodes].some(c=>c.nodeType===3&&c.textContent.trim())&&parseFloat(getComputedStyle(e).fontSize)<16).map(e=>e.textContent.slice(0,80)));
    assert.deepEqual(small,[],module+' '+label+' tiny text');checks.push({module,tab:label,width,minFont:16,overflow:false});
   }
  }
  await fs.writeFile('docs/screenshots/visual-cms/cms-tabs-report.json',JSON.stringify({result:'passed',checks},null,2));console.log('Passed '+checks.length+' CMS tab/width combinations');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
